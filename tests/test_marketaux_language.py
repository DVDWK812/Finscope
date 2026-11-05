
"""Authored Marketaux response fixtures; no transport, models, or saved news."""
import json
import unittest
from datetime import datetime, timedelta, timezone

from finscope.api_sources import normalize
from finscope.batch_records import eligibility
from finscope.local_news import ContentRights, NewsItem
from finscope.media_use import apply
from finscope.text_processing import detect_language, prepare


class MarketauxLanguageTests(unittest.TestCase):
    def item(self, title, *, declared=None, summary='', fields=('title',)):
        now = datetime.now(timezone.utc)
        row = {'title': title, 'description': summary, 'url': 'https://example.org/authored-test',
               'source': 'Authored fixture', 'published_at': '2026-11-05T12:00:00+00:00'}
        if declared is not None:
            row['language'] = declared
        (article,), _ = normalize('marketaux', {'data': [row]})
        raw = NewsItem.from_article(article, ContentRights(), now=now)
        return apply(raw, dict(source='marketaux', status='research_unverified',
                               reference='Authored language regression fixture', fields=list(fields),
                               expires_at=(now + timedelta(days=1)).isoformat(), confirmed=True))

    def test_short_headlines_use_explicit_article_language_without_changing_identity(self):
        for title in ('Nvidia lifts revenue outlook', 'NVDA posts record margin', 'Chipmakers cut capital spending'):
            with self.subTest(title=title):
                self.assertEqual(detect_language(title), 'unknown')
                item = self.item(title, declared='en')
                self.assertEqual(item.article_id, self.item(title).article_id)
                self.assertEqual(json.loads(item.provenance)['api_record']['language'], 'en')
                result, evidence = prepare(item)
                self.assertEqual(result.language, 'en')
                self.assertEqual(result.processed_text, title)
                self.assertEqual(evidence['analysis_basis'], 'title')
                self.assertEqual(evidence['declared_language'], 'en')
                self.assertTrue(eligibility(result)[0])

    def test_missing_or_malformed_metadata_does_not_imply_english(self):
        for declared in (None, 'English', ['en']):
            with self.subTest(declared=declared):
                item, evidence = prepare(self.item('Nvidia lifts revenue outlook', declared=declared))
                self.assertEqual(item.language, 'unknown')
                self.assertNotIn('declared_language', evidence)
                self.assertFalse(eligibility(item)[0])

    def test_explicit_english_does_not_override_script_or_ticker_only_guards(self):
        for title, expected in (('NVDA 盈利增长', 'zh'), ('NVDA акции растут', 'unknown'), ('NVDA EPS +2%', 'unknown')):
            with self.subTest(title=title):
                item, _ = prepare(self.item(title, declared='en'))
                self.assertEqual(item.language, expected)
                self.assertFalse(eligibility(item)[0])

    def test_explicit_non_english_is_not_admitted_by_the_vocabulary_heuristic(self):
        title = 'La société a annoncé the new marge'
        self.assertEqual(detect_language(title), 'en')
        item, evidence = prepare(self.item(title, declared='fr'))
        self.assertEqual(item.language, 'fr')
        self.assertEqual(evidence['declared_language'], 'fr')
        self.assertFalse(eligibility(item)[0])

    def test_summary_affects_detection_only_when_permitted(self):
        title = 'Chipmakers cut capital spending'
        summary = 'The company has raised its earnings outlook.'
        title_only, short_evidence = prepare(self.item(title, summary=summary))
        with_summary, long_evidence = prepare(self.item(title, summary=summary, fields=('title', 'summary')))
        self.assertEqual((short_evidence['analysis_basis'], title_only.language, title_only.summary), ('title', 'unknown', ''))
        self.assertEqual((long_evidence['analysis_basis'], with_summary.language), ('summary', 'en'))
        self.assertEqual(with_summary.processed_text, title + '\n' + summary)
