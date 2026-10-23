"""Conservative news API adapters for a small reproducible provider comparison.

Only publicly documented endpoints are used. Never log provider API keys, raw
request URLs containing credentials, or entire HTTP error bodies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlsplit
from pathlib import Path
import re
import time

import requests
from dotenv import dotenv_values

from .rate_limits import safe_retry_after


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


def local_credentials() -> dict[str, str | None]:
    """Read only the project's .env; never inherit shell or parent-folder keys."""
    return dotenv_values(Path(__file__).resolve().parents[1] / ".env", interpolate=False)


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
    normalized_count: int = 0  # Before the local sample cap; not a coverage estimate.
    http_status: int | None = None
    rate_limit_headers: dict[str, str] = field(default_factory=dict)
    outcome: str = ""  # records / empty / invalid_records / classified failure / missing_credentials


@dataclass
class HTTPResponse:
    payload: Any
    status_code: int
    rate_limit_headers: dict[str, str]


class APIError(Exception):
    """Safe, redacted transport error; must not include credentials or URLs."""

    def __init__(self, message: str, *, kind: str = "schema", status: int | None = None,
                 rate_headers: dict[str, str] | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.rate_headers = rate_headers or {}


def _http_get_json(url: str, params: dict[str, Any], headers: dict[str, str], timeout: float) -> Any:
    try:
        # No automatic retries or redirects that might spend quota or forward tokens.
        response = requests.get(url, params=params, headers=headers, timeout=timeout,
                                allow_redirects=False)
    except requests.RequestException as exc:
        # Do not display str(exc): requests may embed URL query parameters / API keys.
        raise APIError(f"Transport error ({type(exc).__name__})", kind="transport") from None
    rate_headers = {}
    for name in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
        value = response.headers.get(name, "")
        # Quotas are numeric; Retry-After also permits a validated HTTP date.
        if name == "Retry-After" and value:
            safe = safe_retry_after(value)
            if safe is not None:
                rate_headers[name] = safe
        elif value and value.isascii() and value.isdecimal():
            rate_headers[name] = value
    if response.status_code != 200:
        kind = "auth" if response.status_code in (401, 403) else (
            "rate_limit" if response.status_code == 429 else "http")
        raise APIError(f"HTTP {response.status_code}", kind=kind,
                       status=response.status_code, rate_headers=rate_headers)
    try:
        payload = response.json()
    except ValueError:
        raise APIError("Invalid JSON response", kind="invalid_json", status=200,
                       rate_headers=rate_headers) from None
    return HTTPResponse(payload, response.status_code, rate_headers)


GetJSON = Callable[[str, dict[str, Any], dict[str, str], float], Any]


def _source(url: str, provider_source: str | None) -> str:
    return _text(provider_source) or urlsplit(url).hostname or "unknown"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _gdelt_datetime(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        return ""
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return ""  # Never pass an unvalidated observed time off as a publication time.


def _published_datetime(value: Any) -> str:
    """Marketaux dates and NewsData's explicitly requested UTC dates."""
    if not isinstance(value, str) or not re.search(r"[T ]\d{2}:\d{2}", value):
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def normalize(provider: str, payload: Any) -> tuple[list[Article], int]:
    """Normalize successful provider responses; fail on unexpected JSON shapes."""
    if provider == "gdelt":
        if not isinstance(payload, dict):
            raise APIError("Unexpected GDELT response shape")
        raw = payload.get("articles")
    elif provider == "marketaux":
        if not isinstance(payload, dict):
            raise APIError("Unexpected Marketaux response shape")
        raw = payload.get("data")
    elif provider == "newsdata":
        if not isinstance(payload, dict):
            raise APIError("Unexpected NewsData response shape")
        if payload.get("status") != "success":
            raise APIError("NewsData did not return success status", kind="provider_error")
        raw = payload.get("results")
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
        title = _text(row.get("headline" if provider == "finnhub" else "title"))
        url = _text(row.get("link" if provider == "newsdata" else "url"))
        try:
            parsed = urlsplit(url)
            valid_url = (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                         and parsed.username is None and parsed.password is None)
        except ValueError:
            valid_url = False
        if not title or not valid_url:
            continue

        if provider == "gdelt":
            ts = _gdelt_datetime(row.get("seendate"))
            kind = "first_seen"
            desc = ""  # DOC API ArticleList does not promise full article descriptions.
            source = _source(url, row.get("domain"))
        elif provider == "marketaux":
            ts = _published_datetime(row.get("published_at"))
            kind = "published"
            desc = _text(row.get("description"))
            source = _source(url, row.get("source"))
        elif provider == "newsdata":
            ts = _published_datetime(row.get("pubDate"))
            kind = "published"
            desc = _text(row.get("description"))
            source = _source(url, row.get("source_name") or row.get("source_id"))
        else:  # finnhub
            unix_time = row.get("datetime")
            try:
                if isinstance(unix_time, bool) or int(unix_time) <= 0:
                    raise ValueError
                ts = datetime.fromtimestamp(int(unix_time), tz=timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError, OSError):
                ts = ""
            kind = "published"
            desc = _text(row.get("summary"))
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
    now = now.astimezone(timezone.utc)
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
            {"q": keyword, "language": "en", "size": min(limit, 10), "timezone": "UTC"},
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
    key = local_credentials().get(env_key) if env_key else None
    if env_key and not key:
        return QueryResult(provider, topic, "not_run", "skipped", [],
                           note=f"Missing {env_key} in local .env", outcome="missing_credentials")
    url, params, headers, query_mode, note = build_request(provider, topic, now, days, limit, key)
    started = time.perf_counter()
    http_status = None
    rate_headers = {}
    try:
        payload = transport(url, params, headers, timeout)
        if isinstance(payload, HTTPResponse):
            http_status = payload.status_code
            rate_headers = payload.rate_limit_headers
            payload = payload.payload
        items, raw_count = normalize(provider, payload)
    except APIError as exc:
        return QueryResult(provider, topic, query_mode, "failed", [],
                           latency_ms=round((time.perf_counter()-started)*1000, 1),
                           http_status=exc.status or http_status,
                           rate_limit_headers=exc.rate_headers or rate_headers,
                           outcome=exc.kind,
                           note=f"{note} Request failed ({exc.kind}); HTTP status={exc.status or http_status}")
    except Exception as exc:
        # Don't leak params, headers, API keys or raw response errors into report.
        return QueryResult(provider, topic, query_mode, "failed", [],
                           latency_ms=round((time.perf_counter()-started)*1000, 1),
                           http_status=http_status, rate_limit_headers=rate_headers,
                           outcome="unexpected_error",
                           note=f"{note} Unexpected error: {type(exc).__name__}")
    if raw_count and not items:
        return QueryResult(provider, topic, query_mode, "failed", [], raw_count=raw_count,
                           latency_ms=round((time.perf_counter()-started)*1000, 1),
                           http_status=http_status, rate_limit_headers=rate_headers,
                           outcome="invalid_records", note=f"{note} No valid records in nonempty array.")
    return QueryResult(provider, topic, query_mode, "ok", items[:limit],
                       raw_count=raw_count, normalized_count=len(items),
                       http_status=http_status, rate_limit_headers=rate_headers,
                       outcome="records" if items else "empty",
                       latency_ms=round((time.perf_counter()-started)*1000, 1), note=note)
