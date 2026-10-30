"""One OS-locked worker with persistent checkpoints; never imports Streamlit."""
import argparse
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
import threading
import time
from uuid import uuid4

from .local_news import Analysis,ContentRights,FetchBlocked,LocalIngestionService,LocalNewsStore,utcnow
from .task_queue import TaskQueue,ProcessLock,Cancelled
from .product_storage import ProductStorage,decode
from .text_processing import prepare,VERSION


class ResourceBlocked(ValueError):pass


def resource_check(mode,*,loading=False):
    from .lmstudio_runtime import system_resources,GIB
    r=system_resources()
    # The loaded Qwen is left alone; never silently unload a user's model.
    required=5*GIB if mode=='Local FinBERT' and loading else 2*GIB
    if r['ram_available']<required:
        raise ResourceBlocked('Insufficient free RAM for this model stage; free resources or explicitly change/unload models in Settings, then resume')
    if mode=='Local LM Studio' and r['gpu_available']<512*1024**2:
        raise ResourceBlocked('Insufficient free VRAM; stage paused, no model was unloaded')
    return r


class Worker:
    def __init__(self,store,*,fetch=None,infer=None,resources=resource_check):
        self.store=store;self.queue=TaskQueue(store);self.data=ProductStorage(store)
        self.fetch_override=fetch;self.infer_override=infer;self.resources=resources;self.backend=None
    def fetch(self,source,c,check):
        if self.fetch_override:return self.fetch_override(source,c,check)
        from .local_collectors import SOURCES,collect_rba
        from .public_sources import collect_source
        service=LocalIngestionService(self.store)
        check()
        if source in {'abs_html','nist_rss','accc_rss'}:
            return collect_source(service,source,limit=c['limit'],explicit=True,check_cancel=check)[0]
        if source in {'rba_rss','rba_html'}:
            from . import rss_collector,html_collector
            module=rss_collector if source=='rba_rss' else html_collector
            rights=ContentRights(True,True,True,False,'RBA copyright policy: https://www.rba.gov.au/copyright/ ; official staff-authored text, no third-party material')
            def get(url):check();return module._get(url)
            return collect_rba(service,'rss' if source=='rba_rss' else 'html',rights,explicit=True,
                               collect=lambda **kw:module.collect_once(get=get,**kw))
        rights=ContentRights(**c.get('source_permissions',{}).get(source,{}))
        rights.require('preview');rights.require('retain');rights.require('analyze')
        budget=c.get('budgets',{}).get(source,{})
        if budget.get('utc_day')!=utcnow().date().isoformat():raise FetchBlocked('Current UTC-day quota attestation is missing or expired')
        from .local_credentials import credential
        key=credential(source)
        if not key:raise FetchBlocked('Project .env / Windows credential missing for '+source)
        # Remaining is an account attestation, not permission to repeat it forever.
        with closing(self.store.connect()) as db:
            used=db.execute('SELECT count(*) FROM local_requests WHERE provider=? AND substr(reserved_at,1,10)=?',(source,budget['utc_day'])).fetchone()[0]
        remaining=budget['remaining']-used
        if remaining<=0:raise FetchBlocked('Attested UTC-day request budget exhausted')
        result,items=service.fetch(source,budget['topic'],api_key=key,rights=rights,remaining=remaining,
                                   symbol=budget.get('symbol') or None,explicit=True)
        if result.status!='ok':raise FetchBlocked('Source request failed; protected provider ledger retained')
        return items[:c['limit']]
    def model_key(self,c):
        from .model_providers import INSTRUCTIONS
        prompt_version=hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()[:16]
        if c['model']=='Local FinBERT':
            from .model_assets import manifest
            m=manifest('finbert');return '|'.join((c['model'],m['model_id'],m['revision'],VERSION,'sentiment-v1'))
        if c['model']=='Local LM Studio':
            from .model_providers import LMStudioProvider,lmstudio_revision,ModelError
            models=LMStudioProvider().inventory();model=models.get(c.get('model_id'))
            if not model or not model['callable']:raise ResourceBlocked('Selected LM Studio model is not loaded/API exposed; explicitly load it in Settings')
            return '|'.join((c['model'],model['model_id'],lmstudio_revision(model),VERSION,'sentiment-v1',prompt_version))
        from .model_providers import OllamaProvider
        inventory=OllamaProvider().inventory()['models']
        if c.get('model_id') not in inventory:raise ResourceBlocked('Selected Ollama local model is unavailable; inspect Settings')
        return '|'.join((c['model'],c['model_id'],inventory[c['model_id']],VERSION,'sentiment-v1',prompt_version))
    def infer(self,item,c):
        if self.infer_override:return self.infer_override(item,c)
        if c['model']=='Local FinBERT':
            if self.backend is None:
                from .finbert_backend import LocalFinBERTBackend
                from .model_assets import model_directory
                self.backend=LocalFinBERTBackend.from_snapshot(model_directory('finbert'),accept_weight_license=True)
            started=time.perf_counter();scores=self.backend.predict([item.analysis_text])[0]
            label=max(scores,key=scores.get).capitalize()
            return Analysis(uuid4().hex,item.article_id,label,'FinBERT',self.backend.manifest['model_id'],self.backend.manifest['revision'],utcnow().isoformat(),
                            dict(scores),elapsed_ms=round((time.perf_counter()-started)*1000,2),provenance={'output_kind':'actual_local_inference'})
        from .model_providers import LMStudioProvider,OllamaProvider
        # Existing providers save results. Intercept that write only so the queue
        # can commit analysis+cache together, preserving their validations/rights.
        class Capture:
            def save_analysis(self,_):pass
        provider=LMStudioProvider() if c['model']=='Local LM Studio' else OllamaProvider()
        return provider.analyze(item,Capture(),model=c['model_id'])
    def run_one(self):
        task=self.queue.get()
        if not task or task['status']!='queued':return False
        identity=task['id'];c=task['snapshot'];counts=task['counts'];errors=[]
        self.queue.update(identity,status='running',stage='preflight')
        def check():self.queue.check_cancel(identity)
        def stage(name):check();self.queue.update(identity,stage=name,counts=counts)
        try:
            check();self.resources(c['model'],loading=self.backend is None)
            model_key=self.model_key(c) if not self.infer_override else c['model']+'|mock-test|'+VERSION
            from .industry_classifier import IndustryClassifier
            classifier=IndustryClassifier(c['taxonomy'],llm_model=c.get('model_id') if c.get('classifier_llm') else None)
            any_source=False
            for source in (['saved_originals'] if c.get('article_ids') else c['sources']):
                stage('fetch: '+source)
                key='fetch:'+source;step=self.queue.step(identity,key)
                if step:
                    if step[0]=='ok':items=[decode(json.dumps(row)) for row in step[1]]
                    else:
                        # Unknown dispatch, failed or skipped sources never auto resend.
                        errors.append(source+': '+step[1].get('reason','Previous source attempt requires review'));continue
                else:
                    # Mark before dispatch, so a killed worker cannot replay HTTP.
                    self.queue.save_step(identity,key,'pending',{'reason':'Source dispatch outcome unknown; no automatic resend'})
                    try:
                        fetched=([n for n in self.data.news() if n.article_id in c['article_ids']]
                                 if source=='saved_originals' else self.fetch(source,c,check));items=[]
                        for item in fetched:
                            if item.rights.preview and item.rights.retain and item.rights.analyze and item.rights.reference:
                                items.append(item)
                            else:
                                counts['skipped']+=1;errors.append(source+': text lacks source-level storage/NLP permission; skipped')
                        self.queue.save_step(identity,key,'ok',[__import__('dataclasses').asdict(i) for i in items])
                    except Cancelled:raise
                    except (FetchBlocked,ValueError):
                        import sys
                        error=sys.exception()
                        reason=str(error) if isinstance(error,FetchBlocked) else 'Source permission/configuration is missing or invalid'
                        self.queue.save_step(identity,key,'blocked',{'reason':reason});counts['skipped']+=1;errors.append(source+': '+reason);continue
                    except Exception:
                        self.queue.save_step(identity,key,'failed',{'reason':'Source failed; inspect persistent request state; no retry'})
                        counts['failed']+=1;errors.append(source+': source failure');continue
                any_source=True
                for raw in items:
                    stage('text / save: '+source)
                    try:
                        raw.rights.require('retain');raw.rights.require('analyze')
                        item,coverage=prepare(raw)
                        item,fresh,changed=self.data.save(item)
                    except ValueError:
                        counts['failed']+=1;errors.append('One text/URL record failed validation');continue
                    content_step='content:'+item.article_id+':'+item.content_version
                    if not self.queue.step(identity,content_step):
                        counts['new' if fresh else 'duplicates']+=1;self.queue.save_step(identity,content_step,'ok',{})
                    stage('classify: '+source)
                    if not self.data.classification(item,classifier.cache_key):
                        check()
                        if classifier.llm_model:self.resources(c['model'])
                        try:
                            classification=classifier.classify(item)
                            self.data.save_classification(item,classifier.cache_key,classification);counts['classified']+=1
                        except Exception:
                            counts['failed']+=1;errors.append('One classification failed ID/evidence validation; unknown retained')
                    stage('sentiment: '+source)
                    if self.data.cached(item,model_key) and not c.get('force_reanalysis'):continue
                    if item.language!='en':
                        errors.append('Non-English/unknown text has no verified language-adapted model in this configuration');counts['skipped']+=1;continue
                    infer_step='infer:'+item.article_id+':'+item.content_version+':'+hashlib.sha256(model_key.encode()).hexdigest()
                    if self.queue.step(identity,infer_step):
                        errors.append('Earlier inference outcome unknown/failed; explicit article reanalysis required');continue
                    self.resources(c['model'],loading=c['model']=='Local FinBERT' and self.backend is None);check()
                    self.queue.save_step(identity,infer_step,'pending',{})
                    try:
                        result=self.infer(item,c)
                        result=replace(result,provenance={**result.provenance,**coverage,'task_id':identity,'language':item.language})
                        self.data.analysis(item,model_key,result)
                        self.queue.save_step(identity,infer_step,'ok',{'analysis_id':result.analysis_id});counts['analyzed']+=1
                    except Exception:
                        self.queue.save_step(identity,infer_step,'failed',{'reason':'Model output/transport/token limit failed; no label saved, no automatic retry'})
                        counts['failed']+=1;errors.append('One model result failed validation/transport/token bounds')
                    self.queue.update(identity,counts=counts)
            self.queue.update(identity,status='partial_failed' if errors and any_source else 'blocked' if errors else 'completed',stage='finished',counts=counts,error='; '.join(dict.fromkeys(errors))[:1500])
        except Cancelled:
            self.queue.update(identity,status='cancelled',stage='cancelled',counts=counts,error='Stopped; completed stages retained; no further requests or inference')
        except ResourceBlocked as error:
            self.queue.update(identity,status='blocked',stage='resources / model',counts=counts,error=str(error))
        except Exception:
            self.queue.update(identity,status='partial_failed',stage='failed',counts=counts,error='Local processing failed; originals/history retained; inspect configuration, then explicit resume')
        return True


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--db',default='reports/finscope_local.sqlite3');parser.add_argument('--once',action='store_true');args=parser.parse_args(argv)
    store=LocalNewsStore(args.db)
    try:
        with ProcessLock(str(store.path)+'.worker.lock'):
            worker=Worker(store);worker.queue.interrupt_orphans()
            stop=threading.Event()
            def heartbeat():
                while not stop.is_set():worker.queue.heartbeat();stop.wait(2)
            pulse=threading.Thread(target=heartbeat,daemon=True);pulse.start()
            try:
                while True:
                    worker.run_one()
                    if args.once:break
                    stop.wait(.5)
            finally:stop.set();pulse.join(5)
    except RuntimeError:
        return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
