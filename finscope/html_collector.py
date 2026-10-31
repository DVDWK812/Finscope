"""Optional, manual RBA HTML-index collector; no RSS, APIs or article-page requests."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .api_sources import Article
from . import rss_collector as rss


INDEX_URL = "https://www.rba.gov.au/media-releases/"
ROBOTS_URL = rss.ROBOTS_URL
SOURCE = rss.SOURCE
TERMS_URL = rss.TERMS_URL
LICENSE_URL = rss.LICENSE_URL
USER_AGENT = "FinScope-RBA-HTML-Prototype/0.1"
from .test_safety import data_path
DATA_DIR = data_path('reports', 'html')
MAX_BYTES = 1_000_000
MAX_STORED = 100
MAX_STORE_BYTES = 5_000_000
RELEASE_PATH = re.compile(r"/media-releases/(20\d{2})/mr-(\d{2})-\d{2}\.html\Z")
DATE_TEXT = re.compile(
    r"\b([1-9]|[12]\d|3[01])\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(20\d{2})\b", re.IGNORECASE,
)


class CollectionError(ValueError):
    """Redacted outcome category; never includes fetched text or personal data."""


def _release_url(href: str) -> str:
    """Allow only an actual RBA media-release HTML page; never follow hrefs."""
    if not href or len(href) > 1000 or any(c.isspace() or ord(c) < 32 for c in href):
        return ""
    try:
        url = urljoin(INDEX_URL, href)
        parts = urlsplit(url)
        match = RELEASE_PATH.fullmatch(parts.path)
        if (parts.scheme != "https" or parts.hostname != "www.rba.gov.au"
                or parts.username is not None or parts.password is not None
                or parts.port is not None or parts.query or parts.fragment
                or not match or int(match.group(1)) % 100 != int(match.group(2))):
            return ""
        return url
    except ValueError:
        return ""


def _tidy(value: str) -> str:
    return " ".join(value.split())


class _IndexParser(HTMLParser):
    """Collect anchor titles and nearby following date text, not arbitrary site links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []
        self._href: str | None = None
        self._title: list[str] = []
        # HTMLParser owns _pending on Python 3.11; keep release state separate.
        self._pending_release: tuple[str, str, list[str]] | None = None
        self._ignored: list[str] = []

    def _flush(self) -> None:
        if self._pending_release is not None:
            href, title, nearby = self._pending_release
            url = _release_url(href)
            if url:
                self.links.append((url, title, _tidy("".join(nearby))[:500]))
        self._pending_release = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "template"):
            self._ignored.append(tag)
        if self._ignored:
            return
        if tag == "a":
            self._flush()
            self._href = dict(attrs).get("href") or ""
            self._title = []
        elif self._pending_release is not None and tag in ("p", "div", "li", "br", "span", "time"):
            self._pending_release[2].append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored:
            if tag == self._ignored[-1]:
                self._ignored.pop()
            return
        if tag == "a" and self._href is not None:
            self._pending_release = (self._href, _tidy("".join(self._title))[:301], [])
            self._href = None
            self._title = []
        elif tag in ("article", "li", "tr"):
            # A missing date must not be borrowed from the following release.
            self._flush()
            self._href = None
            self._title = []

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        if self._href is not None:
            self._title.append(data)
        elif self._pending_release is not None:
            self._pending_release[2].append(data)

    def finish(self) -> None:
        self._flush()


def _date_info(nearby: str, url: str) -> tuple[str, str]:
    matches = list(DATE_TEXT.finditer(nearby))
    if not matches:
        return "", ""
    original = " | ".join(match.group(0) for match in matches)
    if len(matches) != 1:
        return original, ""  # Ambiguous nearby dates are not publication evidence.
    try:
        parsed = datetime.strptime(original.title(), "%d %B %Y")
    except ValueError:
        return original, ""
    # Fail closed on inconsistent date/year instead of silently assigning a wrong date.
    if str(parsed.year) != urlsplit(url).path.split("/")[2]:
        return original, ""
    return original, parsed.date().isoformat()


def parse_index(payload: bytes, *, seen_urls=(), limit: int = 3) -> dict:
    """Extract only index-linked releases. A date-only value never becomes a UTC timestamp."""
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if len(payload) > MAX_BYTES:
        raise CollectionError("response_too_large")
    try:
        html = payload.decode("utf-8-sig")
    except UnicodeError:
        raise CollectionError("invalid_html_encoding") from None
    if "\x00" in html:
        raise CollectionError("invalid_html_encoding")
    if "media releases" not in html.lower():
        raise CollectionError("unexpected_html_schema")
    parser = _IndexParser()
    try:
        parser.feed(html)
        parser.close()
        parser.finish()
    except (ValueError, AssertionError):
        raise CollectionError("invalid_html") from None
    if not parser.links:
        raise CollectionError("unexpected_html_schema")
    seen = set(seen_urls)
    articles, provenance = [], []
    duplicates = invalid = eligible = 0
    for url, title, nearby in parser.links:
        if url in seen:
            duplicates += 1
            continue
        seen.add(url)
        if not title or len(title) > 300:
            invalid += 1
            continue
        eligible += 1
        if len(articles) >= limit:
            continue
        original_date, date_only = _date_info(nearby, url)
        year = urlsplit(url).path.split("/")[2]
        articles.append(Article("rba_html", title, url, SOURCE, "", "", "published"))
        provenance.append({
            "url": url,
            "publication_date_original": original_date,
            "publication_date": date_only,
            "timestamp_precision": "date_only" if date_only else "unknown",
            "attribution": f"Source: {SOURCE} {year}",
        })
    return {
        "articles": articles, "provenance": provenance,
        "raw_count": len(parser.links), "duplicate_urls": duplicates,
        "invalid_records": invalid, "eligible_new_records": eligible,
        "missing_exact_publication_times": len(articles),
        "missing_publication_dates": sum(not p["publication_date"] for p in provenance),
        "missing_summaries": len(articles),
    }


def _get(url: str, *, request_log: list[dict] | None = None) -> tuple[bytes, int]:
    """Only two fixed endpoints, at most one GET each, bounded and nonredirecting."""
    if url not in (INDEX_URL, ROBOTS_URL):
        raise CollectionError("unapproved_endpoint")
    started = time.monotonic()
    request = {"url": url, "query_utc": datetime.now(timezone.utc).isoformat(),
               "http_status": None, "received_bytes": 0}
    if request_log is not None:
        request_log.append(request)
    try:
        with requests.get(
            url, headers={"User-Agent": USER_AGENT,
                          "Accept": "text/html" if url == INDEX_URL else "text/plain"},
            timeout=(5, 10), allow_redirects=False, stream=True,
        ) as response:
            request["http_status"] = response.status_code
            if response.status_code != 200:
                raise CollectionError(f"http_{response.status_code}")
            if response.headers.get("Retry-After"):
                raise CollectionError("retry_after_stop")
            kind = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if url == INDEX_URL and kind not in ("text/html", "application/xhtml+xml"):
                raise CollectionError("unexpected_content_type")
            if url == ROBOTS_URL and kind not in ("text/plain", ""):
                raise CollectionError("unexpected_content_type")
            chunks = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                chunks.extend(chunk)
                request["received_bytes"] = len(chunks)
                if len(chunks) > MAX_BYTES:
                    raise CollectionError("response_too_large")
                if time.monotonic() - started > 20:
                    raise CollectionError("response_deadline")
            return bytes(chunks), response.status_code
    except requests.RequestException:
        raise CollectionError("transport") from None


def collect_once(*, seen_urls=(), limit: int = 3, get=None,
                 request_log: list[dict] | None = None) -> dict:
    """Check robots on every invocation; never visit discovered article links."""
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if get is None:
        def get(url):
            return _get(url, request_log=request_log)
    robots, robots_http_status = get(ROBOTS_URL)
    try:
        text = robots.decode("utf-8-sig")
        if "user-agent:" not in text.lower() or "\x00" in text:
            raise CollectionError("invalid_robots")
        policy = RobotFileParser()
        policy.parse(text.splitlines())
    except UnicodeError:
        raise CollectionError("invalid_robots") from None
    if not policy.can_fetch(USER_AGENT, INDEX_URL):
        raise CollectionError("robots_disallowed")
    query_utc = datetime.now(timezone.utc).isoformat()
    page, index_http_status = get(INDEX_URL)
    return {
        **parse_index(page, seen_urls=seen_urls, limit=limit),
        "robots_http_status": robots_http_status,
        "index_http_status": index_http_status,
        "index_bytes": len(page), "index_query_utc": query_utc,
    }


def _load_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        if path.stat().st_size > MAX_STORE_BYTES:
            raise ValueError()
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) > MAX_STORED:
            raise ValueError()
        seen = set()
        for row in rows:
            article = Article(**row["article"])
            if (not all(isinstance(v, str) for v in asdict(article).values())
                    or article.provider != "rba_html" or article.source != SOURCE
                    or article.timestamp or article.description
                    or article.timestamp_kind != "published"
                    or _release_url(article.url) != article.url or not article.url or article.url in seen
                    or not isinstance(row["provenance"], dict)):
                raise ValueError()
            seen.add(article.url)
        return rows
    except (OSError, ValueError, TypeError, KeyError):
        raise CollectionError("invalid_local_store_review_required") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--collect", action="store_true", help="Explicit manual network collection")
    mode.add_argument("--dry-run", action="store_true", help="Offline preview (also the default)")
    parser.add_argument("--limit", type=int, choices=range(1, 11), default=3)
    args = parser.parse_args(argv)
    if not args.collect:
        print(json.dumps({"status": "skipped", "outcome": "preview", "index_url": INDEX_URL,
                          "limit": args.limit, "network_requests": 0,
                          "article_page_requests": 0, "public_app_integration": False}))
        return 0
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = DATA_DIR / "collection.lock"
    try:
        lock_fd = lock.open("x")
    except FileExistsError:
        print(json.dumps({"status": "skipped", "outcome": "locked_review_if_stale"}))
        return 1
    started = datetime.now(timezone.utc)
    report = {
        "query_utc": started.isoformat(), "index_url": INDEX_URL, "source": SOURCE,
        "terms_url": TERMS_URL, "license_url": LICENSE_URL,
        "rights_scope": "RBA-authored index titles; exclusions apply; local review only",
        "public_app_integration": False, "article_page_requests": 0, "limit": args.limit,
        "new_records": 0, "requests": [],
    }
    try:
        store = DATA_DIR / "articles.json"
        rows = _load_store(store)
        if len(rows) >= MAX_STORED:
            report.update(status="skipped", outcome="local_capacity")
        else:
            # The RSS store is read-only. A malformed RSS file must be reviewed;
            # never silently assume its URLs are safe or unique.
            try:
                rss_rows = rss._load_store(rss.DATA_DIR / "articles.json")
            except rss.CollectionError:
                raise CollectionError("invalid_rss_store_review_required") from None
            seen_urls = [r["article"]["url"] for r in rows + rss_rows]
            result = collect_once(seen_urls=seen_urls, limit=min(args.limit, MAX_STORED - len(rows)),
                                  request_log=report["requests"])
            articles = result.pop("articles")
            provenance = result.pop("provenance")
            report.update(result, status="ok",
                          outcome="records" if articles else "no_new_records")
            for article, origin in zip(articles, provenance):
                rows.append({
                    "article": asdict(article), "provenance": origin,
                    "collected_at_utc": started.isoformat(), "index_url": INDEX_URL,
                    "terms_url": TERMS_URL, "license_url": LICENSE_URL,
                })
            serialized = json.dumps(rows, indent=2, ensure_ascii=False)
            if len(serialized.encode("utf-8")) > MAX_STORE_BYTES:
                raise CollectionError("local_store_byte_capacity")
            temporary = store.with_suffix(".tmp")
            temporary.write_text(serialized, encoding="utf-8")
            temporary.replace(store)
            report["new_records"] = len(articles)
    except CollectionError as exc:
        report.update(status="failed", outcome=str(exc))
    except OSError:
        report.update(status="failed", outcome="local_io")
    finally:
        lock_fd.close()
        lock.unlink()
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["network_requests"] = len(report["requests"])
    evidence = DATA_DIR / f"run_{started.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    evidence.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(report["status"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
