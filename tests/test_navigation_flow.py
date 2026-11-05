"""Local navigation, truthful progress and expiring view-cache regressions."""
from contextlib import closing
from dataclasses import replace
from datetime import timedelta
import json,os,unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from finscope.local_news import LocalNewsStore
from finscope.product_storage import ProductStorage
from finscope.task_queue import TaskQueue
from finscope.local_worker import Worker,ResourceBlocked
from finscope.text_processing import prepare
from test_batch import prediction,C
from test_source_policies import item as fixture

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class NavigationFlowTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store);self.data=ProductStorage(self.store)
        self.q.configure({**C,'limit':3})
        self.items=[self.data.save(prepare(replace(fixture(),url=fixture().url+str(i)))[0])[0] for i in range(3)]
        for mocker in (patch('requests.sessions.Session.request',side_effect=AssertionError('No view HTTP')),
                       patch('finscope.finbert_backend.LocalFinBERTBackend.from_snapshot',side_effect=AssertionError('No view model load'))):
            mocker.start();self.addCleanup(mocker.stop)
    def app(self,page=None):
        app=AppTest.from_file(str(APP),default_timeout=30)
        app.session_state['product_page']=page;app.run();self.assertFalse(app.exception);return app
    def worker(self,**kwargs):
        return Worker(self.store,fetch=lambda *a:self.fail('Offline job collected news'),infer=kwargs.get('infer',prediction),resources=kwargs.get('resources',lambda *a,**k:None))
    def submit(self):return self.q.submit_batch('analyze',C,confirmed=True,article_ids=[n.article_id for n in self.items])[0]
    def test_home_is_initial_and_always_accessible_with_integrated_guide(self):
        app=self.app();self.assertEqual(app.title[0].value,'Home')
        self.assertTrue(any(h.value=='How FinScope works' for h in app.subheader))
        self.assertNotIn('User Guide',app.radio(key='product_page').options)
        self.assertEqual(app.radio(key='product_page').options[0],'News Update')
        app.radio(key='product_page').set_value('Dashboard').run()
        app.button(key='home_navigation').click().run();self.assertEqual(app.title[0].value,'Home');self.assertIsNone(self.q.get())
    def test_update_operations_exist_only_on_news_update(self):
        app=self.app('News Update');self.assertTrue(any(b.key=='product_update' for b in app.button))
        self.assertTrue(any(b.key=='batch_analyze' for b in app.button))
        for page in ('Dashboard','Industries','Knowledge Graph','News Explorer','Settings'):
            app.radio(key='product_page').set_value(page).run();self.assertFalse(app.exception)
            self.assertFalse(any(b.key in {'product_update','batch_analyze','product_resume','product_cancel'} for b in app.button))
    def test_folded_configuration_keeps_actions_and_failure_reasons_accessible(self):
        identity=self.submit();self.q.update(identity,status='blocked',error='Authored permission review required')
        app=self.app('News Update')
        advanced=next(e for e in app.expander if e.label=='Advanced configuration')
        self.assertFalse(advanced.proto.expanded)
        advanced_buttons={b.key for b in advanced.get('button')}
        self.assertTrue({'batch_collect','batch_analyze','settings_save'}<=advanced_buttons)
        self.assertFalse({'product_update','offline_submit','product_resume','task_results'}&advanced_buttons)
        details=next(e for e in app.expander if e.label=='Task details')
        self.assertFalse(details.proto.expanded);self.assertFalse(details.get('warning'))
        self.assertTrue(any(w.value=='Authored permission review required' for w in app.warning))
        self.assertEqual(self.q.get()['id'],identity)
    def test_folded_counts_keep_model_revision_and_not_applicable_visible(self):
        item=self.items[0];origin=json.loads(item.provenance)
        origin.update(sentiment_eligible=False,ineligible_reason='Authored metadata only')
        # Saved content versions are immutable; a new authored revision carries
        # the not-applicable metadata into the current view.
        revised=prepare(replace(item,title='Authored metadata-only notice',provenance=json.dumps(origin)))[0]
        self.data.save(revised)
        app=self.app('Dashboard')
        coverage=next(e for e in app.expander if e.label=='Data coverage and counts')
        filters=next(e for e in app.expander if e.label=='Filters and model')
        self.assertFalse(coverage.proto.expanded);self.assertFalse(filters.proto.expanded)
        self.assertEqual(len(coverage.get('metric')),4)
        self.assertEqual(len(app.metric),8)
        self.assertTrue(any('1 Not applicable' in c.value for c in app.caption if c not in coverage.get('caption')))
        self.assertTrue(any(c.value.startswith('Results model:') for c in app.caption if c not in filters.get('caption')))
        self.assertNotIn('local_search',{w.key for w in filters.get('text_input')})
        self.assertEqual(app.text_input(key='local_search').value,'')
    def test_explicit_confirmation_one_job_and_task_results(self):
        app=self.app('News Update');self.assertTrue(app.button(key='offline_submit').disabled)
        app.checkbox(key='offline_confirm').check().run()
        self.assertFalse(app.button(key='offline_submit').disabled,str((app.checkbox(key='offline_confirm').value,app.multiselect(key='offline_articles').value,[x.value for x in app.info],self.q.get())))
        app.button(key='offline_submit').click().run()
        task=self.q.get();self.assertEqual(task['status'],'queued');self.assertEqual(task['snapshot']['sources'],[])
        self.assertEqual(task['counts']['total'],3)
        for page in ('Dashboard','News Explorer','Knowledge Graph','News Update'):
            app.radio(key='product_page').set_value(page).run();self.assertFalse(app.exception)
        self.assertTrue(app.button(key='offline_submit').disabled)
        app.button(key='product_cancel').click().run();self.assertFalse(app.exception)
        self.assertTrue(self.q.get()['cancel']);self.worker().run_one();app.run()
        self.assertEqual(self.q.get()['status'],'cancelled')
        app.button(key='product_resume').click().run();self.assertFalse(app.exception)
        self.assertEqual(self.q.get()['id'],task['id'])
        self.worker().run_one();app.run();self.assertEqual(self.q.get()['counts']['analyzed'],3)
        app.button(key='task_results').click().run();self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value,'News Explorer');self.assertTrue(app.session_state['explorer_task_scope'])
        self.assertEqual(len(self.data.task_results(self.q,self.q.get())),3)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_tasks').fetchone()[0],1)
    def test_page_filters_and_graph_perspective_survive_navigation_independently(self):
        app=self.app('Dashboard');app.text_input(key='local_search').set_value('First-page query').run()
        app.radio(key='product_page').set_value('News Explorer').run()
        self.assertEqual(app.text_input(key='local_search').value,'')
        app.text_input(key='local_search').set_value('Second-page query').run()
        app.radio(key='product_page').set_value('Knowledge Graph').run()
        app.radio(key='graph_perspective').set_value('Company').run()
        app.radio(key='product_page').set_value('Dashboard').run()
        self.assertEqual(app.text_input(key='local_search').value,'First-page query')
        app.radio(key='product_page').set_value('Knowledge Graph').run()
        self.assertEqual(app.radio(key='graph_perspective').value,'Company')
        app.radio(key='product_page').set_value('News Explorer').run()
        self.assertEqual(app.text_input(key='local_search').value,'Second-page query')
        app.button(key='reset_page_filters').click().run();self.assertEqual(app.text_input(key='local_search').value,'')
    def test_repeat_analysis_records_reuse_without_new_inference(self):
        self.submit();self.worker().run_one();self.submit()
        self.worker(infer=lambda *a:self.fail('Valid cache must not infer')).run_one()
        task=self.q.get();self.assertEqual(task['counts']['analyzed'],0);self.assertEqual(task['counts']['reused'],3)
        self.assertEqual(task['counts']['processed'],3);self.assertEqual(len(self.data.task_results(self.q,task)),3)
    def test_resume_keeps_this_tasks_new_results_distinct_from_prior_task_reuse(self):
        identity=self.submit();self.worker().run_one()
        self.q.update(identity,status='interrupted');self.q.resume(identity)
        self.worker(infer=lambda *a:self.fail('Resume inferred twice')).run_one()
        self.assertEqual(self.q.get()['counts']['analyzed'],3)
        self.assertEqual(self.q.get()['counts']['reused'],0)
        self.assertTrue(all(r['state']=='new' for r in self.q.outcomes(identity).values()))
    def test_pause_during_inference_saves_returned_result_before_stopping(self):
        identity=self.submit();calls=[]
        def infer(item,c):
            calls.append(item.article_id);self.q.cancel(identity);return prediction(item,c)
        self.worker(infer=infer).run_one()
        self.assertEqual(len(calls),1);self.assertEqual(self.q.get()['status'],'cancelled')
        self.assertEqual(len(self.data.task_results(self.q,self.q.get())),1)
    def test_pause_failure_and_resume_keep_holds_and_no_duplicate_results(self):
        identity=self.submit()
        def blocked(*a,**kw):raise ResourceBlocked('Authored low-memory pause')
        self.worker(resources=blocked).run_one();self.assertEqual(self.q.get()['status'],'blocked')
        self.q.resume(identity);self.worker().run_one();self.assertEqual(len(self.data.analyses()),3)
        # A fresh text version that fails must retain a failed dispatch fence.
        item=prepare(replace(self.items[0],summary='A changed authored operating loss.',content_version='',processed_text=''))[0]
        self.data.save(item);identity=self.submit()
        def fail(*a):raise ValueError('Authored output failure')
        self.worker(infer=fail).run_one();self.assertEqual(self.q.get()['status'],'partial_failed')
        self.q.resume(identity);self.worker(infer=lambda *a:self.fail('Failed dispatch replayed')).run_one()
        self.assertEqual(self.q.get()['status'],'partial_failed');self.assertEqual(len(self.data.analyses()),3)
    def test_known_total_and_unknown_total_status_are_distinct(self):
        from finscope.pipeline_ui import task_message
        identity=self.submit();app=self.app('News Update');self.assertEqual(len(app.get('progress')),1)
        for stage,label in [('collection preflight','Collecting'),('classification: saved originals','Classifying'),
                            ('sentiment: saved originals','Analyzing'),('loading: sentiment','Loading'),('saving: analysis result','Saving')]:
            self.q.update(identity,status='running',stage=stage)
            self.assertEqual(task_message(self.q.get())[0],label)
        self.q.update(identity,counts={});app.run();self.assertFalse(app.get('progress'))
        self.assertTrue(any('reliable total' in c.value for c in app.caption))
    def test_snapshot_reuses_only_unchanged_data_and_drops_changed_permissions(self):
        state={};a=self.data.view_snapshot(state,'US-BUSINESS-1')
        a['computed']['sentinel']='value'
        with patch.object(ProductStorage,'news',side_effect=AssertionError('Unchanged library rebuilt')):
            b=self.data.view_snapshot(state,'US-BUSINESS-1');self.assertIs(a,b)
        with closing(self.store.connect()) as db:
            original=json.loads(db.execute('SELECT payload FROM local_news WHERE id=?',(self.items[0].article_id,)).fetchone()[0])
            original['rights']['preview']=False
            db.execute('UPDATE local_news SET payload=? WHERE id=?',(json.dumps(original),self.items[0].article_id))
            # Simulate a stricter imported permission decision, including an
            # in-place update that counts/max timestamps alone cannot detect.
            db.execute('INSERT INTO local_permission_history VALUES (?,?,?,?)',
                       (self.items[0].article_id,'2026-11-05T00:00:00Z','{}',json.dumps(original['rights'])))
            db.commit()
        c=self.data.view_snapshot(state,'US-BUSINESS-1');self.assertIsNot(a,c)
        self.assertNotIn('sentinel',c['computed']);self.assertNotIn(self.items[0].article_id,{n.article_id for n in c['news']})
    def test_task_results_reject_changed_text_model_and_permission(self):
        self.submit();self.worker().run_one();task=self.q.get()
        self.assertEqual(len(self.data.task_results(self.q,task)),3)
        changed=prepare(replace(self.items[0],summary='Different fictional news.',content_version='',processed_text=''))[0]
        self.data.save(changed)
        self.assertNotIn(changed.article_id,self.data.task_results(self.q,task))
        self.store.update_rights(self.items[1].article_id,replace(self.items[1].rights,analyze=False))
        self.assertNotIn(self.items[1].article_id,self.data.task_results(self.q,task))
        # A receipt cannot point at a different model's cache, even for the same text.
        receipt=self.q.outcomes(task['id'])[self.items[2].article_id]
        self.q.record_outcome(task['id'],self.items[2],'reused',cache_key='different-model',analysis_id=receipt['analysis_id'])
        self.assertEqual(self.data.task_results(self.q,task),{})
    def test_cache_rechecks_model_revision_and_in_place_database_edit(self):
        state={};a=self.data.view_snapshot(state,'US-BUSINESS-1')
        with patch('finscope.batch_config.finbert_cache_key',return_value='new-pinned-revision'):
            self.assertIsNot(a,self.data.view_snapshot(state,'US-BUSINESS-1'))
        before=self.data.view_revision()
        with closing(self.store.connect()) as db:db.execute("UPDATE product_classifications SET cache_key='other'")
        # No classifications yet: a no-op update must not create a false data revision.
        self.assertEqual(before,self.data.view_revision())
    def test_progress_fragment_never_full_reruns_for_worker_stage_changes(self):
        import finscope.pipeline_ui as ui
        self.submit();app=self.app('News Update')
        self.q.update(self.q.get()['id'],status='running',stage='sentiment: saved originals')
        with patch.object(ui.st.raw,'rerun') as rerun:
            app.run();self.assertFalse(app.exception);rerun.assert_not_called()


class FiniteViewSnapshotTests(unittest.TestCase):
    from test_finite_media import FiniteMediaTests as Fixtures
    setUp=Fixtures.setUp
    scope=Fixtures.scope
    item=Fixtures.item
    def test_expiry_without_write_discards_snapshot_and_derived_content(self):
        self.data.save(self.item());state={}
        snapshot=self.data.view_snapshot(state,'US-BUSINESS-1');self.assertEqual(len(snapshot['news']),1)
        snapshot['computed']['private']='derived fictional content'
        self.now+=timedelta(days=8)
        after=self.data.view_snapshot(state,'US-BUSINESS-1')
        self.assertEqual(after['news'],[]);self.assertEqual(after['computed'],{})


if __name__=='__main__':unittest.main()
