"""Offline HTML collector tests; no live news requests."""
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch
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

if __name__=="__main__": unittest.main()
