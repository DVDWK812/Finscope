"""One-shot provider probe controls, using only authored metadata fixtures."""
from contextlib import closing
from datetime import datetime,timezone
import os,unittest
from finscope.api_sources import Article,QueryResult
from finscope.local_news import LocalNewsStore,NewsItem,ContentRights
from finscope.task_queue import TaskQueue
from finscope.media_reuters import probe,report

class ReutersProbeTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);TaskQueue(self.store)
    def test_requires_new_explicit_budget_no_dispatch(self):
        for kwargs in ({},{'confirmed':True},{'confirmed':True,'total_day_budget':1}):
            with self.assertRaises(ValueError):probe(self.store,fetch=lambda **k:self.fail('No unconfirmed request'),**kwargs)
        self.assertEqual(report(self.store),{})
    def test_exact_reuters_scope_primary_only_and_no_article_save(self):
        calls=[]
        def fetch(**kw):
            calls.append(kw);self.assertEqual(kw['marketaux_filters'].domains,('reuters.com',));self.assertFalse(kw['rights'].retain);self.assertFalse(kw['rights'].analyze)
            n=NewsItem.from_article(Article('marketaux','Authored fixture','https://www.reuters.com/authored-fixture','reuters.com','Authored only','2026-11-01T05:00:00+00:00','published'),ContentRights(True,False,False,False,'authored fixture'))
            return QueryResult('marketaux','technology','media_entity_filters','ok',[],raw_count=1,http_status=200,outcome='records'),[n]
        r=probe(self.store,confirmed=True,total_day_budget=1,reference='Authored account budget fixture',fetch=fetch)
        self.assertEqual(r['direct_reuters_links'],1);self.assertNotIn('title',r['observations'][0]);self.assertEqual(r['saved_articles'],0)
        again=probe(self.store,confirmed=True,total_day_budget=1,reference='Same bounded milestone',fetch=lambda **k:self.fail('No second query'))
        self.assertEqual(r,again);self.assertEqual(len(calls),1);self.assertFalse(self.store.list_news());self.assertFalse(self.store.list_analyses())
    def test_empty_200_is_not_reuters_coverage(self):
        def empty(**kw):return QueryResult('marketaux','technology','media_entity_filters','ok',[],http_status=200,outcome='empty'),[]
        r=probe(self.store,confirmed=True,total_day_budget=1,reference='Authored fixture',fetch=empty)
        self.assertEqual(r['http_status'],200);self.assertEqual(r['direct_reuters_links'],0);self.assertEqual(r['matched_preview_count'],0)
    def test_existing_day_budget_is_not_reused(self):
        now=datetime.now(timezone.utc).isoformat()
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_requests(id,provider,reserved_at,status,http_status) VALUES (?,?,?,?,?)',('already-used','marketaux',now,'ok',200));db.commit()
        with self.assertRaises(ValueError):probe(self.store,confirmed=True,total_day_budget=1,reference='Authored fixture',fetch=lambda **k:self.fail('No exhausted request'))
    def test_known_preflight_block_is_distinct_from_unknown_dispatch(self):
        def blocked(**kw):raise ValueError('Authored missing configuration')
        with self.assertRaises(ValueError):probe(self.store,confirmed=True,total_day_budget=1,reference='Authored fixture',fetch=blocked)
        self.assertEqual(report(self.store)['state'],'preflight_blocked')
