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
    def selection_fixture(self):
        from finscope.batch_config import finbert_cache_key
        from finscope.industry_classifier import IndustryClassifier
        analyzed,failed,not_applicable=self.items
        self.data.analysis(analyzed,finbert_cache_key(),replace(prediction(analyzed,C),provenance={'content_sha256':analyzed.content_version}))
        self.data.save_classification(analyzed,IndustryClassifier().cache_key,{'taxonomy':'US-BUSINESS-1','status':'failed','labels':[]})
        self.data.state(failed,'failed','Authored model-output failure')
        origin=json.loads(not_applicable.provenance);origin['sentiment_eligible']=False
        not_applicable=prepare(replace(not_applicable,title='Authored metadata-only notice',provenance=json.dumps(origin),content_version='',processed_text=''))[0]
        self.data.save(not_applicable)
        return analyzed,failed,not_applicable
    def test_saved_record_shortcuts_use_current_failure_text_model_and_permissions(self):
        from finscope.pipeline_ui import offline_record_selection
        from finscope.batch_config import finbert_cache_key
        analyzed,failed,na=self.selection_fixture()
        select=lambda kind:offline_record_selection(self.data,C,kind)
        self.assertEqual(set(select('failed')),{analyzed.article_id,failed.article_id})
        self.assertEqual(select('unanalyzed'),[failed.article_id])
        with patch('finscope.batch_config.finbert_cache_key',return_value=finbert_cache_key()+'-changed-revision'):
            self.assertEqual(set(select('unanalyzed')),{analyzed.article_id,failed.article_id})
        revised=prepare(replace(analyzed,summary='A new fictional text version.',content_version='',processed_text=''))[0]
        self.data.save(revised)
        self.assertEqual(select('failed'),[failed.article_id])
        self.assertEqual(set(select('unanalyzed')),{analyzed.article_id,failed.article_id})
        self.store.update_rights(failed.article_id,replace(failed.rights,analyze=False))
        self.assertEqual(select('failed'),[]);self.assertEqual(select('unanalyzed'),[analyzed.article_id])
        self.assertIsNone(self.q.get())
    def test_selection_shortcuts_replace_chips_reset_consent_and_preserve_page_state(self):
        from finscope.ui_preferences import save
        analyzed,failed,na=self.selection_fixture()
        for locale in ('en','zh-CN'):
            with self.subTest(locale=locale):
                save(self.store,'ui_language',locale);suffix='' if locale=='en' else '__'+locale
                with patch('finscope.pipeline_ui.offline_record_selection',side_effect=AssertionError('Do not calculate groups on page load')):
                    app=self.app('News Update')
                app.checkbox(key='offline_confirm'+suffix).check().run()
                app.button(key='offline_select_failed').click().run();self.assertFalse(app.exception)
                self.assertEqual(set(app.multiselect(key='offline_articles'+suffix).value),{analyzed.article_id,failed.article_id})
                self.assertFalse(app.checkbox(key='offline_confirm'+suffix).value)
                app.checkbox(key='offline_confirm'+suffix).check().run()
                app.button(key='offline_select_unanalyzed').click().run();self.assertFalse(app.exception)
                self.assertEqual(app.multiselect(key='offline_articles'+suffix).value,[failed.article_id])
                self.assertTrue(app.button(key='offline_submit').disabled)
                app.radio(key='product_page'+suffix).set_value('Dashboard').run()
                app.radio(key='product_page'+suffix).set_value('News Update').run()
                self.assertEqual(app.multiselect(key='offline_articles'+suffix).value,[failed.article_id])
                with patch('finscope.pipeline_ui.offline_record_selection',return_value=[]):
                    app.button(key='offline_select_failed').click().run()
                self.assertEqual(app.multiselect(key='offline_articles'+suffix).value,[])
                with patch('finscope.pipeline_ui.offline_record_selection',side_effect=ValueError('Authored model unavailable')):
                    app.button(key='offline_select_unanalyzed').click().run()
                self.assertEqual(app.multiselect(key='offline_articles'+suffix).value,[])
                self.assertTrue(any('Authored model unavailable' in text.value for text in app.text))
                self.assertIsNone(self.q.get())
        self.submit();app=self.app('News Update')
        self.assertTrue(app.button(key='offline_select_failed').disabled)
        self.assertTrue(app.button(key='offline_select_unanalyzed').disabled)
    def test_unavailable_record_details_distinguish_source_policy_and_hide_revoked_text(self):
        authored=prepare(replace(fixture(),provider='authored_synthetic',url=fixture().url+'authored',
                                 title='Authored policy diagnostic fixture',provenance='{}'))[0]
        self.data.save(authored)
        revoked=self.items[0]
        with closing(self.store.connect()) as db:
            payload=json.loads(db.execute('SELECT payload FROM local_news WHERE id=?',(revoked.article_id,)).fetchone()[0])
            payload['rights']['preview']=False
            db.execute('UPDATE local_news SET payload=? WHERE id=?',(json.dumps(payload),revoked.article_id))
            db.execute('INSERT INTO local_permission_history VALUES (?,?,?,?)',
                       (revoked.article_id,'2026-11-05T00:00:00Z','{}',json.dumps(payload['rights'])));db.commit()
        app=self.app('News Update');details=next(e for e in app.expander if e.label=='Why records are unavailable')
        self.assertTrue(any(authored.title==v.value for v in details.get('text')))
        self.assertFalse(any(revoked.title==v.value for v in details.get('text')))
        self.assertTrue(any('No reviewed automatic-use policy' in v.value for v in details.get('caption')))
        self.assertFalse(any('have expired' in v.value for v in app.info))
        self.assertNotIn(authored.article_id,app.multiselect(key='offline_articles').options)
        self.assertIsNone(self.q.get())
    def test_classification_repair_needs_confirmation_and_only_submits_failed_ids(self):
        item=self.items[0]
        failures=[dict(article_id=item.article_id,reason='evidence_mismatch',can_repair=True,retried=False)]
        with patch('finscope.media_quality.failed_diagnostics',return_value=failures),patch.object(TaskQueue,'submit_reclassify',return_value=('fixture',True)) as submit:
            app=self.app('News Update')
            self.assertTrue(app.button(key='classifier_repair_submit').disabled);submit.assert_not_called()
            app.checkbox(key='classifier_repair_confirm').check().run()
            app.button(key='classifier_repair_submit').click().run();self.assertFalse(app.exception)
            submit.assert_called_once_with(article_ids=[item.article_id],confirmed=True,repair_failed=True)
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
    @patch('finscope.model_ui.sentiment_ready',return_value='mock-preflight')
    def test_explicit_confirmation_one_job_and_task_results(self,_ready):
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
    def test_selection_rechecks_finite_expiry_without_inference(self):
        from finscope.pipeline_ui import offline_record_selection
        item=self.item();self.data.save(item);self.data.state(item,'failed','Authored failure')
        with patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP')):
            self.assertEqual(offline_record_selection(self.data,C,'failed'),[item.article_id])
            self.assertEqual(offline_record_selection(self.data,C,'unanalyzed'),[item.article_id])
            self.now+=timedelta(days=8)
            self.assertEqual(offline_record_selection(self.data,C,'failed'),[])
            self.assertEqual(offline_record_selection(self.data,C,'unanalyzed'),[])
    def test_expiry_without_write_discards_snapshot_and_derived_content(self):
        self.data.save(self.item());state={}
        snapshot=self.data.view_snapshot(state,'US-BUSINESS-1');self.assertEqual(len(snapshot['news']),1)
        snapshot['computed']['private']='derived fictional content'
        self.now+=timedelta(days=8)
        after=self.data.view_snapshot(state,'US-BUSINESS-1')
        self.assertEqual(after['news'],[]);self.assertEqual(after['computed'],{})


if __name__=='__main__':unittest.main()


class SentimentSelectionTests(unittest.TestCase):
    setUp=NavigationFlowTests.setUp
    app=NavigationFlowTests.app
    submit=NavigationFlowTests.submit
    def test_saved_choice_overlays_scopes_without_rewriting_task_snapshot(self):
        from finscope.model_ui import save_sentiment,sentiment_config
        identity=self.submit()
        original=self.q.get(identity)['snapshot']
        save_sentiment(self.store,'Local LM Studio','downloaded-model')
        self.assertEqual(self.q.config()['model_id'],'downloaded-model')
        self.assertEqual(sentiment_config(self.store,{'classifier_options':{'model_key':'independent'}})['classifier_options'],{'model_key':'independent'})
        self.assertEqual(self.q.get(identity)['snapshot'],original)
        self.assertEqual(TaskQueue(self.store).config()['model_id'],'downloaded-model')
        save_sentiment(self.store,'Local FinBERT','')
        self.assertEqual(self.q.config()['model'],'Local FinBERT')

    def test_unloaded_models_are_blocked_without_inference(self):
        from finscope.model_ui import sentiment_ready
        with patch('finscope.model_ui.LMStudioProvider.inventory',return_value={'downloaded':{'loaded':False,'callable':False}}):
            with self.assertRaisesRegex(ValueError,'not ready'):
                sentiment_ready(self.store,{'model':'Local LM Studio','model_id':'downloaded'})
        with patch('finscope.model_ui.OllamaProvider') as provider:
            provider.return_value.inventory.return_value={'models':{'installed':'abc'}}
            provider.return_value.transport.return_value={'models':[]}
            with self.assertRaisesRegex(ValueError,'not ready'):
                sentiment_ready(self.store,{'model':'Local Ollama','model_id':'installed'})
            self.assertEqual(provider.return_value.transport.call_args.args[0],'GET')
            provider.return_value.analyze.assert_not_called()

    def test_selecting_provider_persists_and_does_not_submit(self):
        app=self.app('News Update')
        app.selectbox(key='offline_sentiment').set_value('Local Ollama').run()
        self.assertFalse(app.exception)
        self.assertEqual(self.q.config()['model'],'Local Ollama')
        self.assertIsNone(self.q.get())
        app.radio(key='product_page').set_value('Dashboard').run()
        app.radio(key='product_page').set_value('News Update').run()
        self.assertEqual(app.selectbox(key='offline_sentiment').value,'Local Ollama')
        self.assertFalse(app.exception)

    def test_version_change_blocks_and_classifier_choice_survives(self):
        from finscope.settings_state import save_sentiment,sentiment_config
        original={**C,'model':'Local LM Studio','model_id':'classifier-original','classifier_llm':True}
        save_sentiment(self.store,'Local Ollama','sentiment-other')
        result=sentiment_config(self.store,original)
        self.assertEqual(result['classifier_model_id'],'classifier-original')
        self.assertEqual(result['model_id'],'sentiment-other')
        with patch.object(Worker,'_model_key',return_value='new-revision'):
            with self.assertRaisesRegex(ResourceBlocked,'version changed'):
                Worker(self.store).model_key({'sentiment_model_key':'old-revision'})

    def test_new_controls_in_both_languages_and_themes(self):
        from finscope.ui_preferences import save
        from finscope.model_ui import save_sentiment
        from finscope.model_discovery import Discovery
        fake=Discovery();fake.publish({'fixture-local':{'loaded':False,'callable':False}})
        for locale in ('en','zh-CN'):
            for theme in ('dark','light'):
                save(self.store,'ui_language',locale);save(self.store,'ui_theme',theme)
                save_sentiment(self.store,'Local LM Studio','fixture-local')
                with patch('finscope.model_discovery.discovery',fake):
                    app=self.app('News Update')
                    key='offline_installed'+('__zh-CN' if locale=='zh-CN' else '')
                    self.assertEqual(app.selectbox(key=key).value,'fixture-local')
                    self.assertTrue(any('not ready' in str(v.value) or '尚未就绪' in str(v.value) for v in app.info))
                    self.assertIsNone(self.q.get())

    def test_ollama_unloaded_after_submission_never_dispatches_inference(self):
        from finscope.model_providers import OllamaProvider,ModelError
        from unittest.mock import Mock
        transport=Mock(return_value={'models':[]})
        provider=OllamaProvider(transport=transport)
        with patch.object(provider,'installed_models',return_value={'installed':'digest'}):
            with self.assertRaisesRegex(ModelError,'no longer loaded'):
                provider.analyze(self.items[0],self.store,model='installed',require_loaded=True)
        self.assertEqual([call.args[0] for call in transport.call_args_list],['GET'])
