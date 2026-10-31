from contextlib import closing
from datetime import date
from pathlib import Path
from string import Formatter
import json
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from finscope.i18n import resources,t,tr,display,Verbatim,component_labels,node_name
from finscope.ui_preferences import activate,save,load
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.product_storage import ProductStorage
from finscope.text_processing import prepare
from finscope.taxonomy import load_taxonomy,node_label
from finscope.view_preferences import normalize
from test_product_pipeline import fixture,C

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class I18nTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'local.sqlite3')
        TaskQueue(self.store).configure(C);self.store.set_setting('guide_completed',True)
        self.addCleanup(lambda:activate({}))

    def test_catalogs_have_identical_keys_and_format_fields(self):
        en,zh=resources('en'),resources('zh-CN')
        self.assertEqual(set(en),set(zh));self.assertGreater(len(en),500)
        for key in en:
            with self.subTest(key=key):
                fields=lambda s:{(name,spec) for _,name,spec,_ in Formatter().parse(s) if name is not None}
                self.assertEqual(fields(en[key]),fields(zh[key]))
                self.assertTrue(en[key]);self.assertTrue(zh[key])

    def test_invalid_locale_is_rejected_and_corrupt_saved_value_falls_back(self):
        for locale in ('zh','fr','',None):
            with self.assertRaises(ValueError):resources(locale)
            with self.assertRaises(ValueError):activate({'ui_language':locale})
        with closing(self.store.connect()) as db:
            db.execute("INSERT INTO product_settings VALUES ('ui_language',?)",(json.dumps('fr'),));db.commit()
        self.assertEqual(load(self.store)['ui_language'],'en')

    def test_verbatim_data_and_raw_taxonomy_identifiers_are_preserved(self):
        activate({'ui_language':'zh-CN'})
        for raw in ('Positive','Dashboard','https://example.test/Negative','Original model rationale'):
            self.assertEqual(tr(Verbatim(raw)),raw);self.assertEqual(display(Verbatim(raw)),raw)
        self.assertEqual(t('Dashboard'),'数据概览');self.assertEqual(t('Not analyzed'),'未分析')
        self.assertEqual(tr('Keyword match · Title'),t('Keyword match · {v0}',v0='Title'))
        for mode in ('US-BUSINESS-1','CSRC-JRT0020-2024'):
            for node in load_taxonomy(mode)['nodes']:
                raw=node_label(node);self.assertEqual(display(raw),node['name_zh'])
                activate({'ui_language':'en'});self.assertEqual(display(raw),node['name_en'])
                activate({'ui_language':'zh-CN'});self.assertEqual(node_name(node),node['name_zh'])
        self.assertEqual(display('Local LM Studio · actual/model-Q4_K_M'),'本地 LM Studio · actual/model-Q4_K_M')

    def test_legacy_english_industry_preferences_remain_valid(self):
        node=next(n for n in load_taxonomy()['nodes'] if n['id']=='technology')
        for value in (node['id'],node['name_en'],node['name_zh'],node_label(node)):
            self.assertEqual(normalize({'local_sectors':[value]},self.store)['local_sectors'],[node_label(node)])

    def test_twenty_page_modes_keep_filters_selection_and_pipeline_without_io(self):
        from finscope.industry_classifier import IndustryClassifier
        item=prepare(fixture())[0];data=ProductStorage(self.store);data.save(item)
        data.save_classification(item,'authored-development-test',IndustryClassifier().classify(item))
        with patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)}),patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP during UI preference changes')) as http:
            app=AppTest.from_file(str(APP),default_timeout=20).run();self.assertFalse(app.exception)
            dates=app.date_input(key='local_dates').value
            app.session_state['explorer_article']=item.article_id
            config=TaskQueue(self.store).config()
            for theme in ('dark','light'):
                for language in ('en','zh-CN'):
                    save(self.store,'ui_theme',theme);save(self.store,'ui_language',language)
                    for page in ('Dashboard','Industries','Knowledge Graph','News Explorer','Settings'):
                        with self.subTest(theme=theme,language=language,page=page):
                            # Serialize the control currently on screen, then
                            # verify the new presentation keeps the canonical ID.
                            next(r for r in app.radio if r.key.startswith('product_page')).set_value(page).run()
                            self.assertFalse(app.exception)
                            self.assertEqual(app.session_state['product_page'],page)
                            self.assertEqual(next(r for r in app.radio if r.key.startswith('product_page')).value,page)
                            self.assertEqual(app.session_state['explorer_article'],item.article_id)
                            self.assertEqual(app.session_state['filter_preferences']['local_dates'],dates)
                            self.assertTrue(any(b.label==('☀' if theme=='dark' else '☾') for b in app.button))
                            self.assertTrue(any(h.value==resources(language)[page] for h in app.title))
            self.assertEqual(TaskQueue(self.store).config(),config)
            self.assertIsNone(TaskQueue(self.store).get());http.assert_not_called()
            self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.store.list_analyses()),0)

    def test_language_save_preserves_page_and_does_not_save_pipeline(self):
        with patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)}),patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP')):
            app=AppTest.from_file(str(APP),default_timeout=20).run()
            app.radio(key='product_page').set_value('Settings').run()
            before=TaskQueue(self.store).config()
            app.selectbox(key='ui_language_choice').set_value('zh-CN').run()
            app.button(key='ui_language_save').click().run()
            self.assertFalse(app.exception);self.assertEqual(load(self.store)['ui_language'],'zh-CN')
            self.assertEqual(app.session_state['product_page'],'Settings')
            self.assertEqual(TaskQueue(self.store).config(),before)

    def test_iframe_labels_change_but_scope_and_event_ids_do_not(self):
        from finscope.chart_interactions import interactive_chart
        calls=[];data={'terms':[{'term':'revenue','count':2}]}
        with patch('finscope.chart_interactions._chart',side_effect=lambda **kw:calls.append(kw) or {'scope':kw['scope'],'id':'revenue'}):
            for locale in ('en','zh-CN'):
                activate({'ui_language':locale});self.assertEqual(interactive_chart('cloud',data,key='terms_'+locale),'revenue')
        self.assertEqual(calls[0]['data'],calls[1]['data']);self.assertEqual(calls[0]['scope'],calls[1]['scope'])
        self.assertEqual(calls[0]['labels']['Articles'],'Articles')
        self.assertEqual(calls[1]['labels']['Articles'],resources('zh-CN')['Articles'])
        self.assertNotEqual(calls[0]['labels']['Articles'],calls[1]['labels']['Articles'])


if __name__=='__main__':unittest.main()
