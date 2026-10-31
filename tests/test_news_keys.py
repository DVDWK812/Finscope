from contextlib import closing
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
from finscope.local_news import LocalNewsStore,LocalIngestionService,ContentRights,FetchBlocked
from finscope.local_credentials import credential_store,credential,project_env_path
from finscope.news_keys import NewsKeyRegistry,NewsKeyError,LEGACY
from finscope.api_sources import HTTPResponse,APIError
from finscope.task_queue import TaskQueue
from finscope.local_worker import Worker
from test_product_pipeline import C,fixture,prediction

RIGHTS=ContentRights(True,True,True,False,'Authored offline permission fixture')


class NewsKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=LocalNewsStore(self.root/'news.sqlite3')
        self.memory=credential_store();self.registry=NewsKeyRegistry(self.store);self.now=datetime.now(timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0)
        self.calls=[];self.reply=HTTPResponse({'data':[]},200,{})
        def transport(*args):
            self.calls.append(args)
            if isinstance(self.reply,Exception):raise self.reply
            return self.reply
        self.service=LocalIngestionService(self.store,transport=transport,clock=lambda:self.now,
            cooldown_path=self.root/'holds.json',study_path=self.root/'study.sqlite3')
        for guard in (patch('requests.sessions.Session.request',side_effect=AssertionError('No live requests')),
                      patch('finscope.windows_credentials.c.WinDLL',create=True,side_effect=AssertionError('No native credential calls'))):
            guard.start();self.addCleanup(guard.stop)
    def add(self,p='marketaux',name='Primary',key='AUTHORED-PRIMARY-KEY',primary=True):return self.registry.add(p,name,key,primary=primary)
    def config(self,sources=('marketaux',),remaining=3):
        return {**deepcopy(C),'sources':list(sources),
            'source_permissions':{p:dict(preview=True,retain=True,analyze=True,external=False,reference=RIGHTS.reference) for p in sources},
            'budgets':{p:dict(utc_day=datetime.now(timezone.utc).date().isoformat(),remaining=remaining,topic='technology',symbol='NVDA' if p=='finnhub' else '') for p in sources}}
    def fetch(self,p='marketaux',**kwargs):return self.registry.fetch(self.service,p,'technology',rights=RIGHTS,remaining=3,explicit=True,symbol='NVDA' if p=='finnhub' else None,**kwargs)
    def worker_fetch(self,c,p='marketaux'):
        with patch('finscope.local_worker.LocalIngestionService',return_value=self.service):
            return Worker(self.store).fetch(p,c,lambda:None)
    def rows(self,table):
        with closing(self.store.connect()) as db:return db.execute('SELECT * FROM '+table).fetchall()
    def assert_no_secret_in_db(self,*values):
        with closing(self.store.connect()) as db:dump='\n'.join(db.iterdump())
        for value in values:self.assertNotIn(value,dump)

    def test_sources_have_independent_primary_and_multiple_backups(self):
        for p in ('marketaux','finnhub','newsdata'):
            a=self.add(p,key='AUTHORED-'+p+'-MAIN')
            b=self.add(p,'Backup','AUTHORED-'+p+'-BACKUP',False)
            self.assertEqual(sum(r['is_primary'] for r in self.registry.rows(p)),1)
            self.registry.promote(p,b)
            self.assertEqual(self.registry.selection(p)['slot_id'],b)
            self.assertEqual(credential(p,store=self.store),'AUTHORED-'+p+'-BACKUP')
            self.assertEqual(len(self.registry.rows(p)),2)
        self.assert_no_secret_in_db(*['AUTHORED-'+p+suffix for p in ('marketaux','finnhub','newsdata') for suffix in ('-MAIN','-BACKUP')])
        self.assertEqual(self.calls,[])

    def test_no_primary_does_not_fall_back_to_a_backup_or_legacy(self):
        self.memory.write('marketaux','AUTHORED-LEGACY-ONLY')
        a=self.add();self.registry.enable('marketaux',a,False)
        self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        self.assertIsNone(self.registry.selection('marketaux'));self.assertFalse(self.registry.configured('marketaux'))
        self.assertEqual(credential('marketaux',store=self.store),'')
        self.assertEqual(self.memory.read('marketaux'),'AUTHORED-LEGACY-ONLY')

    def test_enable_disable_and_confirmed_delete_do_not_promote_automatically(self):
        a=self.add();b=self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        self.registry.enable('marketaux',a,False);self.assertIsNone(self.registry.selection('marketaux'))
        self.registry.enable('marketaux',a,True);self.assertIsNone(self.registry.selection('marketaux'))
        self.registry.promote('marketaux',b)
        with self.assertRaises(NewsKeyError):self.registry.delete('marketaux',b)
        ref=self.registry.selection('marketaux')['credential_ref'];self.registry.delete('marketaux',b,confirmed=True)
        self.assertEqual(self.memory.read_slot('marketaux',ref),'');self.assertIsNone(self.registry.selection('marketaux'))
        self.assertEqual([r['slot_id'] for r in self.registry.rows('marketaux')],[a])

    def test_legacy_vault_and_literal_env_are_visible_but_never_migrated_silently(self):
        path=project_env_path();path.write_text('FINNHUB_API_KEY=AUTHORED-ENV-FINNHUB\nMARKETAUX_API_KEY=AUTHORED-ENV-MARKET\n')
        self.memory.write('marketaux','AUTHORED-VAULT-MARKET');before=path.read_bytes()
        self.assertEqual(self.registry.resolve('marketaux'),'AUTHORED-VAULT-MARKET')
        self.assertEqual(self.registry.resolve('finnhub'),'AUTHORED-ENV-FINNHUB')
        self.assertEqual(self.registry.rows('marketaux')[0]['slot_id'],LEGACY)
        self.assertEqual(self.rows('news_key_slots'),[])
        self.add(primary=False);self.assertEqual(self.registry.selection('marketaux')['slot_id'],LEGACY)
        self.assertEqual(self.memory.read('marketaux'),'AUTHORED-VAULT-MARKET');self.assertEqual(path.read_bytes(),before)
        with self.assertRaises(NewsKeyError):self.registry.delete('marketaux',LEGACY,confirmed=True)
        self.registry.enable('marketaux',LEGACY,False);self.assertFalse(self.registry.configured('marketaux'))
        self.registry.enable('marketaux',LEGACY,True);self.registry.promote('marketaux',LEGACY)
        self.assertTrue(self.registry.configured('marketaux'))

    def test_replace_uses_new_verified_reference_and_keeps_old_on_partial_write_failure(self):
        a=self.add();old=self.registry.selection('marketaux');original_write=self.memory.write_slot
        def partial(p,r,v):original_write(p,r,v);raise OSError(v)
        with patch.object(self.memory,'write_slot',side_effect=partial):
            with self.assertRaises(NewsKeyError) as error:self.registry.replace('marketaux',a,'AUTHORED-REPLACEMENT')
        self.assertNotIn('AUTHORED-REPLACEMENT',str(error.exception));self.assertEqual(self.registry.selection('marketaux'),old)
        self.assertEqual(self.registry.resolve('marketaux'),'AUTHORED-PRIMARY-KEY')
        self.registry.replace('marketaux',a,'AUTHORED-VALID-NEW')
        self.assertNotEqual(self.registry.selection('marketaux')['credential_ref'],old['credential_ref'])
        self.assertEqual(self.memory.read_slot('marketaux',old['credential_ref']),'AUTHORED-PRIMARY-KEY')
        self.assert_no_secret_in_db('AUTHORED-PRIMARY-KEY','AUTHORED-VALID-NEW','AUTHORED-REPLACEMENT')

    def test_failed_readback_does_not_publish_new_key_and_delete_clears_owned_versions(self):
        a=self.add();old=self.registry.selection('marketaux');read=self.memory.read_slot
        with patch.object(self.memory,'read_slot',side_effect=lambda p,r:read(p,r) if r==old['credential_ref'] else ''):
            with self.assertRaises(NewsKeyError):self.registry.replace('marketaux',a,'AUTHORED-UNVERIFIED')
        self.assertEqual(self.registry.selection('marketaux'),old)
        self.registry.replace('marketaux',a,'AUTHORED-VERIFIED');new=self.registry.selection('marketaux')
        self.registry.delete('marketaux',a,confirmed=True)
        self.assertEqual(read('marketaux',old['credential_ref']),'');self.assertEqual(read('marketaux',new['credential_ref']),'')

    def test_delete_failure_remains_disabled_and_does_not_touch_other_sources_or_legacy(self):
        a=self.add();b=self.add('finnhub',key='AUTHORED-FINNHUB')
        self.memory.write('marketaux','AUTHORED-LEGACY')
        with patch.object(self.memory,'delete_slot',side_effect=OSError('AUTHORED-PRIMARY-KEY')):
            with self.assertRaises(NewsKeyError):self.registry.delete('marketaux',a,confirmed=True)
        row=self.registry.rows('marketaux')[-1];self.assertTrue(row['deletion_pending']);self.assertFalse(row['enabled'])
        self.assertFalse(self.registry.configured('marketaux'));self.assertTrue(self.registry.configured('finnhub'))
        self.assertEqual(self.memory.read('marketaux'),'AUTHORED-LEGACY')
        self.registry.delete('marketaux',a,confirmed=True)

    def test_worker_pins_slot_ids_for_each_explicit_task_and_never_serializes_key(self):
        a=self.add();b=self.add(name='Backup',key='AUTHORED-BACKUP-KEY',primary=False)
        q=TaskQueue(self.store);c=self.config();q.configure(c);task,_=q.submit()
        old=q.get(task)['snapshot'];self.assertEqual(old['news_key_slots']['marketaux']['slot_id'],a)
        self.registry.promote('marketaux',b);self.worker_fetch(old)
        self.assertIn('AUTHORED-PRIMARY-KEY',str(self.calls[0]))
        q.update(task,status='completed');self.now+=timedelta(seconds=61);task2,_=q.submit();self.worker_fetch(q.get(task2)['snapshot'])
        self.assertIn('AUTHORED-BACKUP-KEY',str(self.calls[1]));self.assertEqual(len(self.calls),2)
        self.assertEqual(len(self.rows('local_requests')),2)
        self.assertEqual([r[2] for r in self.rows('news_request_keys')],[a,b])
        self.assert_no_secret_in_db('AUTHORED-PRIMARY-KEY','AUTHORED-BACKUP-KEY')

    def test_null_snapshot_and_replaced_reference_never_silently_switch_an_existing_task(self):
        a=self.add();self.registry.enable('marketaux',a,False)
        q=TaskQueue(self.store);q.configure(self.config());task,_=q.submit();snapshot=q.get(task)['snapshot']
        self.add(name='New primary',key='AUTHORED-NEW-PRIMARY')
        with self.assertRaises(FetchBlocked):self.worker_fetch(snapshot)
        self.assertEqual(self.calls,[]);self.assertEqual(self.rows('local_requests'),[])
        q.update(task,status='completed');task,_=q.submit();snapshot=q.get(task)['snapshot']
        slot=snapshot['news_key_slots']['marketaux']['slot_id'];self.registry.replace('marketaux',slot,'AUTHORED-CHANGED-PRIMARY')
        with self.assertRaises(FetchBlocked):self.worker_fetch(snapshot)
        self.assertEqual(self.calls,[])

    def test_all_guards_precede_plaintext_resolution_even_after_backup_promotion(self):
        a=self.add();b=self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        cases=[('pending',self.now-timedelta(days=2),None),('failed',self.now,None),
               ('ok',self.now-timedelta(seconds=30),None),('ok',self.now-timedelta(days=2),self.now+timedelta(hours=3))]
        for index,(status,when,hold) in enumerate(cases):
            with self.subTest(status=status,hold=hold):
                # Distinct mock databases, never reset a live ledger.
                store=LocalNewsStore(self.root/(str(index)+'.sqlite3'));registry=NewsKeyRegistry(store)
                selected=registry.add('marketaux','Selected','AUTHORED-A',primary=True)
                backup=registry.add('marketaux','Backup','AUTHORED-B',primary=False)
                with closing(store.connect()) as db:
                    db.execute('INSERT INTO local_requests VALUES (?,?,?,?,?,?,?,?)',('held','marketaux',when.isoformat(),None if status=='pending' else when.isoformat(),status,None,hold.isoformat() if hold else None,'fixture'));db.commit()
                registry.promote('marketaux',backup)
                service=LocalIngestionService(store,clock=lambda:self.now,cooldown_path=self.root/'none.json',study_path=self.root/'none.sqlite3',transport=Mock())
                with patch.object(self.memory,'read_slot',wraps=self.memory.read_slot) as secret:
                    with self.assertRaises(FetchBlocked):registry.fetch(service,'marketaux','technology',rights=RIGHTS,remaining=3,explicit=True)
                    secret.assert_not_called();service.transport.assert_not_called()
                with closing(store.connect()) as db:self.assertEqual(db.execute('SELECT status FROM local_requests').fetchall(),[(status,)])

    def test_newsdata_pause_and_marketaux_study_hold_never_resolve_any_key(self):
        self.add('newsdata',key='AUTHORED-NEWS-DATA');self.add()
        with closing(__import__('sqlite3').connect(self.service.study_path)) as db:
            db.execute('CREATE TABLE attempts(reserved_at TEXT,completed_at TEXT,status TEXT,cooldown_until TEXT)')
            db.execute('INSERT INTO attempts VALUES (?,?,?,?)',((self.now-timedelta(days=2)).isoformat(),None,'attempted_outcome_unknown',None));db.commit()
        before=self.service.study_path.read_bytes()
        with patch.object(self.memory,'read_slot',wraps=self.memory.read_slot) as read:
            for p in ('newsdata','marketaux'):
                with self.assertRaises(FetchBlocked):self.fetch(p)
            read.assert_not_called()
        self.assertEqual(self.calls,[]);self.assertEqual(self.service.study_path.read_bytes(),before)

    def test_source_budget_is_not_multiplied_by_key_count(self):
        self.add();b=self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        c=self.config(remaining=1);self.worker_fetch(c);self.registry.promote('marketaux',b);self.now+=timedelta(seconds=61)
        with patch.object(self.memory,'read_slot',wraps=self.memory.read_slot) as read:
            with self.assertRaises(FetchBlocked):self.worker_fetch(c)
            read.assert_not_called()
        self.assertEqual(len(self.calls),1);self.assertEqual(len(self.rows('local_requests')),1)

    def test_daily_cap_survives_three_different_primary_keys(self):
        slots=[self.add(name='Key '+str(i),key='AUTHORED-CAP-'+str(i),primary=i==0) for i in range(4)]
        for slot in slots[:3]:
            self.registry.promote('marketaux',slot);self.fetch();self.now+=timedelta(seconds=61)
        self.registry.promote('marketaux',slots[3])
        with patch.object(self.memory,'read_slot',wraps=self.memory.read_slot) as read:
            with self.assertRaisesRegex(FetchBlocked,'3 requests/provider/UTC day'):self.fetch()
            read.assert_not_called()
        self.assertEqual(len(self.calls),3);self.assertEqual(len(self.rows('local_requests')),3)

    def test_shared_cooldown_and_study_retry_after_survive_primary_switch(self):
        self.add();backup=self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        self.registry.promote('marketaux',backup)
        for source in ('shared','study'):
            with self.subTest(source=source):
                cooldown=self.root/(source+'-cooldown.json');study=self.root/(source+'-study.sqlite3')
                expiry=(self.now+timedelta(hours=3)).isoformat()
                if source=='shared':cooldown.write_text(json.dumps({'marketaux':expiry}))
                else:
                    with closing(__import__('sqlite3').connect(study)) as db:
                        db.execute('CREATE TABLE attempts(reserved_at TEXT,completed_at TEXT,status TEXT,cooldown_until TEXT)')
                        db.execute('INSERT INTO attempts VALUES (?,?,?,?)',((self.now-timedelta(days=2)).isoformat(),(self.now-timedelta(days=2)).isoformat(),'success',expiry));db.commit()
                file=cooldown if source=='shared' else study;before=file.read_bytes()
                service=LocalIngestionService(self.store,clock=lambda:self.now,cooldown_path=cooldown,study_path=study,transport=Mock())
                with patch.object(self.memory,'read_slot',wraps=self.memory.read_slot) as read:
                    with self.assertRaises(FetchBlocked):self.registry.fetch(service,'marketaux','technology',rights=RIGHTS,remaining=3,explicit=True)
                    read.assert_not_called();service.transport.assert_not_called()
                self.assertEqual(file.read_bytes(),before)
        self.assertEqual(self.rows('local_requests'),[])

    def test_concurrent_primary_changes_have_only_one_durable_primary(self):
        from concurrent.futures import ThreadPoolExecutor
        slots=[self.add(name='Concurrent '+str(i),key='AUTHORED-CONCURRENT-'+str(i),primary=False) for i in range(4)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda slot:self.registry.promote('marketaux',slot),slots))
        selected=[r for r in self.registry.rows('marketaux') if r['is_primary']]
        self.assertEqual(len(selected),1);self.assertIn(selected[0]['slot_id'],slots)
        self.assertEqual(self.calls,[])

    def test_401_marks_exact_version_invalid_but_403_and_429_do_not(self):
        for code in (401,403,429):
            with self.subTest(code=code):
                store=LocalNewsStore(self.root/(str(code)+'.sqlite3'));reg=NewsKeyRegistry(store)
                a=reg.add('finnhub','Main','AUTHORED-FIN-'+str(code),primary=True)
                b=reg.add('finnhub','Backup','AUTHORED-BACK-'+str(code),primary=False)
                transport=Mock(side_effect=APIError('auth',status=code,rate_headers={'Retry-After':'600'} if code==429 else {}))
                service=LocalIngestionService(store,transport=transport,clock=lambda:self.now,cooldown_path=self.root/'none.json',study_path=self.root/'none.sqlite3')
                result,_=reg.fetch(service,'finnhub','technology',symbol='NVDA',rights=RIGHTS,remaining=3,explicit=True)
                main=next(r for r in reg.rows('finnhub') if r['slot_id']==a)
                self.assertEqual(main['last_status'],'invalid' if code==401 else 'failed')
                reg.promote('finnhub',b)
                with self.assertRaises(FetchBlocked):reg.fetch(service,'finnhub','technology',symbol='NVDA',rights=RIGHTS,remaining=3,explicit=True)
                self.assertEqual(transport.call_count,1)

    def test_pending_requests_block_secret_mutation_and_switch_does_not_clear_unknown(self):
        a=self.add();b=self.add(name='Backup',key='AUTHORED-BACKUP',primary=False)
        self.service._reserve('marketaux',3,credential_resolver=lambda db,i:self.registry.resolve('marketaux',transaction=db,request_id=i))
        for action in (lambda:self.registry.replace('marketaux',a,'AUTHORED-NEW'),lambda:self.registry.enable('marketaux',a,False),lambda:self.registry.delete('marketaux',a,confirmed=True)):
            with self.assertRaises(NewsKeyError):action()
        self.registry.promote('marketaux',b)
        with self.assertRaises(FetchBlocked):self.fetch()
        self.assertEqual(self.calls,[]);self.assertEqual(self.rows('local_requests')[0][4],'pending')

    def test_absent_key_skips_source_but_other_permitted_source_still_completes(self):
        c=self.config(('finnhub','abs_html'));c['budgets'].pop('abs_html');c['source_permissions'].pop('abs_html')
        q=TaskQueue(self.store);q.configure(c);task,_=q.submit()
        worker=Worker(self.store,infer=prediction,resources=lambda *a,**k:None);actual=worker.fetch
        worker.fetch=lambda p,c,check:[fixture()] if p=='abs_html' else actual(p,c,check)
        with patch('finscope.local_worker.LocalIngestionService',return_value=self.service):worker.run_one()
        result=q.get(task);self.assertEqual(result['status'],'partial_failed');self.assertEqual(result['counts']['new'],1)
        self.assertEqual(self.calls,[]);self.assertEqual(self.rows('local_requests'),[])

    def test_metadata_and_task_free_text_reject_known_slot_secret(self):
        self.add();q=TaskQueue(self.store);q.configure(self.config())
        with self.assertRaises(NewsKeyError):self.add(name='AUTHORED-PRIMARY-KEY',key='AUTHORED-SECOND-KEY')
        c=self.config();c['source_permissions']['marketaux']['reference']='AUTHORED-PRIMARY-KEY'
        with self.assertRaises(ValueError):q.submit(c)
        self.assertEqual(self.rows('product_tasks'),[])

    def test_model_credentials_and_legacy_targets_cannot_be_deleted_by_news_api(self):
        self.memory.write('openai','AUTHORED-OPENAI');self.memory.write('deepseek','AUTHORED-DEEPSEEK')
        for p in ('openai','deepseek'):
            with self.assertRaises(NewsKeyError):self.registry.add(p,'No','AUTHORED-NEW')
            with self.assertRaises(NewsKeyError):self.registry.resolve(p,selection={'slot_id':LEGACY,'credential_ref':LEGACY})
        self.assertEqual(self.memory.read('openai'),'AUTHORED-OPENAI');self.assertEqual(self.memory.read('deepseek'),'AUTHORED-DEEPSEEK')


if __name__=='__main__':unittest.main()
