"""Authored feeds only. Real five-source receipts remain separate local evidence."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
from dataclasses import asdict
import json,os,unittest
from unittest.mock import patch
import requests
from finscope.local_news import LocalNewsStore,LocalIngestionService,ContentRights
from finscope.task_queue import TaskQueue
from finscope.media_monitor import MediaMonitor,FEEDS,MAX_BYTES,parse_feed,policy,get_feed
from finscope.api_sources import MarketauxFilters,build_request,fetch_provider
from finscope.product_storage import ProductStorage
from finscope.batch_records import eligibility

NOW=datetime(2026,11,1,5,tzinfo=timezone.utc)
XML=b'''<rss version="2.0"><channel><title>Authored fixture</title><item>
<title>The fictional chip company grows in revenue</title><link>https://example.com/authored/one</link>
<pubDate>Sun, 01 Nov 2026 04:30:00 GMT</pubDate><description>Authored financial test summary.</description>
<author>Reuters</author><encoded>DO NOT RETAIN BODY</encoded></item></channel></rss>'''
GRANT=dict(basis='Authored fixture; test-only rights',fields=['title','summary'],purposes=['display','retain','nlp','poll'],retention='no_fixed_expiry',expires_at='',publisher_domains=['example.com'])

class MediaTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);TaskQueue(self.store);self.now=NOW;self.calls=[]
        def get(url,headers):self.calls.append((url,headers));return 200,{'ETag':'"fixture"','Last-Modified':'Sun, 01 Nov 2026 04:30:00 GMT'},XML
        self.monitor=MediaMonitor(self.store,get=get,clock=lambda:self.now)
    def advance(self):self.now+=timedelta(minutes=16)
    def test_realistic_store_and_offline_replay_without_copied_text(self):
        r,visible=self.monitor.check('cnbc',explicit=True)
        self.assertEqual((r['new'],r['valid_items'],r['processable']),(1,1,0));self.assertNotIn('title',visible[0])
        rows,_=parse_feed(XML,'cnbc');self.assertEqual(self.monitor.replay('cnbc',rows)['duplicates'],1)
        self.assertEqual(len(self.calls),1)
        with closing(self.store.connect()) as db:
            payload=db.execute('select payload from media_seen').fetchone()[0]
            self.assertNotIn('title',json.loads(payload));self.assertNotIn('summary',json.loads(payload));self.assertEqual(db.execute('select count(*) from media_versions').fetchone()[0],1)
        self.assertEqual(ProductStorage(self.store).news(),[]);self.assertEqual(self.store.list_analyses(),[])
    def test_default_tick_is_offline(self):self.assertIsNone(self.monitor.tick());self.assertFalse(self.calls)
    def test_permission_and_expiry_required_for_scheduler(self):
        with self.assertRaises(ValueError):self.monitor.configure('cnbc',enabled=True)
        with self.assertRaises(ValueError):self.monitor.configure('cnbc',enabled=True,grant={**GRANT,'expires_at':'2026-10-01T00:00:00Z'})
        self.assertFalse(self.calls)
    def test_polling_interval_and_conditional304(self):
        self.monitor.configure('cnbc',enabled=True,interval=5,grant=GRANT)
        self.monitor.tick();self.assertIsNone(self.monitor.tick());self.advance()
        def not_modified(url,headers):
            self.assertEqual(headers['If-None-Match'],'"fixture"');self.assertIn('If-Modified-Since',headers);return 304,{},b''
        self.monitor.get=not_modified;r,_=self.monitor.tick();self.assertEqual(r['http_status'],304);self.assertEqual(r['new'],0)
        self.assertTrue(self.monitor.states()['cnbc']['watermark'])
    def test_unsolicited304_is_failure(self):
        self.monitor.get=lambda *a:(304,{},b'');r,_=self.monitor.check('ft',explicit=True)
        self.assertIn('Unexpected 304',r['reason']);self.assertTrue(self.monitor.states()['ft']['hold'])
    def test_dailycap_durable_across_new_instances(self):
        self.monitor.configure('cnbc',daily_cap=1);self.monitor.check('cnbc',explicit=True);self.advance()
        other=MediaMonitor(self.store,get=lambda *a:self.fail('No over-cap dispatch'),clock=lambda:self.now)
        with self.assertRaises(ValueError):other.check('cnbc',explicit=True)
    def test_failure_isolation_no_redirect_or_domain_fallback(self):
        self.monitor.get=lambda *a:(302,{'Location':'https://unreviewed.example/elsewhere'},b'')
        r,_=self.monitor.check('bloomberg',explicit=True);self.assertEqual(r['http_status'],302)
        with self.assertRaises(ValueError):self.monitor.check('bloomberg',explicit=True)
        self.monitor.get=lambda *a:(200,{},XML);self.assertEqual(self.monitor.check('cnbc',explicit=True)[0]['new'],1)
    def test429_backoff_respects_retry_after_and_persists(self):
        self.monitor.configure('ft',enabled=True,interval=5,grant=GRANT)
        self.monitor.get=lambda *a:(429,{'Retry-After':'7200'},b'');self.monitor.tick();self.advance()
        self.assertIsNone(self.monitor.tick());self.assertGreaterEqual(self.monitor.states()['ft']['next_due'],'2026-11-01T07:00:00')
    def test_unknown_transport_never_reissued(self):
        def lost(*a):raise requests.Timeout('must not print raw diagnostics')
        self.monitor.get=lost;r,_=self.monitor.check('wsj',explicit=True);self.assertIsNone(r['http_status']);self.advance()
        with self.assertRaises(ValueError):MediaMonitor(self.store,clock=lambda:self.now).check('wsj',explicit=True)
    def test_crash_after_dispatch_keeps_inflight_hold(self):
        with patch.object(self.monitor,'_ingest',side_effect=RuntimeError('Authored simulated disk error')):
            with self.assertRaises(RuntimeError):self.monitor.check('wsj',explicit=True)
        with self.assertRaises(ValueError):MediaMonitor(self.store,clock=lambda:self.now).check('wsj',explicit=True)
        with closing(self.store.connect()) as db:
            status,http,report=db.execute('select status,http_status,report from media_requests').fetchone()
            self.assertEqual((status,http),('received',200));self.assertEqual(json.loads(report)['valid_items'],1)
        report=self.monitor.recover_received('wsj');self.assertEqual(report['new'],1)
        self.assertEqual(len(self.calls),1);self.assertNotIn('title',self.monitor.index('wsj')[0])
        with self.assertRaises(ValueError):self.monitor.recover_received('wsj')
    def test_same_event_different_media_not_merged(self):
        for source in ('wsj','ft'):self.monitor.check(source,explicit=True)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('select count(*) from media_seen').fetchone()[0],2)
    def test_syndicated_publisher_needs_its_own_covered_domain(self):
        self.monitor.configure('yahoo',grant={**GRANT,'publisher_domains':[]})
        report,visible=self.monitor.check('yahoo',explicit=True)
        self.assertEqual(report['new'],1);self.assertEqual(report['stored'],0);self.assertEqual(report['processable'],0)
        self.assertEqual(visible[0]['publishing_domain'],'example.com');self.assertEqual(visible[0]['feed_provider'],'Yahoo Finance')
        self.assertNotIn('title',visible[0]);self.assertEqual(self.monitor.promote('yahoo')['new'],0)
        self.monitor.configure('yahoo',grant=GRANT)
        rows,_=parse_feed(XML,'yahoo');self.monitor.replay('yahoo',rows)
        self.assertEqual(self.monitor.promote('yahoo')['new'],1)
    def test_revisions_and_late_arrivals_not_dropped_by_watermark(self):
        self.monitor.check('wsj',explicit=True);self.advance()
        changed=XML.replace(b'grows',b'declines').replace(b'04:30:00',b'04:00:00')
        self.monitor.get=lambda *a:(200,{},changed);r,_=self.monitor.check('wsj',explicit=True)
        self.assertEqual(r['changed'],1);self.assertIn('04:30:00',self.monitor.states()['wsj']['watermark'])
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('select count(*) from media_versions').fetchone()[0],2)
    def test_licensed_title_only_promotes_without_summary_body_or_model(self):
        self.monitor.configure('cnbc',grant={**GRANT,'fields':['title']})
        self.monitor.check('cnbc',explicit=True);self.assertEqual(self.monitor.promote('cnbc')['new'],1)
        n=ProductStorage(self.store).news()[0];self.assertFalse(n.summary);self.assertFalse(n.body);self.assertTrue(eligibility(n)[0])
        self.assertEqual(self.monitor.promote('cnbc')['duplicates'],1);self.assertEqual(self.store.list_analyses(),[])
    def test_unlicensed_and_finite_grants_do_not_enter_permanent_library(self):
        self.monitor.check('ft',explicit=True)
        with self.assertRaises(ValueError):self.monitor.promote('ft')
        self.monitor.configure('ft',grant={**GRANT,'retention':'30 days','expires_at':'2026-12-01T00:00:00Z'})
        with self.assertRaises(ValueError):self.monitor.promote('ft')
        self.assertFalse(ProductStorage(self.store).news())
    def test_policy_expiry_hides_text_and_disallows_promote(self):
        self.monitor.configure('wsj',grant={**GRANT,'expires_at':'2026-11-01T05:05:00Z'})
        self.monitor.check('wsj',explicit=True);self.assertIn('title',self.monitor.index('wsj')[0]);self.advance()
        self.assertNotIn('title',self.monitor.index('wsj')[0])
        with closing(self.store.connect()) as db:self.assertNotIn('title',json.loads(db.execute('select payload from media_seen').fetchone()[0]))
        with self.assertRaises(ValueError):self.monitor.promote('wsj')
    def test_feed_credit_is_not_direct_reuters_license(self):
        rows,meta=parse_feed(XML,'cnbc');self.assertIn('syndicated',rows[0]['wire_credit']);self.assertEqual(rows[0]['publisher'],'CNBC')
        rows,_=parse_feed(XML.replace(b'<author>Reuters</author>',b''),'cnbc');self.assertEqual(rows[0]['wire_credit'],'')
        self.assertNotIn('body',rows[0]);self.assertIn('encoded',meta['fields'])
    def test_no_dtd_oversize_html_or_private_link(self):
        for body in (b'<!DOCTYPE rss><rss/>',b'<html/>',b'x'*(MAX_BYTES+1)):
            with self.assertRaises(ValueError):parse_feed(body,'cnbc')
        rows,_=parse_feed(XML.replace(b'https://example.com/authored/one',b'http://127.0.0.1/x'),'cnbc');self.assertFalse(rows)
    def test_atom_parser_uses_alternate_and_validated_time(self):
        rows,m=parse_feed(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Authored</title><link rel="alternate" href="https://example.com/a"/><published>2026-11-01T05:00:00Z</published></entry></feed>','ft')
        self.assertEqual(m['format'],'feed');self.assertEqual(len(rows),1)
    def test_stream_transport_no_redirect_retry_and_sizebound(self):
        response=unittest.mock.MagicMock();response.__enter__.return_value=response;response.status_code=200;response.headers={};response.iter_content.return_value=[b'x'*(MAX_BYTES+1)]
        with patch('finscope.media_monitor.requests.get',return_value=response) as get:
            with self.assertRaises(ValueError):get_feed(FEEDS['wsj'].url,{})
            self.assertFalse(get.call_args.kwargs['allow_redirects']);self.assertTrue(get.call_args.kwargs['stream'])
    def test_marketaux_documented_filters_replace_keyword_and_preserve_freecap(self):
        f=MarketauxFilters(('reuters.com','bloomberg.com'),('NVDA','MSFT'),('Technology',),'2026-11-01T15:00:00+11:00')
        _,p,_,mode,_=build_request('marketaux','technology',NOW,2,100,'test',marketaux_filters=f)
        self.assertNotIn('search',p);self.assertEqual(p['domains'],'reuters.com,bloomberg.com');self.assertEqual(p['symbols'],'NVDA,MSFT')
        self.assertEqual(p['industries'],'Technology');self.assertEqual(p['published_after'],'2026-11-01T04:00:00');self.assertEqual(p['limit'],3);self.assertEqual(p['group_similar'],'false')
    def test_invalid_marketaux_scope_never_spends_ledger(self):
        with self.assertRaises(ValueError):self.store.set_setting('marketaux_media_filters',asdict(MarketauxFilters(('https://reuters.com',))))
        # A malformed legacy/local preference must also fail before reservation.
        with closing(self.store.connect()) as db:
            db.execute('INSERT OR REPLACE INTO local_settings VALUES (?,?)',('marketaux_media_filters',json.dumps(asdict(MarketauxFilters(('https://reuters.com',))))));db.commit()
        svc=LocalIngestionService(self.store,transport=lambda *a:self.fail('No dispatch'))
        with self.assertRaises(ValueError):svc.fetch('marketaux','technology',api_key='test-only',rights=ContentRights(True,False,False,False,'authored test'),remaining=1,explicit=True)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('select count(*) from local_requests').fetchone()[0],0)
    def test_marketaux_fetchexecution_carries_offlinefilters(self):
        f=MarketauxFilters(('reuters.com',),('MSFT',))
        def get(url,params,headers,timeout):self.assertEqual(params['domains'],'reuters.com');self.assertNotIn('search',params);return {'data':[]}
        self.assertEqual(fetch_provider('marketaux','technology',api_key='test-only',marketaux_filters=f,transport=get).status,'ok')
    def test_marketaux_reuters_syndication_cannot_impersonate_direct_source(self):
        payload={'data':[dict(title='Authored Reuters credit',url='https://example.com/wire',source='reuters.com',description='Authored fixture',published_at='2026-11-01T01:00:00Z')]}
        result=fetch_provider('marketaux','technology',api_key='test-only',marketaux_filters=MarketauxFilters(('reuters.com',)),transport=lambda *a:payload)
        self.assertFalse(result.articles);self.assertIn('Outside-whitelist',result.note)
    def test_bounds_and_policies_reject_broadening(self):
        for kwargs in ({'interval':4},{'interval':16},{'daily_cap':289}):
            with self.assertRaises(ValueError):self.monitor.configure('ft',**kwargs)
        for g in ({**GRANT,'fields':['body']},{**GRANT,'basis':''},{**GRANT,'purposes':['nlp']},{**GRANT,'expires_at':'yesterday'}):
            with self.assertRaises(ValueError):policy(g)
    def test_source_revocation_blocks_promoted_original_and_removes_cache_text(self):
        self.monitor.configure('cnbc',grant=GRANT);self.monitor.check('cnbc',explicit=True);self.monitor.promote('cnbc')
        self.monitor.configure('cnbc')
        self.assertFalse(eligibility(ProductStorage(self.store).news()[0])[0]);self.assertNotIn('title',self.monitor.index('cnbc')[0])
    def test_scheduled_licensed_source_queues_existing_offline_worker_without_inference(self):
        self.monitor.configure('cnbc',enabled=True,grant=GRANT);self.monitor.tick()
        task=TaskQueue(self.store).get();self.assertEqual(task['snapshot']['operation'],'analyze');self.assertEqual(task['snapshot']['sources'],[])
        self.assertEqual(self.store.list_analyses(),[])
    def test_concurrent_disable_is_not_overwritten_by_response(self):
        self.monitor.configure('cnbc',enabled=True,grant=GRANT)
        def get(*a):self.monitor.configure('cnbc');return 200,{},XML
        self.monitor.get=get;self.monitor.check('cnbc',explicit=True)
        s=self.monitor.states()['cnbc'];self.assertFalse(s['enabled']);self.assertEqual(s['policy']['fields'],[])
        self.assertNotIn('title',self.monitor.index('cnbc')[0])
    def test_repeated_render_does_not_send_http_or_change_commercial_ledgers(self):
        for _ in range(3):self.monitor.states();self.monitor.index('wsj')
        self.assertFalse(self.calls)
        self.monitor.check('wsj',explicit=True)
        with closing(self.store.connect()) as db:
            for table in ('local_requests','local_collector_http','local_model_requests','local_analyses'):
                self.assertEqual(db.execute('select count(*) from '+table).fetchone()[0],0)
    def test_monitor_ui_renders_offline_and_does_not_fill_rights(self):
        from streamlit.testing.v1 import AppTest
        rows,_=parse_feed(XML,'bloomberg');self.monitor.replay('bloomberg',rows)
        def render():
            import os
            from finscope.local_news import LocalNewsStore
            from finscope.task_queue import TaskQueue
            from finscope.media_ui import controls
            store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);TaskQueue(store);controls(store)
        app=AppTest.from_function(render).run();self.assertFalse(app.exception)
        self.assertTrue(any(e.label=='Global media monitor' for e in app.expander))
        self.assertEqual(app.selectbox(key='media_original_bloomberg').value,'https://example.com/authored/one')
        self.assertFalse(any(c.value for c in app.checkbox))
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('select count(*) from media_requests').fetchone()[0],0)
