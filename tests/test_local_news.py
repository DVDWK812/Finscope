"""Local product regressions. All news is authored and all HTTP is mocked."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from finscope.api_sources import Article, APIError, HTTPResponse, fetch_provider
from finscope.demo_pipeline import DemoPipeline
from finscope.local_news import (ContentRights, FetchBlocked, LocalIngestionService,
                                LocalNewsStore, NewsItem, analyze_finbert)

NOW = datetime(2026, 10, 29, 9, tzinfo=timezone.utc)
RIGHTS = ContentRights(True, True, True, False, "Authored unit fixture")


def item(**kwargs):
    record = NewsItem.from_article(Article("authored_synthetic", "Fictional chipmaker grows",
        "", "Fixture author", "Fictional semiconductor profits rise.", NOW.isoformat(), "submitted"), RIGHTS, now=NOW)
    return replace(record, **kwargs)


def pipeline():
    class Encoder:
        revision = "mock-embedding"
        def tokenize(self, texts): return {}, [10]*len(texts)
        def encode(self, texts): return [[1., 0.] for _ in texts]
    class Sentiment:
        def predict(self, records):
            return [SimpleNamespace(label="positive", positive=.8, negative=.1, neutral=.1, revision="mock-finbert")]
    return DemoPipeline(Sentiment(), Encoder())


class LocalNewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = LocalNewsStore(self.root/"local.sqlite3")
        self.now = NOW
        self.calls = []
        def transport(url, params, headers, timeout):
            self.calls.append((url, params, headers))
            return HTTPResponse({"data": [{"title": "Fictional chipmaker grows", "url": "https://example.org/original?ref=source",
                "source": "Fixture wire", "description": "Authored summary", "published_at": NOW.isoformat()}]}, 200, {})
        self.service = LocalIngestionService(self.store, cooldown_path=self.root/"holds.json",
            study_path=self.root/"study.sqlite3", clock=lambda: self.now, transport=transport)

    def fetch(self, **kwargs):
        options = dict(api_key="UNIT-SECRET-ONLY", rights=RIGHTS, remaining=100, explicit=True)
        options.update(kwargs)
        return self.service.fetch("marketaux", "technology", **options)

    def test_no_fetch_during_construction_or_library_reads(self):
        self.assertEqual(self.store.list_news(), [])
        self.assertEqual(self.store.list_analyses(), [])
        self.assertFalse(self.calls)

    def test_real_adapter_preview_preserves_original_source_time_url(self):
        result, rows = self.fetch()
        self.assertEqual((result.status, result.http_status), ("ok", 200))
        self.assertEqual(rows[0].timestamp, NOW.isoformat())
        self.assertEqual(rows[0].timestamp_kind, "published")
        self.assertEqual(rows[0].source, "Fixture wire")
        self.assertEqual(rows[0].url, "https://example.org/original?ref=source")
        self.assertEqual(self.calls[0][1]["group_similar"], "false")
        self.assertEqual(self.store.list_news(), [])  # Fetch is not retention consent.

    def test_secret_never_persisted_or_exported(self):
        _, rows = self.fetch()
        self.store.save_news(rows[0])
        self.assertNotIn("UNIT-SECRET-ONLY", json.dumps(self.store.export()))
        self.assertNotIn(b"UNIT-SECRET-ONLY", self.store.path.read_bytes())

    def test_secret_echo_is_withheld(self):
        self.service.transport = lambda *args: {"data": [{"title": "UNIT-SECRET-ONLY", "url": "https://example.org"}]}
        result, rows = self.fetch()
        self.assertEqual(result.outcome, "unsafe_response")
        self.assertEqual(rows, [])

    def test_explicit_fetch_preview_and_quota_required(self):
        for options in ({"explicit": False}, {"remaining": 0}, {"api_key": None},
                        {"rights": ContentRights()}, {"days": 0}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.fetch(**options)
        self.assertEqual(self.calls, [])

    def test_pause_and_no_gdelt_recreation(self):
        for provider in ("newsdata", "gdelt"):
            with self.subTest(provider=provider), self.assertRaises(FetchBlocked):
                self.service.fetch(provider, "technology", api_key="x", rights=RIGHTS, remaining=100, explicit=True)
        self.assertEqual(self.calls, [])

    def test_spacing_daily_cap_and_restart_enforcement(self):
        self.fetch()
        with self.assertRaisesRegex(FetchBlocked, "60 seconds"):
            self.fetch()
        for _ in range(2):
            self.now += timedelta(seconds=61)
            self.fetch()
        self.now += timedelta(seconds=61)
        with self.assertRaisesRegex(FetchBlocked, "cap reached"):
            self.fetch()
        self.assertEqual(len(self.calls), 3)

    def test_existing_hold_and_malformed_hold_fail_closed(self):
        path = self.root/"holds.json"
        path.write_text(json.dumps({"marketaux": (NOW+timedelta(hours=1)).isoformat()}))
        with self.assertRaisesRegex(FetchBlocked, "cooldown"):
            self.fetch()
        path.write_text("broken")
        with self.assertRaisesRegex(FetchBlocked, "review"):
            self.fetch()
        self.assertFalse(self.calls)

    def test_rate_limit_and_transport_failures_are_safe_and_not_retried(self):
        def fail(*args):
            raise APIError("UNIT-SECRET-ONLY", kind="rate_limit", status=429, rate_headers={"Retry-After": "120"})
        self.service.transport = fail
        result, rows = self.fetch()
        self.assertEqual((result.status, result.outcome), ("failed", "rate_limit"))
        self.assertNotIn("UNIT-SECRET-ONLY", result.note)
        self.now += timedelta(seconds=61)
        with self.assertRaisesRegex(FetchBlocked, "Retry-After"):
            self.fetch()

    def test_unknown_reservation_survives_process_restart(self):
        self.service._reserve("marketaux", 100)
        self.now += timedelta(seconds=100)
        with self.assertRaisesRegex(FetchBlocked, "unknown outcome"):
            self.fetch()
        self.assertFalse(self.calls)

    def test_permissions_separate_preview_retention_and_analysis(self):
        preview_only = item(rights=ContentRights(True, False, False, False, "Preview only"))
        with self.assertRaisesRegex(ValueError, "retain"):
            self.store.save_news(preview_only)
        with self.assertRaisesRegex(ValueError, "analyze"):
            analyze_finbert(preview_only, self.store, pipeline())

    def test_finbert_reuses_pipeline_probabilities_and_persists_originals(self):
        original = item()
        self.store.save_news(original)
        result = analyze_finbert(original, self.store, pipeline())
        self.assertEqual(result.probabilities, {"positive": .8, "negative": .1, "neutral": .1})
        self.assertEqual(result.revision, "mock-finbert")
        self.assertEqual(result.embedding_revision, "mock-embedding")
        restarted = LocalNewsStore(self.store.path)
        self.assertEqual(restarted.list_news(), [original])
        self.assertEqual(restarted.latest_analyses()[original.article_id], result)

    def test_reanalysis_preserves_history_and_excludes_self_matching(self):
        original = item(); self.store.save_news(original)
        first = analyze_finbert(original, self.store, pipeline())
        second = analyze_finbert(original, self.store, pipeline())
        self.assertNotEqual(first.analysis_id, second.analysis_id)
        self.assertIsNone(second.similarity)
        self.assertEqual(len(self.store.list_analyses()), 2)
        self.assertEqual(self.store.list_news(), [original])

    def test_unknown_publication_time_is_not_fabricated(self):
        original = item(timestamp="", publication_date="2026-10-28", timestamp_kind="published")
        self.store.save_news(original)
        result=analyze_finbert(original, self.store, pipeline())
        self.assertEqual(result.label,"Positive")
        self.assertEqual(result.candidate_id,"")
        self.assertEqual(result.provenance["temporal_grouping"],"disabled_unknown_publication_time")
        self.assertEqual(self.store.list_news()[0].timestamp, "")

    def test_model_failure_does_not_save_a_prediction(self):
        original = item(); self.store.save_news(original)
        engine = pipeline(); engine.sentiment.predict = lambda _: (_ for _ in ()).throw(RuntimeError("fixture failure"))
        with self.assertRaises(RuntimeError):
            analyze_finbert(original, self.store, engine)
        self.assertEqual(self.store.list_analyses(), [])
        self.assertEqual(len(self.store.list_news()), 1)

    def test_explicit_ui_key_never_uses_dotenv_and_all_adapters_are_reused(self):
        payloads = {"marketaux": {"data": []}, "newsdata": {"status": "success", "results": []}, "finnhub": []}
        with patch("finscope.api_sources.local_credentials", side_effect=AssertionError("Unexpected .env access")):
            for provider, payload in payloads.items():
                seen = []
                result = fetch_provider(provider, "technology", now=NOW, api_key="UI-SECRET",
                    symbol="MSFT", transport=lambda *args: seen.append(args) or payload)
                self.assertEqual(result.status, "ok")
                self.assertEqual(len(seen), 1)
                self.assertNotIn("UI-SECRET", repr(result))
                if provider == "finnhub":
                    self.assertEqual(seen[0][1]["symbol"], "MSFT")
                    self.assertEqual(result.query_mode, "company_symbol")
            self.assertEqual(fetch_provider("marketaux", "technology", api_key=None).status, "skipped")


if __name__ == "__main__": unittest.main()
