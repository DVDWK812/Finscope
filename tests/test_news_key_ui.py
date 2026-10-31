from contextlib import closing
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.news_keys import NewsKeyRegistry
from finscope.local_credentials import credential_store
from finscope.ui_preferences import save,load
from finscope.news_readiness import key_metadata,verify_api
from finscope.settings_state import editable
from finscope.api_sources import HTTPResponse
from finscope.local_news import LocalIngestionService
from datetime import datetime,timezone
from copy import deepcopy
from test_product_pipeline import C

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


def widget(app,kind,key):
    return next(x for x in getattr(app,kind) if x.key in (key,key+'__en',key+'__zh-CN'))


class NewsKeyUITests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store)
        self.q.configure({**C,'sources':['marketaux','finnhub','newsdata']});self.store.set_setting('guide_completed',True)
        self.registry=NewsKeyRegistry(self.store)
        for p in (patch('requests.sessions.Session.request',side_effect=AssertionError('No API requests')),
                  patch('finscope.windows_credentials.c.WinDLL',create=True,side_effect=AssertionError('No native credentials'))):
            p.start();self.addCleanup(p.stop)
    def app(self):
        app=AppTest.from_file(str(APP),default_timeout=20);app.session_state['product_page']='Settings';app.run()
        self.assertFalse(app.exception);return app
    def source(self,app,p):widget(app,'button','settings_edit_'+p).click().run()
    def action(self,app,p,slot,choice):
        widget(app,'selectbox','news_keys_'+p+'_selected').set_value(slot).run()
        widget(app,'selectbox','news_keys_'+p+'_action_'+slot).set_value(choice).run()
    def add(self,app,p,name,value,primary):
        widget(app,'button','settings_secret_'+p+'_edit').click().run()
        widget(app,'text_input','news_keys_'+p+'_new_name').set_value(name).run()
        widget(app,'text_input','settings_secret_'+p).set_value(value).run()
        widget(app,'checkbox','news_keys_'+p+'_new_primary').set_value(primary).run()
        widget(app,'button','settings_secret_'+p+'_save').click().run();self.assertFalse(app.exception)
    def test_three_sources_share_compact_editor_and_all_key_operations_are_offline(self):
        app=self.app()
        for p in ('marketaux','finnhub','newsdata'):
            with self.subTest(provider=p):
                self.source(app,p);self.add(app,p,'Main','AUTHORED-'+p+'-MAIN',True)
                first=self.registry.selection(p)['slot_id']
                self.add(app,p,'Backup','AUTHORED-'+p+'-BACKUP',False)
                rows=self.registry.rows(p);second=next(r['slot_id'] for r in rows if r['slot_id']!=first)
                self.assertEqual(sum(r['is_primary'] for r in rows),1)
                self.action(app,p,second,'Make primary')
                widget(app,'button','news_keys_'+p+'_primary_'+second).click().run()
                self.assertEqual(self.registry.selection(p)['slot_id'],second)
                self.action(app,p,second,'Replace key');widget(app,'button','news_keys_'+p+'_replace_'+second).click().run()
                self.assertEqual(sum(t.proto.type==1 for t in app.text_input),1)
                widget(app,'text_input','settings_secret_'+p).set_value('AUTHORED-'+p+'-NEW').run()
                widget(app,'button','settings_secret_'+p+'_save').click().run()
                self.assertEqual(self.registry.resolve(p),'AUTHORED-'+p+'-NEW')
                self.action(app,p,second,'Disable key');widget(app,'checkbox','news_keys_'+p+'_availability_confirm_'+second).check().run()
                widget(app,'button','news_keys_'+p+'_enabled_'+second).click().run()
                self.assertIsNone(self.registry.selection(p))
                self.action(app,p,second,'Enable key');widget(app,'checkbox','news_keys_'+p+'_availability_confirm_'+second).check().run()
                widget(app,'button','news_keys_'+p+'_enabled_'+second).click().run()
                self.action(app,p,second,'Make primary')
                widget(app,'button','news_keys_'+p+'_primary_'+second).click().run()
                self.action(app,p,second,'Delete key')
                self.assertTrue(widget(app,'button','news_keys_'+p+'_delete_'+second).disabled)
                widget(app,'checkbox','news_key_delete_'+p+'_'+second).check().run()
                widget(app,'button','news_keys_'+p+'_delete_'+second).click().run()
                self.assertEqual([r['slot_id'] for r in self.registry.rows(p)],[first])
                self.assertFalse(app.exception)
        self.assertIsNone(self.q.get())
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
            self.assertNotIn('AUTHORED-', '\n'.join(db.iterdump()))

    def test_add_backup_does_not_reuse_first_add_primary_checkbox(self):
        app=self.app();self.source(app,'marketaux');self.add(app,'marketaux','First','AUTHORED-FIRST',True)
        widget(app,'button','settings_secret_marketaux_edit').click().run()
        self.assertFalse(widget(app,'checkbox','news_keys_marketaux_new_primary').value)
        self.assertEqual(widget(app,'text_input','news_keys_marketaux_new_name').value,'')

    def test_keys_persist_across_four_language_theme_modes_and_new_sessions(self):
        self.registry.add('marketaux','Authored primary','AUTHORED-PRIMARY',primary=True)
        for language in ('en','zh-CN'):
            for theme in ('dark','light'):
                with self.subTest(language=language,theme=theme):
                    save(self.store,'ui_language',language);save(self.store,'ui_theme',theme)
                    app=self.app();self.source(app,'marketaux')
                    self.assertFalse(app.exception);self.assertEqual(load(self.store),{'ui_theme':theme,'ui_language':language})
                    self.assertEqual(self.registry.resolve('marketaux'),'AUTHORED-PRIMARY')
                    labels=[b.label for b in app.button]
                    self.assertIn('Add news key' if language=='en' else '添加新闻密钥',labels)
                    self.assertFalse(any(t.proto.type==1 for t in app.text_input))
        self.assertIsNone(self.q.get())

    def test_configure_write_failure_cannot_replace_primary_or_expose_secret(self):
        self.registry.add('marketaux','Authored primary','AUTHORED-PRIOR',primary=True)
        original=self.registry.selection('marketaux');app=self.app();self.source(app,'marketaux')
        widget(app,'button','settings_secret_marketaux_edit').click().run()
        widget(app,'text_input','news_keys_marketaux_new_name').set_value('Failed backup').run()
        widget(app,'text_input','settings_secret_marketaux').set_value('AUTHORED-FAILURE').run()
        with patch.object(credential_store(),'write_slot',side_effect=OSError('AUTHORED-FAILURE')):
            widget(app,'button','settings_secret_marketaux_save').click().run()
        self.assertFalse(app.exception);self.assertEqual(self.registry.selection('marketaux'),original)
        self.assertTrue(app.error);self.assertFalse(any('AUTHORED-' in e.value for e in app.error))

    def test_default_cards_exist_for_disabled_sources_without_reading_credentials(self):
        self.q.configure(C)
        memory=credential_store()
        with patch.object(memory,'read',side_effect=AssertionError('No legacy value read')),patch.object(memory,'read_slot',side_effect=AssertionError('No protected value read')),patch('finscope.local_credentials.environment_credentials',side_effect=AssertionError('No env read')):
            app=self.app()
            self.assertEqual(sum(b.label=='Manage' for b in app.button),3)
            self.assertFalse(any(b.key.startswith('news_keys_') for b in app.button))
            self.source(app,'marketaux');self.assertFalse(app.exception)
        self.assertIsNone(self.q.get())

    def test_three_cards_show_one_primary_two_backups_without_false_verification(self):
        for p in ('marketaux','newsdata','finnhub'):
            self.registry.add(p,'Main','AUTHORED-'+p+'-MAIN',primary=True)
            for name in ('Backup A','Backup B'):self.registry.add(p,name,'AUTHORED-'+p+'-'+name,primary=False)
        app=self.app()
        self.assertEqual(sum(c.value=='Backup keys: 2' for c in app.caption),3)
        self.assertEqual(sum(c.value=='API verification: Not tested' for c in app.caption),3)
        self.assertEqual(sum(b.label=='Manage' for b in app.button),3)
        self.source(app,'newsdata')
        self.assertTrue(any('Existing manual pause' in c.value for c in app.caption))
        self.assertTrue(widget(app,'button','news_api_verify_newsdata').disabled)

    def test_explicit_local_check_only_updates_nonsecret_check_metadata(self):
        self.registry.add('marketaux','Main','AUTHORED-LOCAL-CHECK',primary=True)
        app=self.app();self.source(app,'marketaux')
        widget(app,'button','news_keys_marketaux_check_local').click().run()
        self.assertFalse(app.exception);self.assertEqual(key_metadata(self.store,'marketaux')['primary']['check_basis'],'explicit_read')
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
        self.assertIsNone(self.q.get())

    def test_preview_button_is_explicit_one_request_and_cannot_grant_nlp_rights(self):
        c=deepcopy(C);c['sources']=['marketaux'];c['source_permissions']={'marketaux':dict(preview=True,retain=False,analyze=False,external=False,reference='Authored preview only')}
        c['budgets']={'marketaux':dict(utc_day=datetime.now(timezone.utc).date().isoformat(),remaining=1,topic='technology',symbol='')}
        self.q.configure(c);self.registry.add('marketaux','Main','AUTHORED-PREVIEW',primary=True)
        app=self.app();self.source(app,'marketaux')
        self.assertTrue(widget(app,'button','news_api_verify_marketaux').disabled)
        key=next(x.key for x in app.checkbox if x.key.startswith('news_api_confirm_marketaux_'))
        app.checkbox(key=key).check().run()
        calls=[]
        service=LocalIngestionService(self.store,transport=lambda *a:(calls.append(1) or HTTPResponse({'data':[]},200,{})),study_path=self.store.path.parent/'none.sqlite3',cooldown_path=self.store.path.parent/'none.json')
        with patch('finscope.news_source_ui.verify_api',side_effect=lambda *args,**kwargs:verify_api(*args,**kwargs,service=service)):
            widget(app,'button','news_api_verify_marketaux').click().run();app.run()
        self.assertEqual(len(calls),1);self.assertFalse(app.exception)
        self.assertFalse(self.q.config()['source_permissions']['marketaux']['analyze'])
        self.assertEqual(key_metadata(self.store,'marketaux')['primary']['api_state'],'verified')
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_news').fetchone()[0],0)
        self.assertIsNone(self.q.get())

    def test_unsaved_settings_prevent_silent_old_config_submission(self):
        self.q.configure(C)
        app=self.app();widget(app,'number_input','settings_limit').set_value(9).run()
        widget(app,'radio','product_page').set_value('Dashboard').run()
        self.assertTrue(widget(app,'button','product_update').disabled)
        self.assertEqual(self.q.config()['limit'],C['limit']);self.assertIsNone(self.q.get())

    def test_disabled_source_preview_parameters_save_without_enabling_or_requesting(self):
        self.q.configure(C);app=self.app();self.source(app,'marketaux')
        self.assertEqual(app.session_state['_settings_edit'],editable(self.q))
        widget(app,'text_input','settings_permission_ref_marketaux').set_value('Authored offline preview permission').run()
        widget(app,'checkbox','settings_preview_marketaux').check().run()
        widget(app,'number_input','settings_budget_marketaux').set_value(1).run()
        widget(app,'button','settings_save').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('marketaux',self.q.config()['sources'])
        self.assertEqual(self.q.config()['budgets']['marketaux']['remaining'],1)
        self.assertTrue(self.q.config()['source_permissions']['marketaux']['preview'])
        self.assertFalse(any('Unsaved settings edits' in e.value for e in app.info))
        returning=self.app();self.source(returning,'marketaux')
        self.assertEqual(widget(returning,'number_input','settings_budget_marketaux').value,1)
        self.assertIsNone(self.q.get())
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)


if __name__=='__main__':unittest.main()
