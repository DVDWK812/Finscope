from dataclasses import replace
from datetime import date
import unittest

from finscope.local_analytics import (Filters, daily_counts, evidence_graph, heatmap_cells,
    model_key, overview_counts, sector_counts, select_articles)
from finscope.local_news import Analysis
from test_local_news import item


class LocalAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.first = item(article_id="first", source="Authored A", sectors=("Technology", "Healthcare"), company="MOCK")
        self.second = item(article_id="second", source="Authored B", timestamp="2026-10-28T12:00:00+00:00")
        self.unknown = item(article_id="unknown", timestamp="", publication_date="")
        self.a = Analysis("a", "first", "Positive", "FinBERT", "fixture-finbert", "mock-v1", "2026-10-29T12:00:00Z",
                          probabilities={"positive": .8, "negative": .1, "neutral": .1}, candidate_id="candidate", embedding_revision="mock-vector")
        self.b = replace(self.a, analysis_id="b", article_id="second", label="Negative")
        self.news = [self.first, self.second, self.unknown]

    def test_shared_date_sector_source_label_search_intersection(self):
        selected, results = select_articles(self.news, [self.a, self.b], Filters(
            date(2026,10,29), date(2026,10,29), ("Healthcare",), ("Authored A",), ("Positive",), search="chipmaker"))
        self.assertEqual(selected, [self.first])
        self.assertEqual(set(results), {"first"})
        self.assertEqual(overview_counts(selected, results)["raw_articles"], 1)

    def test_latest_matching_model_and_no_double_counting_reanalysis(self):
        llm = replace(self.a, analysis_id="llm", family="External LLM", revision="mock-llm",
                      label="Neutral", analyzed_at="2026-10-29T13:00:00Z", probabilities=None)
        news, results = select_articles(self.news, [self.a, llm], Filters(models=(model_key(self.a),)))
        self.assertEqual(len(news), 1)
        self.assertEqual(results["first"].label, "Positive")
        all_news, all_results = select_articles(self.news, [self.a, llm], Filters())
        self.assertEqual(len(all_news), 3)
        self.assertEqual(all_results["first"].label, "Neutral")

    def test_unknown_dates_are_explicit_and_never_daily_counts(self):
        start, end = date(2026,10,28), date(2026,10,30)
        news, results = select_articles(self.news, [self.a], Filters(start,end))
        self.assertEqual(len(news), 2)
        news, results = select_articles(self.news, [self.a], Filters(start,end,include_unknown_dates=True))
        self.assertEqual(len(news), 3)
        self.assertEqual(sum(sum(v for k,v in row.items() if k != "Date") for row in daily_counts(news,results,start,end)), 2)

    def test_date_only_is_a_day_not_a_fabricated_timestamp(self):
        record = replace(self.unknown, publication_date="2026-10-29")
        selected, _ = select_articles([record], [], Filters(date(2026,10,29),date(2026,10,29)))
        self.assertEqual(selected, [record])
        self.assertEqual(record.timestamp, "")

    def test_record_day_uses_utc_without_rewriting_original_timestamp(self):
        record = replace(self.first,timestamp="2026-10-29T01:00:00+11:00")
        self.assertEqual(record.record_date,"2026-10-28")
        self.assertEqual(record.timestamp,"2026-10-29T01:00:00+11:00")

    def test_daily_gaps_and_sentiment_denominators(self):
        rows = daily_counts(self.news, {"first":self.a,"second":self.b},date(2026,10,28),date(2026,10,30))
        self.assertEqual([r["Positive"] for r in rows],[0,1,0])
        self.assertEqual([r["Negative"] for r in rows],[1,0,0])
        self.assertEqual(rows[-1]["Not analyzed"],0)

    def test_heatmap_missing_versus_neutral_and_low_sample(self):
        cells = heatmap_cells([self.first], {"first":replace(self.a,label="Neutral")},date(2026,10,29),date(2026,10,30))
        first = next(c for c in cells if c["Date"]=="2026-10-29" and c["Sector"]=="Technology")
        missing = next(c for c in cells if c["Date"]=="2026-10-30" and c["Sector"]=="Technology")
        self.assertEqual((first["Balance"],first["Sample"]),(0,"Low sample (n<3)"))
        self.assertIsNone(missing["Balance"])
        self.assertEqual(missing["Sample"],"No local records")

    def test_sector_multi_label_memberships_and_raw_counts(self):
        rows = sector_counts([self.first], {"first":self.a})
        self.assertEqual(sum(r["Positive"] for r in rows),2)
        self.assertEqual(overview_counts([self.first], {"first":self.a})["raw_articles"],1)

    def test_graph_relationships_have_evidence_and_resolvable_originals(self):
        data = evidence_graph(self.news[:2], {"first":self.a,"second":self.b})
        allowed = {"provider_source","keyword_sector","returned_for_ticker","unverified_cosine_candidate"}
        nodes = {n["id"] for n in data["nodes"]}
        for edge in data["edges"]:
            self.assertIn(edge["relationship"],allowed)
            self.assertTrue(edge["evidence"])
            self.assertIn(edge["from"],nodes)
            self.assertIn(edge["to"],nodes)
            self.assertIn(edge["article_id"],{"first","second"})
        self.assertEqual({n["article_id"] for n in data["nodes"] if n["kind"]=="Article"},{"first","second"})
        self.assertTrue(any(n["kind"]=="Unverified candidate" for n in data["nodes"]))
        self.assertFalse(any("caus" in e["relationship"] for e in data["edges"]))

    def test_empty_and_range_bounds(self):
        self.assertEqual(evidence_graph([],{}), {"nodes":[],"edges":[]})
        with self.assertRaises(ValueError):
            heatmap_cells([],{},date(2024,1,1),date(2026,1,1))
        with self.assertRaises(ValueError):
            select_articles([],[],Filters(date(2026,10,30),date(2026,10,29)))

