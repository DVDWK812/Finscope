"""Authored, offline review boundaries and four-view integration; no model calls."""
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from finscope.human_review import HumanReviews, TABLE, SOURCE
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
        self.ids = [self.child]
        for mock in (patch('requests.sessions.Session.request', side_effect=AssertionError('No HTTP in review')),
                     patch('finscope.finbert_backend.LocalFinBERTBackend.from_snapshot', side_effect=AssertionError('No inference in review'))):
            mock.start(); self.addCleanup(mock.stop)

    def save(self, **kwargs):
        return self.reviews.save(self.item, self.catalog['id'], self.ids, **kwargs)

    def seed_legacy(self):
        # Use the original persisted shape (including a parent inherited from a child).
        saved = self.save()
        old = {k: v for k, v in saved.items() if k not in ('format_version', 'industry_ids', 'note', 'method')}
        start = len(self.item.title) + len(self.item.summary) + 2
        evidence = [dict(quote=QUOTE, start=start, end=start+len(QUOTE))]
        label = dict(id=self.child, parent_id='technology', method='Local user review',
                     evidence=evidence, reason='Explicit cybersecurity software activity.')
        old.update(reason='Legacy review reason.', labels=[label, {**label, 'id':'technology', 'parent_id':None, 'derived_from':self.child}])
        with closing(self.store.connect()) as db:
            db.execute('UPDATE '+TABLE+' SET payload=? WHERE id=?', (json.dumps(old), saved['id'])); db.commit()
        return old

    def test_append_only_review_overlay_preserves_auto_and_all_view_denominators(self):
        before = self.data.view_revision(); result = self.save()
        self.assertNotEqual(before, self.data.view_revision())
        self.assertEqual(result['reviewer'], 'Local user review')
        self.assertEqual(result['industry_ids'], self.ids)
        self.assertEqual(result['note'], '')
        for field in ('labels', 'evidence', 'quote', 'reason', 'evidence_attestation'):
            self.assertNotIn(field, result)
        active = self.reviews.active(self.item, self.catalog['id'])
        self.assertEqual({l['id'] for l in active['labels']}, {self.child, 'technology'})
        self.assertEqual(self.data.classifications(self.catalog['id'])[self.item.article_id], self.auto)
        displayed = self.reviews.overlay([self.item], self.catalog['id'], {self.item.article_id: self.auto})
        projected = project_news([self.item], displayed, self.catalog)
        self.assertNotEqual(projected[0].sectors, ('Unclassified',))
        rows = industry_rows(projected, {}, displayed, self.catalog)
        self.assertEqual(next(r['Articles'] for r in rows if r['ID'] == self.child), 1)
        graph, _ = taxonomy_graph(projected, {}, displayed, self.catalog)
        edges = [e for e in graph['edges'] if e['from'].startswith('article:')]
        self.assertEqual(len(edges), 2)
        self.assertTrue(all(e['relationship']=='manual_industry_selection' and e['source']==SOURCE and not e['evidence'] for e in edges))
        self.assertEqual(len(self.store.list_news()), 1)
        self.assertEqual(self.store.list_analyses(), [])

    def test_restart_taxonomy_and_revocation_preserve_both_histories(self):
        self.save()
        reopened = HumanReviews(LocalNewsStore(self.store.path))
        self.assertIsNotNone(reopened.active(self.item, self.catalog['id']))
        self.assertIsNone(reopened.active(self.item, 'CSRC-JRT0020-2024'))
        reopened.save(self.item, self.catalog['id'], [], revoke=True)
        self.assertIsNone(reopened.active(self.item, self.catalog['id']))
        self.assertEqual(len(reopened.history(self.item, self.catalog['id'])), 2)
        self.assertEqual(reopened.overlay([self.item], self.catalog['id'], {self.item.article_id:self.auto})[self.item.article_id], self.auto)
        self.assertEqual(len(self.data.classification_history(self.item.article_id, self.catalog['id'])), 1)

    def test_explicit_unknown_is_valid_but_not_automated_success(self):
        self.reviews.save(self.item, self.catalog['id'], [], unclassified=True)
        active = self.reviews.active(self.item, self.catalog['id'])
        self.assertEqual(active['status'], 'unclassified'); self.assertEqual(active['labels'], [])
        self.assertEqual(self.data.classification(self.item, 'authored-test-only'), self.auto)

    def test_invalid_nodes_empty_selection_and_note_limits(self):
        for ids in (['not-a-node'], [['bad']], self.ids*2, [], 'technology'):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.reviews.save(self.item, self.catalog['id'], ids)
        with self.assertRaises(ValueError): self.save(note='x'*501)
        with self.assertRaises(ValueError): self.save(note=None)
        with self.assertRaises(ValueError): self.save(unclassified=True)
        self.assertEqual(self.reviews.history(self.item, self.catalog['id']), [])

    def test_legacy_evidence_remains_visible_and_effective_without_rewriting_history(self):
        old = self.seed_legacy()
        active = self.reviews.active(self.item, self.catalog['id'])
        self.assertEqual(active['industry_ids'], self.ids)
        self.assertEqual(active['labels'], old['labels'])
        self.assertEqual(active['reason'], old['reason'])
        self.assertEqual(self.reviews.history(self.item, self.catalog['id']), [old])
        graph, _ = taxonomy_graph([self.item], {}, self.reviews.overlay([self.item], self.catalog['id'], {}), self.catalog)
        edges = [e for e in graph['edges'] if e['from'].startswith('article:')]
        self.assertEqual(len(edges), 2)
        self.assertTrue(all(e['relationship']=='manual_industry_selection' and not e['evidence'] for e in edges))
        newer = self.reviews.save(self.item, self.catalog['id'], ['technology'], note='Short editorial note.')
        self.assertEqual(self.reviews.history(self.item, self.catalog['id']), [old, newer])
        graph, _ = taxonomy_graph([self.item], {}, self.reviews.overlay([self.item], self.catalog['id'], {}), self.catalog)
        self.assertNotIn(newer['note'], json.dumps(graph))

    def test_changed_text_disables_old_review_and_hides_quotes_and_notes(self):
        self.seed_legacy()
        self.save(note='A note tied to the old version.')
        changed = self.data.save(prepare(replace(self.item, body='A completely new fictional business text.'))[0])[0]
        self.assertIsNone(self.reviews.active(changed, self.catalog['id']))
        history = json.dumps(self.reviews.history(changed, self.catalog['id']))
        self.assertNotIn(QUOTE, history)
        self.assertNotIn('A note tied to the old version.', history)
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
        for field, value in (('taxonomy_digest', 'changed'), ('industry_ids', ['invalid']), ('status', 'wrong')):
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
        self.assertFalse(any(w.key and w.key.startswith('human_review_') for w in app.checkbox))
        widget('multiselect', '_industries').set_value(['technology', None]).run()
        self.assertTrue(widget('button', '_save').disabled)
        widget('multiselect', '_industries').set_value(['technology']).run()
        self.assertEqual(widget('text_area', '_note').value, '')
        widget('button', '_save').click().run(); self.assertFalse(app.exception)
        self.assertEqual(self.reviews.active(self.item, self.catalog['id'])['industry_ids'], ['technology'])
        for page in ('Dashboard', 'Industries', 'Knowledge Graph', 'News Explorer'):
            app.radio(key='product_page').set_value(page).run(); self.assertFalse(app.exception)
            self.assertTrue(any('1 Local user review records' in c.value for c in app.caption))
        self.assertEqual(widget('multiselect', '_industries').value, ['technology'])
        widget('multiselect', '_industries').set_value([self.child]).run()
        widget('text_area', '_note').set_value('Updated note.')
        widget('button', '_save').click().run(); self.assertFalse(app.exception)
        self.assertEqual(self.reviews.active(self.item, self.catalog['id'])['note'], 'Updated note.')
        widget('multiselect', '_industries').set_value([None]).run()
        widget('button', '_save').click().run()
        self.assertEqual(self.reviews.active(self.item, self.catalog['id'])['status'], 'unclassified')
        widget('button', '_revoke').click().run(); self.assertFalse(app.exception)
        self.assertIsNone(self.reviews.active(self.item, self.catalog['id']))
        self.assertEqual(len(self.reviews.history(self.item, self.catalog['id'])), 4)
        self.assertTrue(widget('button', '_save').disabled)

    def test_finite_reviews_follow_expiry_and_source_revocation(self):
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
        self.reviews.save(finite, self.catalog['id'], self.ids, note='Authored topic.')
        self.assertIsNotNone(self.reviews.active(finite, self.catalog['id']))
        with closing(self.store.connect()) as db:
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone())
        record_decision(self.store, {**scope, 'status':'restricted', 'reference':'Authored restriction'})
        self.assertIsNone(self.reviews.active(finite, self.catalog['id']))
        with self.assertRaises(ValueError):
            self.reviews.save(finite, self.catalog['id'], self.ids)
        with patch('finscope.media_use.utcnow', return_value=stamp+timedelta(days=2)):
            part = partition(self.store)
            with closing(part.connect()) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM '+TABLE).fetchone()[0], 0)

    def test_locale_theme_and_taxonomy_change_keep_legacy_history_scoped(self):
        from streamlit.testing.v1 import AppTest
        from finscope.ui_preferences import save as preference
        self.seed_legacy()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'), default_timeout=30)
        app.session_state['product_page'] = 'News Explorer'
        for language in ('en', 'zh-CN'):
            for theme in ('dark', 'light'):
                preference(self.store, 'ui_language', language)
                preference(self.store, 'ui_theme', theme)
                app.run(); self.assertFalse(app.exception)
                label = 'Review Industry Classification' if language=='en' else '人工复核行业分类'
                self.assertTrue(any(e.label == label for e in app.expander))
                self.assertTrue(any(QUOTE in str(j.value) for j in app.json))
                note = 'Note (optional)' if language=='en' else '备注（选填）'
                self.assertTrue(any(w.label == note and w.value == '' for w in app.text_area))
        preference(self.store, 'ui_language', 'en'); app.run()
        app.selectbox(key='product_taxonomy').set_value('CSRC-JRT0020-2024').run()
        self.assertFalse(app.exception)
        save = next(b for b in app.button if b.key and b.key.endswith('_save') and b.key.startswith('human_review_'))
        self.assertTrue(save.disabled)


if __name__ == '__main__': unittest.main()
