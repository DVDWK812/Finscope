from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from finscope.api_sources import Article
from finscope.local_collectors import collect_rba,import_output
from finscope.local_news import ContentRights,FetchBlocked,LocalIngestionService,LocalNewsStore,NewsItem

RIGHTS=ContentRights(True,False,False,False,"Authored collector fixture for preview")


class LocalCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.store=LocalNewsStore(root/"local.sqlite3")
        self.service=LocalIngestionService(self.store,cooldown_path=root/"holds.json",study_path=root/"study.sqlite3")
        self.article=Article("rba_html","Authored fixture release","https://www.rba.gov.au/media-releases/2026/mr-26-01.html",
                             "Reserve Bank of Australia","","","published")
        self.row={"article":asdict(self.article),"provenance":{"publication_date":"2026-10-28",
                            "timestamp_precision":"date_only","attribution":"Source: Reserve Bank of Australia 2026"}}

    def test_import_preserves_date_precision_and_no_implicit_storage_or_http(self):
        with patch("requests.sessions.Session.request",side_effect=AssertionError("No HTTP during import")):
            rows=import_output(json.dumps([self.row]).encode(),RIGHTS)
        self.assertEqual(rows[0].publication_date,"2026-10-28")
        self.assertEqual(rows[0].timestamp,"")
        self.assertEqual(rows[0].timestamp_kind,"published")
        self.assertIn("Reserve Bank",rows[0].provenance)
        self.assertEqual(self.store.list_news(),[])

    def test_reject_arbitrary_site_full_body_fabricated_time_and_invalid_shape(self):
        for changes in ({"url":"https://attacker.invalid/story"},{"description":"Full body not collected by index"},
                        {"timestamp":"2026-10-28T00:00:00Z"},{"provider":"gdelt"}):
            row=json.loads(json.dumps(self.row));row["article"].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                import_output(json.dumps([row]).encode(),RIGHTS)
        for payload in (b'{}',b'not JSON',b' '*1048577):
            with self.assertRaises(ValueError): import_output(payload,RIGHTS)

    def test_explicit_rss_collection_reuses_fixed_robots_and_feed(self):
        from finscope import rss_collector as rss
        fixture=b'''<rss version="2.0"><channel><title>Authored RBA fixture</title><item><title>Authored fixture release</title>
        <link>https://www.rba.gov.au/media-releases/2026/mr-26-01.html</link>
        <pubDate>Wed, 28 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>'''
        seen=[]
        def get(url):
            seen.append(url)
            return (b"User-agent: *\nAllow: /" if url==rss.ROBOTS_URL else fixture),200
        rss_original=rss.collect_once
        rows=collect_rba(self.service,"rss",RIGHTS,explicit=True,collect=lambda **kw:rss_original(get=get,**kw))
        self.assertEqual(seen,[rss.ROBOTS_URL,rss.FEED_URL])
        self.assertEqual(rows[0].timestamp,"2026-10-28T01:00:00+00:00")
        self.assertEqual(rows[0].summary,"")
        self.assertEqual(self.store.list_news(),[])

    def test_collection_requires_explicit_action_and_preserves_unknown_failure_hold(self):
        calls=[]
        with self.assertRaises(FetchBlocked):
            collect_rba(self.service,"rss",RIGHTS,collect=lambda **kw:calls.append(kw))
        self.assertEqual(calls,[])
        def fail(**kwargs): raise RuntimeError("No raw error should escape")
        with self.assertRaisesRegex(FetchBlocked,"failed"):
            collect_rba(self.service,"rss",RIGHTS,explicit=True,collect=fail)
        with self.assertRaises(FetchBlocked):
            collect_rba(self.service,"html",RIGHTS,explicit=True,collect=lambda **kw:calls.append(kw))
        self.assertEqual(calls,[])

    def test_repeat_identical_provider_output_has_stable_original_identity(self):
        one=NewsItem.from_article(self.article,RIGHTS)
        two=NewsItem.from_article(self.article,RIGHTS)
        self.assertEqual(one.article_id,two.article_id)

