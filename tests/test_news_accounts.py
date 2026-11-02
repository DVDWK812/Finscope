from contextlib import closing
from datetime import timedelta
import unittest,json
from unittest.mock import patch,Mock
from tests import test_news_keys as fixtures
from finscope.news_accounts import attest,view,check,SHARED
from finscope.local_news import FetchBlocked
from finscope.api_sources import APIError,_http_get_json

class AccountTests(unittest.TestCase):
    setUp=fixtures.NewsKeyTests.setUp
    add=fixtures.NewsKeyTests.add
    fetch=fixtures.NewsKeyTests.fetch
    def evidence(self,slot,identity=SHARED,remaining=2,budget=10):
        return attest(self.store,'marketaux',slot,identity,remaining=remaining,day_budget=budget,
            reference='Authored balance check and permitted independent subscription terms',
            independent_confirmed=identity!=SHARED,confirmed=True,now=self.now)
    def test_same_account_keys_share_allowance_no_automatic_rotation(self):
        a=self.add();b=self.add(name='Second',key='AUTHORED-SECOND',primary=False)
        self.evidence(a);self.evidence(b)
        self.fetch(application_daily_cap=10);self.now+=timedelta(seconds=61)
        self.registry.promote('marketaux',b);self.fetch(application_daily_cap=10);self.now+=timedelta(seconds=61)
        with self.assertRaisesRegex(FetchBlocked,'account allowance'):self.fetch(application_daily_cap=10)
        self.assertEqual(len(self.calls),2)
        with closing(self.store.connect()) as db:self.assertEqual(view(db,'marketaux',b,self.now)['remaining_after_local_requests'],0)
    def test_same_day_budget_increase_preserves_requests(self):
        a=self.add();self.evidence(a,remaining=10,budget=1);self.fetch(application_daily_cap=1);self.now+=timedelta(seconds=61)
        with self.assertRaises(FetchBlocked):self.fetch(application_daily_cap=1)
        self.evidence(a,remaining=9,budget=2);self.fetch(application_daily_cap=2)
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT count(*) FROM news_account_history').fetchone()[0],2)
    def test_402_account_hold_independent_accounts_and_429_retry_after(self):
        a=self.add();b=self.add(name='Independent',key='AUTHORED-INDEPENDENT',primary=False)
        self.evidence(a,identity='account-a');self.evidence(b,identity='account-b')
        self.reply=APIError('HTTP 402',kind='usage_limit',status=402,rate_headers={'X-UsageLimit-Limit':'100','Authorization':'DO NOT SAVE'})
        self.fetch(application_daily_cap=10);self.now+=timedelta(seconds=61)
        with self.assertRaisesRegex(FetchBlocked,'402'):self.fetch(application_daily_cap=10)
        self.registry.promote('marketaux',b);self.reply=APIError('HTTP 429',kind='rate_limit',status=429,rate_headers={'Retry-After':'120'})
        self.fetch(application_daily_cap=10);self.now+=timedelta(seconds=61)
        with self.assertRaises(FetchBlocked):self.fetch(application_daily_cap=10)
        self.assertEqual(len(self.calls),2)
        with closing(self.store.connect()) as db:
            payloads=[json.loads(r[0]) for r in db.execute('SELECT headers FROM news_usage_receipts')]
            self.assertEqual(payloads,[{'X-UsageLimit-Limit':'100'},{'Retry-After':'120'}])
    def test_unknown_evidence_and_no_secret_read_for_attestation(self):
        a=self.add()
        with patch.object(self.memory,'read_slot',side_effect=AssertionError('No key reads')),patch.object(self.registry,'legacy_key',side_effect=AssertionError('No key reads')):
            with closing(self.store.connect()) as db:self.assertIsNone(view(db,'marketaux',a,self.now)['remaining_after_local_requests'])
            self.evidence(a,remaining=None)
        with self.assertRaisesRegex(FetchBlocked,'unknown'):self.fetch(application_daily_cap=10)
        self.assertFalse(self.calls)
    def test_unmapped_backup_cannot_be_treated_as_independent_quota(self):
        a=self.add();b=self.add(name='Unmapped backup',key='AUTHORED-UNMAPPED',primary=False)
        self.evidence(a,identity='account-a',remaining=1)
        self.fetch(application_daily_cap=10);self.now+=timedelta(seconds=61)
        self.registry.promote('marketaux',b)
        with self.assertRaisesRegex(FetchBlocked,'unknown'):self.fetch(application_daily_cap=10)
        self.assertEqual(len(self.calls),1)
    @patch('finscope.api_sources.requests.get')
    def test_usage_http_headers_strict_allowlist(self,get):
        get.return_value=Mock(status_code=402,headers={'x-usagelimit-limit':'100','X-UsageLimit-Remaining':'0','X-UsageLimit-Reset':'SECRET','Authorization':'SECRET'})
        with self.assertRaises(APIError) as caught:_http_get_json('https://example.com',{}, {},1)
        self.assertEqual(caught.exception.kind,'usage_limit')
        self.assertEqual(caught.exception.rate_headers,{'X-UsageLimit-Limit':'100','X-UsageLimit-Remaining':'0'})
