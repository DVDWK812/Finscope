import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from finscope.api_sources import APIError, build_request, fetch_provider, normalize
from finscope.benchmark import summarize


NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


class NormalizationTests(unittest.TestCase):
    def test_gdelt_first_seen_not_mislabelled_publication(self):
        items, count = normalize("gdelt", {"articles": [{
            "title": "Copper demand rises", "url": "https://example.org/story",
            "domain": "example.org", "seendate": "20261023T150000Z",
        }]})
        self.assertEqual(count, 1)
        self.assertEqual(items[0].timestamp_kind, "first_seen")
        self.assertEqual(items[0].timestamp, "2026-10-23T15:00:00+00:00")
        self.assertEqual(items[0].description, "")

    def test_marketaux_parsing(self):
        items, _ = normalize("marketaux", {"data": [{
            "title": "Chipmakers rally", "url": "https://example.com/news",
            "description": "Semiconductor sector", "source": "ExampleWire",
            "published_at": "2026-10-23T12:00:00.000000Z",
        }]})
        self.assertEqual(items[0].source, "ExampleWire")
        self.assertEqual(summarize(items)["description_available_ratio_among_valid"], 1.0)

    def test_newsdata_parsing(self):
        items, _ = normalize("newsdata", {"status": "success", "results": [{
            "title": "Bank lending expands", "link": "https://example.org/bank",
            "description": "Business update", "pubDate": "2026-10-23 09:00:00",
            "source_name": "Example",
        }]})
        self.assertEqual(items[0].timestamp_kind, "published")
        self.assertEqual(items[0].source, "Example")

    def test_finnhub_parsing(self):
        items, _ = normalize("finnhub", [{
            "headline": "Company reports profits", "url": "https://example.com/report",
            "source": "Example", "summary": "Quarterly update", "datetime": 1792800000,
        }])
        self.assertEqual(items[0].timestamp_kind, "published")
        self.assertIn("+00:00", items[0].timestamp)

    def test_reject_invalid_entries(self):
        items, count = normalize("marketaux", {"data": [
            {"title": "", "url": "https://a.com"},
            {"title": "A", "url": "javascript:alert(1)"},
        ]})
        self.assertEqual(count, 2)
        self.assertEqual(items, [])


class RequestTests(unittest.TestCase):
    def test_marketaux_disables_provider_dedup(self):
        _, params, _, mode, _ = build_request("marketaux", "materials", NOW, 2, 50, "fake-key")
        self.assertEqual(params["group_similar"], "false")
        self.assertEqual(params["limit"], 3)
        self.assertEqual(mode, "keyword")

    def test_newsdata_uses_header_auth(self):
        _, params, headers, _, _ = build_request("newsdata", "healthcare", NOW, 2, 5, "fake-key")
        self.assertNotIn("apikey", params)
        self.assertEqual(headers["X-ACCESS-KEY"], "fake-key")

    def test_finnhub_marked_symbol_scoped(self):
        _, params, _, mode, _ = build_request("finnhub", "technology", NOW, 2, 3, "fake-key")
        self.assertEqual(params["symbol"], "NVDA")
        self.assertEqual(mode, "company_symbol")

    def test_missing_credentials_are_skipped(self):
        with patch.dict(os.environ, {}, clear=True):
            result = fetch_provider("marketaux", "technology", now=NOW)
        self.assertEqual(result.status, "skipped")

    def test_transport_error_is_redacted(self):
        def fake_transport(*args):
            raise APIError("HTTP 429")
        with patch.dict(os.environ, {"MARKETAUX_API_KEY": "TOP-SECRET"}):
            result = fetch_provider("marketaux", "technology", now=NOW, transport=fake_transport)
        self.assertEqual(result.status, "failed")
        self.assertIn("HTTP 429", result.note)
        self.assertNotIn("TOP-SECRET", result.note)

    def test_fixture_success_with_mock_transport(self):
        def fake_transport(*args):
            return {"data": [{"title": "Copper market rises", "url": "https://example.org/a"}]}
        with patch.dict(os.environ, {"MARKETAUX_API_KEY": "test"}):
            result = fetch_provider("marketaux", "materials", now=NOW, transport=fake_transport)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.articles), 1)


if __name__ == "__main__":
    unittest.main()
