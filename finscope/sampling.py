"""Guarded Phase 1.5 sampler. No default HTTP backend, scheduler or live CLI.

SQLite reservations are committed before dispatch. Unknown outcomes consume
budget and block further collection until investigated, never retried.
Use one protected ledger for the entire study; never delete/reset/copy it.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sqlite3
from typing import Callable

from .api_sources import QueryResult
from .description_review import Annotator, review_descriptions
from .rate_limits import COOLDOWN_PATH, load_cooldowns, retry_deadline


STUDY_ID = "marketaux-phase15-v1"
ROUND_DATES = (date(2026, 10, 26), date(2026, 10, 28), date(2026, 10, 31))
SECTORS = ("healthcare", "technology", "materials")
from .test_safety import data_path
LEDGER_PATH = data_path('reports', 'marketaux_phase15.sqlite3')
MIN_SPACING = timedelta(seconds=60)


class SamplingBlocked(ValueError):
    """Safe reason code only: no response text, credential or backend errors."""


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SamplingBlocked("aware_utc_time_required")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class SamplingAuthorization:
    """External human approval attestation, not granted by constructing a sampler.

    Only create this after explicit authorization of the particular dates.
    There is no CLI flag, saved permit or default approval in this release.
    """
    approved_dates: frozenset[date]
    study_id: str = STUDY_ID


@dataclass(frozen=True)
class QuotaSnapshot:
    """Operator-confirmed dashboard balance/reset window; not inferred headers.

    Other account clients can consume quota after this snapshot. Single-operator
    coordination is required; this local ledger cannot coordinate remote clients.
    """
    observed_at: datetime
    period_start: datetime
    period_end: datetime
    remaining: int

    def validate(self, now: datetime) -> None:
        observed, start, end = map(utc, (self.observed_at, self.period_start, self.period_end))
        if (type(self.remaining) is not int or not 0 <= self.remaining <= 100
                or not start <= observed <= now < end
                or end - start != timedelta(days=1)
                or now - observed > timedelta(minutes=5)):
            raise SamplingBlocked("quota_snapshot_invalid_or_stale")


@dataclass(frozen=True)
class SampleOutcome:
    status: str
    http_status: int | None
    sampled_records: int
    description_reviews: tuple[dict, ...]
    latency_ms: float | None
    raw_records: int
    normalized_records: int


class AttemptLedger:
    """Local SQLite lock + durable unique reservation + conservative budgets."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=0, isolation_level=None)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == 0 and not tables and not existed:
                connection.execute("CREATE TABLE study (id TEXT NOT NULL)")
                connection.execute("INSERT INTO study VALUES (?)", (STUDY_ID,))
                connection.execute("""CREATE TABLE attempts (
                    day TEXT NOT NULL, sector TEXT NOT NULL, reserved_at TEXT NOT NULL,
                    completed_at TEXT, status TEXT NOT NULL, http_status INTEGER,
                    cooldown_until TEXT, review_json TEXT, PRIMARY KEY(day, sector))""")
                connection.execute("PRAGMA user_version=1")
            elif version != 1 or connection.execute("SELECT id FROM study").fetchall() != [(STUDY_ID,)]:
                raise SamplingBlocked("ledger_schema_invalid")
            yield connection
            connection.commit()
        except sqlite3.Error:
            if connection:
                connection.rollback()
            raise SamplingBlocked("ledger_unavailable_or_corrupt") from None
        except BaseException:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()

    def reserve(self, sector: str, now: datetime, quota: QuotaSnapshot,
                cooldown_path: Path) -> None:
        with self.transaction() as db:
            try:
                holds = load_cooldowns(cooldown_path)
            except (ValueError, OSError):
                raise SamplingBlocked("cooldown_state_invalid") from None
            if holds.get("marketaux", now) > now:
                raise SamplingBlocked("provider_cooldown")
            rows = db.execute("SELECT day, sector, reserved_at, completed_at, status, cooldown_until FROM attempts").fetchall()
            if any(day == now.date().isoformat() and topic == sector for day, topic, *_ in rows):
                raise SamplingBlocked("duplicate_attempt")
            if any(row[4] == "attempted_outcome_unknown" for row in rows):
                raise SamplingBlocked("unresolved_attempt")
            if len(rows) >= 9:
                raise SamplingBlocked("study_budget_exhausted")
            # Recheck snapshot freshness under the database lock.
            quota.validate(now)
            in_period = 0
            since_snapshot = 0
            try:
                for day, topic, reserved, completed, status, hold in rows:
                    start = utc(datetime.fromisoformat(reserved))
                    end = utc(datetime.fromisoformat(completed)) if completed else start
                    if (date.fromisoformat(day) not in ROUND_DATES or topic not in SECTORS
                            or start.date().isoformat() != day or end < start
                            or status not in {"ok", "empty", "failed", "review_failed"}):
                        raise ValueError
                    if end > now or now - end < MIN_SPACING:
                        raise SamplingBlocked("minimum_spacing")
                    if hold and utc(datetime.fromisoformat(hold)) > now:
                        raise SamplingBlocked("provider_cooldown")
                    if day == now.date().isoformat() and (hold or status in {"failed", "review_failed"}):
                        raise SamplingBlocked("round_stopped")
                    in_period += quota.period_start <= start < quota.period_end
                    since_snapshot += start >= quota.observed_at
            except SamplingBlocked:
                raise
            except (ValueError, TypeError):
                raise SamplingBlocked("ledger_record_invalid") from None
            if in_period >= 3 or sum(row[0] == now.date().isoformat() for row in rows) >= 3:
                raise SamplingBlocked("daily_budget_exhausted")
            if since_snapshot >= quota.remaining:
                raise SamplingBlocked("account_budget_exhausted")
            db.execute("INSERT INTO attempts(day,sector,reserved_at,status) VALUES (?,?,?,?)",
                       (now.date().isoformat(), sector, now.isoformat(), "attempted_outcome_unknown"))
        # FULL synchronous commit completes before the caller can dispatch HTTP.

    def complete(self, day: date, sector: str, now: datetime, status: str,
                 http_status: int | None, deadline: datetime | None, metrics: dict) -> None:
        with self.transaction() as db:
            cursor = db.execute("""UPDATE attempts SET completed_at=?,status=?,http_status=?,
                cooldown_until=?,review_json=? WHERE day=? AND sector=? AND status=?""",
                (now.isoformat(), status, http_status, deadline.isoformat() if deadline else None,
                 json.dumps(metrics), day.isoformat(), sector, "attempted_outcome_unknown"))
            if cursor.rowcount != 1:
                raise SamplingBlocked("reservation_missing_or_completed")


class MarketauxSampler:
    """One authorized, guarded dispatch at a time; deliberately no default backend.

    Fetcher receives only fixed scope/limits. It must not retry, redirect, log
    text/tokens or fetch pages; the existing adapter meets that transport policy.
    No API/model/UI connection or authorization is installed by this module.
    """

    def __init__(self, *, ledger_path: Path = LEDGER_PATH, cooldown_path: Path = COOLDOWN_PATH,
                 fetcher: Callable[..., QueryResult] | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.ledger = AttemptLedger(ledger_path)
        self.cooldown_path = cooldown_path
        self.fetcher = fetcher
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def collect_one(self, sector: str, *, authorization: SamplingAuthorization | None = None,
                    quota: QuotaSnapshot | None = None, annotator: Annotator | None = None) -> SampleOutcome:
        now = utc(self.clock())
        if (not isinstance(authorization, SamplingAuthorization) or authorization.study_id != STUDY_ID
                or now.date() not in authorization.approved_dates):
            raise SamplingBlocked("explicit_authorization_required")
        if sector not in SECTORS or now.date() not in ROUND_DATES or not (1 <= now.hour < 2):
            raise SamplingBlocked("outside_planned_round")
        if not isinstance(quota, QuotaSnapshot):
            raise SamplingBlocked("verified_quota_required")
        if self.fetcher is None:
            raise SamplingBlocked("no_dispatch_backend_configured")
        quota.validate(now)
        self.ledger.reserve(sector, now, quota, self.cooldown_path)
        try:
            result = self.fetcher("marketaux", sector, now=now, days=2, limit=3, timeout=15.0)
        except Exception:
            # An exception could occur after dispatch. Preserve unknown reservation.
            raise SamplingBlocked("attempted_outcome_unknown") from None
        finished = utc(self.clock())
        if finished < now:
            raise SamplingBlocked("clock_moved_backwards")
        if not isinstance(result, QueryResult):
            raise SamplingBlocked("attempted_outcome_unknown")
        if (not isinstance(result.rate_limit_headers, dict) or not isinstance(result.articles, list)
                or (result.http_status is not None and
                    (type(result.http_status) is not int or not 100 <= result.http_status <= 599))):
            raise SamplingBlocked("attempted_outcome_unknown")
        if (type(result.raw_count) is not int or type(result.normalized_count) is not int
                or not 0 <= result.normalized_count <= result.raw_count
                or len(result.articles) > result.normalized_count
                or (result.latency_ms is not None and (type(result.latency_ms) not in (int, float)
                    or not math.isfinite(result.latency_ms) or result.latency_ms < 0))):
            raise SamplingBlocked("attempted_outcome_unknown")
        header = result.rate_limit_headers.get("Retry-After")
        deadline = retry_deadline(header, finished) if header or result.http_status == 429 else None
        status, reviews = "failed", ()
        if (result.provider == "marketaux" and result.topic == sector and result.status == "ok"
                and result.http_status == 200 and len(result.articles) <= 3):
            try:
                reviews = tuple(review.safe_dict() for review in review_descriptions(result.articles, annotator))
                status = "ok" if result.articles else "empty"
            except Exception:
                status = "review_failed"
        metrics = {"description_reviews": reviews, "latency_ms": result.latency_ms,
                   "raw_records": result.raw_count, "normalized_records": result.normalized_count,
                   "sampled_records": min(len(result.articles), 3)}
        self.ledger.complete(now.date(), sector, finished, status, result.http_status, deadline, metrics)
        # Retry-After is durably stored in this ledger, even on HTTP 200; shared
        # GDELT/NewsData holds are read but never rewritten by this sampler.
        return SampleOutcome(status, result.http_status, min(len(result.articles), 3), reviews,
                             result.latency_ms, result.raw_count, result.normalized_count)


def plan_summary() -> dict:
    """Offline preview: no ledger, credentials, HTTP, model loading or scheduling."""
    return {"study_id": STUDY_ID, "authorization": "not_granted", "requests_executed": 0,
            "round_dates_utc": [day.isoformat() for day in ROUND_DATES],
            "window_utc": "01:00 inclusive to 02:00 exclusive; no catch-up",
            "sectors": SECTORS, "daily_request_cap": 3, "total_request_cap": 9,
            "sample_cap": 3, "minimum_spacing_seconds": 60, "default_network_backend": False}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Offline preview only; no live sampling is authorized")
    parser.add_argument("--dry-run", required=True, action="store_true")
    parser.parse_args()
    print(json.dumps(plan_summary(), indent=2))
