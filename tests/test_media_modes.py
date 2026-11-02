import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from unittest.mock import patch
from tests import test_media_coverage as fixtures
from datetime import datetime,timezone
from finscope.media_modes import scope,MEDIA_DOMAINS,MODES
from finscope.api_sources import MarketauxFilters,build_request
from finscope.media_broad import key

class ModeTests(unittest.TestCase):
    def test_three_modes_mapping_and_exclusivity(self):
        self.assertEqual(len(MODES),3);self.assertEqual(len(MEDIA_DOMAINS),6)
        self.assertEqual(scope('all'),[])
        self.assertEqual(scope('media',['Reuters','Yahoo Finance']),['finance.yahoo.com','reuters.com'])
        for args in [('media',[], 'latest'),('media',['Reuters'],'stratified'),('company',['Reuters'],'latest'),('all',['Reuters'],'latest')]:
            with self.assertRaises(ValueError):scope(*args)
        domains=scope('media',list(MEDIA_DOMAINS))
        _,p,*_=build_request('marketaux','technology',datetime.now(timezone.utc),1,3,'AUTHORED',marketaux_filters=MarketauxFilters(tuple(domains)))
        self.assertEqual(set(p['domains'].split(',')),set(domains));self.assertFalse(set(p)&{'symbols','industries','search','source_ids'})
        self.assertNotEqual(key({'scope':{'domains':[]},'per_request':3}),key({'scope':{'domains':domains},'per_request':3}))

class ModeUITests(unittest.TestCase):
    setUp=fixtures.CoverageTests.setUp
    scope=fixtures.CoverageTests.scope
    def test_radio_modes_only_show_supported_controls_without_key_reads_or_http(self):
        self.store.set_setting('guide_completed',True)
        with patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP')),patch('finscope.news_keys.NewsKeyRegistry.legacy_key',side_effect=AssertionError('No credential reads')):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'),default_timeout=30).run()
            self.assertFalse(app.exception)
            radio=app.radio(key='media_acquisition_mode');self.assertEqual(radio.options,list(MODES));self.assertEqual(radio.value,MODES[0])
            self.assertFalse(any(w.label in MEDIA_DOMAINS for w in app.checkbox))
            radio.set_value(MODES[1]).run();self.assertFalse(app.exception)
            self.assertEqual({w.label for w in app.checkbox if w.label in MEDIA_DOMAINS},set(MEDIA_DOMAINS))
            self.assertFalse(any('whitelist' in w.label for w in app.text_input))
            self.assertEqual(next(w for w in app.selectbox if w.label=='Broad collection strategy').options,['Latest news'])
            self.assertFalse(any('watchlist:' in w.label for w in app.text_area))
            app.radio(key='media_acquisition_mode').set_value(MODES[2]).run();self.assertFalse(app.exception)
            self.assertTrue(any('watchlist:' in w.label for w in app.text_area))
            self.assertFalse(any(w.label in MEDIA_DOMAINS for w in app.checkbox))
