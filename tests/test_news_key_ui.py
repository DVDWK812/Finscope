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
                widget(app,'button','news_keys_'+p+'_manage_'+second).click().run()
                widget(app,'button','news_keys_'+p+'_primary_'+second).click().run()
                self.assertEqual(self.registry.selection(p)['slot_id'],second)
                widget(app,'button','news_keys_'+p+'_replace_'+second).click().run()
                self.assertEqual(sum(t.proto.type==1 for t in app.text_input),1)
                widget(app,'text_input','settings_secret_'+p).set_value('AUTHORED-'+p+'-NEW').run()
                widget(app,'button','settings_secret_'+p+'_save').click().run()
                self.assertEqual(self.registry.resolve(p),'AUTHORED-'+p+'-NEW')
                widget(app,'button','news_keys_'+p+'_enabled_'+second).click().run()
                self.assertIsNone(self.registry.selection(p))
                widget(app,'button','news_keys_'+p+'_enabled_'+second).click().run()
                widget(app,'button','news_keys_'+p+'_primary_'+second).click().run()
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


if __name__=='__main__':unittest.main()
