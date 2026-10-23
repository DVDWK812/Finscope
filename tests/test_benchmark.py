import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from finscope.api_sources import Article, QueryResult
from finscope.benchmark import run


class BenchmarkTests(unittest.TestCase):
    def execute(self, args):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "report.json"
            with contextlib.redirect_stdout(io.StringIO()), \
                    patch("finscope.benchmark.COOLDOWN_PATH", Path(folder) / "cooldowns.json"):
                code = run([*args, "--output", str(output)])
            return code, json.loads(output.read_text(encoding="utf-8"))

    @patch("finscope.benchmark.fetch_provider")
    @patch("finscope.benchmark.local_credentials", return_value={"MARKETAUX_API_KEY": "SECRET"})
    def test_dry_run_has_query_metadata_and_never_calls_provider(self, credentials, fetch):
        code, report = self.execute(["--dry-run"])
        fetch.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(len(report["results"]), 12)
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertNotIn("REDACTED", json.dumps(report))
        self.assertTrue(all(row["query_at_utc"].endswith("+00:00") for row in report["results"]))
        self.assertTrue(all("query_parameters" in row for row in report["results"]))

    @patch("finscope.benchmark.time.sleep")
    @patch("finscope.benchmark.local_credentials", return_value={})
    @patch("finscope.benchmark.fetch_provider")
    def test_provider_order_and_duplicate_inputs_do_not_spend_extra_quota(self, fetch, credentials, sleep):
        fetch.side_effect = lambda provider, topic, **kwargs: QueryResult(
            provider, topic, "keyword", "skipped", [], outcome="missing_credentials")
        code, report = self.execute(["--providers", "gdelt", "marketaux", "gdelt",
                                     "--topics", "technology", "healthcare", "technology"])
        self.assertEqual(code, 0)
        self.assertEqual([call.args for call in fetch.call_args_list], [
            ("gdelt", "technology"), ("gdelt", "healthcare"),
            ("marketaux", "technology"), ("marketaux", "healthcare")])
        sleep.assert_called_once()

    @patch("finscope.benchmark.local_credentials", return_value={})
    @patch("finscope.benchmark.fetch_provider")
    def test_report_separates_normalization_from_sample_truncation(self, fetch, credentials):
        article = Article("finnhub", "Synthetic headline", "https://example.org/a", "example.org",
                          "Do not persist body or summary", "", "published")
        fetch.return_value = QueryResult("finnhub", "technology", "company_symbol", "ok", [article],
                                         raw_count=10, normalized_count=8, outcome="records")
        code, report = self.execute(["--providers", "finnhub", "--topics", "technology", "--limit", "1"])
        row = report["results"][0]
        self.assertEqual(row["valid_article_ratio"], 0.8)
        self.assertEqual(row["valid_articles"], 1)
        self.assertTrue(row["sample_truncated"])
        self.assertEqual(row["samples"][0]["url"], article.url)
        self.assertNotIn(article.description, json.dumps(report))

    @patch("finscope.benchmark.local_credentials", return_value={})
    @patch("finscope.benchmark.fetch_provider")
    def test_failed_live_attempt_writes_report_and_returns_nonzero(self, fetch, credentials):
        fetch.return_value = QueryResult("gdelt", "technology", "keyword", "failed", [], outcome="transport")
        code, report = self.execute(["--providers", "gdelt", "--topics", "technology"])
        self.assertEqual(code, 1)
        self.assertEqual(report["results"][0]["status"], "failed")

    @patch("finscope.benchmark.time.sleep")
    @patch("finscope.benchmark.local_credentials", return_value={})
    @patch("finscope.benchmark.fetch_provider")
    def test_rate_limit_stops_provider_without_stopping_other_providers(self, fetch, credentials, sleep):
        def result(provider, topic, **kwargs):
            if provider == "gdelt":
                return QueryResult(provider, topic, "keyword", "failed", [], http_status=429,
                                   outcome="rate_limit")
            return QueryResult(provider, topic, "not_run", "skipped", [], outcome="missing_credentials")
        fetch.side_effect = result
        code, report = self.execute(["--providers", "gdelt", "marketaux"])
        self.assertEqual(code, 1)
        self.assertEqual(fetch.call_count, 4)  # One GDELT attempt plus three other-provider checks.
        sleep.assert_not_called()
        self.assertEqual([r["outcome"] for r in report["results"][:3]],
                         ["rate_limit", "provider_rate_limited", "provider_rate_limited"])
        self.assertFalse(report["results"][1]["request_attempted"])
        self.assertIsNone(report["results"][1]["request_at_utc"])

    @patch("finscope.benchmark.local_credentials", return_value={})
    @patch("finscope.benchmark.fetch_provider")
    def test_second_invocation_respects_persisted_retry_after(self, fetch, credentials):
        fetch.return_value = QueryResult("gdelt", "healthcare", "keyword", "failed", [],
                                         http_status=429, rate_limit_headers={"Retry-After": "3600"})
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), \
                patch("finscope.benchmark.COOLDOWN_PATH", Path(folder) / "cooldowns.json"):
            args = ["--providers", "gdelt", "--topics", "healthcare", "--output", str(Path(folder) / "report.json")]
            self.assertEqual(run(args), 1)
            self.assertEqual(run(args), 0)
            row = json.loads((Path(folder) / "report.json").read_text())["results"][0]
        fetch.assert_called_once()
        self.assertEqual(row["outcome"], "provider_cooldown")
        self.assertFalse(row["request_attempted"])

    @patch("finscope.benchmark.fetch_provider")
    def test_corrupt_cooldown_state_fails_closed(self, fetch):
        with tempfile.TemporaryDirectory() as folder, \
                patch("finscope.benchmark.COOLDOWN_PATH", Path(folder) / "state.json"):
            (Path(folder) / "state.json").write_text("broken", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                run(["--providers", "gdelt"])
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
