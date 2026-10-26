"""One-sample live wiring for the existing guard; offline preview by default.

This module does not confer human authorization. Only use --execute after the
user explicitly approves a round, with local approval and fresh quota evidence.
No scheduler, automatic waiting, retries, state reset or AI/news connection.
"""

import argparse
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from pathlib import Path

from .api_sources import fetch_provider, local_credentials
from .sampling import (COOLDOWN_PATH, LEDGER_PATH, ROUND_DATES, SECTORS, STUDY_ID,
                       MarketauxSampler, QuotaSnapshot, SamplingAuthorization,
                       SamplingBlocked, plan_summary)


def approval_from_dict(document: dict, sector: str) -> SamplingAuthorization:
    try:
        if (set(document) != {"study_id", "explicit_user_authorization", "approved_dates", "approved_sectors"}
                or document["study_id"] != STUDY_ID or document["explicit_user_authorization"] is not True
                or not isinstance(document["approved_dates"], list)
                or not isinstance(document["approved_sectors"], list)):
            raise ValueError
        days = frozenset(date.fromisoformat(day) for day in document["approved_dates"])
        sectors = frozenset(document["approved_sectors"])
        if (not days or not days.issubset(ROUND_DATES) or not sectors
                or not sectors.issubset(SECTORS) or sector not in sectors):
            raise ValueError
        return SamplingAuthorization(days)
    except (ValueError, TypeError, KeyError):
        raise SamplingBlocked("invalid_explicit_approval") from None


def quota_from_dict(document: dict) -> QuotaSnapshot:
    try:
        if set(document) != {"observed_at", "period_start", "period_end", "remaining"}:
            raise ValueError
        return QuotaSnapshot(*(datetime.fromisoformat(document[key]) for key in
                               ("observed_at", "period_start", "period_end")), document["remaining"])
    except (ValueError, TypeError, KeyError):
        raise SamplingBlocked("invalid_quota_evidence") from None


def execute_one(sector: str, approval: dict, quota_evidence: dict, *, clock=None,
                dispatcher=None, annotator=None) -> dict:
    """Guard a single dispatch; tests inject synthetic backends and temp paths.

    Approval/quota are operator attestations, never created or inferred here.
    The optional annotator must be local and must not echo/store/send news text.
    CLI leaves semantic labels uncertain rather than installing an AI annotator.
    """
    attempted = False
    try:
        authorization = approval_from_dict(approval, sector)
        quota = quota_from_dict(quota_evidence)
        now = clock or (lambda: datetime.now(timezone.utc))
        quota.validate(now())
        if not local_credentials().get("MARKETAUX_API_KEY"):
            raise SamplingBlocked("missing_credentials")

        def dispatch(*args, **kwargs):
            nonlocal attempted
            attempted = True
            return (dispatcher or fetch_provider)(*args, **kwargs)

        sampler = MarketauxSampler(ledger_path=LEDGER_PATH, cooldown_path=COOLDOWN_PATH,
                                   clock=now, fetcher=dispatch)
        result = sampler.collect_one(sector, authorization=authorization, quota=quota, annotator=annotator)
        return {**asdict(result), "this_invocation_request_attempted": attempted,
                "provider": "marketaux", "sector": sector}
    except SamplingBlocked as error:
        return {"status": "blocked", "reason": str(error),
                "this_invocation_request_attempted": attempted}


def read_evidence(path: str | None) -> dict:
    try:
        if not path:
            raise ValueError
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError
        return document
    except (OSError, ValueError, TypeError):
        raise SamplingBlocked("local_approval_and_quota_files_required") from None


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Marketaux runner; defaults to a no-HTTP preview")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true", help="Requires prior explicit human authorization")
    parser.add_argument("--sector", choices=SECTORS, default="healthcare")
    parser.add_argument("--approval-file")
    parser.add_argument("--quota-file")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({**plan_summary(), "runner_mode": "offline_preflight",
                          "requests_executed": 0, "approval_files_read": False,
                          "ledger_created": False}, indent=2))
        return 0
    try:
        result = execute_one(args.sector, read_evidence(args.approval_file), read_evidence(args.quota_file))
    except SamplingBlocked as error:
        result = {"status": "blocked", "reason": str(error), "this_invocation_request_attempted": False}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"ok", "empty"} else 1


if __name__ == "__main__":
    raise SystemExit(run())
