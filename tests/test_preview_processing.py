"""Offline handoff checks, not real-news/provider/model acceptance evidence."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from finscope.local_news import Analysis, ContentRights, LocalNewsStore, NewsItem
from finscope.local_worker import Worker
from finscope.product_storage import ProductStorage
from finscope.task_queue import TaskQueue


RIGHTS=ContentRights(True,True,True,False,'Authored offline fixture; title and supplied summary')


def preview():
    return NewsItem('a'*32,'marketaux','The company develops a new semiconductor chip design',
        'Authored fixture publisher','https://example.invalid/preview',
        'The company reported higher revenue from its computer chip business.',
        '2026-10-31T01:00:00+00:00','published','2026-10-31T02:00:00+00:00',
        ('untrusted-preview-sector',),ContentRights(True,reference='Personal preview only'))


class PreviewProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'preview.sqlite3');self.q=TaskQueue(self.store)
        self.inferred=[]
    def submit(self,item=None,rights=RIGHTS,**kwargs):
        return self.q.submit_preview(item or preview(),rights,scope=kwargs.pop('scope','title_summary'),
                                     confirmed=kwargs.pop('confirmed',True),**kwargs)
    def worker(self):
        def infer(item,c):
            self.inferred.append((item,c))
            return Analysis(uuid4().hex,item.article_id,'Neutral','Mock only','offline','mock',
                            '2026-10-31T03:00:00+00:00')
        return Worker(self.store,fetch=lambda *a:self.fail('A retained preview must not fetch'),
                      infer=infer,resources=lambda *a,**k:None)
    def test_missing_permission_confirmation_or_invalid_scope_writes_no_job_or_text(self):
        cases=[dict(rights=replace(RIGHTS,retain=False)),dict(rights=replace(RIGHTS,analyze=False)),
               dict(rights=replace(RIGHTS,reference='')),dict(confirmed=False),dict(scope='publisher_body'),
               dict(item=replace(preview(),rights=ContentRights())),dict(item=replace(preview(),provider='newsdata'))]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):self.submit(**case)
        with closing(self.store.connect()) as db:
            for table in ('product_tasks','product_steps','local_news','local_requests'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
    def test_atomic_checkpoint_forces_finbert_despite_incomplete_external_model_draft(self):
        from finscope.settings_state import save,saved
        draft=dict(sources=['marketaux'],model='Local LM Studio',model_id='',taxonomy='US-BUSINESS-1',
                   limit=3,budgets={},source_permissions={})
        save(self.q,draft);before=saved(self.q)
        identity,created=self.submit();self.assertTrue(created)
        task=self.q.get(identity);c=task['snapshot']
        self.assertEqual(c['sources'],[]);self.assertEqual(c['budgets'],{})
        self.assertEqual(c['model'],'Local FinBERT');self.assertFalse(c['classifier_llm'])
        self.assertEqual(self.q.step(identity,'fetch:saved_originals')[0],'ok')
        self.assertEqual(saved(self.q),before)
        self.worker().run_one();self.assertEqual(self.q.get(identity)['status'],'completed')
        self.assertEqual(len(self.inferred),1)
        item=self.inferred[0][0];self.assertEqual((item.url,item.timestamp,item.source,item.fetched_at),
            (preview().url,preview().timestamp,preview().source,preview().fetched_at))
        result=self.store.list_analyses()[0]
        self.assertEqual(result.provenance['task_id'],identity)
        self.assertEqual(result.provenance['analysis_basis'],'summary')
        self.assertTrue(result.provenance['content_sha256'])
    def test_title_only_never_persists_or_classifies_excluded_summary_or_body(self):
        item=replace(preview(),summary='EXCLUDED_SUMMARY_123 healthcare',body='EXCLUDED_BODY_456',
                     processed_text='EXCLUDED_PROCESSED_789',content_version='old')
        self.submit(item,scope='title',rights=replace(RIGHTS,external=True));self.worker().run_one()
        retained=ProductStorage(self.store).news()[0]
        self.assertEqual(retained.summary,'');self.assertEqual(retained.body,'')
        self.assertEqual(retained.analysis_text,retained.title);self.assertFalse(retained.rights.external)
        self.assertEqual(retained.sectors,())
        with closing(self.store.connect()) as db:
            dump='\n'.join(db.iterdump())
        for text in ('EXCLUDED_SUMMARY_123','EXCLUDED_BODY_456','EXCLUDED_PROCESSED_789'):
            self.assertNotIn(text,dump)
        self.assertEqual(self.store.list_analyses()[0].provenance['analysis_basis'],'title')
    def test_repeated_preview_deduplicates_original_and_reuses_versioned_results(self):
        w=self.worker();self.submit();w.run_one();self.submit();w.run_one()
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.inferred),1)
        self.assertEqual(len(self.store.list_analyses()),1)
        self.assertEqual(self.q.get()['counts']['duplicates'],1)
        item=ProductStorage(self.store).news()[0]
        history=ProductStorage(self.store).classification_history(item.article_id,'US-BUSINESS-1')
        labels=history[0]['classification']['labels']
        self.assertTrue(any(x['parent_id'] for x in labels));self.assertTrue(all(x['evidence'] for x in labels))
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
    def test_existing_article_restriction_cannot_be_overridden_by_preview_grant(self):
        self.submit();self.worker().run_one();item=self.store.list_news()[0]
        self.store.update_rights(item.article_id,replace(RIGHTS,analyze=False))
        with self.assertRaises(ValueError):self.submit()
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM product_tasks').fetchone()[0],1)
    def test_checkpoint_failure_rolls_back_job_with_no_partial_saved_text(self):
        with closing(self.store.connect()) as db:
            db.execute("CREATE TRIGGER reject_checkpoint BEFORE INSERT ON product_steps BEGIN SELECT RAISE(ABORT,'test'); END")
            db.commit()
        with self.assertRaises(Exception):self.submit()
        self.assertIsNone(self.q.get());self.assertEqual(self.store.list_news(),[])
    def test_active_job_does_not_replace_checkpoint_or_submit_second_article(self):
        identity,_=self.submit();before=self.q.step(identity,'fetch:saved_originals')
        again,created=self.submit(replace(preview(),article_id='b'*32,url='https://example.invalid/second'))
        self.assertEqual(again,identity);self.assertFalse(created)
        self.assertEqual(self.q.step(identity,'fetch:saved_originals'),before)

    def test_ui_requires_selection_permissions_and_fresh_scope_confirmation(self):
        import os
        from streamlit.testing.v1 import AppTest
        os.environ['FINSCOPE_LOCAL_DB']=str(self.store.path)
        app=AppTest.from_string('''
import os
from finscope.local_news import LocalNewsStore
from finscope.news_source_ui import process_preview
from tests.test_preview_processing import preview
process_preview(LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']),'marketaux',[preview()])
''',default_timeout=20).run()
        def button():return next(b for b in app.button if b.label=='Analyze selected preview locally')
        def checkbox(label):return next(b for b in app.checkbox if b.label==label)
        self.assertFalse(app.exception);self.assertTrue(button().disabled);self.assertIsNone(self.q.get())
        app.selectbox[0].select(0).run()
        app.text_input[0].input('Authored fixture permission').run()
        checkbox('Permission covers local storage of the selected fields').check().run()
        checkbox('Permission covers local NLP of the selected fields').check().run()
        checkbox('I confirm this article and permitted text scope').check().run()
        self.assertFalse(button().disabled)
        app.radio[0].set_value('title_summary').run()
        self.assertFalse(checkbox('I confirm this article and permitted text scope').value)
        self.assertTrue(button().disabled)
        checkbox('I confirm this article and permitted text scope').check().run()
        button().click().run();self.assertFalse(app.exception)
        self.assertEqual(self.q.get()['snapshot']['sources'],[])
        self.assertEqual(self.q.get()['snapshot']['model'],'Local FinBERT')
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
        app.run();self.assertFalse(app.exception)
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM product_tasks').fetchone()[0],1)
