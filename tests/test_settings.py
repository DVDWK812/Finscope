from contextlib import closing
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.settings_state import editable,save,saved
from test_product_pipeline import C

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'news.sqlite3');self.q=TaskQueue(self.store);self.q.configure(C)
        self.store.set_setting('guide_completed',True)
        env=patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)});env.start();self.addCleanup(env.stop)
        guard=patch('requests.sessions.Session.request',side_effect=AssertionError('Settings must not perform implicit HTTP'))
        self.http=guard.start();self.addCleanup(guard.stop)
        vault=patch('finscope.local_credentials.vault_key',return_value='')
        self.vault=vault.start();self.addCleanup(vault.stop)
    def app(self):
        app=AppTest.from_file(str(APP),default_timeout=20);app.session_state['product_page']='Settings';app.run()
        self.assertFalse(app.exception);return app
    def test_three_tabs_single_language_editor_and_no_nested_help_page(self):
        app=self.app()
        self.assertEqual([x.label for x in app.tabs],['General','News sources','Analysis models'])
        self.assertEqual(sum(s.key=='ui_language_choice' for s in app.selectbox),1)
        self.assertFalse(any(h.value=='Settings / Help' for h in app.title))
        self.assertEqual([x.label for x in app.expander],['Advanced & diagnostics'])
        self.assertFalse(any(x.key.startswith('settings_secret_') for x in app.text_input))
    def test_complete_offline_model_can_save_without_connection_load_or_jobs(self):
        config={**editable(self.q),'model':'Local LM Studio','model_id':'installed/actual-id'}
        self.assertEqual(save(self.q,config),[])
        self.assertEqual(self.q.config()['model_id'],'installed/actual-id');self.assertIsNone(saved(self.q))
        self.assertIsNone(self.q.get());self.http.assert_not_called()
    def test_incomplete_draft_preserves_active_pipeline_and_cannot_submit_even_explicitly(self):
        config={**editable(self.q),'sources':[],'model':'Local LM Studio','model_id':''}
        pending=save(self.q,config);self.assertTrue(pending)
        self.assertEqual(self.q.config(),C);self.assertEqual(saved(self.q),config)
        for c in (None,C):
            with self.assertRaisesRegex(ValueError,'draft'):self.q.submit(c)
        self.assertIsNone(self.q.get())
        save(self.q,editable(self.q)|{'sources':['abs_html'],'model':'Local FinBERT'})
        self.assertIsNone(saved(self.q));self.assertIsNone(self.q.get())
    def test_invalid_secret_and_unknown_fields_never_enter_draft(self):
        for extra in ({'api_key':'unit-secret'},{'model_id':'unit-secret'},{'sources':None}):
            with patch('finscope.api_sources.local_credentials',return_value={'DEEPSEEK_API_KEY':'unit-secret'}),self.assertRaises(ValueError):
                save(self.q,{**editable(self.q),**extra})
        self.assertIsNone(saved(self.q));self.assertEqual(self.q.config(),C)
    def test_current_source_only_fields_and_key_input_requires_edit(self):
        app=self.app();app.multiselect(key='settings_sources').set_value(['marketaux','finnhub']).run()
        app.button(key='settings_edit_marketaux').click().run()
        self.assertFalse(any(x.key=='settings_ticker' for x in app.text_input))
        self.assertFalse(any(x.key.startswith('settings_secret_') for x in app.text_input))
        app.button(key='settings_secret_marketaux_edit').click().run()
        self.assertEqual([x.key for x in app.text_input if x.key.startswith('settings_secret_')],['settings_secret_marketaux'])
        self.assertEqual(app.text_input(key='settings_secret_marketaux').proto.type,1)
        app.button(key='settings_edit_finnhub').click().run()
        self.assertTrue(any(x.key=='settings_ticker' for x in app.text_input))
        self.assertFalse(any(x.key=='settings_secret_marketaux' for x in app.text_input))
        self.http.assert_not_called()
    def test_language_change_and_failed_refresh_keep_unsaved_values_and_model_id(self):
        self.q.configure({**C,'model':'Local LM Studio','model_id':'installed/actual-id'})
        app=self.app();app.number_input(key='settings_limit').set_value(9).run()
        app.selectbox(key='ui_language_choice').set_value('zh-CN').run();app.button(key='ui_language_save').click().run()
        with patch('finscope.model_ui.LMStudioProvider.inventory',side_effect=ValueError('unused')):
            # Model failure is handled using the existing typed provider error.
            from finscope.model_providers import ModelError
            with patch('finscope.model_ui.LMStudioProvider.inventory',side_effect=ModelError('Offline')):
                app.button(key='pipeline_lmstudio_refresh').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='settings_limit__zh-CN').value,9)
        self.assertEqual(app.selectbox(key='pipeline_lmstudio_model__zh-CN').value,'installed/actual-id')
        self.assertEqual(self.q.config()['limit'],3);self.assertIsNone(self.q.get())
    def test_key_save_clears_password_and_has_no_sql_or_request_side_effect(self):
        app=self.app();app.multiselect(key='settings_sources').set_value(['marketaux']).run()
        app.button(key='settings_edit_marketaux').click().run();app.button(key='settings_secret_marketaux_edit').click().run()
        app.text_input(key='news_keys_marketaux_new_name').set_value('Authored main').run()
        app.text_input(key='settings_secret_marketaux').set_value('UNIT-KEY-ONLY').run()
        app.button(key='settings_secret_marketaux_save').click().run()
        from finscope.news_keys import NewsKeyRegistry
        self.assertEqual(NewsKeyRegistry(self.store).resolve('marketaux'),'UNIT-KEY-ONLY')
        self.assertFalse(any(x.key=='settings_secret_marketaux' for x in app.text_input))
        self.assertNotIn('settings_secret_marketaux',app.session_state)
        self.assertNotIn('UNIT-KEY-ONLY',str(app.session_state['_ui_mirrors']))
        self.assertNotIn(b'UNIT-KEY-ONLY',self.store.path.read_bytes());self.assertEqual(self.q.config(),C)
        self.http.assert_not_called()


if __name__=='__main__':unittest.main()
