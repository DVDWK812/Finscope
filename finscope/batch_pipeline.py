"""Two persistent phases. Collection never loads or probes a model."""
from contextlib import closing
from dataclasses import replace,asdict
import hashlib,json
from .local_news import FetchBlocked
from .task_queue import Cancelled
from .product_storage import decode
from .source_policies import authorize,POLICIES
from .batch_records import eligibility
from .text_processing import prepare


class BatchRunner:
    def __init__(self,worker):
        self.worker=worker;self.store=worker.store;self.queue=worker.queue;self.data=worker.data
    def run(self,task):
        from .local_worker import ResourceBlocked
        from .model_providers import ModelError
        identity=task['id'];c=task['snapshot'];counts=task['counts'];errors=[]
        def check():self.queue.check_cancel(identity)
        def stage(name):check();self.queue.update(identity,stage=name,counts=counts)
        def once(key,counter):
            if not self.queue.step(identity,key):
                counts[counter]+=1;self.queue.save_step(identity,key,'ok',{})
        self.queue.update(identity,status='running',stage='collection preflight')
        try:
            selected=[]
            def persist(raw):
                check()
                try:
                    raw=self.data.apply_permissions(raw)
                    raw=self.data.merge_available_text(raw)
                    policy=authorize(raw,('retain','local_display'))
                    origin=json.loads(raw.provenance);origin['automatic_use_policy']=policy
                    item,coverage=prepare(replace(raw,provenance=json.dumps(origin,ensure_ascii=False)))
                    item,fresh,changed=self.data.save(item,require_analysis=False)
                    once('batch_content:'+item.article_id+':'+item.content_version,'new' if fresh else 'duplicates')
                    eligible,reason=eligibility(item)
                    if (item.article_id,item.content_version) not in self.data.states():
                        self.data.state(item,'pending' if eligible else 'not_applicable',reason)
                    selected.append(item.article_id)
                except ValueError:
                    once('batch_rejected:'+raw.article_id,'skipped');errors.append('Record outside reviewed storage policy; not retained')
                self.queue.update(identity,counts=counts)
                return item.article_id if 'item' in locals() and item.article_id in selected else None
            collected=self.queue.step(identity,'phase:collection')
            if collected:
                selected=collected[1]['article_ids'];errors.extend(collected[1].get('errors',[]))
            elif c['operation']=='analyze':
                selected=c['article_ids']
                self.queue.save_step(identity,'phase:collection','ok',dict(article_ids=selected,network=False))
            elif c.get('media_batch'):
                from .media_batch import collect
                selected,media_errors=collect(self.worker,task,persist,check)
                errors.extend(media_errors)
                counts['failed']+=len(media_errors)
                self.queue.save_step(identity,'phase:collection','ok',dict(article_ids=selected,errors=errors))
            else:
                preview=self.queue.step(identity,'fetch:saved_originals')
                if preview:
                    for row in preview[1]:persist(decode(json.dumps(row)))
                else:
                    for source in c['sources']:
                        stage('collection: '+source)
                        if source not in POLICIES:
                            errors.append(source+': no reviewed automatic-use source policy; no fetch');counts['skipped']+=1;continue
                        key='batch_source:'+source;step=self.queue.step(identity,key)
                        if step:
                            selected.extend(step[1].get('article_ids',[]))
                            if step[0]!='ok':errors.append(source+': earlier source attempt requires review')
                            continue
                        start=len(selected)
                        # SEC has finer per-request durable checkpoints; it can
                        # resume successful company stages without dispatching again.
                        if source not in {'sec_press','sec_submissions'}:
                            self.queue.save_step(identity,key,'pending',{'article_ids':[]})
                        try:
                            if source in {'sec_press','sec_submissions'}:
                                from .sec_sources import SECCollector
                                collector=SECCollector(self.store,self.queue,identity,c.get('sec_options',{}),check)
                                collector.collect(source,c['limit'],on_items=lambda rows:[persist(n) for n in rows])
                                if collector.failures:
                                    errors.extend(collector.failures);counts['failed']+=len(collector.failures)
                            else:
                                for raw in self.worker.fetch(source,{**c,'limit':min(c['limit'],100 if source=='abs_archive' else 50)},check):persist(raw)
                                if source in self.worker.source_warnings:errors.append(source+': '+self.worker.source_warnings[source])
                            self.queue.save_step(identity,key,'ok',dict(article_ids=selected[start:]))
                        except Cancelled:raise
                        except Exception as error:
                            reason=str(error) if isinstance(error,FetchBlocked) else 'Collection failed; durable HTTP receipts retained; no retry'
                            errors.append(source+': '+reason);counts['failed']+=1
                            self.queue.save_step(identity,key,'failed',dict(article_ids=selected[start:],reason=reason))
                selected=list(dict.fromkeys(selected))
                self.queue.save_step(identity,'phase:collection','ok',dict(article_ids=selected,errors=errors))
            if c['operation']=='collect':
                self.queue.update(identity,status='partial_failed' if errors else 'completed',stage='collection saved; no model loaded',counts=counts,error='; '.join(dict.fromkeys(errors))[:1500]);return True
            from .industry_classifier import IndustryClassifier
            classifier=IndustryClassifier(c['taxonomy'],llm_model=c.get('model_id') if c.get('classifier_llm') else None)
            legacy_classifier=classifier
            semantic=None
            if c.get('classifier_options'):
                from .semantic_classifier import SemanticIndustryClassifier
                semantic=SemanticIndustryClassifier(self.store,c['classifier_options'],check=check)
            model_key=None
            for raw in self.data.news():
                if raw.article_id not in selected:continue
                from .media_use import scope_of
                classifier=semantic if semantic and scope_of(raw) else legacy_classifier
                stage('classification: saved originals')
                try:policy=authorize(raw,('retain','local_classification','local_sentiment','local_display'))
                except ValueError:
                    self.data.state(raw,'permission_required','No applicable local NLP policy or record permission')
                    once('batch_rights:'+raw.article_id+':'+raw.content_version,'skipped');continue
                item,coverage=prepare(raw)
                # Legacy originals may not yet have a normalized content revision.
                item,_,_=self.data.save(item)
                if not self.data.classification(item,classifier.cache_key):
                    try:
                        self.data.save_classification(item,classifier.cache_key,classifier.classify(item))
                        once('batch_class:'+item.article_id+':'+item.content_version+':'+c['taxonomy'],'classified')
                    except Cancelled:raise
                    except ModelError:
                        # Pre-dispatch model/resource prerequisites are resumable,
                        # not invalid evidence. Keep collection and prior caches.
                        self.data.state(item,'blocked','Local classifier prerequisite unavailable; saved text retained')
                        raise
                    except Exception:
                        self.data.state(item,'failed','Classification evidence validation failed');errors.append('Classification failed; original retained');counts['failed']+=1;continue
                current_classification=self.data.classification(item,classifier.cache_key)
                if current_classification and current_classification.get('status')=='failed':
                    once('batch_classifier_failed:'+item.article_id+':'+classifier.cache_key,'failed')
                    errors.append('Topic classifier failed; sentiment uses its independent text/model cache')
                eligible,reason=eligibility(item)
                if not eligible:
                    self.data.state(item,'not_applicable',reason);once('batch_na:'+item.article_id+':'+item.content_version,'skipped');continue
                if item.language!='en':
                    self.data.state(item,'not_applicable','No verified language-adapted model for this text');once('batch_language:'+item.article_id+':'+item.content_version,'skipped');continue
                if model_key is None:
                    model_key=(self.worker.model_key(c) if not self.worker.infer_override else c['model']+'|'+c.get('model_id','')+'|mock-test|'+__import__('finscope.text_processing',fromlist=['VERSION']).VERSION)
                if self.data.cached(item,model_key):
                    self.data.state(item,'completed','Cached current text/model result');continue
                stage('sentiment: saved originals')
                infer_key='batch_infer:'+item.article_id+':'+item.content_version+':'+hashlib.sha256(model_key.encode()).hexdigest()
                from .media_use import scope_of
                if scope_of(item):
                    from .expiring_media import partition
                    infer_key+=':finite-epoch:'+str(partition(self.store).epoch(item))
                with closing(self.store.connect()) as db:
                    previous=db.execute('SELECT status FROM product_steps WHERE step=? ORDER BY rowid DESC LIMIT 1',(infer_key,)).fetchone()
                if previous:
                    self.data.state(item,'blocked','Previous model dispatch failed/unknown; explicitly review individual reanalysis')
                    errors.append('Previous model dispatch needs review; not repeated');continue
                try:self.worker.resources(c['model'],loading=c['model']=='Local FinBERT' and self.worker.backend is None)
                except (ResourceBlocked,ModelError):
                    self.data.state(item,'blocked','Model resources unavailable; downloaded text retained for later offline analysis');raise
                check();self.queue.save_step(identity,infer_key,'pending',{})
                try:
                    result=self.worker.infer(item,c)
                    origin=json.loads(item.provenance)
                    extraction={k:origin[k] for k in ('input_text_type','extraction_version','document_characters','document_span_start','document_span_end','document_coverage','event_section') if k in origin}
                    result=replace(result,provenance={**result.provenance,**coverage,**extraction,'source_policy':policy,
                        'text_basis':'selected_'+item.text_basis+'_excerpt','task_id':identity,'language':item.language,
                        'input_fields':['title','body'] if item.body else ['title','summary'] if item.summary else ['title'],
                        'input_characters':len(item.analysis_text),'input_sha256':hashlib.sha256(item.analysis_text.encode()).hexdigest(),
                        'source_type':item.source_type,'document_type':item.document_type})
                    self.data.analysis(item,model_key,result)
                    self.queue.save_step(identity,infer_key,'ok',dict(analysis_id=result.analysis_id))
                    self.data.state(item,'completed');counts['analyzed']+=1
                except Exception:
                    self.queue.save_step(identity,infer_key,'failed',{'reason':'Model output failed validation/transport/token bounds'})
                    self.data.state(item,'failed','Model output failed; no sentiment label saved');errors.append('One model output failed; no automatic retry');counts['failed']+=1
                self.queue.update(identity,counts=counts)
            self.queue.save_step(identity,'phase:analysis','ok',dict(article_ids=selected))
            self.queue.update(identity,status='partial_failed' if errors else 'completed',stage='batch finished',counts=counts,error='; '.join(dict.fromkeys(errors))[:1500])
        except Cancelled:
            self.queue.update(identity,status='cancelled',stage='cancelled; saved stages retained',counts=counts)
        except (ResourceBlocked,ModelError) as error:
            from .local_worker import record_resource_pause
            record_resource_pause(self.queue,identity,counts,error)
            self.queue.update(identity,status='blocked',stage='analysis paused; collection retained',counts=counts,error=str(error))
        except Exception:
            self.queue.update(identity,status='partial_failed',stage='batch interrupted',counts=counts,error='Local batch failed; saved records/checkpoints retained; inspect and explicitly resume')
        return True
