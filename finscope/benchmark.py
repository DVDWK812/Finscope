"""Run a low-volume financial-news API feasibility comparison.

Usage:
    python -m finscope.benchmark --dry-run
    python -m finscope.benchmark --topics technology healthcare materials
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

from .api_sources import (PROVIDERS, TOPICS, ENV_KEYS, Article, fetch_provider,
                          build_request, local_credentials, QueryResult)
from .rate_limits import COOLDOWN_PATH, load_cooldowns, save_cooldowns, retry_deadline


def summarize(articles: list[Article]) -> dict:
    n = len(articles)
    urls = {a.url.split("#")[0] for a in articles}
    sources = {a.source.lower().strip() for a in articles}
    title_chars = [len(a.title.strip()) for a in articles]
    title_words = [len(a.title.split()) for a in articles]
    return {
        "valid_articles": n,
        "unique_urls": len(urls),
        "distinct_sources": len(sources),
        "title_available_ratio_among_valid": round(sum(bool(a.title) for a in articles)/n, 3) if n else None,
        "description_available_ratio_among_valid": round(sum(bool(a.description.strip()) for a in articles)/n, 3) if n else None,
        "timestamp_available_ratio_among_valid": round(sum(bool(a.timestamp) for a in articles)/n, 3) if n else None,
        "timestamp_kind": sorted({a.timestamp_kind for a in articles}),
        "mean_description_chars": round(statistics.mean(len(a.description) for a in articles), 1) if n else None,
        "min_title_chars": min(title_chars) if n else None,
        "max_title_chars": max(title_chars) if n else None,
        "mean_title_chars": round(statistics.mean(title_chars), 1) if n else None,
        "mean_title_whitespace_words": round(statistics.mean(title_words), 1) if n else None,
        "published_timestamp_ratio_among_valid": round(sum(bool(a.timestamp) and a.timestamp_kind == "published" for a in articles)/n, 3) if n else None,
        "first_seen_timestamp_ratio_among_valid": round(sum(bool(a.timestamp) and a.timestamp_kind == "first_seen" for a in articles)/n, 3) if n else None,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", nargs="+", choices=PROVIDERS, default=list(PROVIDERS))
    parser.add_argument("--topics", nargs="+", choices=TOPICS, default=["technology", "healthcare", "materials"])
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", help="Local JSON path; defaults to a unique file in reports/")
    parser.add_argument("--dry-run", action="store_true", help="Show query strategies; do not make API calls")
    args = parser.parse_args(argv)
    if args.days < 1 or args.limit < 1 or args.timeout <= 0:
        parser.error("--days, --limit and --timeout must be positive")
    credentials = local_credentials()
    try:
        cooldowns = {} if args.dry_run else load_cooldowns(COOLDOWN_PATH)
    except (ValueError, OSError):
        parser.error("Cannot read valid local cooldown state; no API requests made")
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for provider in dict.fromkeys(args.providers):
        previous_request = None
        rate_limited = False
        for topic in dict.fromkeys(args.topics):
            held = cooldowns.get(provider)
            if not args.dry_run and not rate_limited and not (held and held > datetime.now(timezone.utc)) and provider == "gdelt" and previous_request is not None:
                # Conservative spacing, not a claim of an official quota or SLA.
                time.sleep(max(0, 6 - (time.monotonic() - previous_request)))
            query_time = datetime.now(timezone.utc)
            endpoint, params, _, mode, note = build_request(
                provider, topic, query_time, args.days, args.limit, "REDACTED")
            # Explicit allowlist: credentials and headers cannot enter report metadata.
            safe_params = {k: v for k, v in params.items() if k in {
                "query", "mode", "format", "timespan", "maxrecords", "search", "language",
                "published_after", "limit", "group_similar", "q", "size", "timezone",
                "symbol", "from", "to"}}
            query_metadata = {"query_at_utc": query_time.isoformat(), "endpoint": endpoint,
                              "query_parameters": safe_params,
                              "query_keyword_or_symbol": TOPICS[topic][
                                  "symbol" if mode == "company_symbol" else "keyword"]}
            if args.dry_run:
                key_present = (not ENV_KEYS[provider]) or bool(credentials.get(ENV_KEYS[provider]))
                rows.append({"topic": topic, "provider": provider, "query_mode": mode,
                             **query_metadata,
                             "credentials_configured": key_present,
                             "query_keyword_or_symbol": TOPICS[topic]["symbol" if mode=="company_symbol" else "keyword"],
                             "planned_article_cap": params.get("limit", params.get("size", params.get("maxrecords", "provider-defined"))),
                             "note": note})
                continue
            if rate_limited:
                result = QueryResult(provider, topic, mode, "skipped", [],
                                     outcome="provider_rate_limited",
                                     note="Earlier request to this provider returned HTTP 429; no further requests this run.")
            elif held and held > query_time and (provider == "gdelt" or credentials.get(ENV_KEYS[provider])):
                result = QueryResult(provider, topic, mode, "skipped", [],
                                     outcome="provider_cooldown",
                                     note=f"Local provider cooldown until {held.isoformat()}; no request made.")
            else:
                previous_request = time.monotonic()
                result = fetch_provider(provider, topic, now=query_time, days=args.days,
                                        limit=args.limit, timeout=args.timeout)
                rate_limited = result.http_status == 429
                if rate_limited or result.rate_limit_headers.get("Retry-After"):
                    deadline = retry_deadline(result.rate_limit_headers.get("Retry-After"),
                                              datetime.now(timezone.utc))
                    cooldowns[provider] = max(cooldowns.get(provider, deadline), deadline)
                    save_cooldowns(COOLDOWN_PATH, cooldowns)
            rows.append({"topic": topic, "provider": provider, "query_mode": result.query_mode,
                         **query_metadata,
                         "request_attempted": result.status != "skipped",
                         "request_at_utc": query_time.isoformat() if result.status != "skipped" else None,
                         "status": result.status, "latency_ms": result.latency_ms,
                         "outcome": result.outcome, "http_status": result.http_status,
                         "rate_limit_headers": result.rate_limit_headers,
                         "cooldown_until_utc": cooldowns[provider].isoformat() if provider in cooldowns else None,
                         "raw_articles": result.raw_count,
                         "normalized_articles_before_cap": result.normalized_count,
                         "valid_article_ratio": round(result.normalized_count/result.raw_count,3) if result.raw_count else None,
                         "sample_truncated": result.normalized_count > len(result.articles),
                         **summarize(result.articles), "note": result.note,
                         "samples": [{"title": a.title, "url": a.url, "source": a.source,
                                      "timestamp": a.timestamp, "timestamp_kind": a.timestamp_kind}
                                     for a in result.articles[:10]],
                         "manual_relevance": "not_reviewed",
                         "link_validation": "syntax_only; publisher pages not fetched"})
            print(f"{provider:9} {topic:11} {result.status:7} "
                  f"articles={len(result.articles):3} elapsed_ms={result.latency_ms}")
    document = {
        "generated_at_utc": now.isoformat(),
        "experiment_type": "dry_run" if args.dry_run else "live_attempt",
        "parameters": {"topics": args.topics, "providers": args.providers,
                       "requested_days": args.days, "requested_max_articles": args.limit},
        "warnings": [
            "Provider scopes differ (keyword vs North-American company news). Article counts are not directly comparable.",
            "Provider timestamps differ: GDELT first-seen is not publication time.",
            "API success does not confer permission to scrape, store or redistribute article full text.",
            "Missing credentials produce skipped results, not evidence of provider failure.",
            "One low-volume query per topic/provider does not establish reliability or historical coverage.",
        ],
        "results": rows,
    }
    output = Path(args.output) if args.output else Path("reports") / (
        f"api_benchmark_{document['experiment_type']}_{now.strftime('%Y%m%dT%H%M%S%fZ')}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report written to {output}")
    if args.dry_run:
        for row in rows:
            print(f"{row['provider']:9} {row['topic']:11} mode={row['query_mode']:14} "
                  f"credentials={row['credentials_configured']}")
    return 1 if any(row.get("status") == "failed" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(run())
