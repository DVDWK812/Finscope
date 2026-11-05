"""Authored, offline review boundaries and four-view integration; no model calls."""
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from finscope.human_review import HumanReviews, TABLE
from finscope.local_news import LocalNewsStore
from finscope.product_storage import ProductStorage
from finscope.product_analytics import project_news, industry_rows, taxonomy_graph
from finscope.task_queue import TaskQueue
from finscope.taxonomy import load_taxonomy
from finscope.text_processing import prepare
from test_source_policies import item as fixture
from test_product_pipeline import C

QUOTE = 'The company develops cybersecurity software to protect business networks.'


class HumanReviewTests(unittest.TestCase):
    def setUp(self):
        self.store = LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB'])
        self.q = TaskQueue(self.store); self.q.configure(C)
        self.data = ProductStorage(self.store)
        self.item = self.data.save(prepare(replace(fixture(), body=QUOTE))[0])[0]
        self.auto = dict(taxonomy='US-BUSINESS-1', labels=[], status='unclassified', entities=[], topics=[])
        self.data.save_classification(self.item, 'authored-test-only', self.auto)
        self.reviews = HumanReviews(self.store)
        self.catalog = load_taxonomy()
        self.child = next(n['id'] for n in self.catalog['nodes'] if n['name_en'] == 'Cybersecurity')
        self.entries = [dict(id=self.child, quote=QUOTE, reason='Explicit cybersecurity software activity.')]
        for mock in (patch('requests.sessions.Session.request', side_effect=AssertionError('No HTTP in review')),
                     patch('finscope.finbert_backend.LocalFinBERTBackend.from_snapshot', side_effect=AssertionError('No inference in review'))):
            mock.start(); self.addCleanup(mock.stop)

    def save(self, **kwargs):
        options = dict(reason='Business topic explicitly supported by the original.', confirmed=True)
        options.update(kwargs)
        return self.reviews.save(self.item, self.catalog['id'], self.entries, **options)

    def test_append_only_review_overlay_preserves_auto_and_all_view_denominators(self):
        before = self.data.view_revision(); result = self.save()
        self.assertNotEqual(before, self.data.view_revision())
        self.assertEqual(result['reviewer'], 'Local user review')
        self.assertEqual({l['id'] for l in result['labels']}, {self.child, 'technology'})
        self.assertEqual(self.data.classifications(self.catalog['id'])[self.item.article_id], self.auto)
        displayed = self.reviews.overlay([self.item], self.catalog['id'], {self.item.article_id: self.auto})
        projected = project_news([self.item], displayed, self.catalog)
        self.assertNotEqual(projected[0].sectors, ('Unclassified',))
        rows = industry_rows(projected, {}, displayed, self.catalog)
        self.assertEqual(next(r['Articles'] for r in rows if r['ID'] == self.child), 1)
        graph, _ = taxonomy_graph(projected, {}, displayed, self.catalog)
        self.assertTrue(any('Local user review' in e['evidence'] for e in graph['edges']))
        self.assertEqual(len(self.store.list_news()), 1)
        self.assertEqual(self.store.list_analyses(), [])

    def test_restart_taxonomy_and_revocation_preserve_both_histories(self):
        self.save()
        reopened = HumanReviews(LocalNewsStore(self.store.path))
        self.assertIsNotNone(reopened.active(self.item, self.catalog['id']))
        self.assertIsNone(reopened.active(self.item, 'CSRC-JRT0020-2024'))
        reopened.save(self.item, self.catalog['id'], [], confirmed=True, revoke=True)
        self.assertIsNone(reopened.active(self.item, self.catalog['id']))
        self.assertEqual(len(reopened.history(self.item, self.catalog['id'])), 2)
        self.assertEqual(reopened.overlay([self.item], self.catalog['id'], {self.item.article_id:self.auto})[self.item.article_id], self.auto)
        self.assertEqual(len(self.data.classification_history(self.item.article_id, self.catalog['id'])), 1)

    def test_explicit_unknown_is_valid_but_not_automated_success(self):
        self.reviews.save(self.item, self.catalog['id'], [], unclassified=True, reason='Insufficient evidence.', confirmed=True)
        active = self.reviews.active(self.item, self.catalog['id'])
        self.assertEqual(active['status'], 'unclassified'); self.assertEqual(active['labels'], [])
        self.assertEqual(self.data.classification(self.item, 'authored-test-only'), self.auto)

    def test_invalid_nodes_quotes_company_only_and_confirmation_fail_closed(self):
        for entries in ([dict(id='not-a-node', quote=QUOTE, reason='Reason')],
                        [dict(id=['bad'], quote=QUOTE, reason='Reason')],
                        [dict(id=self.child, quote=123, reason='Reason')],
                        [dict(id=self.child, quote='Invented exact quotation that is not in the original.', reason='Reason')],
                        [dict(id=self.child, quote='The company', reason='Name alone')],
                        [dict(id=self.child, quote=QUOTE, reason='')], self.entries*2, []):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.reviews.save(self.item, self.catalog['id'], entries, reason='Reason', confirmed=True)
        with self.assertRaises(ValueError): self.save(confirmed=False)
        with self.assertRaises(ValueError): self.save(unclassified=True)
        self.assertEqual(self.reviews.history(self.item, self.catalog['id']), [])

    def test_changed_text_disables_old_review_and_hides_historical_quotes(self):
        self.save()
        changed = self.data.save(prepare(replace(self.item, body='A completely new fictional business text.'))[0])[0]
        self.assertIsNone(self.reviews.active(changed, self.catalog['id']))
        self.assertNotIn(QUOTE, json.dumps(self.reviews.history(changed, self.catalog['id'])))
        with self.assertRaises(ValueError): self.save()

    def test_revoked_permission_blocks_stale_object_reads_writes_and_overlay(self):
        self.save()
        self.store.update_rights(self.item.article_id, replace(self.item.rights, analyze=False))
        self.assertIsNone(self.reviews.active(self.item, self.catalog['id']))
        with self.assertRaises(ValueError): self.save()
        with self.assertRaises(ValueError): self.reviews.history(self.item, self.catalog['id'])
        self.assertEqual(self.reviews.overlay([self.item], self.catalog['id'], {}), {})

    def test_tampered_stored_label_parent_or_taxonomy_version_cannot_be_effective(self):
        saved = self.save()
        for field, value in (('taxonomy_digest', 'changed'), ('labels', [dict(id='invalid')])):
            altered = {**saved, field: value}
            with closing(self.store.connect()) as db:
                db.execute('UPDATE '+TABLE+' SET payload=?', (json.dumps(altered),)); db.commit()
            self.assertIsNone(self.reviews.active(self.item, self.catalog['id']))

    def test_snapshot_revision_and_effective_labels_refresh_without_new_inference(self):
        state = {}; old = self.data.view_snapshot(state, self.catalog['id'])
        old['computed']['old-chart'] = 'stale'
        self.save(); new = self.data.view_snapshot(state, self.catalog['id'])
        self.assertEqual(new['computed'], {})
        self.assertEqual(new['classes'][self.catalog['id']][self.item.article_id], self.auto)

    def test_apptest_save_all_pages_restore_and_revoke(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'), default_timeout=30)
        app.session_state['product_page'] = 'News Explorer'; app.run()
        self.assertFalse(app.exception)
        self.assertFalse(next(e for e in app.expander if e.label == 'Review Industry Classification').proto.expanded)
        def widget(group, suffix):
            return next(w for w in getattr(app, group) if w.key and w.key.startswith('human_review_') and w.key.endswith(suffix))
        self.assertTrue(widget('button', '_save').disabled)
        widget('multiselect', '_labels').set_value([self.child]).run()
        widget('text_area', '_quote').set_value(QUOTE)
        widget('text_input', '_why').set_value('Explicit software activity.')
        widget('text_area', '_reason').set_value('Supported original topic.')
        widget('checkbox', '_confirm').check().run()
        widget('button', '_save').click().run(); self.assertFalse(app.exception)
        self.assertIsNotNone(self.reviews.active(self.item, self.catalog['id']))
        self.assertFalse(widget('checkbox', '_confirm').value)
        for page in ('Dashboard', 'Industries', 'Knowledge Graph', 'News Explorer'):
            app.radio(key='product_page').set_value(page).run(); self.assertFalse(app.exception)
            self.assertTrue(any('1 Local user review records' in c.value for c in app.caption))
        widget('checkbox', '_revoke_confirm').check().run()
        widget('button', '_revoke').click().run(); self.assertFalse(app.exception)
        self.assertIsNone(self.reviews.active(self.item, self.catalog['id']))

    def test_finite_quotes_follow_expiry_and_source_revocation(self):
        from datetime import datetime, timezone, timedelta
        from finscope.media_use import apply, record_decision
        from finscope.expiring_media import partition
        stamp = datetime.now(timezone.utc)
        scope = dict(source='finnhub', status='research_unverified', reference='Authored test permission',
                     fields=['title','summary'], expires_at=(stamp+timedelta(days=1)).isoformat(), confirmed=True, domains=[])
        raw = replace(self.item, provider='finnhub', source='Authored', body='', summary=QUOTE,
                      url='https://example.invalid/review-test', provenance='')
        finite = apply(raw, scope)
        origin = json.loads(finite.provenance); origin['capture_task_id'] = 'review-fixture'
        finite = self.data.save(prepare(replace(finite, provenance=json.dumps(origin)))[0])[0]
        self.reviews.save(finite, self.catalog['id'], self.entries, reason='Authored topic.', confirmed=True)
        self.assertIsNotNone(self.reviews.active(finite, self.catalog['id']))
        with closing(self.store.connect()) as db:
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
        record_decision(self.store, {**scope, 'status':'restricted', 'reference':'Authored restriction'})
        self.assertIsNone(self.reviews.active(finite, self.catalog['id']))
        with self.assertRaises(ValueError):
            self.reviews.save(finite, self.catalog['id'], self.entries, reason='Reason', confirmed=True)
        with patch('finscope.media_use.utcnow', return_value=stamp+timedelta(days=2)):
            part = partition(self.store)
            with closing(part.connect()) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM '+TABLE).fetchone()[0], 0)

    def test_locale_theme_and_taxonomy_change_do_not_transfer_confirmation(self):
        from streamlit.testing.v1 import AppTest
        from finscope.ui_preferences import save as preference
        self.save()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'), default_timeout=30)
        app.session_state['product_page'] = 'News Explorer'
        for language in ('en', 'zh-CN'):
            for theme in ('dark', 'light'):
                preference(self.store, 'ui_language', language)
                preference(self.store, 'ui_theme', theme)
                app.run(); self.assertFalse(app.exception)
                label = 'Review Industry Classification' if language=='en' else '人工复核行业分类'
                self.assertTrue(any(e.label == label for e in app.expander))
                self.assertTrue(any('fs-news-copy' in m.value and QUOTE in m.value for m in app.markdown))
                self.assertTrue(next(b for b in app.button if b.key and b.key.endswith('_save') and b.key.startswith('human_review_')).disabled)
        preference(self.store, 'ui_language', 'en'); app.run()
        confirm = next(w for w in app.checkbox if w.key and w.key.startswith('human_review_') and w.key.endswith('_confirm'))
        confirm.check().run()
        app.selectbox(key='product_taxonomy').set_value('CSRC-JRT0020-2024').run()
        self.assertFalse(app.exception)
        self.assertFalse(next(w for w in app.checkbox if w.key and w.key.startswith('human_review_') and w.key.endswith('_confirm')).value)


if __name__ == '__main__': unittest.main()
