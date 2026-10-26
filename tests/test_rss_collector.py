"""Authored RSS fixtures only; no external requests, models or UI inference."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from finscope import rss_collector as rss
from finscope.api_sources import Article


URL = "https://www.rba.gov.au/media-releases/2026/synthetic.html?ref=original#part"


def item(url=URL, title="Authored synthetic release", date="Tue, 27 Oct 2026 14:30:00 +1100",
         summary="&lt;p&gt;Synthetic summary &amp; details&lt;/p&gt;"):
    return (f"<item><title>{title}</title><link>{url.replace('&', '&amp;')}</link>"
            f"<pubDate>{date}</pubDate><description>{summary}</description></item>")


def feed(*items):
    return ("<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
            "<title>Synthetic fixture</title>" + "".join(items) + "</channel></rss>").encode()


class ParserTests(unittest.TestCase):
    def test_rba_rss1_rdf_and_dublin_core_date(self):
        payload = b'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
          <channel rdf:about="https://www.rba.gov.au/rss/synthetic.xml"><title>Fixture</title></channel>
          <item><title>Synthetic only</title>
            <link>https://www.rba.gov.au/media-releases/2026/synthetic.html</link>
            <description>Authored summary</description><dc:date>2026-10-27T14:30:00+11:00</dc:date>
          </item></rdf:RDF>'''
        result = rss.parse_feed(payload)
        self.assertEqual(result["raw_count"], 1)
        self.assertEqual(result["articles"][0].timestamp, "2026-10-27T03:30:00+00:00")
        self.assertEqual(result["articles"][0].description, "Authored summary")

    def test_unified_schema_attribution_original_url_and_times(self):
        result = rss.parse_feed(feed(item()))
        article = result["articles"][0]
        self.assertIsInstance(article, Article)
        self.assertEqual(article.url, URL)
        self.assertEqual(article.source, rss.SOURCE)
        self.assertEqual(article.provider, "rba_rss")
        self.assertEqual(article.description, "<p>Synthetic summary & details</p>")
        self.assertEqual(article.timestamp, "2026-10-27T03:30:00+00:00")
        self.assertEqual(article.timestamp_kind, "published")
        self.assertEqual(result["provenance"][0]["attribution"],
                         "Source: Reserve Bank of Australia 2026")
        self.assertIn("+1100", result["provenance"][0]["publication_time_original"])

    def test_dedup_before_fields_and_limit_including_prior_runs(self):
        result = rss.parse_feed(feed(item(), item(title="Changed duplicate"),
                                     item(URL + "x"), item(URL + "y")), limit=1)
        self.assertEqual(result["duplicate_urls"], 1)
        self.assertEqual(result["eligible_new_records"], 3)
        self.assertEqual(len(result["articles"]), 1)
        result = rss.parse_feed(feed(item(title=""), item(title="Duplicate valid"),
                                     item(URL + "x")), seen_urls=[URL])
        self.assertEqual(result["duplicate_urls"], 2)
        self.assertEqual([a.url for a in result["articles"]], [URL + "x"])

    def test_missing_summary_and_invalid_or_naive_dates_not_collection_time(self):
        for date in ("", "bad", "2026-10-27", "2026-10-27T12:00:00"):
            with self.subTest(date=date):
                result = rss.parse_feed(feed(item(date=date, summary="")))
                self.assertEqual(result["articles"][0].timestamp, "")
                self.assertEqual(result["missing_publication_times"], 1)
                self.assertEqual(result["missing_summaries"], 1)
        self.assertEqual(rss._publication("2026-10-27T03:00:00Z"),
                         "2026-10-27T03:00:00+00:00")

    def test_untrusted_links_and_blank_titles_are_invalid(self):
        urls = ["https://finance.yahoo.com/news/a", "javascript:alert(1)",
                "https://www.rba.gov.au.evil.org/media-releases/a",
                "https://user:pass@www.rba.gov.au/media-releases/a",
                "https://[broken", "https://www.rba.gov.au/media-releases/a b",
                "https://www.rba.gov.au:443/media-releases/a"]
        result = rss.parse_feed(feed(*(item(url=u) for u in urls), item(title="")))
        self.assertEqual(result["invalid_records"], len(urls) + 1)
        self.assertEqual(result["articles"], [])

    def test_empty_distinct_from_malformed_or_unsafe(self):
        self.assertEqual(rss.parse_feed(feed())["raw_count"], 0)
        for payload in (b"<broken", b"<html/>", b"<rss version='2.0'/>",
                        b"<!DOCTYPE rss [<!ENTITY x 'bad'>]><rss/>",
                        "<!DOCTYPE rss><rss/>".encode("utf-16"), b"\x00<rss/>",
                        b"x" * (rss.MAX_BYTES + 1)):
            with self.subTest(payload=payload[:25]), self.assertRaises(rss.CollectionError):
                rss.parse_feed(payload)
        for limit in (0, 11):
            with self.assertRaises(ValueError):
                rss.parse_feed(feed(), limit=limit)


class CollectionTests(unittest.TestCase):
    def test_single_fixed_feed_and_robots_no_article_page_calls(self):
        get = Mock(side_effect=[(b"User-agent: *\nDisallow: /private/", 200),
                                (feed(item()), 200)])
        result = rss.collect_once(get=get)
        self.assertEqual([c.args[0] for c in get.call_args_list],
                         [rss.ROBOTS_URL, rss.FEED_URL])
        self.assertEqual(len(result["articles"]), 1)

    def test_robots_denial_and_transport_stop_without_feed_retry(self):
        for first in ((b"User-agent: *\nDisallow: /rss/", 200),
                      rss.CollectionError("http_403")):
            get = Mock(side_effect=[first])
            with self.assertRaises(rss.CollectionError):
                rss.collect_once(get=get)
            self.assertEqual(get.call_count, 1)

    def test_transport_bounds_and_status_failures(self):
        for status, headers, chunks, category in (
                (302, {}, [], "http_302"), (403, {}, [], "http_403"),
                (429, {}, [], "http_429"), (200, {"Retry-After": "60"}, [], "retry_after_stop"),
                (200, {}, [b"x" * (rss.MAX_BYTES + 1)], "response_too_large")):
            response = Mock(status_code=status, headers=headers)
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.iter_content.return_value = chunks
            with patch.object(rss.requests, "get", return_value=response) as get:
                with self.assertRaisesRegex(rss.CollectionError, category):
                    rss._get(rss.FEED_URL)
                self.assertEqual(get.call_count, 1)
                self.assertFalse(get.call_args.kwargs["allow_redirects"])
                self.assertEqual(get.call_args.kwargs["timeout"], (5, 10))
                self.assertTrue(get.call_args.kwargs["stream"])
        with patch.object(rss.requests, "get", side_effect=requests.Timeout("secret body")):
            with self.assertRaisesRegex(rss.CollectionError, "^transport$"):
                rss._get(rss.FEED_URL)

    def test_default_preview_has_no_network_or_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rss, "DATA_DIR", Path(folder) / "absent"), \
                patch.object(rss.requests, "get") as get, redirect_stdout(StringIO()) as output:
            self.assertEqual(rss.main([]), 0)
            self.assertEqual(rss.main(["--dry-run"]), 0)
            get.assert_not_called()
            self.assertFalse(rss.DATA_DIR.exists())
            self.assertIn('"status": "skipped"', output.getvalue())

    def test_bounded_local_smoke_persistence_and_second_run_dedup(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rss, "DATA_DIR", Path(folder)), \
                redirect_stdout(StringIO()):
            fake = Mock(side_effect=[(b"User-agent: *\nAllow: /", 200),
                                     (feed(item(), item(), item(URL + "2")), 200)] * 2)
            # Exercise the CLI through the real collector/parser, replacing only HTTP.
            original = rss.collect_once
            with patch.object(rss, "collect_once", side_effect=lambda **kw: original(get=fake, **kw)):
                self.assertEqual(rss.main(["--collect", "--limit", "2"]), 0)
                self.assertEqual(rss.main(["--collect", "--limit", "2"]), 0)
            rows = json.loads((Path(folder) / "articles.json").read_text())
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({r["article"]["url"] for r in rows}), 2)
            self.assertTrue(all(r["collected_at_utc"] != r["article"]["timestamp"] for r in rows))
            reports = [json.loads(p.read_text()) for p in sorted(Path(folder).glob("run_*.json"))]
            self.assertEqual([r["new_records"] for r in reports], [2, 0])
            self.assertEqual(reports[1]["outcome"], "no_new_records")
            self.assertEqual(fake.call_count, 4)
            self.assertFalse((Path(folder) / "collection.lock").exists())

    def test_failure_preserves_store_and_records_failed_not_skipped(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rss, "DATA_DIR", Path(folder)), \
                redirect_stdout(StringIO()):
            store = Path(folder) / "articles.json"
            store.write_text("[]")
            with patch.object(rss, "collect_once", side_effect=rss.CollectionError("http_429")) as collect:
                self.assertEqual(rss.main(["--collect"]), 1)
                self.assertEqual(collect.call_count, 1)
            self.assertEqual(store.read_text(), "[]")
            report = json.loads(next(Path(folder).glob("run_*.json")).read_text())
            self.assertEqual((report["status"], report["outcome"]), ("failed", "http_429"))

    def test_locked_or_invalid_store_never_collects(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rss, "DATA_DIR", Path(folder)), \
                patch.object(rss, "collect_once") as collect, redirect_stdout(StringIO()):
            lock = Path(folder) / "collection.lock"
            lock.touch()
            self.assertEqual(rss.main(["--collect"]), 1)
            lock.unlink()
            (Path(folder) / "articles.json").write_text("invalid")
            self.assertEqual(rss.main(["--collect"]), 1)
            collect.assert_not_called()

    def test_store_capacity_skips_network_and_byte_overflow_preserves_store(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(rss, "DATA_DIR", Path(folder)), \
                redirect_stdout(StringIO()):
            store = Path(folder) / "articles.json"
            store.write_text("[]")
            with patch.object(rss, "MAX_STORED", 0), patch.object(rss, "collect_once") as collect:
                self.assertEqual(rss.main(["--collect"]), 0)
                collect.assert_not_called()
            result = rss.parse_feed(feed(item()))
            with patch.object(rss, "MAX_STORE_BYTES", 5), \
                    patch.object(rss, "collect_once", return_value=result):
                self.assertEqual(rss.main(["--collect"]), 1)
            self.assertEqual(store.read_text(), "[]")
            reports = [json.loads(p.read_text()) for p in sorted(Path(folder).glob("run_*.json"))]
            self.assertEqual(reports[-1]["outcome"], "local_store_byte_capacity")
            self.assertEqual(reports[-1]["new_records"], 0)


if __name__ == "__main__":
    unittest.main()
