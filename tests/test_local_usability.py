"""User-flow regressions: authored fixtures only, no provider/model traffic."""
from dataclasses import replace
from contextlib import closing
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from finscope.local_analytics import default_result_model, model_key, select_articles, Filters
from finscope.local_news import Analysis, LocalIngestionService, LocalNewsStore
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
        app.text_input(key='key_marketaux').set_value('PRIVATE-MARKETAUX-UNIT').run()
        app.selectbox(key='api_provider').set_value('Finnhub').run()
        self.assertEqual(app.text_input(key='key_finnhub').value,'')
        self.assertTrue(any(t.label=='Company ticker' for t in app.text_input))
        self.assertFalse(any(s.label=='News topic' for s in app.selectbox))
        app.selectbox(key='api_provider').set_value('Local Collector').run()
        self.assertFalse(any(t.label.endswith('API key') for t in app.text_input))
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
