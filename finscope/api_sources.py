"""Conservative news API adapters for a small reproducible provider comparison.

Only publicly documented endpoints are used. Never log provider API keys, raw
request URLs containing credentials, or entire HTTP error bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlsplit
import os
import time

import requests


TOPICS: dict[str, dict[str, str]] = {
    "technology": {"keyword": "semiconductor", "symbol": "NVDA"},
    "healthcare": {"keyword": "pharmaceutical", "symbol": "PFE"},
    "materials": {"keyword": "copper", "symbol": "FCX"},
    "energy": {"keyword": "oil", "symbol": "XOM"},
    "financials": {"keyword": "bank", "symbol": "JPM"},
}

PROVIDERS = ("gdelt", "marketaux", "newsdata", "finnhub")
ENV_KEYS = {
    "gdelt": None,
    "marketaux": "MARKETAUX_API_KEY",
    "newsdata": "NEWSDATA_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
}


@dataclass(frozen=True)
class Article:
    provider: str
    title: str
    url: str
    source: str
    description: str
    timestamp: str
    timestamp_kind: str  # 'published' or 'first_seen'


@dataclass
class QueryResult:
    provider: str
    topic: str
    query_mode: str
    status: str  # ok / skipped / failed
    articles: list[Article]
    raw_count: int = 0
    latency_ms: float | None = None
    note: str = ""


class APIError(Exception):
    """Safe, redacted transport error; must not include credentials or URLs."""


def _http_get_json(url: str, params: dict[str, Any], headers: dict[str, str], timeout: float) -> Any:
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        # Do not display str(exc): requests may embed URL query parameters / API keys.
        raise APIError(f"Transport error ({type(exc).__name__})") from None
    if response.status_code != 200:
        raise APIError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise APIError("Invalid JSON response") from None


GetJSON = Callable[[str, dict[str, Any], dict[str, str], float], Any]


def _source(url: str, provider_source: str | None) -> str:
    return str(provider_source or urlsplit(url).hostname or "unknown")


def _gdelt_datetime(value: str | None) -> str:
    if not value:
        return ""
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return ""  # Never pass an unvalidated observed time off as a publication time.


def normalize(provider: str, payload: Any) -> tuple[list[Article], int]:
    """Normalize successful provider responses; fail on unexpected JSON shapes."""
    if provider == "gdelt":
        if not isinstance(payload, dict):
            raise APIError("Unexpected GDELT response shape")
        raw = payload.get("articles", [])
    elif provider == "marketaux":
        if not isinstance(payload, dict):
            raise APIError("Unexpected Marketaux response shape")
        raw = payload.get("data", [])
    elif provider == "newsdata":
        if not isinstance(payload, dict):
            raise APIError("Unexpected NewsData response shape")
        if payload.get("status") == "error":
            raise APIError("NewsData returned error status")
        raw = payload.get("results", [])
    elif provider == "finnhub":
        raw = payload
    else:
        raise ValueError(f"Unknown provider: {provider}")

    if not isinstance(raw, list):
        raise APIError("Unexpected article array shape")

    records: list[Article] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        title = str(row.get("headline" if provider == "finnhub" else "title") or "").strip()
        url = str(row.get("link" if provider == "newsdata" else "url") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue

        if provider == "gdelt":
            ts = _gdelt_datetime(row.get("seendate"))
            kind = "first_seen"
            desc = ""  # DOC API ArticleList does not promise full article descriptions.
            source = _source(url, row.get("domain"))
        elif provider == "marketaux":
            ts = str(row.get("published_at") or "")
            kind = "published"
            desc = str(row.get("description") or "")
            source = _source(url, row.get("source"))
        elif provider == "newsdata":
            ts = str(row.get("pubDate") or "")
            kind = "published"
            desc = str(row.get("description") or "")
            source = _source(url, row.get("source_name") or row.get("source_id"))
        else:  # finnhub
            unix_time = row.get("datetime")
            try:
                ts = datetime.fromtimestamp(int(unix_time), tz=timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError, OSError):
                ts = ""
            kind = "published"
            desc = str(row.get("summary") or "")
            source = _source(url, row.get("source"))
        records.append(Article(provider, title, url, source, desc, ts, kind))
    return records, len(raw)


def build_request(provider: str, topic: str, now: datetime, days: int, limit: int, key: str | None):
    """Return (url, params, headers, query_mode, note). No network operation."""
    if topic not in TOPICS:
        raise ValueError(f"Unsupported topic: {topic}")
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    keyword = TOPICS[topic]["keyword"]
    symbol = TOPICS[topic]["symbol"]
    earlier = now - timedelta(days=days)
    headers = {"Accept": "application/json", "User-Agent": "FinScope-research-prototype/0.1"}
    if provider == "gdelt":
        return (
            "https://api.gdeltproject.org/api/v2/doc/doc",
            {"query": f"{keyword} sourcelang:english", "mode": "artlist", "format": "json",
             "timespan": f"{days}d", "maxrecords": min(limit, 250)},
            headers, "keyword",
            "GDELT seendate is first-seen time, not confirmed publication time; titles/URLs, typically no summaries.",
        )
    if provider == "marketaux":
        return (
            "https://api.marketaux.com/v1/news/all",
            {"api_token": key, "search": keyword, "language": "en",
             "published_after": earlier.strftime("%Y-%m-%dT%H:%M"),
             "limit": min(limit, 3), "group_similar": "false"},
            headers, "keyword",
            "Free tier currently caps 3 articles/request; group_similar=false to measure our own deduplication.",
        )
    if provider == "newsdata":
        # Latest covers approximately 48 hours; archive is typically gated by plan.
        headers["X-ACCESS-KEY"] = str(key)
        return (
            "https://newsdata.io/api/1/latest",
            {"q": keyword, "language": "en", "size": min(limit, 10)},
            headers, "keyword",
            "Latest endpoint is approximately 48h coverage; do not interpret days as a guaranteed lookback.",
        )
    return (
        "https://finnhub.io/api/v1/company-news",
        {"token": key, "symbol": symbol,
         "from": earlier.strftime("%Y-%m-%d"), "to": now.strftime("%Y-%m-%d")},
        headers, "company_symbol",
        f"Company-focused query ({symbol}), not a sector-wide keyword query; not directly count-comparable.",
    )


def fetch_provider(
    provider: str,
    topic: str,
    *,
    now: datetime | None = None,
    days: int = 2,
    limit: int = 3,
    timeout: float = 15,
    transport: GetJSON = _http_get_json,
) -> QueryResult:
    if days < 1 or limit < 1 or timeout <= 0:
        raise ValueError("days, limit and timeout must be positive")
    if now is None:
        now = datetime.now(timezone.utc)
    env_key = ENV_KEYS[provider]
    key = os.getenv(env_key) if env_key else None
    if env_key and not key:
        return QueryResult(provider, topic, "not_run", "skipped", [], note=f"Missing {env_key}")
    url, params, headers, query_mode, note = build_request(provider, topic, now, days, limit, key)
    started = time.perf_counter()
    try:
        payload = transport(url, params, headers, timeout)
        items, raw_count = normalize(provider, payload)
    except APIError as exc:
        return QueryResult(provider, topic, query_mode, "failed", [],
                           latency_ms=round((time.perf_counter()-started)*1000, 1),
                           note=f"{note} {exc}")
    except Exception as exc:
        # Don't leak params, headers, API keys or raw response errors into report.
        return QueryResult(provider, topic, query_mode, "failed", [],
                           latency_ms=round((time.perf_counter()-started)*1000, 1),
                           note=f"{note} Unexpected error: {type(exc).__name__}")
    return QueryResult(provider, topic, query_mode, "ok", items[:limit],
                       raw_count=raw_count,
                       latency_ms=round((time.perf_counter()-started)*1000, 1), note=note)
