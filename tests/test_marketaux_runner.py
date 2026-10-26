import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from finscope.api_sources import Article, QueryResult
from finscope.marketaux_runner import execute_one, run
from finscope.sampling import STUDY_ID


class MarketauxRunnerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 1, tzinfo=timezone.utc)
        self.approval = {"study_id": STUDY_ID, "explicit_user_authorization": True,
                         "approved_dates": ["2026-10-26"], "approved_sectors": ["healthcare"]}
        self.quota = {"observed_at": self.now.isoformat(), "period_start": "2026-10-26T00:00:00+00:00",
                      "period_end": "2026-10-27T00:00:00+00:00", "remaining": 3}

    def test_default_and_dry_run_never_read_credentials_approval_or_create_sampler(self):
        for args in ([], ["--dry-run", "--approval-file", "DO_NOT_READ"]):
            with patch("finscope.marketaux_runner.local_credentials") as keys, \
                    patch("finscope.marketaux_runner.MarketauxSampler") as sampler, \
                    patch("finscope.marketaux_runner.read_evidence") as evidence, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run(args), 0)
                self.assertEqual(json.loads(output.getvalue())["requests_executed"], 0)
                keys.assert_not_called(); sampler.assert_not_called(); evidence.assert_not_called()

    def test_execute_without_evidence_files_never_attempts_http(self):
        with patch("finscope.marketaux_runner.fetch_provider") as fetch, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run(["--execute"]), 1)
        self.assertFalse(json.loads(output.getvalue())["this_invocation_request_attempted"])
        fetch.assert_not_called()

    def test_approval_does_not_authorize_other_sectors_or_dates_or_extra_fields(self):
        invalid = [self.approval | {"explicit_user_authorization": False},
                   self.approval | {"approved_dates": ["2026-10-27"]},
                   self.approval | {"provider_override": "gdelt"},
                   self.approval | {"approved_sectors": ["materials"]}]
        with patch("finscope.marketaux_runner.local_credentials") as keys:
            for approval in invalid:
                result = execute_one("healthcare", approval, self.quota, clock=lambda: self.now)
                self.assertFalse(result["this_invocation_request_attempted"])
                self.assertEqual(result["reason"], "invalid_explicit_approval")
            keys.assert_not_called()

    def test_single_mock_dispatch_preserves_ledger_then_duplicate_is_blocked(self):
        record = Article("marketaux", "Invented title", "https://example.org", "example.org",
                          "Invented private description", self.now.isoformat(), "published")
        fetch = Mock(return_value=QueryResult("marketaux", "healthcare", "keyword", "ok", [record],
                                              raw_count=1, normalized_count=1, http_status=200))
        with tempfile.TemporaryDirectory() as folder, \
                patch("finscope.marketaux_runner.LEDGER_PATH", Path(folder)/"study.sqlite3"), \
                patch("finscope.marketaux_runner.COOLDOWN_PATH", Path(folder)/"holds.json"), \
                patch("finscope.marketaux_runner.local_credentials", return_value={"MARKETAUX_API_KEY": "TEST_ONLY"}):
            result = execute_one("healthcare", self.approval, self.quota, clock=lambda: self.now, dispatcher=fetch)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["this_invocation_request_attempted"])
            self.assertNotIn(record.description, json.dumps(result))
            self.assertNotIn("TEST_ONLY", json.dumps(result))
            self.now += timedelta(seconds=61)
            again = execute_one("healthcare", self.approval, self.quota, clock=lambda: self.now, dispatcher=fetch)
            self.assertEqual(again["reason"], "duplicate_attempt")
            self.assertFalse(again["this_invocation_request_attempted"])
        fetch.assert_called_once()

    def test_dispatch_exception_is_attempted_unknown_not_false_zero_traffic(self):
        fetch = Mock(side_effect=RuntimeError("PRIVATE_KEY_OR_BODY"))
        with tempfile.TemporaryDirectory() as folder, \
                patch("finscope.marketaux_runner.LEDGER_PATH", Path(folder)/"study.sqlite3"), \
                patch("finscope.marketaux_runner.COOLDOWN_PATH", Path(folder)/"holds.json"), \
                patch("finscope.marketaux_runner.local_credentials", return_value={"MARKETAUX_API_KEY": "TEST_ONLY"}):
            result = execute_one("healthcare", self.approval, self.quota, clock=lambda: self.now, dispatcher=fetch)
        self.assertTrue(result["this_invocation_request_attempted"])
        self.assertEqual(result["reason"], "attempted_outcome_unknown")
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_missing_key_or_stale_quota_does_not_construct_sampler(self):
        with patch("finscope.marketaux_runner.local_credentials", return_value={}), \
                patch("finscope.marketaux_runner.MarketauxSampler") as sampler:
            self.assertEqual(execute_one("healthcare", self.approval, self.quota,
                                         clock=lambda: self.now)["reason"], "missing_credentials")
            stale = self.quota | {"observed_at": "2026-10-26T00:50:00+00:00"}
            self.assertEqual(execute_one("healthcare", self.approval, stale,
                                         clock=lambda: self.now)["reason"], "quota_snapshot_invalid_or_stale")
            sampler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
