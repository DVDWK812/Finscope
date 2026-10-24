from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from finscope.api_sources import Article, QueryResult
from finscope.benchmark import run as benchmark
from finscope.description_review import Quality, review_descriptions
from finscope.sampling import (MarketauxSampler, QuotaSnapshot, ROUND_DATES,
                               SamplingAuthorization, SamplingBlocked, plan_summary)


def article(title="Synthetic company invests", description="Invented investment is 12 million dollars."):
    return Article("marketaux", title, "https://example.org/synthetic", "example.org",
                   description, "2026-10-26T00:00:00+00:00", "published")


class DescriptionReviewTests(unittest.TestCase):
    def test_missing_and_exact_title_repetition_do_not_require_annotator(self):
        annotate = Mock()
        rows = review_descriptions([article(description="  "),
                                    article("Synthetic Growth!", "SYNTHETIC growth.")], annotate)
        self.assertEqual([r.category for r in rows], [Quality.MISSING, Quality.REPETITION])
        annotate.assert_not_called()

    def test_added_facts_are_uncertain_until_explicitly_annotated(self):
        self.assertEqual(review_descriptions([article()])[0].category, Quality.UNCERTAIN)
        review = review_descriptions([article()], lambda t, d: Quality.ADDS_FACT)[0]
        self.assertEqual(review.category, Quality.ADDS_FACT)
        self.assertEqual(review.basis, "provided_annotator")
        self.assertEqual(review.description_words, 6)
        self.assertNotIn(article().description, json.dumps(review.safe_dict()))
        self.assertNotIn(article().title, repr(review))

    def test_boilerplate_is_an_annotation_not_automatic_model_accuracy(self):
        row = review_descriptions([article(description="Subscribe for more information.")],
                                  lambda t, d: Quality.BOILERPLATE)[0]
        self.assertEqual(row.category, Quality.BOILERPLATE)

    def test_caps_do_not_truncate_text_into_a_false_positive(self):
        annotate = Mock(return_value=Quality.ADDS_FACT)
        row = review_descriptions([article(description="x" * 2001)], annotate)[0]
        self.assertTrue(row.over_limit)
        self.assertEqual(row.category, Quality.UNCERTAIN)
        annotate.assert_not_called()
        with self.assertRaises(ValueError):
            review_descriptions([article()] * 4, annotate)

    def test_annotator_errors_and_invalid_labels_never_echo_text(self):
        for annotate in (Mock(side_effect=RuntimeError("PRIVATE_TEXT")), lambda t, d: "informative"):
            with self.subTest(annotate=type(annotate)), self.assertRaises(ValueError) as caught:
                review_descriptions([article()], annotate)
            self.assertNotIn("PRIVATE_TEXT", str(caught.exception))
        with self.assertRaises(ValueError):
            review_descriptions([article(description=None)])


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "attempts.sqlite3"
        self.holds = Path(self.temp.name) / "cooldowns.json"
        self.holds.write_text(json.dumps({"gdelt": "2026-10-27T00:00:00+00:00",
                                          "newsdata": "2026-10-24T13:02:57+00:00"}))
        self.saved_holds = self.holds.read_bytes()
        self.now = datetime(2026, 10, 26, 1, tzinfo=timezone.utc)
        self.authorization = SamplingAuthorization(frozenset(ROUND_DATES))
        self.fetch = Mock(side_effect=self.response)
        self.sampler = self.new_sampler()

    def response(self, provider, sector, **kwargs):
        return QueryResult(provider, sector, "keyword", "ok", [article()], raw_count=1,
                           normalized_count=1, http_status=200, outcome="records")

    def new_sampler(self):
        return MarketauxSampler(ledger_path=self.path, cooldown_path=self.holds,
                                clock=lambda: self.now, fetcher=self.fetch)

    def quota(self, remaining=100, observed=None):
        start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        return QuotaSnapshot(observed or self.now, start, start + timedelta(days=1), remaining)

    def collect(self, sector="healthcare", **kwargs):
        return self.sampler.collect_one(sector, authorization=self.authorization,
                                        quota=kwargs.pop("quota", self.quota()), **kwargs)

    def test_no_authorization_no_backend_no_dispatch_or_ledger(self):
        with self.assertRaisesRegex(SamplingBlocked, "explicit_authorization"):
            self.sampler.collect_one("healthcare")
        self.fetch.assert_not_called()
        self.assertFalse(self.path.exists())
        offline = MarketauxSampler(ledger_path=self.path, clock=lambda: self.now)
        with self.assertRaisesRegex(SamplingBlocked, "no_dispatch_backend"):
            offline.collect_one("healthcare", authorization=self.authorization, quota=self.quota())
        self.assertFalse(self.path.exists())
        self.assertEqual(plan_summary()["requests_executed"], 0)

    def test_fixed_parameters_and_committed_reservation_before_dispatch(self):
        def fetch(provider, sector, **kwargs):
            with contextlib.closing(sqlite3.connect(self.path)) as db:
                self.assertEqual(db.execute("SELECT status FROM attempts").fetchall(),
                                 [("attempted_outcome_unknown",)])
            self.assertEqual((provider, sector), ("marketaux", "healthcare"))
            self.assertEqual(kwargs, {"now": self.now, "days": 2, "limit": 3, "timeout": 15.0})
            return self.response(provider, sector, **kwargs)
        self.fetch.side_effect = fetch
        result = self.collect(annotator=lambda t, d: Quality.ADDS_FACT)
        self.assertEqual(result.status, "ok")
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            saved = db.execute("SELECT review_json FROM attempts").fetchone()[0]
        self.assertEqual(json.loads(saved)["raw_records"], 1)
        self.assertEqual(json.loads(saved)["normalized_records"], 1)
        self.assertIn("adds_concrete_fact", saved)
        self.assertNotIn(article().description, saved)
        self.assertNotIn(article().title, saved)
        self.assertEqual(self.holds.read_bytes(), self.saved_holds)

    def test_new_process_instance_cannot_repeat_date_sector(self):
        self.collect()
        self.now += timedelta(seconds=61)
        self.sampler = self.new_sampler()
        with self.assertRaisesRegex(SamplingBlocked, "duplicate_attempt"):
            self.collect()
        self.fetch.assert_called_once()

    def test_unknown_dispatch_exception_consumes_slot_and_blocks_further_calls(self):
        self.fetch.side_effect = RuntimeError("PRIVATE_BODY_OR_KEY")
        with self.assertRaisesRegex(SamplingBlocked, "^attempted_outcome_unknown$"):
            self.collect()
        self.now += timedelta(seconds=61)
        self.sampler = self.new_sampler()
        with self.assertRaisesRegex(SamplingBlocked, "unresolved_attempt"):
            self.collect("technology")
        self.fetch.assert_called_once()

    def test_spacing_is_since_completion_and_never_sleeps(self):
        def slow(*args, **kwargs):
            self.now += timedelta(seconds=10)
            return self.response(*args, **kwargs)
        self.fetch.side_effect = slow
        self.collect()
        self.now += timedelta(seconds=50)
        with patch("time.sleep") as sleep:
            with self.assertRaisesRegex(SamplingBlocked, "minimum_spacing"):
                self.collect("technology")
            sleep.assert_not_called()
        self.now += timedelta(seconds=10)
        self.collect("technology")
        self.assertEqual(self.fetch.call_count, 2)

    def test_planned_dates_window_scope_and_verified_quota_fail_closed(self):
        for moment, sector in ((self.now - timedelta(days=1), "healthcare"),
                               (self.now.replace(hour=2), "healthcare"), (self.now, "energy")):
            self.now = moment
            with self.assertRaises(SamplingBlocked):
                self.collect(sector)
        self.now = datetime(2026, 10, 26, 1, tzinfo=timezone.utc)
        for quota in (self.quota(0), self.quota(observed=self.now - timedelta(minutes=6)),
                      self.quota(observed=self.now + timedelta(seconds=1)), self.quota(True)):
            with self.assertRaises(SamplingBlocked):
                self.collect(quota=quota)
        self.fetch.assert_not_called()

    def test_account_balance_counts_reservations_since_same_snapshot(self):
        quota = self.quota(remaining=2)
        self.collect(quota=quota)
        self.now += timedelta(seconds=61)
        self.collect("technology", quota=quota)
        self.now += timedelta(seconds=61)
        with self.assertRaisesRegex(SamplingBlocked, "account_budget_exhausted"):
            self.collect("materials", quota=quota)
        self.assertEqual(self.fetch.call_count, 2)

    def test_nine_slots_only_across_all_three_rounds(self):
        for day in ROUND_DATES:
            self.now = datetime.combine(day, datetime.min.time(), timezone.utc).replace(hour=1)
            for sector in ("healthcare", "technology", "materials"):
                self.collect(sector)
                self.now += timedelta(seconds=61)
        with self.assertRaises(SamplingBlocked):
            self.collect("materials")
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM attempts").fetchone()[0], 9)
        self.assertEqual(self.fetch.call_count, 9)

    def test_existing_and_corrupt_cooldowns_prevent_dispatch(self):
        for contents in (json.dumps({"marketaux": (self.now + timedelta(hours=1)).isoformat()}), "broken"):
            self.holds.write_text(contents)
            with self.assertRaises(SamplingBlocked):
                self.collect()
        self.fetch.assert_not_called()

    def test_200_retry_after_persists_and_stops_entire_round_even_after_expiry(self):
        response = self.response("marketaux", "healthcare")
        response.rate_limit_headers = {"Retry-After": "900"}
        self.fetch.return_value, self.fetch.side_effect = response, None
        self.assertEqual(self.collect().status, "ok")
        self.now += timedelta(seconds=61)
        self.sampler = self.new_sampler()
        with self.assertRaisesRegex(SamplingBlocked, "provider_cooldown"):
            self.collect("technology")
        self.now += timedelta(minutes=15)
        with self.assertRaisesRegex(SamplingBlocked, "round_stopped"):
            self.collect("technology")
        self.fetch.assert_called_once()
        self.assertEqual(self.holds.read_bytes(), self.saved_holds)

    def test_429_without_header_auth_and_schema_failures_stop_round(self):
        for http in (429, 401, 403, 402, 500):
            with self.subTest(http=http), tempfile.TemporaryDirectory() as folder:
                self.path = Path(folder) / "attempts.sqlite3"
                self.sampler = self.new_sampler()
                self.fetch.side_effect = lambda p, t, **k: QueryResult(p, t, "keyword", "failed", [], http_status=http)
                self.assertEqual(self.collect().status, "failed")
                self.now += timedelta(seconds=61)
                with self.assertRaises(SamplingBlocked):
                    self.collect("technology")

    def test_review_failure_is_recorded_without_retaining_text_or_requery(self):
        self.assertEqual(self.collect(annotator=Mock(side_effect=ValueError("PRIVATE"))).status,
                         "review_failed")
        self.now += timedelta(seconds=61)
        with self.assertRaisesRegex(SamplingBlocked, "round_stopped"):
            self.collect("technology")
        self.fetch.assert_called_once()
        self.assertNotIn(b"PRIVATE", self.path.read_bytes())

    def test_invalid_count_or_latency_metadata_stays_unknown_and_never_retries(self):
        response = self.response("marketaux", "healthcare")
        response.latency_ms = float("nan")
        self.fetch.return_value, self.fetch.side_effect = response, None
        with self.assertRaisesRegex(SamplingBlocked, "attempted_outcome_unknown"):
            self.collect()
        self.now += timedelta(seconds=61)
        with self.assertRaisesRegex(SamplingBlocked, "unresolved_attempt"):
            self.collect("technology")
        self.fetch.assert_called_once()

    def test_corrupt_and_empty_existing_ledgers_block_dispatch(self):
        for contents in (b"broken", b""):
            self.path.write_bytes(contents)
            with self.assertRaises(SamplingBlocked):
                self.collect()
        self.fetch.assert_not_called()

    def test_concurrent_connections_cannot_dispatch_the_same_slot_twice(self):
        # Initialize schema first so the test checks reservation contention,
        # independently of first-file creation timing on the host filesystem.
        with self.sampler.ledger.transaction():
            pass
        def attempt(_):
            try:
                return self.new_sampler().collect_one("healthcare", authorization=self.authorization,
                                                      quota=self.quota()).status
            except SamplingBlocked:
                return "blocked"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(outcomes), ["blocked", "ok"])
        self.fetch.assert_called_once()

    def test_committed_attempt_survives_abrupt_process_exit(self):
        script = """
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os, sys
from finscope.sampling import AttemptLedger, QuotaSnapshot
now = datetime(2026, 10, 26, 1, tzinfo=timezone.utc)
start = now.replace(hour=0)
AttemptLedger(Path(sys.argv[1])).reserve('healthcare', now,
    QuotaSnapshot(now, start, start + timedelta(days=1), 100), Path(sys.argv[2]))
os._exit(7)
"""
        process = subprocess.run([sys.executable, "-c", script, str(self.path), str(self.holds)],
                                 capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 7)
        self.now += timedelta(seconds=61)
        for sector in ("healthcare", "technology"):
            with self.assertRaises(SamplingBlocked):
                self.collect(sector)
        self.fetch.assert_not_called()

    def test_legacy_cli_cannot_bypass_guards_with_configured_marketaux_key(self):
        with patch("finscope.benchmark.local_credentials", return_value={"MARKETAUX_API_KEY": "SYNTHETIC_KEY"}), \
                patch("finscope.benchmark.fetch_provider") as fetch, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            benchmark(["--providers", "marketaux", "--topics", "healthcare"])
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
