"""Authored HTTP fixtures; no actual publisher calls in regression tests."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json,os,unittest
from unittest.mock import patch
import requests
from finscope.local_news import LocalNewsStore
from finscope.task_queue import TaskQueue
from finscope.media_monitor import MediaMonitor,policy
from finscope.media_probe import MediaProbe,reviewed_ft_url
from finscope.media_schedule import capacity,validate_schedule

NOW=datetime(2026,11,1,6,tzinfo=timezone.utc)
XML=b'<rss><channel><item><title>Authored financial fixture</title><link>https://example.com/research</link><pubDate>Sun, 01 Nov 2026 05:30:00 GMT</pubDate></item></channel></rss>'

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);TaskQueue(self.store);self.now=NOW;self.calls=[]
        def get(url,headers):self.calls.append(url);return 200,{'ETag':'"authored"'},XML
        self.probe=MediaProbe(self.store,get=get,clock=lambda:self.now)
    def begin(self,source='bloomberg',cap=1):return self.probe.begin(source,max_gets=cap,reference='Actual test-fixture operator approval',confirmed=True)
    def test_no_dispatch_without_actual_confirmation_and_caps(self):
        for source,n in [('bloomberg',2),('ft',4),('cnbc',1)]:
            with self.assertRaises(ValueError):self.probe.begin(source,max_gets=n,reference='fixture',confirmed=True)
        with self.assertRaises(ValueError):self.probe.begin('ft',max_gets=1,reference='fixture')
        self.assertFalse(self.calls)
    def test_complete_receipt_is_saved_and_duplicate_run_never_fetches(self):
        rid=self.begin();r=self.probe.run(rid);self.assertEqual(r['state'],'completed');self.assertEqual(r['used'],1)
        r=self.probe.run(rid);self.assertEqual(len(self.calls),1)
        self.assertEqual(self.begin(),rid)
        report=r['chain'][0];self.assertEqual(report['http_status'],200);self.assertEqual(report['valid_items'],1)
        self.assertEqual(report['response_headers']['ETag'],'"authored"');self.assertTrue(report['response_sha256'])
    def test_ft_count_every_actual_hop_and_capture_location(self):
        target='https://www.ft.com/rss/home/international'
        def get(url,headers):
            self.calls.append(url)
            return (301,{'Location':target},b'') if url.endswith('/home') else (200,{'ETag':'"ft-fixture"'},XML)
        self.probe.get=get
        with patch('finscope.media_probe.time.sleep'):
            r=self.probe.run(self.begin('ft',3))
        self.assertEqual(r['state'],'completed');self.assertEqual(r['used'],2)
        with closing(self.store.connect()) as db:self.assertEqual([v[0] for v in db.execute('select http_status from media_requests order by rowid')],[301,200])
        self.assertEqual(r['chain'][0]['response_headers']['Location'],target)
        self.assertEqual(self.probe.monitor.states()['ft']['resolved_url'],target)
    def test_bad_redirect_never_follows_external_login_http_or_query(self):
        for u in ('http://www.ft.com/rss/home/international','https://accounts.ft.com/login','https://www.ft.com/content/article','https://evil.example/rss/home','https://www.ft.com/rss/home?login=1','https://www.ft.com:444/rss/home'):
            with self.assertRaises(ValueError):reviewed_ft_url(u,'https://www.ft.com/rss/home')
        self.probe.get=lambda *a:(301,{'Location':'https://accounts.ft.com/login'},b'')
        r=self.probe.run(self.begin('ft',3));self.assertEqual(r['used'],1);self.assertEqual(r['state'],'blocked')
    def test_bound_stops_even_when_redirect_valid(self):
        self.probe.get=lambda *a:(301,{'Location':'/rss/home/international'},b'')
        r=self.probe.run(self.begin('ft',1));self.assertEqual(r['used'],1);self.assertEqual(r['state'],'blocked')
    def test_transport_unknown_is_preserved_and_cannot_restart(self):
        def lost(*a):raise requests.Timeout('redacted')
        self.probe.get=lost;r=self.probe.run(self.begin());self.assertEqual(r['state'],'blocked')
        with self.assertRaises(ValueError):self.probe.begin('bloomberg',max_gets=1,reference='Another approval cannot erase unknown dispatch',confirmed=True)
    def test_old_receipt_and_hold_preserved_even_after_new_success(self):
        monitor=self.probe.monitor
        with closing(self.store.connect()) as db:
            s=monitor._state(db,'bloomberg');s.update(inflight='old',hold='Original indexing unresolved')
            monitor._put(db,'bloomberg',s)
            db.execute('INSERT INTO media_requests VALUES (?,?,?,?,?,?,?)',('old','bloomberg',NOW.isoformat(),NOW.isoformat(),'persistence_failed',200,'{"original_unknown_metrics":true}'));db.commit()
            before=db.execute("select * from media_requests where id='old'").fetchone()
        r=self.probe.run(self.begin());self.assertEqual(r['state'],'completed')
        with closing(self.store.connect()) as db:self.assertEqual(before,db.execute("select * from media_requests where id='old'").fetchone())
        s=monitor.states()['bloomberg'];self.assertEqual(s['inflight'],'old');self.assertTrue(s['hold'])
    def test_parser_error_has_durable200_headers_and_hash(self):
        self.probe.get=lambda *a:(200,{'ETag':'"bad-xml"'},b'<html>fixture</html>')
        r=self.probe.run(self.begin());self.assertEqual(r['state'],'blocked')
        self.assertEqual(r['chain'][0]['http_status'],200);self.assertTrue(r['chain'][0]['response_sha256'])
    def test_expired_diagnostic_does_not_dispatch(self):
        rid=self.begin();self.now+=timedelta(hours=2)
        with self.assertRaises(ValueError):self.probe.run(rid)
        self.assertFalse(self.calls)
    def test_15_and_5_minute_full_day_capacity_and_longer_interval(self):
        self.assertEqual(validate_schedule(15,96,'full_day'),96)
        self.assertEqual(validate_schedule(5,288,'full_day'),288)
        self.assertEqual(validate_schedule(120,12,'full_day'),12)
        with self.assertRaises(ValueError):validate_schedule(15,12,'full_day')
        self.assertEqual(validate_schedule(15,12,'bounded_window'),96)
    def test_budget_expiry_and_coverage_are_bounded_by_utc_midnight(self):
        s=dict(interval=15,daily_cap=12,enabled=True,budget_day='2026-11-01',budget_reference='fixture')
        p=capacity(s,0,NOW);self.assertEqual(p['rounds_available_today'],12);self.assertEqual(p['estimated_span_minutes'],165)
        p=capacity(s,0,NOW.replace(hour=23,minute=50));self.assertEqual(p['rounds_available_today'],1)
        p=capacity(s,12,NOW);self.assertIn('exhausted',p['status'])
        p=capacity(s,0,NOW+timedelta(days=1));self.assertFalse(p['budget_attested'])
    def test_polling_requires_today_budget_and_does_not_renew_on_restart(self):
        m=self.probe.monitor
        grant=dict(basis='Authored fixture licence',fields=[],purposes=['poll'],retention='',expires_at='')
        with self.assertRaises(ValueError):m.configure('yahoo',enabled=True,grant=grant)
        m.configure('yahoo',enabled=True,grant=grant,budget_day=NOW.date().isoformat(),budget_reference='Two real requests only',daily_cap=2,interval=5)
        m=MediaMonitor(self.store,get=lambda *a:(200,{'ETag':'"x"'},XML),clock=lambda:self.now);m.tick();self.now+=timedelta(minutes=5);m.tick()
        self.assertIn('exhausted',m.capacity('yahoo')['status']);self.now+=timedelta(days=1)
        m=MediaMonitor(self.store,get=lambda *a:self.fail('No expired budget dispatch'),clock=lambda:self.now);self.assertIsNone(m.tick())
