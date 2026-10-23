from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from finscope.rate_limits import load_cooldowns, save_cooldowns, retry_deadline, safe_retry_after


NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


class CooldownTests(unittest.TestCase):
    def test_seconds_and_http_date_have_equivalent_deadlines(self):
        self.assertEqual(retry_deadline("60", NOW), NOW + timedelta(minutes=1))
        self.assertEqual(retry_deadline("Sat, 24 Oct 2026 00:01:00 GMT", NOW), NOW + timedelta(minutes=1))

    def test_missing_invalid_and_extreme_headers_are_conservative(self):
        for value in (None, "SECRET", "-1"):
            self.assertEqual(retry_deadline(value, NOW), NOW + timedelta(hours=24))
        self.assertEqual(retry_deadline("9" * 100, NOW), datetime.max.replace(tzinfo=timezone.utc))
        self.assertIsNone(safe_retry_after("SECRET"))

    def test_state_round_trip_and_aware_timestamp_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            self.assertEqual(load_cooldowns(path), {})
            save_cooldowns(path, {"gdelt": NOW})
            self.assertEqual(load_cooldowns(path), {"gdelt": NOW})
            for content in ('[]', '{"gdelt":"2026-10-24"}', '{"unknown":"2026-10-24T00:00:00+00:00"}'):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_cooldowns(path)


if __name__ == "__main__":
    unittest.main()
