from contextlib import closing
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,os,unittest
from unittest.mock import patch,Mock
from finscope.local_news import LocalNewsStore,LocalIngestionService,FetchBlocked
from finscope.local_credentials import credential_store
from finscope.news_keys import NewsKeyRegistry,LEGACY
from finscope.news_readiness import key_metadata,check_local,source_readiness,source_plan,verify_api
from finscope.task_queue import TaskQueue
from finscope.settings_state import save,saved
from finscope.api_sources import HTTPResponse,APIError
from test_product_pipeline import C


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB'])
        self.registry=NewsKeyRegistry(self.store);self.memory=credential_store()
        self.root=self.store.path.parent;self.now=datetime.now(timezone.utc)
        self.transport=Mock(return_value=HTTPResponse({'data':[]},200,{}))
        self.service=LocalIngestionService(self.store,clock=lambda:self.now,transport=self.transport,
            study_path=self.root/'study.sqlite3',cooldown_path=self.root/'hold.json')
        self.config={**deepcopy(C),'sources':['marketaux','finnhub','newsdata'],
            'source_permissions':{p:dict(preview=True,retain=True,analyze=True,external=False,reference='Authored offline permission') for p in ('marketaux','finnhub','newsdata')},
            'budgets':{p:dict(utc_day=self.now.date().isoformat(),remaining=3,topic='technology',symbol='NVDA' if p=='finnhub' else '') for p in ('marketaux','finnhub','newsdata')}}
        guard=patch('requests.sessions.Session.request',side_effect=AssertionError('No real request'));guard.start();self.addCleanup(guard.stop)
    def add(self,p='marketaux',name='Main',primary=True):
        return self.registry.add(p,name,'AUTHORED-'+p+'-'+name,primary=primary)
    def state(self,p='marketaux',target='pipeline'):
        return source_readiness(self.store,p,self.config,target=target,service=self.service)
    def test_three_sources_one_primary_two_backups_have_metadata_only_evidence(self):
        for p in self.config['sources']:
            self.add(p);self.add(p,'Backup one',False);self.add(p,'Backup two',False)
        with patch.object(self.memory,'read_slot',side_effect=AssertionError('No implicit credential reads')),patch.object(self.memory,'read',side_effect=AssertionError('No legacy reads')),patch('finscope.local_credentials.environment_credentials',side_effect=AssertionError('No env reads')):
            for p in self.config['sources']:
                info=key_metadata(self.store,p)
                self.assertEqual(info['backups'],2);self.assertEqual(info['primary']['name'],'Main')
                self.assertTrue(all(r['local_state']=='saved' and r['api_state']=='untested' for r in info['rows']))
                self.state(p)
        self.transport.assert_not_called()
    def test_unknown_legacy_existence_is_not_claimed_saved_or_verified(self):
        info=key_metadata(self.store,'finnhub')
        self.assertEqual(info['primary']['slot_id'],LEGACY)
        self.assertEqual(info['primary']['local_state'],'unchecked');self.assertEqual(info['primary']['api_state'],'untested')
        self.assertFalse(self.state('finnhub')['ready'])
    def test_provider_historical_200_cannot_verify_new_primary_or_backups(self):
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_requests VALUES (?,?,?,?,?,?,?,?)',('old','marketaux','2020-01-01T00:00:00+00:00','2020-01-01T00:00:01+00:00','ok',200,None,'records'));db.commit()
        self.add();self.add(name='Backup',primary=False)
        self.assertTrue(all(r['api_state']=='untested' for r in key_metadata(self.store,'marketaux')['rows']))
    def test_api_evidence_is_scoped_to_exact_version_and_replacement_resets_it(self):
        slot=self.add();backup=self.add(name='Backup',primary=False)
        self.assertEqual(verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service),('ok',0))
        rows=key_metadata(self.store,'marketaux')['rows']
        self.assertEqual(next(r for r in rows if r['slot_id']==slot)['api_state'],'verified')
        self.assertEqual(next(r for r in rows if r['slot_id']==backup)['api_state'],'untested')
        self.registry.replace('marketaux',slot,'AUTHORED-REPLACEMENT')
        self.assertEqual(key_metadata(self.store,'marketaux')['primary']['api_state'],'untested')
    def test_local_check_returns_only_status_and_preserves_request_history(self):
        slot=self.add();ref=self.registry.selection('marketaux')['credential_ref']
        self.assertEqual(check_local(self.store,'marketaux',slot),'saved')
        self.memory.delete_slot('marketaux',ref,confirmed=True)
        self.assertEqual(check_local(self.store,'marketaux',slot),'missing')
        self.assertIn('local',self.state()['missing'])
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
            self.assertNotIn('AUTHORED-',str(db.execute('SELECT * FROM news_key_checks').fetchall()))
        self.transport.assert_not_called()
    def test_local_read_error_is_redacted_and_independent_of_api_state(self):
        slot=self.add()
        with patch.object(self.memory,'read_slot',side_effect=OSError('AUTHORED-DO-NOT-PRINT')):
            self.assertEqual(check_local(self.store,'marketaux',slot),'read_failed')
        info=key_metadata(self.store,'marketaux')['primary']
        self.assertEqual(info['api_state'],'untested');self.assertNotIn('AUTHORED',json.dumps(info))
    def test_preview_does_not_require_storage_nlp_or_enable_pipeline(self):
        self.add();self.config['source_permissions']['marketaux']['retain']=False
        self.config['source_permissions']['marketaux']['analyze']=False
        self.config['sources'].remove('marketaux')
        self.assertTrue(self.state(target='preview')['ready'])
        self.assertEqual(set(self.state()['missing']),{'processing','enabled'})
    def test_preview_still_requires_permission_quota_and_finnhub_ticker(self):
        self.add('finnhub')
        self.config['budgets']['finnhub']['remaining']=0;self.config['budgets']['finnhub']['symbol']=''
        self.config['source_permissions']['finnhub']['preview']=False
        self.assertEqual(set(self.state('finnhub','preview')['missing']),{'quota','ticker','preview'})
        with self.assertRaises(FetchBlocked):verify_api(self.store,'finnhub',self.config,confirmed=True,service=self.service)
        self.transport.assert_not_called()
    def test_newsdata_pause_remains_with_valid_backup_and_invalid_primary(self):
        a=self.add('newsdata');self.add('newsdata','Backup',False)
        with closing(self.store.connect()) as db:
            db.execute("UPDATE news_key_slots SET last_status='invalid' WHERE provider='newsdata' AND slot_id=?",(a,));db.commit()
        self.assertIn('primary',self.state('newsdata')['missing']);self.assertIn('hold',self.state('newsdata')['missing'])
        backup=next(r['slot_id'] for r in key_metadata(self.store,'newsdata')['rows'] if not r['is_primary'])
        # Hypothetical historical validation in a temporary fixture, predating
        # the current manual pause. A verified backup still cannot bypass it.
        row=next(r for r in key_metadata(self.store,'newsdata')['rows'] if r['slot_id']==backup)
        old=(self.now-timedelta(days=3)).isoformat()
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_requests VALUES (?,?,?,?,?,?,?,?)',('offline-history','newsdata',old,old,'ok',200,None,'fixture'))
            db.execute('INSERT INTO news_request_keys VALUES (?,?,?,?,?,?,?)',('offline-history','newsdata',backup,row['credential_ref'],old,'ok',None));db.commit()
        self.registry.promote('newsdata',backup)
        self.assertEqual(self.state('newsdata')['keys']['primary']['api_state'],'verified')
        self.assertEqual(self.state('newsdata')['hold_reason'],'Existing manual pause; no requests allowed')
        with patch.object(self.memory,'read_slot',side_effect=AssertionError('Paused before secret resolution')):
            with self.assertRaises(FetchBlocked):verify_api(self.store,'newsdata',self.config,confirmed=True,service=self.service)
        self.transport.assert_not_called()
    def test_api_check_requires_per_action_confirmation_and_never_retries(self):
        self.add()
        with self.assertRaises(FetchBlocked):verify_api(self.store,'marketaux',self.config,service=self.service)
        self.transport.assert_not_called()
        verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service)
        with self.assertRaises(FetchBlocked):verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service)
        self.assertEqual(self.transport.call_count,1)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_news').fetchone()[0],0)
    def test_switching_primary_cannot_reuse_an_old_api_confirmation(self):
        self.add();old=self.registry.selection('marketaux');backup=self.add(name='Backup',primary=False)
        self.registry.promote('marketaux',backup)
        with self.assertRaisesRegex(FetchBlocked,'Primary key changed'):
            verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service,expected_selection=old)
        self.transport.assert_not_called()
    def test_quota_exhaustion_is_provider_wide(self):
        self.add();self.config['budgets']['marketaux']['remaining']=1
        verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service)
        backup=self.add(name='Backup',primary=False);self.registry.promote('marketaux',backup)
        self.assertIn('quota',self.state()['missing']);self.assertEqual(self.transport.call_count,1)
    def test_403_is_restricted_not_invalid_and_no_success_label_from_http_alone(self):
        self.add();self.transport.side_effect=APIError('redacted',status=403)
        verify_api(self.store,'marketaux',self.config,confirmed=True,service=self.service)
        self.assertEqual(key_metadata(self.store,'marketaux')['primary']['api_state'],'restricted')
        self.assertIn('hold',self.state()['missing'])
    def test_explicit_ready_submission_uses_draft_not_previous_pipeline(self):
        q=TaskQueue(self.store);q.configure(C);self.add()
        draft=deepcopy(self.config);draft['sources']=['marketaux','finnhub','abs_html'];draft['taxonomy']='CSRC-JRT0020-2024'
        draft['source_permissions'].pop('newsdata');draft['budgets'].pop('newsdata')
        self.assertTrue(save(q,draft));self.assertIsNotNone(saved(q))
        with self.assertRaises(ValueError):q.submit()
        with self.assertRaises(ValueError):q.submit_ready()
        task,fresh=q.submit_ready(confirmed=True)
        snapshot=q.get(task)['snapshot'];self.assertTrue(fresh)
        self.assertEqual(snapshot['sources'],['marketaux','abs_html'])
        self.assertEqual(snapshot['taxonomy'],'CSRC-JRT0020-2024');self.assertEqual(q.config(),C)
        self.assertEqual(saved(q),draft);self.transport.assert_not_called()
    def test_stale_scope_or_changed_saved_draft_cannot_queue_a_task(self):
        q=TaskQueue(self.store);q.configure(C)
        with self.assertRaisesRegex(ValueError,'readiness changed'):q.submit_ready(confirmed=True,expected_sources=['marketaux'])
        with self.assertRaisesRegex(ValueError,'settings changed'):q.submit_ready(confirmed=True,expected_config={'sources':['marketaux']})
        self.assertIsNone(q.get())
    def test_paused_only_source_has_no_ready_task_and_no_credential_read(self):
        q=TaskQueue(self.store);q.configure({**self.config,'sources':['newsdata'],
            'source_permissions':{'newsdata':self.config['source_permissions']['newsdata']},
            'budgets':{'newsdata':self.config['budgets']['newsdata']}});self.add('newsdata')
        with patch.object(self.memory,'read_slot',side_effect=AssertionError('No request key read')):
            self.assertEqual(source_plan(self.store,{'sources':['newsdata']},service=self.service)[0],[])
            with self.assertRaisesRegex(ValueError,'No selected source'):q.submit_ready(confirmed=True)
        self.assertIsNone(q.get());self.transport.assert_not_called()

    def test_disabled_profiles_are_valid_metadata_but_never_dispatch_or_store_keys(self):
        q=TaskQueue(self.store);self.add()
        c=deepcopy(self.config);c['sources']=['abs_html']
        self.assertEqual(save(q,c),[])
        self.assertEqual(q.config()['source_permissions'],c['source_permissions'])
        task,_=q.submit_ready(confirmed=True)
        self.assertEqual(q.get(task)['snapshot']['sources'],['abs_html'])
        self.assertEqual(q.get(task)['snapshot']['source_permissions'],{})
        c['source_permissions']['marketaux']['reference']='AUTHORED-marketaux-Main'
        for action in (lambda:save(q,c),lambda:q.configure(c)):
            with self.assertRaises(ValueError):action()
        with closing(self.store.connect()) as db:self.assertNotIn('AUTHORED-marketaux-Main','\n'.join(db.iterdump()))
        self.transport.assert_not_called()


if __name__=='__main__':unittest.main()
