import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import requests

from finscope.api_sources import (APIError, build_request, fetch_provider, normalize,
                                  _http_get_json, local_credentials)
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

    def test_missing_arrays_and_provider_errors_are_not_empty_success(self):
        for provider, payload in (("gdelt", {}), ("marketaux", {"error": "bad token"}),
                                  ("newsdata", {"status": "success"}),
                                  ("newsdata", {"status": "error"}), ("finnhub", {})):
            with self.subTest(provider=provider, payload=payload), self.assertRaises(APIError):
                normalize(provider, payload)

    def test_explicit_empty_arrays_are_valid(self):
        for provider, payload in (("gdelt", {"articles": []}), ("marketaux", {"data": []}),
                                  ("newsdata", {"status": "success", "results": []}),
                                  ("finnhub", [])):
            with self.subTest(provider=provider):
                self.assertEqual(normalize(provider, payload), ([], 0))

    def test_hostname_required_and_original_url_retained(self):
        url = "https://example.org/story?ref=original#part"
        items, count = normalize("marketaux", {"data": [
            {"title": "bad", "url": "https:///missing-host"},
            {"title": "bad", "url": "https://[broken"},
            {"title": "valid", "url": url}]})
        self.assertEqual(count, 3)
        self.assertEqual([a.url for a in items], [url])

    def test_publication_dates_are_validated_and_utc(self):
        items, _ = normalize("marketaux", {"data": [
            {"title": "A", "url": "https://example.org", "published_at": "not-a-date"},
            {"title": "B", "url": "https://example.org", "published_at": "2026-10-24T01:00:00+11:00"}]})
        self.assertEqual(items[0].timestamp, "")
        self.assertEqual(items[1].timestamp, "2026-10-23T14:00:00+00:00")


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
        self.assertEqual(params["timezone"], "UTC")

    def test_finnhub_marked_symbol_scoped(self):
        _, params, _, mode, _ = build_request("finnhub", "technology", NOW, 2, 3, "fake-key")
        self.assertEqual(params["symbol"], "NVDA")
        self.assertEqual(mode, "company_symbol")

    def test_missing_credentials_are_skipped(self):
        with patch("finscope.api_sources.local_credentials", return_value={}):
            result = fetch_provider("marketaux", "technology", now=NOW)
        self.assertEqual(result.status, "skipped")

    def test_only_local_dotenv_credentials_are_loaded(self):
        with patch.dict(os.environ, {"MARKETAUX_API_KEY": "SHELL-SECRET"}), \
                patch("finscope.api_sources.dotenv_values", return_value={}) as reader:
            self.assertEqual(local_credentials(), {})
        self.assertEqual(reader.call_args.args[0].name, ".env")
        self.assertFalse(reader.call_args.kwargs["interpolate"])

    def test_request_dates_use_utc(self):
        local = datetime(2026, 10, 24, 1, tzinfo=timezone(timedelta(hours=11)))
        _, params, _, _, _ = build_request("finnhub", "technology", local, 2, 3, "test")
        self.assertEqual(params["to"], "2026-10-23")

    def test_transport_error_is_redacted(self):
        def fake_transport(*args):
            raise APIError("HTTP 429 TOP-SECRET", kind="rate_limit", status=429)
        with patch("finscope.api_sources.local_credentials", return_value={"MARKETAUX_API_KEY": "TOP-SECRET"}):
            result = fetch_provider("marketaux", "technology", now=NOW, transport=fake_transport)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.http_status, 429)
        self.assertEqual(result.outcome, "rate_limit")
        self.assertNotIn("TOP-SECRET", result.note)

    def test_fixture_success_with_mock_transport(self):
        def fake_transport(*args):
            return {"data": [{"title": "Copper market rises", "url": "https://example.org/a"}]}
        with patch("finscope.api_sources.local_credentials", return_value={"MARKETAUX_API_KEY": "test"}):
            result = fetch_provider("marketaux", "materials", now=NOW, transport=fake_transport)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.articles), 1)

    def test_normalized_count_is_before_local_cap(self):
        rows = [{"headline": str(i), "url": "https://example.org/" + str(i)} for i in range(5)]
        rows.append({"headline": "invalid", "url": "https:///bad"})
        with patch("finscope.api_sources.local_credentials", return_value={"FINNHUB_API_KEY": "test"}):
            result = fetch_provider("finnhub", "technology", limit=3, transport=lambda *args: rows)
        self.assertEqual(result.raw_count, 6)
        self.assertEqual(result.normalized_count, 5)
        self.assertEqual(len(result.articles), 3)

    def test_empty_and_invalid_records_are_distinguished(self):
        empty = fetch_provider("gdelt", "technology", transport=lambda *args: {"articles": []})
        invalid = fetch_provider("gdelt", "technology", transport=lambda *args: {"articles": [{}]})
        self.assertEqual((empty.status, empty.outcome), ("ok", "empty"))
        self.assertEqual((invalid.status, invalid.outcome), ("failed", "invalid_records"))


class TransportTests(unittest.TestCase):
    @patch("finscope.api_sources.requests.get")
    def test_auth_rate_limit_and_http_classification(self, get):
        for status, kind in ((401, "auth"), (403, "auth"), (429, "rate_limit"), (503, "http")):
            get.return_value = Mock(status_code=status, headers={"Retry-After": "60", "Secret": "never"})
            with self.subTest(status=status), self.assertRaises(APIError) as caught:
                _http_get_json("https://example.org", {}, {}, 1)
            self.assertEqual(caught.exception.kind, kind)
            self.assertEqual(caught.exception.rate_headers, {"Retry-After": "60"})
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    @patch("finscope.api_sources.requests.get")
    def test_invalid_json_preserves_status_and_safe_headers(self, get):
        get.return_value = Mock(status_code=200, headers={"X-RateLimit-Remaining": "4", "Retry-After": "SECRET"})
        get.return_value.json.side_effect = ValueError("SECRET body")
        with self.assertRaises(APIError) as caught:
            _http_get_json("https://example.org", {}, {}, 1)
        self.assertEqual(caught.exception.status, 200)
        self.assertEqual(caught.exception.kind, "invalid_json")
        self.assertEqual(caught.exception.rate_headers, {"X-RateLimit-Remaining": "4"})
        self.assertNotIn("SECRET", str(caught.exception))

    @patch("finscope.api_sources.requests.get")
    def test_timeout_does_not_leak_request_url(self, get):
        get.side_effect = requests.Timeout("https://example.org?api_token=SECRET")
        with self.assertRaises(APIError) as caught:
            _http_get_json("https://example.org", {}, {}, 1)
        self.assertEqual(caught.exception.kind, "transport")
        self.assertNotIn("SECRET", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
