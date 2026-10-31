"""Authored offline fixtures only; UI actions may never dispatch HTTP/inference."""
from contextlib import closing
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.product_storage import ProductStorage
from finscope.text_processing import prepare,keywords
from finscope.industry_classifier import IndustryClassifier
from finscope.product_presentation import article_selection,article_rows,keyword_snippets
from finscope.view_preferences import save,load
from finscope.product_theme import status_markup
from test_product_pipeline import fixture,C

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class PresentationTests(unittest.TestCase):
    def test_filtered_selection_rejects_stale_ids_and_keeps_current(self):
        self.assertEqual(article_selection(['one','two'],'one','two'),'two')
        self.assertEqual(article_selection(['one','two'],'two','removed'),'two')
        self.assertEqual(article_selection(['one'],'removed'),'one')
        self.assertIsNone(article_selection([],None))
    def test_keyword_alias_highlights_actual_text_and_escapes_html(self):
        item=replace(fixture(),body='A company sells <script>unsafe</script> LLMs for banks.')
        snippets=keyword_snippets(item,'large language model')
        self.assertEqual(snippets[0]['match'],'LLMs');self.assertEqual(snippets[0]['field'],'body')
        self.assertIn('<mark>LLMs</mark>',snippets[0]['html']);self.assertNotIn('<script>',snippets[0]['html'])
        self.assertIn('&lt;script&gt;',snippets[0]['html'])
        self.assertEqual(item.body[snippets[0]['start']:snippets[0]['end']],'LLMs')
    def test_highlight_summary_title_fallback_chinese_and_permissions(self):
        item=fixture('Cloud services and 大语言模型 development.')
        self.assertEqual(keyword_snippets(item,'large language model')[0]['match'],'大语言模型')
        self.assertEqual(keyword_snippets(item,'cloud')[0]['field'],'summary')
        self.assertEqual(keyword_snippets(replace(item,rights=replace(item.rights,preview=False)),'cloud'),[])
        self.assertEqual(keyword_snippets(item,'loud'),[])
    def test_document_frequency_is_once_per_article_not_keyword_occurrences(self):
        a=fixture('Manufacturing manufacturing manufacturing and LLMs.')
        b=replace(fixture('Manufacturing with large language models.',number='2'),body='manufacturing '*100)
        terms={v['term']:v for v in keywords([a,b])}
        self.assertEqual(terms['manufacturing']['count'],2)
        self.assertEqual(terms['large language model']['count'],2)
        self.assertEqual(len(terms['manufacturing']['article_ids']),2)
    def test_missing_time_and_sentiment_are_not_replaced(self):
        row=article_rows([replace(fixture(),timestamp='',publication_date='')],{})[0]
        self.assertEqual(row['published'],'Publication date unknown');self.assertEqual(row['tone'],'Not analyzed')
        self.assertEqual(row['title'],fixture().title)
    def test_running_status_keeps_counts_and_escapes_stage_metadata(self):
        html=status_markup('running','fetch: <script>',{'new':2,'classified':3,'analyzed':1,'failed':0})
        self.assertIn('In progress',html);self.assertIn('2</b> new',html)
        self.assertIn('3</b> classified',html);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)


class LocalPresentationUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'news.sqlite3');self.q=TaskQueue(self.store);self.q.configure(C)
        self.store.set_setting('guide_completed',True)
        env=patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)});env.start();self.addCleanup(env.stop)
        guard=patch('requests.sessions.Session.request',side_effect=AssertionError('View-only action dispatched HTTP'))
        self.http=guard.start();self.addCleanup(guard.stop)
        self.items=[];data=ProductStorage(self.store)
        for number,text in [('1','The company develops chip design.'),('2','The company makes DRAM memory chips.')]:
            item=prepare(replace(fixture(text,number),provider='licensed_test_fixture',title='Authored title '+number))[0]
            data.save(item);data.save_classification(item,'offline-test',IndustryClassifier().classify(item));self.items.append(item)
    def app(self):
        app=AppTest.from_file(str(APP),default_timeout=15).run();self.assertFalse(app.exception);return app
    def test_table_click_and_accessible_picker_sync_both_directions(self):
        clicks={};seen={}
        def chart(kind,data,*,key,selected=None):seen[key]=selected;return clicks.pop(key,None)
        with patch('finscope.pipeline_ui.interactive_chart',side_effect=chart):
            app=self.app();app.radio(key='product_page').set_value('News Explorer').run()
            first=app.selectbox(key='explorer_article').value
            target=next(n for n in self.items if n.article_id!=first)
            clicks['explorer_rows']=target.article_id;app.run()
            self.assertEqual(app.selectbox(key='explorer_article').value,target.article_id)
            self.assertTrue(any(h.value==target.title for h in app.subheader))
            app.selectbox(key='explorer_article').set_value(first).run()
            self.assertEqual(seen['explorer_rows'],first)
            self.assertFalse(app.exception);self.http.assert_not_called()
    def test_missing_catalog_results_are_not_absence_of_relevant_news(self):
        app=self.app();app.selectbox(key='product_taxonomy').set_value('CSRC-JRT0020-2024').run()
        self.assertEqual(app.metric[0].value,'2');self.assertEqual(app.metric[2].value,'0')
        self.assertTrue(any('2/2 originals have no saved classification' in x.value for x in app.info))
        app.radio(key='product_page').set_value('Industries').run()
        self.assertEqual(len(app.selectbox(key='industries_article').options),2)
        self.assertTrue(any('awaiting classification' in x.value for x in app.info))
        app.selectbox(key='product_taxonomy').set_value('US-BUSINESS-1').run()
        self.assertFalse(app.exception);self.http.assert_not_called()
    def test_hard_refresh_restores_page_dates_and_catalog_without_jobs(self):
        app=self.app();dates=(date(2026,10,29),date(2026,10,30))
        app.date_input(key='local_dates').set_value(dates).run()
        app.radio(key='product_page').set_value('News Explorer').run()
        app.selectbox(key='explorer_article').set_value(self.items[1].article_id).run()
        again=self.app()
        self.assertEqual(again.radio(key='product_page').value,'News Explorer')
        self.assertEqual(again.date_input(key='local_dates').value,dates)
        self.assertEqual(again.selectbox(key='explorer_article').value,self.items[1].article_id)
        self.assertEqual(self.q.config(),C);self.assertIsNone(self.q.get());self.http.assert_not_called()
    def test_preferences_cannot_store_credentials_search_or_request_state(self):
        save(self.store,{'product_page':'Dashboard','local_search':'fake-test-secret',
                         'OPENAI_API_KEY':'fake-test-secret','model':'OpenAI API','sources':['marketaux'],'budgets':999,
                         'local_sectors':['not-a-sector'],'local_dates':['2026-10-30','invalid']})
        with closing(self.store.connect()) as db:
            payload=db.execute("SELECT payload FROM product_settings WHERE name='view_preferences'").fetchone()[0]
        self.assertNotIn('fake-test-secret',payload);self.assertNotIn('budgets',payload)
        self.assertEqual(load(self.store)['local_sectors'],[]);self.assertNotIn('local_dates',load(self.store))
        self.assertEqual(self.q.config(),C)
    def test_old_dates_keep_new_records_hidden_with_explicit_widen_action(self):
        app=self.app();app.date_input(key='local_dates').set_value((date(2026,10,29),)*2).run()
        self.assertEqual(app.metric[0].value,'0');self.assertTrue(any('outside the current date range' in x.value for x in app.info))
        app.button(key='widen_local_dates').click().run();self.assertEqual(app.metric[0].value,'2')
        self.http.assert_not_called()
    def test_every_page_rerender_preserves_ledgers_and_tasks(self):
        app=self.app()
        for page in ('Industries','Knowledge Graph','News Explorer','Settings','Dashboard'):
            app.radio(key='product_page').set_value(page).run();app.run();self.assertFalse(app.exception)
        with closing(self.store.connect()) as db:
            for table in ('product_tasks','local_requests','local_model_requests','local_collector_http','local_analyses'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
        self.http.assert_not_called()
    def test_running_task_keeps_views_usable_without_resubmission_or_model_load(self):
        identity,_=self.q.submit(C)
        self.q.update(identity,status='running',stage='analyze: authored fixture',
                      counts={'new':2,'duplicates':0,'classified':2,'analyzed':1,'failed':0,'skipped':0})
        with patch('finscope.finbert_backend.LocalFinBERTBackend.from_snapshot',side_effect=AssertionError('UI loaded model')) as model:
            app=self.app();self.assertTrue(app.button(key='product_update').disabled)
            self.assertTrue(any('In progress' in m.value for m in app.markdown))
            app.radio(key='product_page').set_value('News Explorer').run()
            self.assertFalse(app.exception);self.assertEqual(len(app.selectbox(key='explorer_article').options),2)
            app.radio(key='product_page').set_value('Dashboard').run()
            self.assertEqual(self.q.get()['id'],identity);self.assertEqual(self.q.get()['status'],'running')
            model.assert_not_called();self.http.assert_not_called()


if __name__=='__main__':unittest.main()
