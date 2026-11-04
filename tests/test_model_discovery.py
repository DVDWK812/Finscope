import threading,unittest
from unittest.mock import Mock,patch
from finscope.model_discovery import Discovery,sync_session
from finscope.model_providers import ModelError,LMStudioProvider
from finscope.batch_timing import Timing,Measured

class DiscoveryTests(unittest.TestCase):
 def test_concurrent_sessions_reruns_and_selection(self):
  inventory=Mock(return_value={'actual/key':{'loaded':False,'callable':False}});d=Discovery(inventory)
  threads=[threading.Thread(target=d.ensure_started) for _ in range(20)]
  for t in threads:t.start()
  for t in threads:t.join()
  d.thread.join(2)
  with patch('finscope.model_discovery.discovery',d):
   for _ in range(5):
    state={'pipeline_lmstudio_model':'saved/selection'};sync_session(state)
    self.assertEqual(state['pipeline_lmstudio_model'],'saved/selection')
  self.assertEqual(inventory.call_count,1);self.assertIsNotNone(d.snapshot()['checked_at'])
  d.refresh();self.assertEqual(inventory.call_count,2)
  restarted=Discovery(inventory);restarted.ensure_started();restarted.thread.join(2);self.assertEqual(inventory.call_count,3)
 def test_failures_empty_and_stale_are_distinct(self):
  d=Discovery(lambda:{'old':{}});d.refresh()
  for error,status in [(ModelError('auth',status=401),'authentication_failed'),(ModelError('off',kind='connection_refused'),'service_not_running'),(ModelError('slow',kind='timeout'),'timeout')]:
   d.inventory=Mock(side_effect=error);d.refresh()
   self.assertEqual(d.snapshot()['status'],status);self.assertTrue(d.snapshot()['stale']);self.assertIn('old',d.snapshot()['models'])
   with patch('finscope.model_discovery.discovery',d):
    s={};sync_session(s);self.assertFalse(s['lmstudio_connected']);self.assertIn('OLD RESULT',s['lmstudio_status'])
  d.inventory=lambda:{};d.refresh();self.assertEqual(d.snapshot()['status'],'empty');self.assertFalse(d.snapshot()['stale'])
 def test_read_only_native_loaded_state(self):
  from test_lmstudio import LocalTransport,KEYS
  transport=LocalTransport();transport.loaded=None
  d=Discovery(LMStudioProvider(transport).inventory);d.refresh()
  self.assertTrue(d.snapshot()['models']);self.assertTrue(all(not m['loaded'] for m in d.snapshot()['models'].values()))
  self.assertTrue(all(c[0]=='GET' for c in transport.calls))

class TimingTests(unittest.TestCase):
 def test_nested_exclusive_times_and_failed_calls(self):
  tick=[0.];timer=Timing(lambda:tick[0]);timer.set_queue_wait(None)
  def child():tick[0]+=2;raise ValueError('authored')
  def parent():
   tick[0]+=1
   with self.assertRaises(ValueError):timer.call('model_state',child)
   tick[0]+=3
  timer.call('database_and_storage',parent);report=timer.report(None)
  self.assertEqual(report['exclusive_seconds'],{'model_state':2.,'database_and_storage':4.})
  self.assertEqual(report['execution_seconds'],6.)
 def test_cache_classification_and_database_buckets(self):
  timer=Timing();timer.set_queue_wait(None);target=Mock();obj=Measured(target,timer)
  obj.cached('id','key');obj.classification('id','key');obj.state('id','completed')
  self.assertEqual(timer.calls['cache_lookup'],2);self.assertEqual(timer.calls['database_and_storage'],1)
