"""Regression tests for the offline UI data adapter; no Streamlit required."""
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from finscope.ui_data import (
    ArticleRecord, SyntheticNewsRepository, daily_sentiment_counts,
    filter_articles, headline_metrics, sector_sentiment_counts, unique_events,
)


class SyntheticUITests(unittest.TestCase):
    def setUp(self):
        self.anchor = date(2026, 10, 24)
        self.rows = SyntheticNewsRepository(self.anchor).list_articles()

    def test_fixtures_are_synthetic_and_offline(self):
        self.assertEqual(len(self.rows), 12)
        self.assertTrue(all(a.synthetic and a.url is None for a in self.rows))
        self.assertEqual(len({a.event_id for a in self.rows}), 10)

    def test_dedup_preserves_source_records_and_deterministic_representative(self):
        out = unique_events(list(reversed(self.rows)))
        self.assertEqual(len(out), 10)
        self.assertEqual(out, unique_events(self.rows))
        self.assertEqual(next(a for a in out if a.event_id == "e01").article_id, "a01")
        self.assertEqual(len(self.rows), 12)

    def test_multi_label_filter(self):
        filtered = filter_articles(self.rows, sectors=["Healthcare"])
        self.assertEqual({a.article_id for a in filtered}, {"a05", "a08", "a09"})

    def test_source_and_sentiment_filters(self):
        filtered = filter_articles(self.rows, sources=["Demo Wire C"], sentiments=["Negative"])
        self.assertEqual([a.article_id for a in filtered], ["a04"])

    def test_date_range_inclusive(self):
        filtered = filter_articles(self.rows, start=self.anchor, end=self.anchor)
        self.assertEqual(len(filtered), 3)

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            filter_articles(self.rows, start=self.anchor, end=date(2026, 10, 20))

    def test_sector_aggregation_multilabel(self):
        sectors = {r["Sector"]: r for r in sector_sentiment_counts(unique_events(self.rows))}
        self.assertEqual(sectors["Healthcare"]["Positive"], 1)
        self.assertEqual(sectors["Technology"]["Positive"], 2)

    def test_empty_filter_safe(self):
        self.assertEqual(headline_metrics([], [])["positive_share"], 0)
        self.assertEqual(daily_sentiment_counts([]), [])

    def test_metrics_distinguish_raw_vs_unique(self):
        results = headline_metrics(self.rows, unique_events(self.rows))
        self.assertEqual(results["raw_articles"], 12)
        self.assertEqual(results["unique_events"], 10)
        self.assertEqual(results["sources"], 3)

    def test_positive_share_changes_with_counting_basis(self):
        self.assertEqual(headline_metrics(self.rows, self.rows)["positive_share"], 50.0)
        self.assertEqual(headline_metrics(self.rows, unique_events(self.rows))["positive_share"], 40.0)

    def test_multi_sector_filter_does_not_duplicate_matching_articles(self):
        rows = filter_articles(self.rows, sectors=["Healthcare", "Technology"])
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(unique_events(rows)), 4)
        self.assertEqual(len({a.article_id for a in rows}), len(rows))

    def test_source_filter_runs_before_event_representative_selection(self):
        rows = unique_events(filter_articles(self.rows, sources=["Demo Wire C"]))
        self.assertEqual(next(a for a in rows if a.event_id == "e07").article_id, "a09")

    def test_cross_filter_empty_and_reset_equivalent(self):
        self.assertEqual(filter_articles(self.rows, sectors=["Healthcare"], sentiments=["Negative"]), [])
        self.assertEqual(filter_articles(self.rows), self.rows)

    def test_multilabel_totals_distinguish_articles_and_events(self):
        for rows, total in ((self.rows, 14), (unique_events(self.rows), 11)):
            self.assertEqual(sum(r[s] for r in sector_sentiment_counts(rows) for s in ("Positive", "Neutral", "Negative")), total)

    def test_filters_and_trends_use_utc_day_for_non_utc_timestamps(self):
        row = replace(self.rows[0], timestamp=datetime(2026, 10, 24, 0, 30,
                      tzinfo=timezone(timedelta(hours=11))))
        self.assertEqual(filter_articles([row], start=date(2026, 10, 23), end=date(2026, 10, 23)), [row])
        self.assertEqual(filter_articles([row], start=self.anchor), [])
        self.assertEqual(daily_sentiment_counts([row])[0]["Date"], "2026-10-23")

    def test_daily_counts_fill_gaps_and_selected_range_boundaries(self):
        rows = filter_articles(self.rows, sectors=["Technology"])
        daily = daily_sentiment_counts(rows, start=date(2026, 10, 20), end=self.anchor)
        self.assertEqual(len(daily), 5)
        self.assertEqual(daily[0], {"Date": "2026-10-20", "Positive": 0, "Neutral": 0, "Negative": 0})
        self.assertEqual(daily[-1]["Positive"], 1)
        self.assertEqual(sum(r[s] for r in daily for s in ("Positive", "Neutral", "Negative")), len(rows))

    def test_daily_counts_reject_inverted_range(self):
        with self.assertRaises(ValueError):
            daily_sentiment_counts(self.rows, start=self.anchor, end=date(2026, 10, 20))

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            ArticleRecord("id", "ev", "title", "Demo", ("Energy",), "Neutral", datetime(2026, 10, 24), "published")

    def test_synthetic_url_rejected(self):
        with self.assertRaises(ValueError):
            ArticleRecord("id", "ev", "title", "Demo", ("Energy",), "Neutral", datetime.now(timezone.utc), "published", url="https://example.com")


if __name__ == "__main__":
    unittest.main()
