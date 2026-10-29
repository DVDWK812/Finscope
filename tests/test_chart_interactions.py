"""Read-only drilldown contract and evidence graphs; no NLP or HTTP."""
from dataclasses import replace
from datetime import date
import unittest
from unittest.mock import patch

from finscope.chart_interactions import chart_scope, selected_value
from finscope.local_analytics import graph_view, graph_members, cell_members, heatmap_cells
from finscope.local_news import Analysis, LocalNewsStore
from test_local_news import item
import test_product_ui as product_test


class EvidenceInteractionTests(unittest.TestCase):
    def setUp(self):
        self.original=item(article_id='a',timestamp_kind='published',summary='NVIDIA reported revenue growth and record earnings.')
        self.other=replace(self.original,article_id='b',title='Second authored text',company='QUERY')
        self.result=Analysis('r','a','Neutral','FinBERT','mock','v1','2026-10-29T09:00:00Z')

    def test_graph_default_layers_focus_limits_and_expand(self):
        news=[replace(self.original,article_id=str(n)) for n in range(50)]
        data,full,focused=graph_view(news,{},sector='Technology')
        self.assertLessEqual(len(data['nodes']),40)
        self.assertEqual(sum(n['kind']=='Article' for n in data['nodes']),8)
        self.assertEqual(len(focused),50)
        self.assertLess(len(data['nodes']),len(full['nodes']))
        self.assertFalse(any(n['kind']=='Source' for n in data['nodes']))
        expanded,_,_=graph_view(news,{},sector='Technology',article_limit=30,node_limit=120)
        self.assertGreater(len(expanded['nodes']),len(data['nodes']))
        self.assertEqual(graph_view(news,{},sector='Healthcare')[0],{'nodes':[],'edges':[]})

    def test_entities_themes_have_literal_evidence_query_is_not_mention(self):
        data,_,_=graph_view([self.original,self.other],{},sector='Technology')
        self.assertEqual(graph_members(data,'entity:NVIDIA'),{'a','b'})
        self.assertEqual(graph_members(data,'theme:Earnings / results'),{'a','b'})
        self.assertEqual(graph_members(data,'article:a'),{'a'})
        mentions=[e for e in data['edges'] if e['relationship']=='literal_text_mention']
        self.assertTrue(mentions)
        self.assertTrue(all('NVIDIA' in e['evidence'] for e in mentions))
        query=next(e for e in data['edges'] if e['relationship']=='returned_for_ticker')
        self.assertIn('not a verified company mention',query['evidence'])
        self.assertFalse(any('caus' in e['relationship'] for e in data['edges']))

    def test_heatmap_click_members_and_missing_neutral_states(self):
        missing=replace(self.original,article_id='c',timestamp='',publication_date='')
        cells=heatmap_cells([self.original,self.other,missing],{'a':self.result},date(2026,10,29),date(2026,10,30),date_basis='published')
        cell=next(c for c in cells if c['Sector']=='Technology' and c['Date']=='2026-10-29')
        self.assertEqual((cell['Articles'],cell['Analyzed'],cell['Balance']),(2,1,0))
        self.assertEqual(cell_members([self.original,self.other,missing],cell),[self.original,self.other])
        empty=next(c for c in cells if c['Sector']=='Technology' and c['Date']=='2026-10-30')
        self.assertEqual(empty['Articles'],0);self.assertIsNone(empty['Balance'])
        pending=heatmap_cells([self.original],{},date(2026,10,29),date(2026,10,29),date_basis='published')[0]
        self.assertIsNone(pending['Balance'])

    def test_selection_scopes_reject_stale_and_unknown_nodes(self):
        scope=chart_scope('graph',{'model':'one'})
        event={'scope':scope,'id':'a','click':1}
        self.assertEqual(selected_value(event,scope,{'a'}),'a')
        self.assertIsNone(selected_value(event,chart_scope('graph',{'model':'two'}),{'a'}))
        self.assertIsNone(selected_value(event,scope,{'b'}))
        self.assertIsNone(selected_value(None,scope,{'a'}))

    def test_count_charts_validate_without_categorical_scale_bindings(self):
        import altair as alt
        from finscope.dashboard_ui import source_chart,sector_chart,timeline_chart
        specs=[]
        with patch('streamlit.vega_lite_chart',side_effect=lambda spec,**kw:specs.append(spec)):
            source_chart([self.original])
            sector_chart([self.original],{})
            timeline_chart([self.original],{},date(2026,10,29),date(2026,10,30))
        for spec in specs:
            alt.Chart.from_dict(spec).to_json(validate=True)
            self.assertNotIn('params',spec)
        trend=specs[-1]['data']['values']
        self.assertEqual(sum(r['Articles'] for r in trend),1)
        self.assertEqual(specs[-1]['encoding']['y']['scale']['domain'],[0,1])

    def test_single_sentiment_donut_has_finite_explicit_angles(self):
        import altair as alt
        import math
        from finscope.dashboard_ui import distribution_chart
        with patch('streamlit.vega_lite_chart') as chart:
            distribution_chart({'a':self.result})
        spec=chart.call_args.args[0]
        alt.Chart.from_dict(spec).to_json(validate=True)
        rows=spec['data']['values']
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['Sentiment'],rows[0]['Articles'],rows[0]['Start']),('Neutral',1,0))
        self.assertAlmostEqual(rows[0]['End'],2*math.pi)
        self.assertIsNone(spec['encoding']['theta']['scale'])


class ChartUITests(unittest.TestCase):
    setUp=product_test.ProductUITests.setUp
    app=product_test.ProductUITests.app

    def stored(self):
        original=item(article_id='clickable',timestamp_kind='published',summary='NVIDIA revenue grew.')
        LocalNewsStore(self.db).save_news(original)
        return original

    def test_heatmap_event_opens_original_and_empty_cell(self):
        original=self.stored()
        def event(**args):
            return {'scope':args['scope'],'id':'2026-10-29|Technology','click':1} if args['kind']=='heatmap' else None
        with patch('finscope.chart_interactions._chart',side_effect=event):
            app=self.app('Dashboard')
        self.assertFalse(app.exception)
        self.assertTrue(any(h.value=='Technology · 2026-10-29' for h in app.subheader))
        self.assertEqual(app.selectbox(key='heatmap_related').value,original.article_id)

    def test_graph_node_event_opens_article_and_theme_members(self):
        original=self.stored()
        selected=['article:clickable']
        def event(**args):
            return {'scope':args['scope'],'id':selected[0],'click':selected[0]} if args['kind']=='graph' else None
        with patch('finscope.chart_interactions._chart',side_effect=event):
            app=self.app('Dashboard')
            self.assertEqual(app.selectbox(key='graph_node_related').value,original.article_id)
            selected[0]='theme:Earnings / results'
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any(h.value=='Keyword theme: Earnings / results' for h in app.subheader))
            self.assertEqual(app.selectbox(key='graph_node_related').value,original.article_id)

    def test_refresh_search_and_graph_layers_do_not_request_or_analyze(self):
        self.stored()
        with patch('finscope.model_ui.execute',side_effect=AssertionError('No implicit model run')) as run_model, \
             patch('requests.sessions.Session.request',side_effect=AssertionError('No implicit HTTP')) as http:
            app=self.app('Dashboard')
            app.run()
            app.text_input(key='local_search').set_value('NVIDIA').run()
            app.checkbox(key='graph_sources').check().run()
            app.checkbox(key='graph_expand').check().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(LocalNewsStore(self.db).list_analyses()),0)
            run_model.assert_not_called()
            http.assert_not_called()
