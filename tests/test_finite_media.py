"""Authored inputs only; verifies lifecycle and real transport boundaries offline."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json,os,sqlite3,unittest
from uuid import uuid4
from unittest.mock import patch
from finscope.local_news import LocalNewsStore,NewsItem,ContentRights,Analysis,LocalIngestionService
from finscope.task_queue import TaskQueue,validate_config
from finscope.product_storage import ProductStorage
from finscope.expiring_media import partition,TEXT_TABLES
from finscope.media_use import validate,apply,authorize,record_decision
from finscope.media_batch import preflight
from finscope.news_keys import NewsKeyRegistry
from finscope.local_worker import Worker,ResourceBlocked
from finscope.text_processing import prepare
from finscope.api_sources import HTTPResponse,build_request

MARKER='AuthoredFiniteTextUniqueMarker'


class FiniteMediaTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        guard=patch('finscope.media_use.utcnow',side_effect=lambda:self.now);guard.start();self.addCleanup(guard.stop)
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store);self.data=ProductStorage(self.store)
        self.registry=NewsKeyRegistry(self.store)
        self.registry.add('finnhub','Authored fixture primary','AUTHORED-FINNHUB-KEY',primary=True)
    def scope(self,**updates):
        return dict(source='finnhub',status='research_unverified',reference='Personal offline authored fixture; applicability unverified',
            fields=['title','summary'],expires_at=(self.now+timedelta(days=7)).isoformat(),confirmed=True,domains=[],**updates)
    def config(self,n=7):
        return dict(sources=['finnhub'],model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',limit=n,
            media_batch=dict(source='finnhub',scope=self.scope(),batch_id=uuid4().hex,max_requests=1,per_request=n,
                plan_limit=3,utc_day=self.now.date().isoformat(),total_day_budget=1,symbol='NVDA',days=2))
    def item(self):
        raw=NewsItem('0'*32,'finnhub',MARKER+' The semiconductor company invests in chip manufacturing',
            'Authored fixture','https://example.com/authored/one','The chipmaker has new revenue and profits.',
            self.now.isoformat(),'published',self.now.isoformat(),(),ContentRights())
        n=apply(raw,self.scope());origin=json.loads(n.provenance);origin['capture_task_id']='authored-capture'
        return prepare(replace(n,provenance=json.dumps(origin)))[0]
    def prediction(self,n,c):
        return Analysis(uuid4().hex,n.article_id,'Positive','Mock only','Authored fixture','fixture',self.now.isoformat(),rationale=MARKER)
    def service(self,body):
        self.calls=[]
        def transport(*args):self.calls.append(args);return HTTPResponse(body,200,{})
        return LocalIngestionService(self.store,transport=transport,clock=lambda:self.now)
    def response(self,n):
        return [dict(id=i,headline='The semiconductor company invests in chip manufacturing '+str(i),summary=MARKER+' The company has rising revenue and a new factory.',
                     source='Authored fixture',url='https://example.com/authored/'+str(i),datetime=int(self.now.timestamp())) for i in range(n)]
    def test_three_basis_states_and_known_restriction(self):
        n=self.item();e=authorize(n,('retain','local_sentiment'))
        self.assertEqual(e['basis_status'],'research_unverified');self.assertFalse(e['publisher_permission_independently_verified'])
        s=self.scope();s.update(source='rss:cnbc')
        with self.assertRaisesRegex(ValueError,'restriction'):validate(s)
        s.update(status='licensed',exception_reference='Authored source-specific fixture exception');validate(s)
        s.update(status='restricted')
        with self.assertRaisesRegex(ValueError,'restriction'):validate(s)
    def test_recorded_restriction_cannot_be_waived_by_research_checkbox(self):
        s=self.scope();s.update(status='restricted',reference='Authored identified restriction')
        record_decision(self.store,s)
        with self.assertRaises(ValueError):record_decision(self.store,self.scope())
        with self.assertRaises(ValueError):self.data.save(self.item())
    def test_expiry_removes_original_input_quotes_results_cache_and_disk_copies(self):
        n,_,_=self.data.save(self.item());self.data.state(n,'pending')
        self.data.save_classification(n,'fixture',dict(taxonomy='US-BUSINESS-1',labels=[],quote=MARKER))
        self.data.analysis(n,'fixture',self.prediction(n,{}))
        side=partition(self.store)
        self.assertIn(MARKER.encode(),side.path.read_bytes())
        self.now+=timedelta(days=8)
        self.assertEqual(self.data.news(),[]);self.assertEqual(self.data.analyses(),[])
        with closing(side.connect()) as db:
            for table in TEXT_TABLES:self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0,table)
        self.assertNotIn(MARKER.encode(),side.path.read_bytes())
        self.assertFalse(side.path.with_name(side.path.name+'-wal').exists())
        with self.assertRaises(ValueError):self.data.save(n)
        with self.assertRaises(ValueError):self.data.analysis(n,'fixture',self.prediction(n,{}))
    def test_finite_text_never_enters_permanent_queue_db_or_automatic_backup(self):
        n,_,_=self.data.save(self.item())
        with self.assertRaises(ValueError):self.q._enqueue(dict(sources=[],article_ids=[n.article_id]),preview_item=n)
        with closing(self.store.connect()) as db:
            self.assertNotIn(MARKER,'\n'.join(db.iterdump()))
            backup=self.store.path.parent/'permanent-backup.sqlite3'
            with closing(sqlite3.connect(backup)) as target:db.backup(target)
        self.assertNotIn(MARKER.encode(),backup.read_bytes())
        self.assertEqual(self.store.export()['news'],[])
    def test_restart_reads_and_offline_job_never_dispatches_news(self):
        n,_,_=self.data.save(self.item())
        reopened=LocalNewsStore(self.store.path);self.assertEqual(ProductStorage(reopened).news()[0].summary,n.summary)
        c=self.config();self.q.submit_batch('analyze',c,confirmed=True,article_ids=[n.article_id])
        w=Worker(reopened,fetch=lambda *a:self.fail('Offline job fetched news'),infer=self.prediction,resources=lambda *a,**k:None)
        w.run_one();self.assertEqual(self.q.get()['counts']['analyzed'],1)
        self.q.submit_batch('analyze',c,confirmed=True,article_ids=[n.article_id]);w.run_one()
        self.assertEqual(self.q.get()['counts']['analyzed'],0);self.assertEqual(len(self.data.analyses()),1)
    def test_one_finnhub_response_reuses_all_seven_not_groups_of_three(self):
        c=self.config();service=self.service(self.response(7))
        with patch('finscope.local_news.LocalIngestionService',return_value=service):
            first,_=self.q.submit_batch('collect',c,confirmed=True)
            w=Worker(self.store,infer=self.prediction,resources=lambda *a,**k:None);w.run_one()
            self.assertEqual(self.q.get()['status'],'completed')
            self.assertEqual(self.q.get()['counts']['new'],7);self.assertEqual(len(self.calls),1)
            self.assertEqual(self.q.submit_batch('collect',c,confirmed=True),(first,False))
            self.q.submit_batch('update',c,confirmed=True);w.run_one()
            self.assertEqual(self.q.get()['counts']['analyzed'],7);self.assertEqual(len(self.calls),1)
            self.assertEqual(len(self.data.news()),7);self.assertEqual(len(self.data.analyses()),7)
            with closing(self.store.connect()) as db:self.assertNotIn(MARKER,'\n'.join(db.iterdump()))
    def test_unknown_dispatch_is_not_repeated_on_resume(self):
        c=self.config();self.q.submit_batch('collect',c,confirmed=True)
        self.q.save_step(self.q.get()['id'],'media_request:1','pending',{'article_ids':[]})
        w=Worker(self.store,fetch=lambda *a:self.fail('Unknown dispatch repeated'));w.run_one()
        self.assertEqual(self.q.get()['status'],'partial_failed');self.q.resume(self.q.get()['id']);w.run_one()
        self.assertEqual(self.q.get()['status'],'partial_failed')
    def test_stop_after_response_is_cancelled_and_never_replays_dispatch(self):
        c=self.config();identity,_=self.q.submit_batch('collect',c,confirmed=True)
        def stop(*args):self.q.cancel(identity);return [self.item()]
        Worker(self.store,fetch=stop).run_one()
        self.assertEqual(self.q.get()['status'],'cancelled')
        self.q.resume(identity)
        Worker(self.store,fetch=lambda *a:self.fail('Cancelled dispatch replayed')).run_one()
        self.assertEqual(self.q.get()['status'],'partial_failed')
    def test_model_resource_failure_retains_text_for_later_offline_analysis(self):
        n,_,_=self.data.save(self.item());c=self.config()
        self.q.submit_batch('analyze',c,confirmed=True,article_ids=[n.article_id])
        def blocked(*a,**k):raise ResourceBlocked('Authored resource shortage')
        w=Worker(self.store,infer=self.prediction,resources=blocked);w.run_one()
        self.assertEqual(self.q.get()['status'],'blocked');self.assertEqual(len(self.data.news()),1)
        self.q.resume(self.q.get()['id']);w.resources=lambda *a,**k:None;w.run_one()
        self.assertEqual(len(self.data.analyses()),1)
    def test_cli_module_resource_exception_is_a_resource_pause(self):
        import runpy
        with __import__('warnings').catch_warnings():
            __import__('warnings').simplefilter('ignore',RuntimeWarning)
            entry=runpy.run_module('finscope.local_worker',run_name='worker_entry_fixture')
        n,_,_=self.data.save(self.item());self.q.submit_batch('analyze',self.config(),confirmed=True,article_ids=[n.article_id])
        def blocked(*args,**kwargs):raise entry['ResourceBlocked']('Authored entry-point RAM shortage')
        Worker(self.store,infer=self.prediction,resources=blocked).run_one()
        self.assertEqual(self.q.get()['status'],'blocked');self.assertEqual(len(self.data.news()),1)
        self.assertFalse(self.data.analyses())
    def test_budget_is_explicit_dated_and_cannot_be_renewed_implicitly(self):
        d=self.config()['media_batch'];preflight(self.store,d)
        d['utc_day']=(self.now-timedelta(days=1)).date().isoformat()
        with self.assertRaisesRegex(ValueError,'expired'):preflight(self.store,d)
        d=self.config()['media_batch'];d['total_day_budget']=0
        with self.assertRaises(ValueError):validate_config({**self.config(),'media_batch':d,'operation':'update'})
    def test_subscription_end_deletes_source_and_stale_objects_cannot_restore(self):
        n,_,_=self.data.save(self.item());self.data.analysis(n,'fixture',self.prediction(n,{}))
        self.assertEqual(partition(self.store).revoke('finnhub'),1)
        self.assertEqual(self.data.news(),[]);self.assertEqual(self.data.analyses(),[])
        with self.assertRaises(ValueError):self.data.save(n)
    def test_marketaux_free_cap_preserved_and_paid_parameter_is_explicit(self):
        _,p,*_=build_request('marketaux','technology',self.now,2,50,'AUTHORED')
        self.assertEqual(p['limit'],3)
        _,p,*_=build_request('marketaux','technology',self.now,2,30,'AUTHORED',marketaux_plan_limit=20,marketaux_page=2)
        self.assertEqual((p['limit'],p['page'],p['group_similar']),(20,2,'false'))
    def test_long_or_external_media_backend_cannot_be_selected(self):
        for mode in ('Local LM Studio','Local Ollama'):
            self.assertEqual(validate_config({**self.config(),'operation':'update','model':mode,'model_id':'installed'})['model'],mode)
        for change in (dict(model='OpenAI API'),dict(classifier_llm=True),dict(force_reanalysis=True)):
            with self.assertRaises(ValueError):validate_config({**self.config(),'operation':'update',**change})
    def test_explicit_safety_cap_can_exceed_three_without_changing_legacy_default(self):
        service=self.service([])
        end=(self.now-timedelta(minutes=5)).isoformat()
        rows=[(end,end,'ok',None)]*4
        with self.assertRaisesRegex(ValueError,'3 requests'):service._check_holds('finnhub',self.now,rows)
        service._check_holds('finnhub',self.now,rows,daily_cap=5)
    def test_expiry_during_inference_never_saves_late_result_or_neutral(self):
        n,_,_=self.data.save(self.item());c=self.config()
        self.q.submit_batch('analyze',c,confirmed=True,article_ids=[n.article_id])
        def late(n,c):
            self.now+=timedelta(days=8)
            return self.prediction(n,c)
        Worker(self.store,infer=late,resources=lambda *a,**k:None).run_one()
        self.assertFalse(self.data.analyses());self.assertFalse(self.data.news())
        self.assertEqual(self.q.get()['status'],'partial_failed')
    def test_finite_rss_is_stored_outside_permanent_index_and_promotable(self):
        from finscope.media_monitor import MediaMonitor
        from tests.test_media_monitor import GRANT,XML
        monitor=MediaMonitor(self.store,get=lambda *a:self.fail('Offline replay only'),clock=lambda:self.now)
        monitor.configure('ft',grant={**GRANT,'retention':'7 days','expires_at':self.scope()['expires_at'],
            'basis_status':'research_unverified'})
        from finscope.media_monitor import parse_feed
        rows,_=parse_feed(XML,'ft');monitor.replay('ft',rows)
        self.assertEqual(monitor.promote('ft')['duplicates'],1)
        self.assertEqual(len(monitor.index('ft')),1);self.assertIn('title',monitor.index('ft')[0])
        with closing(self.store.connect()) as db:
            raw='\n'.join(db.iterdump())
            self.assertNotIn(rows[0]['title'],raw);self.assertNotIn(rows[0]['summary'],raw)
        monitor.configure('ft',grant={**GRANT,'fields':[],'purposes':[]})
        self.assertFalse(self.data.news());self.assertFalse(self.data.classification_history(rows[0]['identity'][:32],'US-BUSINESS-1'))
    def test_earliest_expiry_cannot_be_extended_or_restored_by_either_old_capture(self):
        first=self.item();short=json.loads(first.provenance);short['media_use']['expires_at']=(self.now+timedelta(hours=1)).isoformat()
        first=replace(first,provenance=json.dumps(short));self.data.save(first)
        second=self.item();other=json.loads(second.provenance);other['capture_task_id']='second-authored-capture'
        second=replace(second,provenance=json.dumps(other));self.data.save(second)
        self.now+=timedelta(hours=2);self.assertFalse(self.data.news())
        for old in (first,second):
            with self.assertRaises(ValueError):self.data.save(old)
        fresh=self.item();origin=json.loads(fresh.provenance);origin['capture_task_id']='fresh-authorized-capture'
        fresh=replace(fresh,provenance=json.dumps(origin));self.data.save(fresh)
        self.assertEqual(partition(self.store).epoch(fresh),2)
        with self.assertRaises(ValueError):self.data.save(second)
        with self.assertRaises(ValueError):self.data.analysis(second,'fixture',self.prediction(second,{}))


if __name__=='__main__':unittest.main()
