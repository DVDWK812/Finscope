"""Public-source adapters use authored fixtures, mock HTTP and temporary stores."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timedelta,timezone,date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from finscope.local_collectors import SOURCES
from finscope.local_news import FetchBlocked,LocalIngestionService,LocalNewsStore,analyze_finbert
from finscope.local_analytics import Filters,select_articles,overview_counts,heatmap_cells,evidence_graph
from finscope.public_sources import collect_source,parse_source,original_url,SourceError
from test_local_news import pipeline
import test_product_ui as product_test


def abs_index(count=20):
    return ('<main><h1>Authored ABS fixture</h1>'+''.join(
        f'<div class="views-row"><time datetime="2026-10-{i%28+1:02}">{i%28+1} October 2026</time>'
        f'<h2><a href="/media-centre/media-releases/fixture-{i}">Authored energy release {i}</a></h2></div>'
        for i in range(count))+'</main>').encode()


def accc_feed(count=30):
    return ('<rss version="2.0"><channel><title>Authored ACCC feed fixture</title>'+''.join(
        f'<item><title>Authored bank release {i}</title><link>https://www.accc.gov.au/media-release/fixture-{i}</link>'
        '<pubDate>Thu, 29 Oct 2026 11:30:00 +1100</pubDate><description>&lt;p&gt;Authored financial summary.&lt;/p&gt;</description></item>'
        for i in range(count))+'</channel></rss>').encode()


class PublicSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=LocalNewsStore(self.root/'news.sqlite3')
        self.now=datetime(2026,10,29,16,tzinfo=timezone.utc)
        self.service=LocalIngestionService(self.store,cooldown_path=self.root/'holds.json',study_path=self.root/'study.sqlite3',clock=lambda:self.now)
        self.calls=[]
        # The live endpoint returned 403; enable only its mock transport here.
        enabled=patch.dict(SOURCES['accc_rss'],{'enabled':True});enabled.start();self.addCleanup(enabled.stop)

    def get(self,url):
        self.calls.append(url)
        return (b'User-agent: *\nAllow: /' if url.endswith('/robots.txt') else abs_index() if 'abs.gov.au' in url else accc_feed()),200

    def test_source_registry_records_license_exclusions_and_independent_publishers(self):
        for key in ('abs_html','accc_rss'):
            config=SOURCES[key]
            self.assertEqual(config['license'],'CC BY 4.0')
            self.assertTrue(config['terms_url'].startswith(config['url'].split('/')[0]+'//'+config['url'].split('/')[2]))
            self.assertIn('Third-party',config['exclusions'])
            self.assertTrue(config['attribution']);self.assertTrue(config['verified_on'])
        self.assertNotEqual(SOURCES['abs_html']['bucket'],SOURCES['accc_rss']['bucket'])

    def test_abs_date_precision_and_no_page_date_or_boilerplate_as_news(self):
        rows=parse_source('abs_html',abs_index(),50)
        self.assertEqual(len(rows),20)
        self.assertEqual(rows[0].publication_date,'2026-10-01')
        self.assertEqual(rows[0].timestamp,'');self.assertEqual(rows[0].summary,'')
        self.assertTrue(all(n.rights.analyze and n.rights.retain and not n.rights.external for n in rows))
        self.assertEqual({n.publication_date for n in rows},{f'2026-10-{i:02}' for i in range(1,21)})
        unknown=parse_source('abs_html',b'<main><a href="/media-centre/media-releases/unknown">Authored unknown release</a></main>',1)[0]
        self.assertEqual(unknown.published_day,'')

    def test_feed_text_timestamp_original_links_and_stable_repeated_identity(self):
        a=parse_source('accc_rss',accc_feed(),30)
        b=parse_source('accc_rss',accc_feed(),30)
        self.assertEqual([n.article_id for n in a],[n.article_id for n in b])
        self.assertEqual(a[0].timestamp,'2026-10-29T00:30:00+00:00')
        self.assertEqual(a[0].summary,'Authored financial summary.')
        self.assertIn('11:30:00 +1100',a[0].provenance)
        self.assertEqual(a[0].company,'')

    def test_source_license_withholds_third_party_or_explicit_restriction(self):
        payload=accc_feed(1).replace(b'Authored financial summary.',b'Courtesy of Third Party. Copyright 2026 Other owner.')
        item=parse_source('accc_rss',payload,1)[0]
        self.assertFalse(item.rights.retain);self.assertFalse(item.rights.analyze)
        with self.assertRaises(ValueError):self.store.save_news(item)

    def test_fixed_addresses_xml_and_response_bounds(self):
        for url in ('https://evil.invalid/media-release/x','https://www.accc.gov.au.evil.invalid/media-release/x',
                    'https://user@www.accc.gov.au/media-release/x','https://www.accc.gov.au/media-release/x?next=2',
                    'https://www.accc.gov.au/system/files/body.pdf'):
            self.assertEqual(original_url('accc_rss',url),'')
        for payload in (b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///private">]><rss/>',b'not XML',b'x'*1000001):
            with self.assertRaises(ValueError):parse_source('accc_rss',payload,50)
        for limit in (0,51,True):
            with self.assertRaises(ValueError):parse_source('abs_html',abs_index(),limit)

    def test_thirty_records_use_two_http_calls_not_thirty_requests(self):
        items,report=collect_source(self.service,'accc_rss',limit=30,explicit=True,get=self.get)
        self.assertEqual(len(items),30)
        self.assertEqual(self.calls,[SOURCES['accc_rss']['robots'],SOURCES['accc_rss']['url']])
        self.assertEqual((report['http_request_budget'],report['parse_record_limit']),(2,30))
        self.assertEqual(self.store.list_news(),[])
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM local_collector_http WHERE status='ok'").fetchone()[0],2)
        self.assertFalse(list((self.root/'public_sources').rglob('response.xml')))
        for n in [*items,*items]:self.store.save_news(n)
        self.assertEqual(len(self.store.list_news()),30)

    def test_source_guards_robots_and_no_implicit_requests(self):
        with self.assertRaises(FetchBlocked):collect_source(self.service,'abs_html',get=self.get)
        self.assertFalse(self.calls)
        def denied(url):self.calls.append(url);return b'User-agent: *\nDisallow: /',200
        with self.assertRaisesRegex(FetchBlocked,'Robots'):
            collect_source(self.service,'abs_html',explicit=True,get=denied)
        self.assertEqual(len(self.calls),1)
        with self.assertRaises(FetchBlocked):collect_source(self.service,'abs_html',explicit=True,get=self.get)
        self.assertEqual(len(self.calls),1)

    def test_unavailable_source_blocks_before_reservation_and_transport(self):
        with patch.dict(SOURCES['accc_rss'],{'enabled':False}):
            with self.assertRaisesRegex(FetchBlocked,'not verified'):
                collect_source(self.service,'accc_rss',explicit=True,get=self.get)
        self.assertEqual(self.calls,[])
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)

    def test_retry_after_and_unknown_outcome_preserve_durable_holds(self):
        def limited(url):raise SourceError('Source stopped: HTTP 429',status=429,retry_after='120')
        with self.assertRaises(FetchBlocked):collect_source(self.service,'accc_rss',explicit=True,get=limited)
        self.assertTrue(self.service.source_status('accc',configured=True).blocked)
        def unknown(url):raise RuntimeError('Mock transport interruption')
        with self.assertRaisesRegex(FetchBlocked,'Outcome needs review'):
            collect_source(self.service,'abs_html',explicit=True,get=unknown)
        self.now+=timedelta(days=1)
        self.assertTrue(self.service.source_status('abs',configured=True).blocked)

    def test_source_license_defaults_allow_local_finbert_and_keep_model_scope(self):
        item=parse_source('abs_html',abs_index(1),1)[0];self.store.save_news(item)
        one=analyze_finbert(item,self.store,pipeline());analyze_finbert(item,self.store,pipeline())
        self.assertEqual(one.provenance['text_basis'],'headline_only')
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.store.list_analyses()),2)
        selected,results=select_articles(self.store.list_news(),self.store.list_analyses(),Filters(models=(),require_results=False))
        self.assertEqual(overview_counts(selected,results)['raw_articles'],1)
        cells=heatmap_cells(selected,results,date(2026,10,1),date(2026,10,1),date_basis='published')
        self.assertEqual(next(c for c in cells if c['Sector']=='Energy')['Analyzed'],1)
        self.assertFalse(any(e['relationship']=='returned_for_ticker' for e in evidence_graph(selected,results)['edges']))


class PublicSourceUITests(unittest.TestCase):
    setUp=product_test.ProductUITests.setUp
    app=product_test.ProductUITests.app

    def test_registered_licensed_preview_needs_no_per_article_attestation_or_news_key(self):
        items=parse_source('abs_html',abs_index(2),2)
        app=self.app('Add news')
        app.selectbox(key='api_provider').set_value('Local Collector').run()
        app.radio(key='fixed_source').set_value('abs_html').run()
        self.assertFalse(any(t.label.endswith('API key') for t in app.text_input))
        app.session_state['news_preview']=items;app.run()
        self.assertFalse(any(t.key=='preview_reference' for t in app.text_input))
        next(b for b in app.button if b.label=='Save permitted preview to local library').click().run()
        self.assertEqual(len(LocalNewsStore(self.db).list_news()),2)
        self.assertFalse(app.exception)

    def test_refresh_and_source_switch_do_not_collect_or_change_api_credentials(self):
        app=self.app('Add news')
        with patch('finscope.public_sources.collect_source') as collect:
            app.selectbox(key='api_provider').set_value('Local Collector').run()
            app.radio(key='fixed_source').set_value('abs_html').run()
            app.run()
            app.radio(key='fixed_source').set_value('accc_rss').run()
            collect.assert_not_called()
        self.assertFalse(app.exception)

    def test_default_date_window_survives_add_news_and_new_records_need_explicit_widening(self):
        store=LocalNewsStore(self.db)
        old=parse_source('abs_html',abs_index(1),1)[0];store.save_news(old)
        app=self.app('Dashboard')
        original_range=app.date_input(key='local_dates').value
        app.radio(key='workspace_page').set_value('Add news').run()
        new=replace(old,article_id='authored-new-row',publication_date='2026-10-29')
        store.save_news(new)
        app.session_state['new_news_ids']=[new.article_id]
        app.radio(key='workspace_page').set_value('Analyze').run()
        self.assertEqual(app.date_input(key='local_dates').value,original_range)
        self.assertTrue(any('1 new records outside' in i.value for i in app.info))
        next(b for b in app.button if b.label=='Include all saved publication dates').click().run()
        self.assertEqual(len(app.multiselect(key='analysis_articles').options),2)

    def test_unavailable_accc_is_not_offered_as_a_working_collection(self):
        app=self.app('Add news')
        app.selectbox(key='api_provider').set_value('Local Collector').run()
        app.radio(key='fixed_source').set_value('accc_rss').run()
        self.assertTrue(any('HTTP 403' in w.value for w in app.warning))
        self.assertFalse(any(b.label=='Fetch official news' for b in app.button))
        self.assertFalse(app.exception)
