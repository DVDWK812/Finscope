from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.ui_preferences import load,save,activate,theme,language,toggle
from finscope.product_theme import palette,colors


class UIPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'ui.sqlite3');TaskQueue(self.store)
        self.addCleanup(lambda:activate({}))
    def test_defaults_and_independent_strict_values(self):
        self.assertEqual(load(self.store),{'ui_theme':'dark','ui_language':'en'})
        for key,value in [('ui_theme','blue'),('ui_language','zh'),('api_key','secret'),('ui_theme',None)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):save(self.store,key,value)
        save(self.store,'ui_theme','light');self.assertEqual(load(self.store)['ui_language'],'en')
        save(self.store,'ui_language','zh-CN');self.assertEqual(load(self.store)['ui_theme'],'light')
    def test_persistence_does_not_submit_or_change_news_or_pipeline(self):
        with patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP')) as request:
            for _ in range(8):toggle(self.store)
            save(self.store,'ui_theme','light');save(self.store,'ui_language','zh-CN')
            self.assertEqual(load(LocalNewsStore(self.store.path)),{'ui_theme':'light','ui_language':'zh-CN'})
            with closing(self.store.connect()) as db:
                for table in ('local_news','local_analyses','local_requests','product_tasks'):
                    self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
                self.assertEqual({r[0] for r in db.execute('SELECT name FROM product_settings')},{'ui_theme','ui_language'})
            request.assert_not_called()
    def test_palette_is_per_context_and_all_render_colors_change(self):
        activate({});dark=palette();activate({'ui_theme':'light'});light=palette()
        self.assertEqual(set(dark),set(light))
        for key in ('background','surface','text','muted','border','hover','focus','positive','neutral','negative','warning_bg'):
            self.assertNotEqual(dark[key],light[key])
        self.assertEqual(colors()[0],light['positive']);self.assertEqual(theme(),'light');self.assertEqual(language(),'en')
    def test_iframe_theme_parameters_do_not_change_click_scope(self):
        import streamlit as st
        from finscope.chart_interactions import interactive_chart
        calls=[]
        with patch('finscope.chart_interactions._chart',side_effect=lambda **kwargs:calls.append(kwargs)):
            for value in ('dark','light'):
                activate({'ui_theme':value});interactive_chart('articles',{'rows':[]},key='test')
        self.assertEqual(calls[0]['scope'],calls[1]['scope'])
        self.assertEqual([r['ui_theme'] for r in calls],['dark','light'])
        self.assertNotEqual(calls[0]['palette']['surface'],calls[1]['palette']['surface'])


if __name__=='__main__':unittest.main()
