import concurrent.futures
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from finscope.local_news import LocalNewsStore,NewsItem,ContentRights,Analysis
from finscope.task_queue import TaskQueue,Cancelled,ProcessLock
from finscope.product_storage import ProductStorage
from finscope.text_processing import prepare

CONFIG={'sources':['abs_html'],'model':'Local FinBERT','model_id':'','taxonomy':'US-BUSINESS-1','limit':3}


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'news.sqlite3';self.store=LocalNewsStore(self.path)
        self.item=NewsItem('original','authored_synthetic','Authored development headline','Fixture','https://example.invalid/report','The company reported a new semiconductor product.','','published','2026-10-30T01:00:00+00:00',(),ContentRights(True,True,True,False,'Authored offline fixture'))
    def test_backup_migration_legacy_rows_and_permissions_unchanged(self):
        self.store.save_news(self.item)
        with closing(self.store.connect()) as db:before=db.execute('SELECT * FROM local_news').fetchall()
        TaskQueue(self.store)
        backup=next((self.path.parent/'backups').glob('*before-product-v1*'))
        with closing(sqlite3.connect(backup)) as db:self.assertEqual(before,db.execute('SELECT * FROM local_news').fetchall())
        self.assertEqual(self.store.list_news(),[self.item])
        TaskQueue(self.store)
        self.assertEqual(len(list(backup.parent.glob('*'))),1)
    def test_concurrent_double_click_creates_exactly_one_task(self):
        q=TaskQueue(self.store)
        with concurrent.futures.ThreadPoolExecutor(8) as pool:results=list(pool.map(lambda _:q.submit(CONFIG),range(16)))
        self.assertEqual(len({r[0] for r in results}),1);self.assertEqual(sum(r[1] for r in results),1)
    def test_cancel_is_persistent_and_no_new_task_on_reads(self):
        q=TaskQueue(self.store);key,_=q.submit(CONFIG);q.cancel(key)
        with self.assertRaises(Cancelled):TaskQueue(self.store).check_cancel(key)
        for _ in range(10):self.assertEqual(q.get()['id'],key)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_tasks').fetchone()[0],1)
    def test_restart_requires_explicit_resume_preserves_steps(self):
        q=TaskQueue(self.store);key,_=q.submit(CONFIG);q.update(key,status='running')
        q.save_step(key,'fetch:abs_html','ok',[]);q.save_step(key,'infer:unknown','pending',{})
        q.interrupt_orphans();self.assertEqual(q.get()['status'],'interrupted')
        q.resume(key);self.assertEqual(q.step(key,'infer:unknown')[0],'pending');self.assertEqual(q.step(key,'fetch:abs_html')[0],'ok')
    def test_worker_process_lock_excludes_second_worker(self):
        with ProcessLock(str(self.path)+'.worker.lock'):
            with self.assertRaises(RuntimeError):
                with ProcessLock(str(self.path)+'.worker.lock'):pass
    def test_snapshot_rejects_secrets_external_endpoints_and_known_key_echo(self):
        q=TaskQueue(self.store)
        for addition in ({'api_key':'secret'},{'endpoint':'https://example.invalid'},{'model':'OpenAI API'}):
            with self.assertRaises(ValueError):q.submit({**CONFIG,**addition})
        with patch('finscope.api_sources.local_credentials',return_value={'KEY':'do-not-store-this-key'}):
            with self.assertRaises(ValueError):q.submit({**CONFIG,'model_id':'do-not-store-this-key'})
    def test_content_revisions_duplicate_urls_and_publisher_evidence(self):
        TaskQueue(self.store);data=ProductStorage(self.store)
        one,_=prepare(self.item);one,new,changed=data.save(one);self.assertTrue(new and changed)
        same,_=prepare(replace(self.item,url=self.item.url+'?utm_source=test'))
        two,new,changed=data.save(same);self.assertEqual(one.article_id,two.article_id);self.assertFalse(new or changed)
        revised,_=prepare(replace(self.item,summary='The company reported revised quarterly revenue.'))
        _,new,changed=data.save(revised);self.assertFalse(new);self.assertTrue(changed)
        independent,_=prepare(replace(self.item,source='Independent publisher'))
        data.save(independent);self.assertEqual(len(data.news()),2)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_content').fetchone()[0],3)
    def test_cache_and_analysis_commit_together_without_overwriting_history(self):
        TaskQueue(self.store);data=ProductStorage(self.store);item,_,_=data.save(prepare(self.item)[0])
        result=Analysis('v1',item.article_id,'Positive','Test','model','v1','2026-10-30T01:00:00+00:00')
        data.analysis(item,'model-v1',result);self.assertEqual(data.cached(item,'model-v1'),'v1');self.assertIsNone(data.cached(item,'model-v2'))
        data.analysis(item,'model-v2',replace(result,analysis_id='v2',revision='v2'))
        self.assertEqual(len(self.store.list_analyses()),2);self.assertEqual(len(data.news()),1)
    def test_configuration_persists_separately_from_ui_and_credentials(self):
        q=TaskQueue(self.store);q.configure(CONFIG)
        self.assertEqual(TaskQueue(self.store).config(),CONFIG)
        with closing(self.store.connect()) as db:self.assertNotIn('api_key',str(db.execute('SELECT * FROM product_settings').fetchall()))


if __name__=='__main__':unittest.main()
