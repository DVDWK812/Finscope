"""Authored offline fixtures; no provider quota, real articles or model dispatch."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json,os,unittest
from uuid import uuid4
from unittest.mock import patch
from finscope.local_news import LocalNewsStore,NewsItem,ContentRights,LocalIngestionService,Analysis
from finscope.task_queue import TaskQueue
from finscope.local_worker import Worker
from finscope.product_storage import ProductStorage
from finscope.expiring_media import partition,TEXT_TABLES
from finscope.media_use import apply
from finscope.media_watchlist import DEFAULT,plan,read,parse,format_rows
from finscope.media_quality import validation_type,batch_receipts,statistics
from finscope.publisher_attribution import attribution
from finscope.api_sources import HTTPResponse,normalize
from finscope.news_keys import NewsKeyRegistry
from finscope.text_processing import prepare


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc);self.start=self.now;self.calls=[]
        p=patch('finscope.media_use.utcnow',side_effect=lambda:self.now);p.start();self.addCleanup(p.stop)
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store);self.data=ProductStorage(self.store)
        registry=NewsKeyRegistry(self.store)
        for s in ('marketaux','finnhub'):registry.add(s,'Authored primary '+s,'AUTHORED-COVERAGE-KEY-'+s,primary=True)
    def scope(self,source):
        return dict(source=source,status='research_unverified',reference='Authored offline test content and private research fixture',fields=['title','summary'],
            expires_at=(self.start+timedelta(days=7)).isoformat(),confirmed=True,domains=['example.com'] if source=='marketaux' else [])
    def config(self,source='marketaux',groups=None):
        groups=groups or DEFAULT
        gets=len(groups) if source=='marketaux' else sum(len(r['symbols']) for r in groups)
        return dict(sources=[source],model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',limit=gets*3,
            media_batch=dict(source=source,scope=self.scope(source),batch_id=uuid4().hex,max_requests=gets,per_request=3,plan_limit=3,
                utc_day=self.now.date().isoformat(),total_day_budget=gets,symbol='',days=2,watchlist=groups))
    def item(self,source='finnhub',url='https://example.com/authored/same',summary='The fictional company supplies new computers to business customers.'):
        n=NewsItem('0'*32,source,'The authored company grows in revenue','Authored fixture',url,summary,
            self.start.isoformat(),'published',self.start.isoformat(),(),ContentRights())
        n=apply(n,self.scope(source));p=json.loads(n.provenance);p['capture_task_id']='authored-'+source
        return prepare(replace(n,provenance=json.dumps(p)))[0]
    def service(self,*,empty=False):
        def transport(url,params,*args):
            self.calls.append((url,params.copy()));self.now+=timedelta(seconds=61)
            if empty:return HTTPResponse({'data':[]} if 'marketaux' in url else [],200,{})
            syms=params.get('symbols',params.get('symbol'));page=params.get('page',1)
            rows=[dict(uuid=syms+'-'+str(page)+'-'+str(i),id=i,headline='The authored company grows in revenue '+str(i),
                title='The authored company grows in revenue '+str(i),url='https://example.com/authored/'+syms+'/'+str(page)+'/'+str(i),
                description='The fictional company supplies new computers to business customers.',summary='The fictional company supplies new computers to business customers.',
                source='Authored fixture',published_at=(self.start-timedelta(hours=1)).isoformat(),datetime=int(self.start.timestamp()),
                entities=[dict(symbol=syms.split(',')[0],name='Authored issuer',industry='Authored supplier industry',highlights=[{'highlight':'DO NOT RETAIN HIGHLIGHT'}])]) for i in range(3)]
            return HTTPResponse({'data':rows} if 'marketaux' in url else rows,200,{})
        return LocalIngestionService(self.store,transport=transport,clock=lambda:self.now)
    def run_collect(self,c,service,operation='collect'):
        with patch('finscope.local_news.LocalIngestionService',return_value=service),patch('finscope.media_batch.time.sleep',side_effect=lambda n:setattr(self,'now',self.now+timedelta(seconds=n))):
            task,_=self.q.submit_batch(operation,c,confirmed=True)
            Worker(self.store,infer=lambda *a:self.fail('Collection called a model')).run_one()
        return task
    def test_six_groups_are_real_distinct_bounded_requests_and_metadata_not_topics(self):
        c=self.config();task=self.run_collect(c,self.service())
        self.assertEqual(self.q.get(task)['status'],'completed');self.assertEqual(len(self.calls),6)
        self.assertEqual([x[1]['symbols'] for x in self.calls],[','.join(g['symbols']) for g in DEFAULT])
        self.assertEqual(len(self.data.news()),18);self.assertFalse(self.data.analyses())
        n=self.data.news()[0];p=json.loads(n.provenance)
        self.assertTrue(p['api_record']['record_id']);self.assertTrue(p['query_cohort']['symbols'])
        self.assertNotIn('DO NOT RETAIN HIGHLIGHT',n.provenance);self.assertFalse(n.issuer_industry)
        self.assertEqual(batch_receipts(self.store,task)['new'],18)
        with closing(self.store.connect()) as db:self.assertNotIn(n.title,'\n'.join(db.iterdump()))
    def test_broad_default_parameters_and_fixed_window_pagination(self):
        from finscope.api_sources import build_request,MarketauxFilters
        for filters in (None,MarketauxFilters()):
            params=build_request('marketaux','technology',self.now,7,3,'AUTHORED',marketaux_filters=filters)[1]
            self.assertFalse(set(params)&{'search','symbols','industries','domains','source_ids','must_have_entities'})
        c=self.config();c['limit']=50;d=c['media_batch'];d.pop('watchlist');d.update(mode='broad',max_requests=4,total_day_budget=4);d['scope']['domains']=[]
        def transport(url,p,*args):
            self.calls.append((url,p.copy()));self.now+=timedelta(seconds=61);page=p['page']
            rows=[dict(uuid=str(i),title='Authored broad headline '+str(i),description='Authored financial research description.',url='https://different.example/news/'+str(i),source='Authored publisher',published_at=self.start.isoformat()) for i in range((page-1)*3,min(page*3,5))]
            return HTTPResponse(dict(data=rows,meta=dict(found=5,returned=len(rows),limit=3,page=page)),200,{})
        service=LocalIngestionService(self.store,transport=transport,clock=lambda:self.now)
        task=self.run_collect(c,service)
        self.assertEqual(len(self.calls),2);self.assertEqual(len(self.data.news()),5)
        self.assertEqual(self.calls[0][1]['published_before'],self.calls[1][1]['published_before'])
        self.assertEqual(self.calls[0][1]['published_after'],self.calls[1][1]['published_after'])
        for _,p in self.calls:self.assertFalse(set(p)&{'search','symbols','industries','domains','source_ids','must_have_entities'})
        self.assertTrue(all('query_cohort' not in json.loads(n.provenance) for n in self.data.news()))
        self.assertEqual(batch_receipts(self.store,task)['normalized'],5)
        self.assertEqual(self.q.submit_batch('collect',c,confirmed=True),(task,False))
        self.assertFalse(self.data.analyses())
        # A supplier may repeat an earlier page despite correct page metadata.
        # Preserve those receipts, stop, and count the single incident once.
        def repeated(url,p,*args):
            response=transport(url,{**p,'page':1},*args)
            response.payload['meta'].update(page=p['page'],found=100)
            return response
        c['media_batch'].update(batch_id=uuid4().hex,total_day_budget=6)
        task=self.run_collect(c,LocalIngestionService(self.store,transport=repeated,clock=lambda:self.now))
        self.assertEqual(self.q.get(task)['status'],'partial_failed')
        self.assertEqual(self.q.get(task)['counts']['failed'],1)
        self.assertEqual(batch_receipts(self.store,task)['request_stages'],2)
        self.assertEqual(len(self.data.news()),5)
    def test_broad_cursor_is_separate_and_metadata_is_required(self):
        from finscope import media_broad
        from finscope.media_batch import validate
        c=self.config();d=c['media_batch']
        with self.assertRaises(ValueError):validate({**d,'mode':'broad'})
        d={**d,'mode':'broad'};d.pop('watchlist');d['scope']['domains']=[]
        self.assertEqual(media_broad.plan(self.store,d,self.now)['page'],1)
        self.assertFalse(media_broad.continuation({},3,1,3,3,3)[0])
        meta=dict(found=100,returned=3,limit=3,page=2)
        self.assertFalse(media_broad.continuation(meta,3,1,3,3,3)[0])
        meta['page']=1
        self.assertFalse(media_broad.continuation(meta,3,1,3,3,3,True)[0])
        query=media_broad.plan(self.store,d,self.now)
        media_broad.commit(self.store,d,query,dict(more=True,pagination_stop='More results within fixed window'))
        resumed=media_broad.plan(self.store,d,self.now+timedelta(days=1))
        self.assertEqual(resumed['page'],2);self.assertEqual(resumed['before'],query['before'])
        self.assertEqual(plan(self.store,{**d,'watchlist':DEFAULT},self.now)[0]['page'],1)
    def test_partial_window_resume_retains_bounds_page_and_no_repeat_same_batch(self):
        c=self.config(groups=DEFAULT[:1]);service=self.service();task=self.run_collect(c,service)
        options=c['media_batch'];next_query=plan(self.store,options,self.now+timedelta(days=1))[0]
        self.assertEqual(next_query['page'],2);self.assertLess(datetime.fromisoformat(next_query['before']),self.now)
        self.assertEqual(self.q.submit_batch('collect',c,confirmed=True),(task,False));self.assertEqual(len(self.calls),1)
        c['media_batch']={**options,'batch_id':uuid4().hex,'total_day_budget':2}
        self.run_collect(c,service)
        self.assertEqual(self.calls[-1][1]['page'],2)
        self.assertEqual(self.calls[0][1]['published_before'],self.calls[-1][1]['published_before'])
        self.assertEqual(len(self.data.news()),6)
    def test_finnhub_watchlist_has_one_request_per_ticker(self):
        c=self.config('finnhub',DEFAULT[:1]);self.run_collect(c,self.service())
        self.assertEqual([x[1]['symbol'] for x in self.calls],['MSFT','AAPL']);self.assertEqual(len(self.data.news()),6)
    def test_quota_expiry_and_utc_budget_never_renew_implicitly(self):
        c=self.config();c['media_batch']['total_day_budget']=1
        with self.assertRaises(ValueError):self.q.submit_batch('collect',c,confirmed=True)
        c=self.config();c['media_batch']['utc_day']='2000-01-01'
        with self.assertRaises(ValueError):self.q.submit_batch('collect',c,confirmed=True)
        self.assertFalse(self.calls)
    def test_failed_persistence_does_not_advance_watermark_or_retry_request(self):
        c=self.config(groups=DEFAULT[:2]);service=self.service()
        with patch('finscope.product_storage.ProductStorage.save',side_effect=ValueError('Authored disk failure')):
            task=self.run_collect(c,service)
        self.assertEqual(len(self.calls),1);self.assertEqual(read(self.store),{})
        self.q.resume(task)
        with patch('finscope.local_news.LocalIngestionService',return_value=service):Worker(self.store).run_one()
        self.assertEqual(len(self.calls),1)
    def test_cross_source_url_dedup_preserves_original_expiry_and_cached_content(self):
        original,_,_=self.data.save(self.item());before=partition(self.store)
        result=Analysis(uuid4().hex,original.article_id,'Positive','Mock only','Authored fixture','fixture',self.now.isoformat())
        self.data.analysis(original,'authored-cache',result)
        with closing(before.connect()) as db:old_rows={t:db.execute('SELECT * FROM '+t).fetchall() for t in ('local_news','product_content','media_lifetimes')}
        incoming=self.item('marketaux','https://example.com/authored/same?utm_source=authored#fixture')
        p=json.loads(incoming.provenance);p['media_use']['expires_at']=(self.start+timedelta(days=10)).isoformat()
        incoming=replace(incoming,provenance=json.dumps(p))
        same,fresh,changed=self.data.save(incoming)
        self.assertEqual(same.article_id,original.article_id);self.assertFalse(fresh or changed)
        self.assertEqual(self.data.cached(same,'authored-cache'),result.analysis_id)
        with closing(before.connect()) as db:
            for t,rows in old_rows.items():self.assertEqual(db.execute('SELECT * FROM '+t).fetchall(),rows)
            self.assertEqual(db.execute('SELECT count(*) FROM product_media_observations').fetchone()[0],2)
        self.assertEqual(len(self.data.news()),1)
        self.now+=timedelta(days=8);self.assertFalse(self.data.news())
        with closing(before.connect()) as db:
            for t in TEXT_TABLES:self.assertEqual(db.execute('SELECT count(*) FROM '+t).fetchone()[0],0,t)
    def test_same_event_on_different_publisher_urls_is_not_merged(self):
        self.data.save(self.item());self.data.save(self.item(url='https://other.example.org/authored/same'))
        self.assertEqual(len(self.data.news()),2)
    def test_supplier_metadata_and_redirect_domain_cannot_claim_original_publisher(self):
        n=self.item(url='https://finnhub.io/api/news?id=authored-fixture');p=json.loads(n.provenance);p['returned_source']='Yahoo';n=replace(n,source='Yahoo',provenance=json.dumps(p))
        a=attribution(n);self.assertEqual(a['supplier_reported_source'],'Yahoo');self.assertEqual(a['linked_publisher'],'Unverified')
        direct=attribution(replace(n,url='https://www.cnbc.com/'))
        self.assertEqual(direct['linked_publisher'],'CNBC');self.assertIn('Unverified',direct['editorial_originality'])
    def test_diagnostic_types_are_read_only_and_distinct_from_semantic_rejection(self):
        def response(out):return dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(out)))])
        self.assertEqual(validation_type(response(dict(labels=[],unclassified_reason='')),'Authored input'),'json_contract_invalid')
        self.assertEqual(validation_type(response(dict(labels=[dict(id='technology',quote='Invented',reason='Authored fixture reason')],unclassified_reason='')),'Authored input'),'evidence_mismatch')
        self.assertEqual(validation_type(response(dict(labels=[],unclassified_reason='macro_non_industry')),'Authored input'),'semantic_rejection')
        self.assertEqual(validation_type({'choices':[]},''),'json_or_envelope_invalid')
    def test_stats_separate_query_cohorts_supplier_entities_and_unclassified(self):
        self.run_collect(self.config(groups=DEFAULT[:1]),self.service());r=statistics(self.store)[0]
        self.assertEqual(r['records'],3);self.assertEqual(r['summaries'],3)
        self.assertEqual(r['classification_pending'],3);self.assertEqual(r['finbert'],0)
        self.assertEqual(r['query_symbols'],['AAPL','MSFT']);self.assertFalse(r['parent_topics'])
        self.assertEqual(r['linked_publisher'],'Unverified');self.assertEqual(r['basis_statuses'],{'research_unverified':3})
        n=self.data.news()[0];self.data.state(n,'failed','Classification evidence validation failed')
        self.assertEqual(statistics(self.store)[0]['sentiment_failed'],0)
        self.data.state(n,'failed','Model output failed; no sentiment label saved')
        self.assertEqual(statistics(self.store)[0]['sentiment_failed'],1)
    def test_watchlist_parser_rejects_duplicate_tickers_and_keeps_issuer_groups_separate(self):
        self.assertEqual(parse(format_rows(DEFAULT)),DEFAULT)
        with self.assertRaises(ValueError):parse('Authored group | MSFT\nOther group | MSFT')


if __name__=='__main__':unittest.main()
