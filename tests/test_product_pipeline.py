from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from finscope.local_news import Analysis,ContentRights,LocalNewsStore,NewsItem,FetchBlocked
from finscope.local_worker import Worker,ResourceBlocked
from finscope.task_queue import TaskQueue,Cancelled
from finscope.product_storage import ProductStorage
from finscope.text_processing import prepare,keywords
from finscope.industry_classifier import IndustryClassifier
from finscope.taxonomy import load_taxonomy

C={'sources':['abs_html'],'model':'Local FinBERT','model_id':'','taxonomy':'US-BUSINESS-1','limit':3}


def fixture(text='The company reported a new chip design and higher revenue.',number='1'):
    return NewsItem('dev'+number,'authored_synthetic','Authored development test','Fixture publisher','https://example.invalid/'+number,text,
                    '2026-10-30T01:00:00+00:00','published','2026-10-30T02:00:00+00:00',(),ContentRights(True,True,True,False,'Authored offline test'))


def prediction(item,c):
    return Analysis(uuid4().hex,item.article_id,'Positive','Mock only',c['model'],'mock','2026-10-30T03:00:00+00:00')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'data.sqlite3');self.q=TaskQueue(self.store)
    def worker(self,fetch=None,infer=None,resources=None):
        return Worker(self.store,fetch=fetch or (lambda *args:[fixture()]),infer=infer or prediction,resources=resources or (lambda *a,**k:None))
    def test_one_submit_completes_every_stage_no_intermediate_ui_action(self):
        key,_=self.q.submit(C);self.worker().run_one()
        self.assertEqual(self.q.get(key)['status'],'completed')
        self.assertEqual(self.q.get()['counts'],dict(new=1,duplicates=0,classified=1,analyzed=1,failed=0,skipped=0))
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.store.list_analyses()),1)
    def test_repeat_response_reuses_analysis_and_classification_but_retains_original(self):
        calls=[]
        w=self.worker(infer=lambda *args:(calls.append(1) or prediction(*args)))
        self.q.submit(C);w.run_one();self.q.submit(C);w.run_one()
        self.assertEqual(calls,[1]);self.assertEqual(len(self.store.list_news()),1)
        self.assertEqual(self.q.get()['counts']['duplicates'],1)
    def test_unknown_dispatch_is_not_reissued_after_restart_resume(self):
        key,_=self.q.submit(C);self.q.update(key,status='running');self.q.save_step(key,'fetch:abs_html','pending',{})
        self.q.interrupt_orphans();self.q.resume(key)
        calls=[];self.worker(fetch=lambda *a:calls.append(1)).run_one();self.assertEqual(calls,[])
        self.assertEqual(self.q.get()['status'],'blocked')
    def test_completed_fetch_and_analysis_do_not_repeat_on_resume(self):
        calls=[]
        w=self.worker(fetch=lambda *a:(calls.append('fetch') or [fixture()]),infer=lambda *a:(calls.append('infer') or prediction(*a)))
        key,_=self.q.submit(C);w.run_one();self.q.update(key,status='interrupted');self.q.resume(key);w.run_one()
        self.assertEqual(calls,['fetch','infer'])
    def test_cancel_after_inflight_result_prevents_next_article_model_call(self):
        calls=[];key,_=self.q.submit(C)
        def infer(item,c):calls.append(item.article_id);self.q.cancel(key);return prediction(item,c)
        self.worker(fetch=lambda *a:[fixture(number='1'),fixture(number='2')],infer=infer).run_one()
        self.assertEqual(len(calls),1);self.assertEqual(self.q.get()['status'],'cancelled');self.assertEqual(len(self.store.list_analyses()),1)
    def test_one_unlicensed_source_does_not_block_licensed_source(self):
        def fetch(source,*a):
            if source=='marketaux':raise FetchBlocked('Source rights missing')
            return [fixture()]
        self.q.submit({**C,'sources':['marketaux','abs_html']});self.worker(fetch=fetch).run_one()
        self.assertEqual(self.q.get()['status'],'partial_failed');self.assertEqual(len(self.store.list_analyses()),1)
    def test_restricted_text_not_saved_even_to_checkpoint_tables(self):
        self.q.submit(C);self.worker(fetch=lambda *a:[replace(fixture(),summary='Restricted marker private text',rights=ContentRights(True,False,False,False,'restricted'))]).run_one()
        with closing(self.store.connect()) as db:
            self.assertNotIn('Restricted marker private text',str(db.execute('SELECT * FROM product_steps').fetchall()))
        self.assertEqual(self.store.list_news(),[])
    def test_invalid_record_does_not_stop_other_records(self):
        self.q.submit(C);self.worker(fetch=lambda *a:[replace(fixture(),url='file:///private'),fixture(number='2')]).run_one()
        self.assertEqual(len(self.store.list_analyses()),1);self.assertEqual(self.q.get()['counts']['failed'],1)
    def test_non_english_not_processed_or_marked_neutral(self):
        self.q.submit(C);self.worker(fetch=lambda *a:[fixture('这是一条中文测试新闻，芯片设计公司发布新的产品。')]).run_one()
        self.assertEqual(self.store.list_analyses(),[]);self.assertEqual(self.q.get()['counts']['skipped'],1)
    def test_model_failure_retains_text_and_no_fabricated_neutral(self):
        def fail(*a):raise ValueError('Do not expose arbitrary model exception text')
        self.q.submit(C);self.worker(infer=fail).run_one()
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(self.store.list_analyses(),[])
        self.assertNotIn('arbitrary',self.q.get()['error'])
    def test_resource_preflight_prevents_network_and_keeps_results(self):
        calls=[]
        def resources(*a,**k):raise ResourceBlocked('RAM low')
        self.q.submit(C);self.worker(fetch=lambda *a:calls.append(1),resources=resources).run_one()
        self.assertEqual(calls,[]);self.assertEqual(self.q.get()['status'],'blocked')
    def test_body_summary_title_fallback_and_explicit_long_span(self):
        for basis,item in [('body',replace(fixture(),body='The body contains new information. '*150)),('summary',fixture()),('title',replace(fixture(),summary=''))]:
            n,p=prepare(item);self.assertEqual(n.text_basis,basis);self.assertLessEqual(len(n.analysis_text),1400)
            self.assertEqual(p['span_end'],len((n.body or n.summary or n.title)[:p['span_end']]))
            if basis=='body':self.assertLess(p['coverage'],1);self.assertGreater(len(n.body),len(n.analysis_text))
    def test_parent_dedup_storage_ai_and_macro_boundaries(self):
        classifier=IndustryClassifier()
        def ids(text):return {x['id'] for x in classifier.classify(prepare(fixture(text))[0])['labels']}
        self.assertIn('energy.midstream',ids('The company expanded oil storage and gas storage facilities.'))
        self.assertNotIn('technology.storage-devices',ids('The oil storage company increased revenue.'))
        labels=ids('The chip manufacturing company uses AI to inspect wafers.')
        self.assertIn('technology.foundry',labels);self.assertNotIn('technology.ai-apps',labels);self.assertNotIn('technology.foundation-models',labels)
        self.assertEqual(ids('The central bank changed its interest rate and monetary policy.'),set())
        labels=ids('The company makes DRAM memory chips and hard drives.')
        self.assertIn('technology.memory-chips',labels);self.assertIn('technology.storage-devices',labels)
        self.assertEqual(sum(x=='technology' for x in labels),1)
    def test_taxonomies_have_complete_legal_two_level_counts(self):
        us=load_taxonomy();cn=load_taxonomy('CSRC-JRT0020-2024')
        self.assertEqual(sum(n['parent_id'] is None for n in us['nodes']),11)
        self.assertEqual(sum(n['parent_id'] is not None for n in us['nodes']),56)
        self.assertEqual(sum(n['parent_id'] is None for n in cn['nodes']),19)
        self.assertEqual(sum(n['parent_id'] is not None for n in cn['nodes']),91)
        self.assertEqual([n['id'] for n in cn['nodes'] if n['parent_id']], [f'{i:02}' for i in range(1,92)])
        self.assertFalse(any(n['name_zh']=='科技' for n in cn['nodes']))
        self.assertEqual(next(n['name_zh'] for n in cn['nodes'] if n['id']=='05'),'农、林、牧、渔专业及辅助性活动')
    def test_word_weights_are_distinct_articles_not_rationale_or_repetition(self):
        one=replace(fixture(),body='large language models '*100)
        terms=keywords([one,fixture('The large language model provider grew.',number='2')],100)
        phrase=next(t for t in terms if t['term']=='large language model');self.assertEqual(phrase['count'],2)
        self.assertEqual(len(phrase['article_ids']),2)


if __name__=='__main__':unittest.main()
