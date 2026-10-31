import concurrent.futures
from contextlib import closing
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch,Mock
from finscope.local_news import LocalNewsStore
from finscope.lmstudio_runtime import start_service,model_operation
from finscope.model_providers import ModelError,LMStudioProvider
from finscope.task_queue import TaskQueue
from test_lmstudio import LocalTransport,KEYS
from test_product_pipeline import C


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'news.sqlite3');TaskQueue(self.store)
        self.http=LocalTransport();self.http.loaded=None;self.commands=[];self.online=False
    def runner(self,args,timeout):
        self.commands.append(args)
        if args==['--version']:return 'CLI commit: 43d4b26'
        if args[-1]=='--help':return '--bind <address> --port <port>'
        self.online=True;return 'Server starting'
    def transport(self,*args):
        if not self.online:raise ModelError('Refused',kind='connection_refused')
        return self.http(*args)
    def start(self,**options):
        return start_service(self.store,explicit=True,runner=self.runner,transport=self.transport,occupied=lambda:False,sleep=lambda _:None,**options)
    def test_running_service_is_reused_without_cli_or_loading(self):
        self.online=True;r=self.start()
        self.assertFalse(r['started']);self.assertEqual(r['checks'],1);self.assertEqual(self.commands,[])
        self.assertEqual(set(r['models']),set(KEYS));self.assertTrue(all(not m['loaded'] for m in r['models'].values()))
        self.assertTrue(all(c[0]=='GET' and c[1].startswith('http://127.0.0.1:1234/') for c in self.http.calls))
    def test_cold_service_waits_for_valid_native_and_compatible_lists(self):
        r=self.start();self.assertTrue(r['started']);self.assertEqual(r['cli_version'],'CLI 43d4b26')
        self.assertEqual(self.commands[-1],['server','start','--bind','127.0.0.1','--port','1234'])
        self.assertEqual(len(self.commands),3);self.assertEqual(set(r['models']),set(KEYS))
        self.assertFalse(any(x in str(self.commands) for x in ('download','get','load','cors','0.0.0.0','auth')))
    def test_successful_cli_exit_does_not_imply_api_ready_and_health_is_bounded(self):
        calls=[]
        def offline(*args):calls.append(args);raise ModelError('Refused',kind='connection_refused')
        with self.assertRaises(ModelError) as caught:
            start_service(self.store,explicit=True,runner=self.runner,transport=offline,occupied=lambda:False,sleep=lambda _:None,max_checks=4)
        self.assertEqual(caught.exception.kind,'startup_timeout');self.assertEqual(len(calls),4)
    def test_initial_timeout_on_unoccupied_port_still_allows_explicit_start(self):
        def transport(*args):
            if not self.online:raise ModelError('Timeout before a service is listening',kind='timeout')
            return self.http(*args)
        report=start_service(self.store,explicit=True,runner=self.runner,transport=transport,occupied=lambda:False)
        self.assertTrue(report['started']);self.assertEqual(len(self.commands),3)
    def test_busy_port_is_never_stopped_or_rebound(self):
        with self.assertRaises(ModelError) as caught:
            start_service(self.store,explicit=True,runner=self.runner,transport=self.transport,occupied=lambda:True)
        self.assertEqual(caught.exception.kind,'port_conflict');self.assertEqual(self.commands,[])
    def test_authentication_and_wrong_api_never_launch_cli(self):
        for status,kind in ((401,'authentication'),(403,'authentication'),(404,'port_conflict')):
            with self.subTest(status=status),self.assertRaises(ModelError) as caught:
                start_service(self.store,explicit=True,runner=self.runner,transport=Mock(side_effect=ModelError('Redacted',status=status,kind='http_error')))
            self.assertEqual(caught.exception.kind,kind)
        self.assertEqual(self.commands,[])
    def test_empty_valid_catalog_and_invalid_registry_are_distinct(self):
        def empty(m,u,*a):return {'models':[]} if '/api/' in u else {'data':[]}
        self.assertEqual(start_service(self.store,explicit=True,transport=empty)['models'],{})
        def malformed(m,u,*a):return {'models':'invalid'} if '/api/' in u else {'data':[]}
        with self.assertRaises(ModelError) as caught:start_service(self.store,explicit=True,transport=malformed)
        self.assertEqual(caught.exception.kind,'invalid_registry')
    def test_cli_missing_and_unsupported_binding_are_specific_errors(self):
        with self.assertRaises(ModelError) as caught:
            start_service(self.store,explicit=True,transport=self.transport,occupied=lambda:False,runner=Mock(side_effect=ModelError('CLI absent',kind='cli_missing')))
        self.assertEqual(caught.exception.kind,'cli_missing')
        with self.assertRaises(ModelError) as caught:
            start_service(self.store,explicit=True,transport=self.transport,occupied=lambda:False,runner=lambda *a:'old CLI')
        self.assertEqual(caught.exception.kind,'unsupported_cli')
    def test_cli_failure_uses_only_installed_runtime_fallback_once(self):
        bootstrap=Mock();attempts=[]
        def runner(args,timeout):
            if args[:2]==['server','start'] and '--help' not in args:
                attempts.append(args)
                if len(attempts)==1:raise ModelError('No runtime',kind='load_error')
            return self.runner(args,timeout)
        r=start_service(self.store,explicit=True,runner=runner,bootstrap=bootstrap,transport=self.transport,occupied=lambda:False)
        self.assertTrue(r['started']);bootstrap.assert_called_once_with();self.assertEqual(len(attempts),2)
    def test_timeout_unknown_startup_does_not_start_a_second_runtime(self):
        bootstrap=Mock();calls=[]
        def runner(args,timeout):
            calls.append(args)
            if '--help' not in args and args[0]=='server':raise ModelError('CLI timed out',kind='timeout')
            return self.runner(args,timeout)
        with self.assertRaises(ModelError):
            start_service(self.store,explicit=True,runner=runner,bootstrap=bootstrap,transport=self.transport,occupied=lambda:False,sleep=lambda _:None,max_checks=3)
        bootstrap.assert_not_called();self.assertEqual(len(calls),3)
    def test_multi_tab_mutex_prevents_double_start(self):
        entered=threading.Event();release=threading.Event()
        def runner(args,timeout):
            if args[0]=='--version':entered.set();release.wait(5)
            return self.runner(args,timeout)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            first=pool.submit(start_service,self.store,explicit=True,runner=runner,transport=self.transport,occupied=lambda:False)
            self.assertTrue(entered.wait(3))
            with self.assertRaises(ModelError) as caught:self.start()
            self.assertEqual(caught.exception.kind,'startup_busy');release.set();self.assertTrue(first.result()['started'])
        self.assertEqual(sum(c[0]=='server' and '--help' not in c for c in self.commands),1)
    def test_worker_active_blocks_backend_model_changes_before_any_probe(self):
        q=TaskQueue(self.store);q.submit(C)
        for action in ('load','unload'):
            with self.assertRaises(ModelError) as caught:getattr(LMStudioProvider(self.http),action)(KEYS[0],explicit=True,store=self.store)
            self.assertEqual(caught.exception.kind,'worker_owns_model')
        self.assertEqual(self.http.calls,[])
    def test_inference_and_load_share_a_cross_process_lock(self):
        from finscope.task_queue import ProcessLock
        with ProcessLock(str(self.store.path)+'.lmstudio-operation.lock'):
            with self.assertRaises(ModelError) as caught:model_operation(self.store,lambda:None)
        self.assertEqual(caught.exception.kind,'model_busy')
    def test_explicit_action_is_required(self):
        with self.assertRaises(ModelError):start_service(self.store,runner=self.runner,transport=self.transport)
        self.assertEqual(self.commands,[]);self.assertEqual(self.http.calls,[])


if __name__=='__main__':unittest.main()
