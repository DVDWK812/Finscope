from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.product_storage import ProductStorage
from finscope.text_processing import prepare
from finscope.industry_classifier import IndustryClassifier
from finscope.taxonomy import load_taxonomy
from finscope.product_analytics import industry_rows,project_news,taxonomy_graph
from test_product_pipeline import fixture,C,Worker,prediction

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class AutomaticUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'local.sqlite3');self.q=TaskQueue(self.store);self.q.configure(C)
        self.store.set_setting('guide_completed',True)
        self.guard=patch('requests.sessions.Session.request',side_effect=AssertionError('Refresh/filter must not perform any HTTP'))
        self.http=self.guard.start();self.addCleanup(self.guard.stop)
        env=patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)});env.start();self.addCleanup(env.stop)
    def app(self):
        app=AppTest.from_file(str(APP),default_timeout=15).run();self.assertFalse(app.exception);return app
    def test_first_run_guide_leads_to_settings_without_requests(self):
        self.store.set_setting('guide_completed',False)
        app=self.app();self.assertEqual(len(app.subheader),4)
        next(b for b in app.button if b.label=='Get Started').click().run()
        self.assertFalse(app.exception);self.assertEqual(app.radio(key='product_page').value,'Settings');self.http.assert_not_called()
    def test_primary_navigation_and_single_queued_task_across_rerenders(self):
        app=self.app();self.assertEqual(app.radio(key='product_page').options,['Dashboard','Industries','Knowledge Graph','News Explorer','Settings'])
        app.button(key='product_update').click().run();key=self.q.get()['id']
        app.run();self.assertTrue(app.button(key='product_update').disabled)
        app.radio(key='product_page').set_value('News Explorer').run();app.run()
        self.assertEqual(self.q.get()['id'],key);self.http.assert_not_called()
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_tasks').fetchone()[0],1)
    def test_synthetic_excluded_by_default_and_pending_is_not_neutral(self):
        data=ProductStorage(self.store)
        data.save(prepare(fixture())[0]);data.save(prepare(replace(fixture(number='2'),provider='licensed_test_fixture'))[0])
        app=self.app();self.assertEqual(app.metric[0].value,'1');self.assertEqual(app.metric[1].value,'0')
        self.assertTrue(any('missing analysis is not Neutral' in x.value for x in app.info))
        app.checkbox(key='product_include_dev').check().run();self.assertEqual(app.metric[0].value,'2');self.http.assert_not_called()
    def test_worker_results_appear_without_user_save_or_run(self):
        from datetime import date
        app=self.app();app.date_input(key='local_dates').set_value((date(2026,10,30),)*2).run()
        app.button(key='product_update').click().run()
        w=Worker(self.store,fetch=lambda *a:[replace(fixture(),provider='licensed_test_fixture')],infer=prediction,resources=lambda *a,**k:None)
        w.run_one();app.run();self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,'1');self.assertEqual(self.q.get()['status'],'completed')
        self.http.assert_not_called()
    def test_date_and_source_filters_survive_navigation_and_no_automatic_inference(self):
        ProductStorage(self.store).save(prepare(replace(fixture(),provider='licensed_test_fixture'))[0])
        app=self.app();dates=app.date_input(key='local_dates').value
        app.radio(key='product_page').set_value('Industries').run()
        app.radio(key='product_page').set_value('Knowledge Graph').run()
        app.radio(key='product_page').set_value('Dashboard').run()
        self.assertFalse(app.exception);self.assertEqual(app.date_input(key='local_dates').value,dates)
        self.assertIsNone(self.q.get());self.http.assert_not_called()
    def test_two_child_topics_parent_count_is_one_and_graph_members_agree(self):
        item=prepare(fixture('The company makes DRAM memory chips and hard drives.'))[0]
        c=IndustryClassifier().classify(item);classes={item.article_id:c};catalog=load_taxonomy()
        news=project_news([item],classes,catalog);rows=industry_rows(news,{},classes,catalog)
        self.assertEqual(next(r['Articles'] for r in rows if r['ID']=='technology'),1)
        graph,_=taxonomy_graph(news,{},classes,catalog)
        from finscope.local_analytics import graph_members
        for key in ('industry:technology','industry:technology.memory-chips','article:'+item.article_id):self.assertEqual(graph_members(graph,key),{item.article_id})
        for edge in graph['edges']:self.assertTrue(edge['evidence'])
    def test_graph_node_bound_and_cloud_events_reject_stale_filter_scope(self):
        from finscope.chart_interactions import selected_value,chart_scope
        item=prepare(fixture())[0];c=IndustryClassifier().classify(item);catalog=load_taxonomy()
        graph,_=taxonomy_graph([item],{}, {item.article_id:c},catalog,node_limit=3)
        self.assertLessEqual(len(graph['nodes']),3)
        scope=chart_scope('cloud',{'terms':[{'term':'semiconductor','count':1}]})
        self.assertEqual(selected_value({'scope':scope,'id':'semiconductor'},scope,{'semiconductor'}),'semiconductor')
        self.assertIsNone(selected_value({'scope':'older-filter','id':'semiconductor'},scope,{'semiconductor'}))

    def test_graph_selection_keeps_word_cloud_at_the_same_host_position(self):
        item=prepare(replace(fixture(),provider='licensed_test_fixture'))[0]
        data=ProductStorage(self.store);data.save(item)
        data.save_classification(item,'offline-test',IndustryClassifier().classify(item))
        app=self.app();app.radio(key='product_page').set_value('Knowledge Graph').run()
        def paths(tree,path=()):
            found=[]
            for key,node in getattr(tree,'children',{}).items():
                here=path+(key,)
                if node.type=='component_instance':found.append(here)
                found.extend(paths(node,here))
            return found
        before=paths(app._tree)
        self.assertEqual(len(before),2)
        app.session_state['product_graph_selected']='industry:technology'
        app.run();self.assertFalse(app.exception)
        self.assertTrue(any('Technology' in h.value for h in app.subheader))
        self.assertEqual(paths(app._tree),before,'detail insertion must not move/remount the word-cloud iframe')


if __name__=='__main__':unittest.main()
