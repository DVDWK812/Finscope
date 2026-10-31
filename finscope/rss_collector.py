"""Manual, local-only RBA media-release RSS prototype. No article-page fetching."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

import requests

from .api_sources import Article


FEED_URL = "https://www.rba.gov.au/rss/rss-cb-media-releases.xml"
ROBOTS_URL = "https://www.rba.gov.au/robots.txt"
SOURCE = "Reserve Bank of Australia"
USER_AGENT = "FinScope-RSS-Prototype/0.1"
TERMS_URL = "https://www.rba.gov.au/copyright/"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
from .test_safety import data_path
DATA_DIR = data_path('reports', 'rss')
MAX_BYTES = 1_000_000
MAX_STORED = 100
MAX_STORE_BYTES = 5_000_000


class CollectionError(ValueError):
    """A safe failure category, without response bodies or request diagnostics."""


def _publication(value: str) -> str:
    try:
        stamp = parsedate_to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return ""
    if stamp.tzinfo is None or not re.search(r"\d{2}:\d{2}", value):
        return ""
    try:
        return stamp.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        return ""


def _official_link(value: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme in ("https", "http") and url.hostname == "www.rba.gov.au"
                and url.username is None and url.password is None and url.port is None
                and url.path.startswith("/media-releases/")
                and not any(c.isspace() or ord(c) < 32 for c in value))
    except ValueError:
        return False


def parse_feed(payload: bytes, *, seen_urls=(), limit: int = 3) -> dict:
    """Parse RSS 1.0/RDF or 2.0; deduplicate links before field processing.

    Descriptions remain feed-provided text (possibly HTML), never rendered or
    fetched. Missing/invalid dates stay blank; collection time is separate.
    """
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if len(payload) > MAX_BYTES:
        raise CollectionError("response_too_large")
    try:
        xml = payload.decode("utf-8-sig")
        if "\x00" in xml or re.search(r"<!\s*(DOCTYPE|ENTITY)", xml, re.I):
            raise CollectionError("unsafe_xml")
        root = ET.fromstring(xml)
    except (UnicodeError, ET.ParseError):
        raise CollectionError("invalid_xml") from None
    namespace = ""
    if root.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF":
        namespace = "{http://purl.org/rss/1.0/}"
        channel = root.find(namespace + "channel")
        items = root.findall(namespace + "item")
    elif root.tag == "rss" and root.get("version") == "2.0":
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
    else:
        raise CollectionError("unexpected_feed_schema")
    if channel is None:
        raise CollectionError("unexpected_feed_schema")
    seen = set(seen_urls)
    articles, provenance = [], []
    duplicates = invalid = eligible = 0
    for item in items:
        url = (item.findtext(namespace + "link") or "").strip()
        if not _official_link(url):
            invalid += 1
            continue
        if url in seen:
            duplicates += 1
            continue
        seen.add(url)
        title = (item.findtext(namespace + "title") or "").strip()
        if not title:
            invalid += 1
            continue
        eligible += 1
        if len(articles) >= limit:
            continue
        raw_date = (item.findtext("pubDate") or
                    item.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
        stamp = _publication(raw_date)
        year = stamp[:4] or re.search(r"/media-releases/(\d{4})/", url)
        if not isinstance(year, str):
            year = year.group(1) if year else "year unavailable"
        articles.append(Article("rba_rss", title, url, SOURCE,
                                (item.findtext(namespace + "description") or "").strip(),
                                stamp, "published"))
        provenance.append({"url": url, "publication_time_original": raw_date,
                           "attribution": f"Source: {SOURCE} {year}",
                           "feed_source_element": (item.findtext(namespace + "source") or "").strip()})
    return {"articles": articles, "provenance": provenance, "raw_count": len(items),
            "duplicate_urls": duplicates, "invalid_records": invalid,
            "eligible_new_records": eligible,
            "missing_publication_times": sum(not a.timestamp for a in articles),
            "missing_summaries": sum(not a.description for a in articles)}


def _get(url: str) -> tuple[bytes, int]:
    """One bounded GET, no redirects/retries, streaming byte/deadline limits."""
    start = time.monotonic()
    try:
        with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=(5, 10),
                          allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise CollectionError(f"http_{response.status_code}")
            # Even a successful Retry-After means stop; never automatically retry.
            if response.headers.get("Retry-After"):
                raise CollectionError("retry_after_stop")
            data = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise CollectionError("response_too_large")
                if time.monotonic() - start > 20:
                    raise CollectionError("response_deadline")
            return bytes(data), response.status_code
    except requests.RequestException:
        raise CollectionError("transport") from None


def collect_once(*, seen_urls=(), limit=3, get=_get) -> dict:
    """Read robots once, then at most one fixed feed; never fetch article URLs."""
    robots, robots_status = get(ROBOTS_URL)
    try:
        policy = RobotFileParser()
        policy.parse(robots.decode("utf-8-sig").splitlines())
    except UnicodeError:
        raise CollectionError("invalid_robots") from None
    if not policy.can_fetch(USER_AGENT, FEED_URL):
        raise CollectionError("robots_disallowed")
    query_utc = datetime.now(timezone.utc).isoformat()
    body, feed_status = get(FEED_URL)
    return {**parse_feed(body, seen_urls=seen_urls, limit=limit),
            "robots_http_status": robots_status, "feed_http_status": feed_status,
            "feed_bytes": len(body), "feed_query_utc": query_utc}


def _load_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        if path.stat().st_size > MAX_STORE_BYTES:
            raise ValueError()
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) > MAX_STORED:
            raise ValueError()
        urls = set()
        for row in rows:
            article = Article(**row["article"])
            if (not all(isinstance(value, str) for value in asdict(article).values())
                    or article.provider != "rba_rss" or article.source != SOURCE
                    or not _official_link(article.url) or article.url in urls):
                raise ValueError()
            urls.add(article.url)
        return rows
    except (OSError, ValueError, TypeError, KeyError):
        raise CollectionError("invalid_local_store_review_required") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--collect", action="store_true", help="Explicit manual network collection")
    mode.add_argument("--dry-run", action="store_true", help="Preview only (also the default)")
    parser.add_argument("--limit", type=int, choices=range(1, 11), default=3)
    args = parser.parse_args(argv)
    if not args.collect:
        print(json.dumps({"status": "skipped", "outcome": "preview", "feed_url": FEED_URL,
                          "limit": args.limit, "network_requests": 0,
                          "public_app_integration": False}))
        return 0
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = DATA_DIR / "collection.lock"
    try:
        lock_fd = lock.open("x")
    except FileExistsError:
        print(json.dumps({"status": "skipped", "outcome": "locked_review_if_stale"}))
        return 1
    started = datetime.now(timezone.utc)
    report = {"query_utc": started.isoformat(), "feed_url": FEED_URL, "source": SOURCE,
              "terms_url": TERMS_URL, "license_url": LICENSE_URL,
              "rights_scope": "RBA-authored RSS text; exclusions/special terms apply; local review only",
              "public_app_integration": False, "limit": args.limit}
    try:
        store = DATA_DIR / "articles.json"
        rows = _load_store(store)
        if len(rows) >= MAX_STORED:
            report.update(status="skipped", outcome="local_capacity", new_records=0)
        else:
            result = collect_once(seen_urls=[r["article"]["url"] for r in rows],
                                  limit=min(args.limit, MAX_STORED - len(rows)))
            articles = result.pop("articles")
            provenance = result.pop("provenance")
            report.update(result, status="ok", outcome=("records" if articles else
                          "empty" if not result["raw_count"] else
                          "invalid_records" if result["invalid_records"] == result["raw_count"]
                          else "no_new_records"), new_records=0)
            for article, origin in zip(articles, provenance):
                rows.append({"article": asdict(article), "provenance": origin,
                             "collected_at_utc": started.isoformat(), "feed_url": FEED_URL,
                             "terms_url": TERMS_URL, "license_url": LICENSE_URL})
            temporary = store.with_suffix(".tmp")
            serialized = json.dumps(rows, indent=2, ensure_ascii=False)
            if len(serialized.encode("utf-8")) > MAX_STORE_BYTES:
                raise CollectionError("local_store_byte_capacity")
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
    evidence = DATA_DIR / f"run_{started.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    evidence.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(report["status"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
