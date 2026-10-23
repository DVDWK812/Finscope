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

from dotenv import load_dotenv

from .api_sources import PROVIDERS, TOPICS, ENV_KEYS, Article, fetch_provider, build_request
import os


def summarize(articles: list[Article]) -> dict:
    n = len(articles)
    urls = {a.url.split("#")[0] for a in articles}
    sources = {a.source.lower().strip() for a in articles}
    return {
        "valid_articles": n,
        "unique_urls": len(urls),
        "distinct_sources": len(sources),
        "title_available_ratio_among_valid": round(sum(bool(a.title) for a in articles)/n, 3) if n else None,
        "description_available_ratio_among_valid": round(sum(bool(a.description) for a in articles)/n, 3) if n else None,
        "timestamp_available_ratio_among_valid": round(sum(bool(a.timestamp) for a in articles)/n, 3) if n else None,
        "timestamp_kind": sorted({a.timestamp_kind for a in articles}),
        "mean_description_chars": round(statistics.mean(len(a.description) for a in articles), 1) if n else None,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", nargs="+", choices=PROVIDERS, default=list(PROVIDERS))
    parser.add_argument("--topics", nargs="+", choices=TOPICS, default=["technology", "healthcare", "materials"])
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", default="reports/api_benchmark.json")
    parser.add_argument("--dry-run", action="store_true", help="Show query strategies; do not make API calls")
    args = parser.parse_args(argv)
    if args.days < 1 or args.limit < 1 or args.timeout <= 0:
        parser.error("--days, --limit and --timeout must be positive")
    load_dotenv()  # local .env only, excluded from git
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for topic in args.topics:
        for provider in args.providers:
            if args.dry_run:
                key_present = (not ENV_KEYS[provider]) or bool(os.getenv(ENV_KEYS[provider]))
                _, params, _, mode, note = build_request(provider, topic, now, args.days, args.limit, "REDACTED")
                rows.append({"topic": topic, "provider": provider, "query_mode": mode,
                             "credentials_configured": key_present,
                             "query_keyword_or_symbol": TOPICS[topic]["symbol" if mode=="company_symbol" else "keyword"],
                             "planned_article_cap": params.get("limit", params.get("size", params.get("maxrecords", "provider-defined"))),
                             "note": note})
                continue
            result = fetch_provider(provider, topic, now=now, days=args.days,
                                    limit=args.limit, timeout=args.timeout)
            rows.append({"topic": topic, "provider": provider, "query_mode": result.query_mode,
                         "status": result.status, "latency_ms": result.latency_ms,
                         "raw_articles": result.raw_count,
                         "valid_article_ratio": round(len(result.articles)/result.raw_count,3) if result.raw_count else None,
                         **summarize(result.articles), "note": result.note})
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
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report written to {output}")
    if args.dry_run:
        for row in rows:
            print(f"{row['provider']:9} {row['topic']:11} mode={row['query_mode']:14} "
                  f"credentials={row['credentials_configured']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
