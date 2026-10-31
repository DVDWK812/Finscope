"""User-flow regressions: authored fixtures only, no provider/model traffic."""
from dataclasses import replace
from contextlib import closing
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
import pandas as pd


def displayed_tables(container):
    """Read the same table data from the themeable component protocol."""
    tree=getattr(container,'_tree',container);result=[]
    for node in getattr(tree,'children',{}).values():
        if node.type=='component_instance':
            payload=json.loads(node.proto.json_args)
            if payload.get('kind')=='data_table':result.append(pd.DataFrame(payload['data']['rows'],columns=payload['data']['headers']))
        result.extend(displayed_tables(node))
    return result
from unittest.mock import patch

from finscope.local_analytics import default_result_model, model_key, select_articles, Filters
from finscope.local_news import Analysis, LocalIngestionService, LocalNewsStore, FetchBlocked
from finscope.api_sources import HTTPResponse
from test_local_news import item, NOW
import test_product_ui as product_test


class SourceStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store = LocalNewsStore(root/'library.sqlite3')
        self.now = NOW
        self.service = LocalIngestionService(self.store, cooldown_path=root/'holds.json',
            study_path=root/'study.sqlite3', clock=lambda:self.now,
            transport=lambda *args: self.fail('Status must never request news'))

    def row(self, provider, stamp, status, hold=None):
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_requests(id,provider,reserved_at,completed_at,status,hold_until) VALUES (?,?,?,?,?,?)',
                (provider+stamp.isoformat(),provider,stamp.isoformat(),stamp.isoformat(),status,hold))
            db.commit()

    def test_each_provider_has_independent_configuration_and_manual_pause(self):
        self.assertEqual(self.service.source_status('marketaux',configured=False).state,'Not configured')
        self.assertEqual(self.service.source_status('finnhub',configured=True).state,'Untested')
        self.assertTrue(self.service.source_status('newsdata',configured=True).blocked)
        self.assertEqual(self.service.source_status('newsdata',configured=False).state,'Paused')

    def test_failure_today_is_blocked_but_yesterday_is_historical(self):
        self.row('marketaux',NOW-timedelta(minutes=2),'failed')
        status=self.service.source_status('marketaux',configured=True)
        self.assertEqual(status.state,'Failed'); self.assertTrue(status.blocked)
        self.assertEqual(self.service.source_status('finnhub',configured=True).state,'Untested')
        self.now=NOW+timedelta(days=1)
        status=self.service.source_status('marketaux',configured=True)
        self.assertEqual(status.state,'Untested'); self.assertFalse(status.blocked)
        self.assertEqual(status.last_outcome,'failed')

    def test_retry_after_and_pending_survive_utc_day_change(self):
        self.row('finnhub',NOW-timedelta(days=1),'failed',(NOW+timedelta(hours=2)).isoformat())
        self.assertTrue(self.service.source_status('finnhub',configured=True).blocked)
        self.row('marketaux',NOW-timedelta(days=2),'pending')
        self.assertEqual(self.service.source_status('marketaux',configured=True).state,'Paused')

    def test_success_is_dated_observation_not_live_probe(self):
        self.row('marketaux',NOW-timedelta(minutes=2),'ok')
        before=self.store.path.read_bytes()
        status=self.service.source_status('marketaux',configured=True)
        self.assertEqual(status.state,'Available')
        self.assertIn('not a live',status.reason)
        self.assertEqual(before,self.store.path.read_bytes())

    def test_all_three_api_credentials_do_not_cross_provider_boundaries(self):
        calls=[]
        def transport(url,params,headers,timeout):
            calls.append((url,params,headers))
            return HTTPResponse([] if 'finnhub' in url else {'data':[]},200,{})
        self.service.transport=transport
        from test_local_news import RIGHTS
        with patch.dict('os.environ',{'MARKETAUX_API_KEY':'ENV-MARKET-SECRET','NEWSDATA_API_KEY':'ENV-NEWSDATA-SECRET','FINNHUB_API_KEY':'ENV-FINNHUB-SECRET'}):
            self.service.fetch('marketaux','technology',api_key='UI-MARKET-SECRET',rights=RIGHTS,remaining=1,explicit=True)
            self.service.fetch('finnhub','technology',api_key='UI-FINNHUB-SECRET',symbol='NVDA',rights=RIGHTS,remaining=1,explicit=True)
            with self.assertRaises(FetchBlocked):
                self.service.fetch('newsdata','technology',api_key='UI-NEWSDATA-SECRET',rights=RIGHTS,remaining=1,explicit=True)
        self.assertEqual(len(calls),2)
        self.assertIn('UI-MARKET-SECRET',str(calls[0])); self.assertNotIn('FINNHUB',str(calls[0]))
        self.assertIn('UI-FINNHUB-SECRET',str(calls[1])); self.assertNotIn('MARKET',str(calls[1]))
        self.assertNotIn('ENV-',str(calls));self.assertNotIn('NEWSDATA',str(calls))
        for secret in ('UI-MARKET-SECRET','UI-FINNHUB-SECRET','UI-NEWSDATA-SECRET'):
            self.assertNotIn(secret.encode(),self.store.path.read_bytes())


class FlowUITests(unittest.TestCase):
    setUp = product_test.ProductUITests.setUp
    app = product_test.ProductUITests.app
    def test_pending_queue_ignores_dashboard_result_filters(self):
        original=item(); LocalNewsStore(self.db).save_news(original)
        app=self.app('Analyze')
        app.session_state['local_sentiments']=['Negative']
        app.session_state['local_models']=['some unrelated model']
        app.run()
        self.assertEqual(app.multiselect(key='analysis_articles').options,[original.title])
        self.assertEqual(app.radio(key='analysis_queue').value,'Pending for selected model')
        next(b for b in app.button if b.label=='Select all pending').click().run()
        self.assertEqual(app.multiselect(key='analysis_articles').value,[original.article_id])
        self.assertFalse(app.exception)

    def test_new_records_outside_old_range_require_explicit_widening(self):
        store=LocalNewsStore(self.db)
        old=item(timestamp_kind='published',timestamp='2026-10-01T12:00:00Z')
        recent=item(timestamp_kind='published',timestamp='2026-10-29T12:00:00Z')
        store.save_news(old); store.save_news(recent)
        app=self.app('Dashboard')
        app.date_input(key='local_dates').set_value((date(2026,10,1),date(2026,10,1))).run()
        app.session_state['new_news_ids']=[recent.article_id]
        app.run()
        self.assertEqual(app.metric[0].value,'1')
        self.assertTrue(any('1 new records outside' in x.value for x in app.info))
        next(b for b in app.button if b.label=='Include all saved publication dates').click().run()
        self.assertEqual(app.metric[0].value,'2')
        self.assertEqual(app.date_input(key='local_dates').value,(date(2026,10,1),date(2026,10,29)))

    def test_finnhub_fields_and_provider_keys_are_separate(self):
        app=self.app('Add news')
        app.selectbox(key='api_provider').set_value('Finnhub').run()
        self.assertFalse(any(t.proto.type==1 for t in app.text_input))
        self.assertTrue(any(t.label=='Company ticker' for t in app.text_input))
        self.assertFalse(any(s.label=='News topic' for s in app.selectbox))
        app.selectbox(key='api_provider').set_value('Local Collector').run()
        self.assertFalse(any(t.label.endswith('API key') for t in app.text_input))
        app.selectbox(key='api_provider').set_value('Marketaux').run()
        from test_product_ui import edit_api_key
        edit_api_key(app,'marketaux')
        app.text_input(key='settings_secret_marketaux').set_value('PRIVATE-MARKETAUX-UNIT').run()
        edit_api_key(app,'finnhub')
        self.assertEqual(app.text_input(key='settings_secret_finnhub').value,'')
        self.assertNotIn('PRIVATE-MARKETAUX-UNIT',self.db.read_bytes().decode(errors='ignore'))

    def test_single_default_model_and_unknown_publication_dates(self):
        store=LocalNewsStore(self.db); original=item(); store.save_news(original)
        finbert=Analysis('a',original.article_id,'Positive','FinBERT','fixture','one','2026-10-29T00:00:00Z')
        external=replace(finbert,analysis_id='b',family='External LLM',model_id='other',label='Negative',analyzed_at='2026-10-29T01:00:00Z')
        store.save_analysis(finbert);store.save_analysis(external)
        app=self.app('Dashboard')
        self.assertEqual(app.selectbox(key='local_result_model').value,model_key(finbert))
        self.assertEqual(app.metric[0].value,'1')
        self.assertTrue(any('no publication date' in c.value for c in app.caption))
        app.selectbox(key='local_result_model').set_value(model_key(external)).run()
        self.assertFalse(app.exception)

    def test_filter_preferences_survive_analysis_navigation_without_hiding_pending(self):
        store=LocalNewsStore(self.db); original=item();store.save_news(original)
        app=self.app('Dashboard')
        app.multiselect(key='local_sentiments').set_value(['Negative']).run()
        self.assertEqual(app.metric[0].value,'0')
        app.radio(key='workspace_page').set_value('Analyze').run()
        self.assertEqual(app.multiselect(key='analysis_articles').options,[original.title])
        app.radio(key='workspace_page').set_value('Dashboard').run()
        self.assertEqual(app.multiselect(key='local_sentiments').value,['Negative'])
        self.assertEqual(app.metric[0].value,'0')

    def test_unknown_new_record_can_be_included_without_inventing_dates(self):
        original=item();LocalNewsStore(self.db).save_news(original)
        app=self.app('Dashboard')
        app.checkbox(key='local_unknown_dates').uncheck().run()
        app.session_state['new_news_ids']=[original.article_id];app.run()
        self.assertEqual(app.metric[0].value,'0')
        next(b for b in app.button if b.label=='Include unknown publication dates').click().run()
        self.assertEqual(app.metric[0].value,'1')
        self.assertEqual(LocalNewsStore(self.db).list_news()[0].published_day,'')

    def test_probability_revision_and_ids_are_inside_collapsed_details(self):
        from finscope.local_news import analyze_finbert
        from test_local_news import pipeline
        store=LocalNewsStore(self.db);original=item();store.save_news(original)
        analyze_finbert(original,store,pipeline())
        app=self.app('Dashboard')
        history=next(e for e in app.expander if e.label=='Provenance, permissions and analysis history')
        self.assertFalse(history.proto.expanded)
        self.assertTrue(any('Revision:' in c.value for c in history.caption))
        self.assertTrue(displayed_tables(history))
        listing=next(d for d in displayed_tables(app) if 'Title' in d.columns)
        self.assertNotIn('Article ID',listing.columns)
        self.assertFalse(any('Revision:' in c.value for c in app.main.caption if c not in history.caption))

    def test_local_import_preview_save_and_finbert_need_no_news_key(self):
        from test_local_news import RIGHTS
        original=item(provider='rba_rss',timestamp_kind='published',url='https://www.rba.gov.au/media-releases/2026/mr-26-29.html')
        app=self.app('Add news')
        with patch('finscope.product_ui.local_credentials',side_effect=AssertionError('Local collector/FinBERT must not read news keys')):
            app.selectbox(key='api_provider').set_value('Local Collector').run()
            app.session_state['news_preview']=[replace(original,rights=replace(RIGHTS,retain=False,analyze=False))]
            app.run()
            app.text_input(key='preview_reference').set_value('Authored offline collector fixture').run()
            app.checkbox(key='preview_retain').check().run()
            app.checkbox(key='preview_analyze').check().run()
            next(b for b in app.button if b.label=='Save permitted preview to local library').click().run()
            next(b for b in app.button if b.label=='Analyze selected news →').click().run()
            self.assertEqual(app.selectbox(key='analysis_model').value,'Local FinBERT')
            self.assertEqual(app.multiselect(key='analysis_articles').value,[original.article_id])
            next(b for b in app.button if b.label=='Run real AI analysis').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(LocalNewsStore(self.db).list_analyses()),1)
            next(b for b in app.button if b.label=='View sector results →').click().run()
            self.assertEqual(app.radio(key='workspace_page').value,'Dashboard')

    def test_selected_sector_limits_charts_and_graph_not_original_metadata(self):
        original=item(sectors=('Financials','Technology'),timestamp_kind='published')
        store=LocalNewsStore(self.db);store.save_news(original)
        seen=[];tables=[]
        def component(**args):
            if args['kind']=='heatmap':seen.append(args['data']['cells'])
            if args['kind']=='data_table':tables.append(pd.DataFrame(args['data']['rows'],columns=args['data']['headers']))
        with patch('finscope.chart_interactions._chart',side_effect=component):
            app=self.app('Dashboard')
            tables.clear()
            app.multiselect(key='local_sectors').set_value(['Financials']).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='graph_sector').options,['Financials'])
        self.assertEqual({c['Sector'] for c in seen[-1]},{'Financials'})
        table=next(d for d in tables if 'Sector' in d.columns and 'Not analyzed' in d.columns)
        self.assertEqual(table['Sector'].tolist(),['Financials'])
        self.assertEqual(store.list_news()[0].sectors,('Financials','Technology'))


class PublicationScopeTests(unittest.TestCase):
    def test_no_invented_publication_day_from_import_or_submission(self):
        submitted=item()
        self.assertEqual(submitted.published_day,'')
        first_seen=replace(submitted,timestamp_kind='first_seen')
        self.assertEqual(first_seen.published_day,'')
        dated=replace(submitted,timestamp_kind='published',timestamp='',publication_date='2026-10-29')
        self.assertEqual(dated.published_day,'2026-10-29')
        chosen,_=select_articles([submitted,first_seen,dated],[],Filters(date(2026,10,29),date(2026,10,29),date_basis='published'))
        self.assertEqual(chosen,[dated])

    def test_default_model_never_falls_back_to_external(self):
        analysis=Analysis('b','x','Negative','External LLM','other','v1','2026-10-29T00:00:00Z')
        self.assertEqual(default_result_model([analysis]),'FinBERT · No saved results')

    def test_detail_publication_label_preserves_unknown_and_date_precision(self):
        from finscope.dashboard_ui import publication_label
        self.assertEqual(publication_label(item()),'Publication date unknown')
        self.assertEqual(publication_label(item(timestamp_kind='published',timestamp='',publication_date='2026-10-29')),
                         'Published 2026-10-29 (date only)')


class ExternalStatusTests(unittest.TestCase):
    setUp=SourceStateTests.setUp
    def test_external_pending_and_hold_are_read_from_persistent_state(self):
        from finscope.model_ui import external_status
        self.assertEqual(external_status(self.store),('Untested · No successful connection check',False))
        with closing(self.store.connect()) as db:
            db.execute("INSERT INTO local_model_requests(id,backend,reserved_at,status) VALUES ('a','openai',?,'pending')",(NOW.isoformat(),))
            db.commit()
        self.assertTrue(external_status(self.store)[1])

    def test_external_historical_failure_is_not_an_active_hold(self):
        from finscope.model_ui import external_status
        with closing(self.store.connect()) as db:
            db.execute("INSERT INTO local_model_requests(id,backend,reserved_at,completed_at,status) VALUES ('b','openai',?,?,'failed')",(NOW.isoformat(),NOW.isoformat()))
            db.commit()
        text,blocked=external_status(self.store)
        self.assertTrue(text.startswith('Failed · Last request failed:'))
        self.assertFalse(blocked)
