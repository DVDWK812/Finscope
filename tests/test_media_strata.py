"""Authored offline stratum plans and real queue/storage with mocked transport."""
from datetime import timedelta,datetime
import hashlib,json,unittest
from uuid import uuid4
from tests import test_media_coverage as coverage
from finscope.api_sources import HTTPResponse
from finscope.local_news import LocalIngestionService
from finscope import media_strata,media_broad
from finscope.media_batch import validate

class StrataTests(unittest.TestCase):
    setUp=coverage.CoverageTests.setUp
    scope=coverage.CoverageTests.scope
    run_collect=coverage.CoverageTests.run_collect
    def config(self):
        c=coverage.CoverageTests.config(self);d=c['media_batch'];d.pop('watchlist')
        d.update(mode='broad',strategy='stratified',max_requests=12,total_day_budget=12,days=1,window_end=(self.start-timedelta(hours=1)).isoformat())
        d['scope']['domains']=[];c['limit']=36
        return c
    def service(self):
        def transport(url,p,*args):
            self.calls.append(p.copy());self.now+=timedelta(seconds=61)
            self.assertFalse(set(p)&{'symbols','industries','search','domains','source_ids','must_have_entities'})
            token=hashlib.sha256(p['published_after'].encode()).hexdigest()[:12]
            rows=[]
            for i in range(3):
                identity='shared-boundary' if i==0 and p['page']==1 else token+'-'+str(p['page'])+'-'+str(i)
                rows.append(dict(uuid=identity,title='Authored financial disclosure '+identity,description='An invented supplier reports its operating results.',url='https://example.com/'+identity,source='Authored fixture',published_at=p['published_before']+'Z'))
            return HTTPResponse(dict(data=rows,meta=dict(page=p['page'],limit=3,returned=3,found=100)),200,{})
        return LocalIngestionService(self.store,transport=transport,clock=lambda:self.now)
    def test_plan_bounds_total_budget_and_unknown_dispatch_fence(self):
        d=self.config()['media_batch'];plan=media_strata.plan(self.store,d,self.start)
        self.assertEqual(len(plan),12);self.assertEqual([p['page'] for p in plan],[1]*6+[2]*6)
        for i,p in enumerate(plan[:6]):
            self.assertEqual(datetime.fromisoformat(p['logical_before'])-datetime.fromisoformat(p['logical_after']),timedelta(hours=4))
            self.assertEqual(datetime.fromisoformat(p['logical_after'])-datetime.fromisoformat(p['after']),timedelta(seconds=1))
            if i:self.assertEqual(plan[i-1]['logical_after'],p['logical_before'])
        with self.assertRaises(ValueError):validate({**d,'max_requests':13,'total_day_budget':13})
        with self.assertRaises(ValueError):validate({**d,'scope':{**d['scope'],'domains':['example.com']}})
        media_strata.record(self.store,plan[0],{'status':'pending','more':False},reserve=True)
        with self.assertRaises(ValueError):media_strata.record(self.store,plan[0],{},reserve=True)
        self.assertEqual(len(media_strata.plan(self.store,d,self.start)),10)
        self.assertFalse(media_broad.plan(self.store,d,self.start).get('blocked'))
    def test_twelve_gets_dedup_and_resume_window_pages_without_models(self):
        c=self.config();c['media_batch']['max_requests']=6
        task=self.run_collect(c,self.service())
        self.assertEqual(len(self.calls),6);self.assertEqual(len(self.data.news()),13)
        self.assertEqual([p['page'] for p in self.calls],[1]*6)
        old_ids={n.article_id for n in self.data.news()}
        c['media_batch']['batch_id']=uuid4().hex
        task2=self.run_collect(c,self.service())
        self.assertEqual(len(self.calls),12);self.assertEqual([p['page'] for p in self.calls[6:]],[2]*6)
        self.assertEqual(len(self.data.news()),31);self.assertFalse(self.data.analyses())
        selected=self.q.step(task2,'phase:collection')[1]['article_ids']
        self.assertFalse(set(selected)&old_ids)
        self.assertEqual(media_strata.plan(self.store,c['media_batch'],self.start),[])
        self.assertEqual(self.q.submit_batch('collect',c,confirmed=True),(task2,False))
        self.assertEqual(len(self.calls),12)
