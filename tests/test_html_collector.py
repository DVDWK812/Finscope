"""Offline HTML collector tests; no live news requests."""
import json
import tempfile
import unittest
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch
import requests
from finscope.api_sources import Article
from finscope import html_collector as h, rss_collector as rss

URL = "https://www.rba.gov.au/media-releases/2026/mr-26-29.html"
URL2 = "https://www.rba.gov.au/media-releases/2026/mr-26-28.html"
def page(*rows):
    return ("<html><h1>Media Releases</h1>" + "".join(rows) + "</html>").encode()
def row(url=URL, title="Synthetic release", date="14 October 2026"):
    return f'<article><a href="{url}">{title}</a><p>{date}</p></article>'

class ParserTests(unittest.TestCase):
    def test_index_date_only(self):
        r = h.parse_index(page(row()))
        self.assertEqual(r["raw_count"], 1)
        self.assertEqual(r["articles"][0].timestamp, "")
        self.assertEqual(r["articles"][0].timestamp_kind, "published")
        self.assertEqual(r["articles"][0].description, "")
        self.assertEqual(r["provenance"][0]["publication_date"], "2026-10-14")
        self.assertEqual(r["provenance"][0]["attribution"], "Source: Reserve Bank of Australia 2026")
    def test_existing_and_duplicate_urls(self):
        r = h.parse_index(page(row(), row(), row(URL2)), seen_urls=[URL2])
        self.assertEqual((r["raw_count"], r["duplicate_urls"]), (3, 2))
        self.assertEqual(len(r["articles"]), 1)
    def test_missing_and_wrong_dates(self):
        for date in ("", "14 October 2025", "32 October 2026"):
            self.assertEqual(h.parse_index(page(row(date=date)))["provenance"][0]["publication_date"], "")
    def test_unsafe_links(self):
        for url in ("https://evil.net/media-releases/2026/mr-26-29.html",
                    "https://www.rba.gov.au:443/media-releases/2026/mr-26-29.html",
                    "javascript:alert(1)", URL + "?x=1", URL + "#fragment",
                    "https://www.rba.gov.au/media-releases/2026/other.html"):
            self.assertFalse(h._release_url(url))
    def test_fail_closed_schema(self):
        for body in (b"<html>captcha</html>", b"\xff", b"\x00hello",
                     b"x"*(h.MAX_BYTES+1), page("<script>"+row()+"</script>")):
            with self.assertRaises(h.CollectionError): h.parse_index(body)
    def test_one_index_request_and_robots(self):
        get=Mock(side_effect=[(b"User-agent: *\nAllow: /",200),(page(row()),200)])
        self.assertEqual(len(h.collect_once(get=get)["articles"]),1)
        self.assertEqual([x.args[0] for x in get.call_args_list],[h.ROBOTS_URL,h.INDEX_URL])
        get=Mock(return_value=(b"User-agent: *\nDisallow: /media-releases/",200))
        with self.assertRaisesRegex(h.CollectionError,"robots_disallowed"): h.collect_once(get=get)
        self.assertEqual(get.call_count,1)
    def test_default_no_network(self):
        with tempfile.TemporaryDirectory() as d, patch.object(h,"DATA_DIR",Path(d)/"none"), \
             patch.object(h.requests,"get") as get, redirect_stdout(StringIO()):
            self.assertEqual(h.main([]),0)
            get.assert_not_called()
            self.assertFalse(h.DATA_DIR.exists())
    def test_persistence_rss_exclusion_repeated_run(self):
        with tempfile.TemporaryDirectory() as d, patch.object(h,"DATA_DIR",Path(d)/"html"), \
             patch.object(rss,"DATA_DIR",Path(d)/"rss"), redirect_stdout(StringIO()):
            from dataclasses import asdict
            from finscope.api_sources import Article
            rss.DATA_DIR.mkdir()
            article=Article("rba_rss","RSS",URL2,rss.SOURCE,"summary","", "published")
            (rss.DATA_DIR/"articles.json").write_text(json.dumps([{"article":asdict(article)}]))
            get=Mock(side_effect=[(b"User-agent: *\nAllow: /",200),
                                  (page(row(),row(URL2)),200)]*2)
            real=h.collect_once
            with patch.object(h,"collect_once",side_effect=lambda **kw:real(get=get,**kw)):
                self.assertEqual(h.main(["--collect"]),0)
                self.assertEqual(h.main(["--collect"]),0)
            stored=json.loads((h.DATA_DIR/"articles.json").read_text())
            self.assertEqual([x["article"]["url"] for x in stored],[URL])
            reports=[json.loads(p.read_text()) for p in sorted(h.DATA_DIR.glob("run_*.json"))]
            self.assertEqual([x["new_records"] for x in reports],[1,0])
            self.assertEqual(get.call_count,4)
    def test_invalid_local_store_stops_before_request(self):
        with tempfile.TemporaryDirectory() as d, patch.object(h,"DATA_DIR",Path(d)/"html"), \
             patch.object(rss,"DATA_DIR",Path(d)/"rss"), redirect_stdout(StringIO()):
            h.DATA_DIR.mkdir()
            (h.DATA_DIR/"articles.json").write_text("corrupt")
            with patch.object(h,"collect_once") as collector:
                self.assertEqual(h.main(["--collect"]),1)
                collector.assert_not_called()

class ParserRegressionTests(unittest.TestCase):
    def test_incremental_feed_close_preserves_htmlparser_internal_buffer(self):
        parser = h._IndexParser()
        # Tiny chunks exercise the base parser's incomplete-tag/entity buffers.
        html = page(row(title="Synthetic &amp; <em>nested</em> title")).decode()
        for char in html:
            parser.feed(char)
        parser.close()
        parser.finish()
        self.assertEqual(parser.links, [(URL, "Synthetic & nested title", "14 October 2026")])
        baseline = HTMLParser()
        if hasattr(baseline, "_pending"):
            self.assertEqual(parser._pending, baseline._pending)

    def test_missing_date_cannot_leak_from_following_item(self):
        result = h.parse_index(page(row(date=""), "<article><p>15 October 2026</p>"
                                    f'<a href="{URL2}">Second synthetic release</a></article>'))
        self.assertEqual([p["publication_date"] for p in result["provenance"]], ["", ""])
        self.assertEqual(result["missing_publication_dates"], 2)

    def test_calendar_dates_ambiguity_and_precision(self):
        for text in ("31 April 2026", "29 February 2026", "14 October 2025",
                     "14 October 2026; revised 15 October 2026"):
            with self.subTest(text=text):
                result = h.parse_index(page(row(date=text)))
                self.assertEqual(result["provenance"][0]["timestamp_precision"], "unknown")
                self.assertEqual(result["provenance"][0]["publication_date"], "")
        result = h.parse_index(page(row(date="1 January 2026")))
        self.assertEqual(result["provenance"][0]["publication_date"], "2026-01-01")
        self.assertEqual(result["articles"][0].timestamp, "")

    def test_unclosed_anchor_and_challenge_fail_but_nested_markup_is_parsed(self):
        for body in (page(f'<a href="{URL}">unfinished'), page("Please sign in"),
                     page("<template>" + row() + "</template>")):
            with self.subTest(body=body[:50]), self.assertRaises(h.CollectionError):
                h.parse_index(body)
        result = h.parse_index(page(row(title="Synthetic <strong>release</strong>")))
        self.assertEqual(result["articles"][0].title, "Synthetic release")

    def test_relative_urls_and_rejection_of_other_hosts_or_credentials(self):
        self.assertEqual(h._release_url("/media-releases/2026/mr-26-29.html"), URL)
        for url in ("https://www.rba.gov.au.evil.net/media-releases/2026/mr-26-29.html",
                    "https://user:password@www.rba.gov.au/media-releases/2026/mr-26-29.html",
                    "//evil.net/media-releases/2026/mr-26-29.html", "https://[broken",
                    URL.replace("https:", "http:"), URL.replace("mr-26", "mr-25"),
                    URL + "\n", "https://finance.yahoo.com/news/example"):
            with self.subTest(url=url):
                self.assertEqual(h._release_url(url), "")

    def test_limit_and_invalid_titles_preserve_dedup_counts(self):
        result = h.parse_index(page(row(title=""), row(title="second duplicate"),
                                    row(URL2), row(URL2), row(URL.replace("29", "27"))), limit=1)
        self.assertEqual(result["invalid_records"], 1)
        self.assertEqual(result["duplicate_urls"], 2)
        self.assertEqual(result["eligible_new_records"], 2)
        self.assertEqual([a.url for a in result["articles"]], [URL2])
        for limit in (0, 11):
            get = Mock()
            with self.assertRaises(ValueError):
                h.collect_once(limit=limit, get=get)
            get.assert_not_called()


def response(status=200, content_type="text/html", chunks=None, extra_headers=None):
    reply = Mock(status_code=status, headers={"Content-Type": content_type, **(extra_headers or {})})
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    reply.iter_content.return_value = chunks if chunks is not None else [page(row())]
    return reply


class TransportSafetyTests(unittest.TestCase):
    def test_http_failures_and_content_types_stop_without_retry_and_keep_status(self):
        for status, content_type, headers, category in (
            (302, "text/html", {}, "http_302"), (401, "text/html", {}, "http_401"),
            (403, "text/html", {}, "http_403"), (429, "text/html", {}, "http_429"),
            (500, "text/html", {}, "http_500"),
            (200, "text/html", {"Retry-After": "900"}, "retry_after_stop"),
            (200, "application/json", {}, "unexpected_content_type"),
        ):
            log = []
            with self.subTest(status=status, category=category), \
                    patch.object(h.requests, "get", return_value=response(status, content_type,
                                                                         extra_headers=headers)) as get:
                with self.assertRaisesRegex(h.CollectionError, "^" + category + "$"):
                    h._get(h.INDEX_URL, request_log=log)
                self.assertEqual(get.call_count, 1)
                self.assertEqual(log[0]["http_status"], status)
                self.assertEqual(get.call_args.kwargs["timeout"], (5, 10))
                self.assertFalse(get.call_args.kwargs["allow_redirects"])
                self.assertTrue(get.call_args.kwargs["stream"])

    def test_size_deadline_and_transport_failure(self):
        with patch.object(h.requests, "get", return_value=response(chunks=[b"x" * (h.MAX_BYTES + 1)])):
            with self.assertRaisesRegex(h.CollectionError, "response_too_large"):
                h._get(h.INDEX_URL)
        with patch.object(h.requests, "get", return_value=response()), \
                patch.object(h.time, "monotonic", side_effect=[0, 21]):
            with self.assertRaisesRegex(h.CollectionError, "response_deadline"):
                h._get(h.INDEX_URL)
        log = []
        with patch.object(h.requests, "get", side_effect=requests.Timeout("private diagnostic")) as get:
            with self.assertRaisesRegex(h.CollectionError, "^transport$"):
                h._get(h.INDEX_URL, request_log=log)
            self.assertEqual(get.call_count, 1)
            self.assertIsNone(log[0]["http_status"])

    def test_unapproved_endpoint_rejected_before_dispatch(self):
        with patch.object(h.requests, "get") as get:
            for url in (URL, rss.FEED_URL, "https://finance.yahoo.com/news/example"):
                with self.assertRaisesRegex(h.CollectionError, "unapproved_endpoint"):
                    h._get(url)
            get.assert_not_called()

    def test_invalid_and_user_agent_specific_robots(self):
        for policy, outcome in ((b"<html>challenge</html>", "invalid_robots"),
                                (b"User-agent: *\n\x00", "invalid_robots"),
                                (b"\xff", "invalid_robots"),
                                (b"User-agent: *\nAllow: /\nUser-agent: FinScope-RBA-HTML-Prototype\n"
                                 b"Disallow: /media-releases/", "robots_disallowed")):
            with self.subTest(policy=policy):
                get = Mock(return_value=(policy, 200))
                with self.assertRaisesRegex(h.CollectionError, outcome):
                    h.collect_once(get=get)
                self.assertEqual(get.call_count, 1)
        with patch.object(h.requests, "get", return_value=response(content_type="text/html")):
            with self.assertRaisesRegex(h.CollectionError, "unexpected_content_type"):
                h._get(h.ROBOTS_URL)


class LocalStorageSafetyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.html_dir = Path(self.folder.name) / "html"
        self.rss_dir = Path(self.folder.name) / "rss"
        for module, directory in ((h, self.html_dir), (rss, self.rss_dir)):
            patcher = patch.object(module, "DATA_DIR", directory)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.html_dir.mkdir()
        self.rss_dir.mkdir()
        self.store = self.html_dir / "articles.json"
        self.rss_store = self.rss_dir / "articles.json"
        self.store.write_text("[]", encoding="utf-8")
        self.rss_store.write_text("[]", encoding="utf-8")
        stdout = redirect_stdout(StringIO())
        stdout.__enter__()
        self.addCleanup(stdout.__exit__, None, None, None)

    def reports(self):
        return [json.loads(p.read_text()) for p in sorted(self.html_dir.glob("run_*.json"))]

    def seed_record(self):
        parsed = h.parse_index(page(row()))
        record = {"article": asdict(parsed["articles"][0]), "provenance": parsed["provenance"][0]}
        self.store.write_text(json.dumps([record]), encoding="utf-8")

    def test_default_and_explicit_preview_ignore_existing_stores_without_network(self):
        self.store.write_text("corrupt", encoding="utf-8")
        before = sorted(p.name for p in self.html_dir.iterdir())
        with patch.object(h.requests, "get") as get:
            for args in ([], ["--dry-run"]):
                self.assertEqual(h.main(args), 0)
            get.assert_not_called()
        self.assertEqual(before, sorted(p.name for p in self.html_dir.iterdir()))

    def test_transport_audit_and_repeated_run_rss_exclusion_offline(self):
        article = Article("rba_rss", "Authored RSS fixture", URL2, rss.SOURCE, "", "", "published")
        self.rss_store.write_text(json.dumps([{"article": asdict(article)}]), encoding="utf-8")
        rss_before = self.rss_store.read_bytes()
        replies = [response(content_type="text/plain", chunks=[b"User-agent: *\nAllow: /"]),
                   response(chunks=[page(row(), row(), row(URL2))])] * 2
        with patch.object(h.requests, "get", side_effect=replies) as get:
            self.assertEqual(h.main(["--collect", "--limit", "3"]), 0)
            self.assertEqual(h.main(["--collect", "--limit", "3"]), 0)
            self.assertEqual([c.args[0] for c in get.call_args_list], [h.ROBOTS_URL, h.INDEX_URL] * 2)
        self.assertEqual(self.rss_store.read_bytes(), rss_before)
        records = json.loads(self.store.read_text())
        self.assertEqual([r["article"]["url"] for r in records], [URL])
        self.assertEqual([r["new_records"] for r in self.reports()], [1, 0])
        self.assertEqual([r["network_requests"] for r in self.reports()], [2, 2])
        self.assertEqual([r["duplicate_urls"] for r in self.reports()], [2, 3])
        self.assertTrue(all(r["http_status"] == 200 for run in self.reports() for r in run["requests"]))

    def test_http_or_parse_failure_preserves_existing_data_and_reports_attempts(self):
        self.seed_record()
        before = self.store.read_bytes()
        for reply in (response(status=403), response(chunks=[b"<html>Access denied</html>"])):
            with patch.object(h.requests, "get", side_effect=[
                    response(content_type="text/plain", chunks=[b"User-agent: *\nAllow: /"]), reply]) as get:
                self.assertEqual(h.main(["--collect"]), 1)
                self.assertEqual(get.call_count, 2)
            self.assertEqual(self.store.read_bytes(), before)
            self.assertEqual(self.reports()[-1]["status"], "failed")
            self.assertEqual(self.reports()[-1]["new_records"], 0)
            self.assertEqual(self.reports()[-1]["network_requests"], 2)
        self.assertEqual(self.reports()[-2]["requests"][-1]["http_status"], 403)

    def test_robots_failure_records_only_one_request_and_preserves_data(self):
        self.seed_record()
        before = self.store.read_bytes()
        with patch.object(h.requests, "get", return_value=response(status=429)) as get:
            self.assertEqual(h.main(["--collect"]), 1)
            self.assertEqual(get.call_count, 1)
        self.assertEqual(self.store.read_bytes(), before)
        self.assertEqual(self.reports()[-1]["network_requests"], 1)
        self.assertEqual(self.reports()[-1]["requests"][0]["http_status"], 429)

    def test_row_and_byte_capacity_never_overwrite_existing_data(self):
        self.seed_record()
        before = self.store.read_bytes()
        with patch.object(h, "MAX_STORED", 1), patch.object(h.requests, "get") as get:
            self.assertEqual(h.main(["--collect"]), 0)
            get.assert_not_called()
        self.assertEqual(self.reports()[-1]["outcome"], "local_capacity")
        with patch.object(h, "MAX_STORE_BYTES", len(before) + 10), \
                patch.object(h, "collect_once", return_value=h.parse_index(page(row(URL2)))):
            self.assertEqual(h.main(["--collect"]), 1)
        self.assertEqual(self.reports()[-1]["outcome"], "local_store_byte_capacity")
        self.assertEqual(self.reports()[-1]["new_records"], 0)
        self.assertEqual(self.store.read_bytes(), before)

    def test_corrupt_rss_or_stale_lock_blocks_before_network(self):
        self.rss_store.write_text("corrupt", encoding="utf-8")
        with patch.object(h.requests, "get") as get:
            self.assertEqual(h.main(["--collect"]), 1)
            get.assert_not_called()
        self.assertEqual(self.reports()[-1]["outcome"], "invalid_rss_store_review_required")
        lock = self.html_dir / "collection.lock"
        lock.touch()
        with patch.object(h.requests, "get") as get:
            self.assertEqual(h.main(["--collect"]), 1)
            get.assert_not_called()
        self.assertTrue(lock.exists())

    def test_atomic_replace_failure_preserves_existing_data(self):
        self.seed_record()
        before = self.store.read_bytes()
        with patch.object(h, "collect_once", return_value=h.parse_index(page(row(URL2)))), \
                patch.object(Path, "replace", side_effect=OSError("synthetic write failure")):
            self.assertEqual(h.main(["--collect"]), 1)
        self.assertEqual(self.store.read_bytes(), before)
        self.assertEqual(self.reports()[-1]["outcome"], "local_io")
        self.assertFalse((self.html_dir / "collection.lock").exists())


if __name__=="__main__": unittest.main()
