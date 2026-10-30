from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

from finscope.connection_diagnostics import api_diagnostic, credential_report
from finscope.local_news import LocalIngestionService, LocalNewsStore
from finscope.model_providers import ModelError, OllamaProvider, OLLAMA_ORIGIN, model_request


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.store=LocalNewsStore(self.root/'news.sqlite3')
        self.env=self.root/'.env';self.env.write_text('MARKETAUX_API_KEY=UNIT-PRIVATE-KEY\nFINNHUB_API_KEY=UNIT-FINNHUB-KEY\nNEWSDATA_API_KEY=UNIT-NEWS-KEY\n')
        for target in ('finscope.api_sources.project_env_path','finscope.connection_diagnostics.project_env_path'):
            p=patch(target,return_value=self.env);p.start();self.addCleanup(p.stop)
        self.now=datetime(2026,10,30,13,tzinfo=timezone.utc)
        self.service=LocalIngestionService(self.store,clock=lambda:self.now,cooldown_path=self.root/'cooldowns.json',study_path=self.root/'study.sqlite3')

    def row(self,status='failed',hold=None):
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_requests VALUES (?,?,?,?,?,?,?,?)',
                ('request-one','marketaux','2026-10-29T10:00:32+00:00','2026-10-29T10:00:48+00:00',status,None,hold,'transport'));db.commit()

    def report(self,provider='marketaux',**kwargs):
        return api_diagnostic(self.store,provider,service=self.service,**kwargs)

    def test_project_file_credentials_and_ui_override_are_isolated_and_redacted(self):
        self.assertTrue(credential_report('finnhub')['present'])
        self.assertFalse(credential_report('openai')['present'])
        self.assertFalse(credential_report('marketaux',use_env=False)['present'])
        self.assertEqual(credential_report('openai',ui_key_present=True)['source'],'Masked UI field (session only)')
        with patch.dict('os.environ',{'OPENAI_API_KEY':'PARENT-SECRET'}):
            self.assertFalse(credential_report('openai')['present'])
        report=self.report();self.assertNotIn('UNIT-PRIVATE-KEY',json.dumps(report))
        self.assertNotIn(b'UNIT-PRIVATE-KEY',self.store.path.read_bytes())

    def test_expired_failure_has_exact_utc_sydney_expiry_and_does_not_imply_outage(self):
        self.row();before=self.store.path.read_bytes();report=self.report()
        self.assertEqual(report['state'],'Untested')
        stop=next(h for h in report['holds'] if h['kind'].startswith('Failure'))
        self.assertFalse(stop['active']);self.assertEqual(stop['record'],'request-one')
        self.assertEqual(stop['until_utc'],'2026-10-30T00:00:00+00:00')
        self.assertEqual(stop['until_sydney'],'2026-10-30T11:00:00+11:00')
        self.assertEqual(self.store.path.read_bytes(),before)
        self.now=datetime(2026,10,29,23,tzinfo=timezone.utc)
        self.assertEqual(self.report()['state'],'Failed')

    def test_unknown_request_and_unexpired_retry_still_block_across_days(self):
        self.row('pending','2026-10-31T10:00:00+00:00');report=self.report()
        self.assertEqual(report['state'],'Paused')
        self.assertEqual(sum(h['active'] for h in report['holds']),2)
        self.assertEqual(report['product_attempt_count'],1)

    def test_newsdata_pause_is_code_level_and_not_a_new_provider_failure(self):
        report=self.report('newsdata')
        self.assertEqual(report['state'],'Paused');self.assertEqual(report['product_attempt_count'],0)
        self.assertTrue(next(h for h in report['holds'] if h['kind']=='Code-level manual pause')['active'])

    def test_finnhub_preview_and_nlp_gates_are_not_connection_failures(self):
        report=self.report('finnhub')
        self.assertTrue(report['credentials']['present']);self.assertEqual(report['state'],'Untested')
        self.assertIn('Fresh confirmed available account request budget',report['required_before_request'])
        self.assertIn('preview permission',report['required_before_request'][1])
        self.assertIn('not an API connection failure',report['downstream_nlp'])

    def test_openai_missing_credential_and_external_consent_are_separate(self):
        report=self.report('openai');self.assertEqual(report['state'],'Not configured')
        self.assertEqual(report['product_attempt_count'],0);self.assertEqual(len(report['required_before_request']),3)
        self.assertEqual(self.report('openai',ui_key_present=True)['state'],'Untested')

    def test_historical_http_is_preserved_and_not_a_current_connection_probe(self):
        (self.root/'keyed_healthcare_initial.json').write_text(json.dumps({'generated_at_utc':'2026-10-24T00:00:00Z',
            'results':[{'provider':'finnhub','status':'ok','http_status':200,'articles':['DO NOT DISPLAY'] }]}))
        report=self.report('finnhub')
        self.assertEqual(report['historical_http_evidence'][0]['http_status'],200)
        self.assertEqual(report['state'],'Untested');self.assertNotIn('DO NOT DISPLAY',json.dumps(report))

    def test_connection_refusal_timeout_http_and_transport_errors_remain_distinct(self):
        for error,kind in [(requests.ConnectionError('[WinError 10061] UNIT-PRIVATE-KEY'),'connection_refused'),
                           (requests.ConnectionError('DNS UNIT-PRIVATE-KEY'),'connection_error'),
                           (requests.Timeout('UNIT-PRIVATE-KEY'),'timeout')]:
            with self.subTest(kind=kind),patch('finscope.model_providers.requests.Session') as session:
                session.return_value.__enter__.return_value.request.side_effect=error
                with self.assertRaises(ModelError) as caught:model_request('GET',OLLAMA_ORIGIN+'/api/tags')
                self.assertEqual(caught.exception.kind,kind);self.assertNotIn('UNIT-PRIVATE-KEY',str(caught.exception))
        with patch('finscope.model_providers.requests.Session') as session:
            response=session.return_value.__enter__.return_value.request.return_value
            response.status_code=503;response.headers={}
            with self.assertRaises(ModelError) as caught:model_request('GET',OLLAMA_ORIGIN+'/api/tags')
            self.assertEqual(caught.exception.status,503);self.assertEqual(caught.exception.kind,'http_error')

    def test_empty_ollama_registry_differs_from_filtered_incompatible_models(self):
        self.assertEqual(OllamaProvider(lambda *a:{'models':[]}).inventory(),{'models':{},'total':0,'filtered':0})
        report=OllamaProvider(lambda *a:{'models':[{'name':'remote:cloud'},{'name':'bad-format'}]}).inventory()
        self.assertEqual(report,{'models':{},'total':2,'filtered':2})

    def test_diagnostics_never_dispatch_or_reserve(self):
        before=self.store.path.read_bytes()
        with patch('requests.sessions.Session.request',side_effect=AssertionError('No diagnostic network')):
            for provider in ('marketaux','newsdata','finnhub','openai'):self.report(provider)
        self.assertEqual(self.store.path.read_bytes(),before)
