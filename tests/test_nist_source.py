from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from finscope.local_news import LocalNewsStore,LocalIngestionService,FetchBlocked
from finscope.local_collectors import SOURCES
from finscope.public_sources import parse_source,extract_nist_body,SourceError,collect_source,original_url
from finscope.task_queue import Cancelled


def feed():
    return b'''<rss><channel><item><title>Authored semiconductor development fixture</title><link>https://www.nist.gov/news-events/news/2026/10/authored-fixture</link><description>The company has developed a new semiconductor device.</description><pubDate>Fri, 30 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'''


def body():
    return b'<html><nav>Ignore navigation</nav><div class="field--name-body"><p>The laboratory developed a new semiconductor device and reported manufacturing improvements. This is authored offline test content only, not actual news.</p><script>secret_code()</script><figure>Third-party media not included</figure></div><footer>Ignore footer</footer></html>'


class NistTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
        self.store=LocalNewsStore(root/'test.sqlite3');self.service=LocalIngestionService(self.store,cooldown_path=root/'hold.json',study_path=root/'study.sqlite3')
        self.patch=patch('finscope.public_sources.time.sleep');self.patch.start();self.addCleanup(self.patch.stop)
    def test_rss_time_summary_source_attribution_and_text_rights(self):
        n=parse_source('nist_rss',feed(),1)[0]
        self.assertEqual(n.timestamp,'2026-10-30T12:00:00+00:00');self.assertTrue(n.rights.retain and n.rights.analyze);self.assertFalse(n.rights.external)
        self.assertIn('NIST',n.provenance);self.assertEqual(n.body,'')
    def test_body_selector_removes_navigation_scripts_footer_and_media(self):
        text,_=extract_nist_body(body())
        self.assertIn('semiconductor',text)
        for word in ('navigation','secret_code','Third-party','footer'):self.assertNotIn(word,text)
        with self.assertRaises(SourceError):extract_nist_body(body().replace(b'new semiconductor',b'copyright new semiconductor'))
    def test_fixed_urls_reject_remote_internal_and_redirect_like_urls(self):
        for value in ('http://127.0.0.1/x','https://evil.invalid/news-events/news/2026/x','https://www.nist.gov@127.0.0.1/news-events/news/x','https://www.nist.gov/news-events/news/x?url=http://127.0.0.1'):
            self.assertEqual(original_url('nist_rss',value),'')
    def test_real_transport_boundary_uses_one_reservation_three_http_calls(self):
        calls=[]
        def get(url):
            calls.append(url)
            return (b'User-agent: *\nAllow: /' if url.endswith('robots.txt') else feed() if url.endswith('rss.xml') else body()),200
        news,report=collect_source(self.service,'nist_rss',limit=1,explicit=True,get=get)
        self.assertEqual(len(calls),3);self.assertTrue(news[0].body);self.assertEqual(report['http_request_budget'],5)
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM local_collector_http').fetchone()[0],3)
    def test_body_failure_falls_back_to_permitted_summary_and_keeps_stop(self):
        def get(url):
            if url.endswith('robots.txt'):return b'User-agent: *\nAllow: /',200
            if url.endswith('rss.xml'):return feed(),200
            raise SourceError('Body stopped: HTTP 429',status=429,retry_after='900')
        news,_=collect_source(self.service,'nist_rss',limit=1,explicit=True,get=get)
        self.assertTrue(news[0].summary);self.assertFalse(news[0].body)
        self.assertTrue(self.service.source_status('nist',configured=True).blocked)
    def test_cancel_before_feed_stops_new_http_and_records_known_cancellation(self):
        calls=[]
        def check():
            if calls:raise Cancelled()
        def get(url):calls.append(url);return b'User-agent: *\nAllow: /',200
        with self.assertRaises(Cancelled):collect_source(self.service,'nist_rss',limit=1,explicit=True,get=get,check_cancel=check)
        self.assertEqual(len(calls),1)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT status FROM local_requests').fetchone()[0],'cancelled')


if __name__=='__main__':unittest.main()
