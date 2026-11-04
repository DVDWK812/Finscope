import hashlib,tempfile,unittest,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from finscope import model_assets as assets
from finscope.model_preparation import Preparation
from finscope import bootstrap

class InstallationTests(unittest.TestCase):
 def test_platform_python_disk_and_unicode_path(self):
  with tempfile.TemporaryDirectory(prefix='FinScope 中文 space ') as d:
   with patch.object(bootstrap.sys,'platform','win32'),patch.object(bootstrap.platform,'machine',return_value='AMD64'),patch.object(bootstrap.sys,'version_info',(3,12)),patch.object(bootstrap.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)):
    self.assertTrue(bootstrap.preflight(Path(d))['root_writable'])
    with patch.object(bootstrap.sys,'version_info',(3,13)):
     with self.assertRaises(RuntimeError):bootstrap.preflight(Path(d))
    with patch.object(bootstrap.shutil,'disk_usage',return_value=SimpleNamespace(free=1)):
     with self.assertRaises(RuntimeError):bootstrap.preflight(Path(d))
 def test_install_arguments_support_zip_path_and_repeat_existing_env(self):
  with tempfile.TemporaryDirectory(prefix='ZIP 中文 space ') as d:
   root=Path(d);calls=[]
   def run(args,**kw):
    calls.append(args)
    if 'venv' in args:
     target=root/'.venv-ai/Scripts';target.mkdir(parents=True);(target/'python.exe').touch()
   with patch.object(bootstrap,'preflight'):
    bootstrap.install(root,run);bootstrap.install(root,run)
   self.assertEqual(sum('venv' in a for a in calls),1)
   self.assertEqual(sum('pip' in a and 'install' in a for a in calls),2)
   self.assertTrue((root/'.venv-ai/finscope-installed.json').exists())
 def test_failed_dependencies_do_not_mark_installed(self):
  with tempfile.TemporaryDirectory() as d,patch.object(bootstrap,'preflight'):
   root=Path(d)
   with self.assertRaises(RuntimeError):bootstrap.install(root,Mock(side_effect=RuntimeError('missing dependency')))
   self.assertFalse((root/'.venv-ai/finscope-installed.json').exists())

class PreparationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  data=b'authored model bytes';self.data=data
  self.spec={'model_id':'test/authored','revision':'fixed','files':{'weights':{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}}}
  for p in (patch.object(assets,'manifest',return_value=self.spec),patch.object(assets,'model_directory',side_effect=lambda k:self.root/k/'fixed')):
   p.start();self.addCleanup(p.stop)
 def response(self,chunks):
  r=Mock();r.iter_content.return_value=iter(chunks);return r
 def test_interruption_recovery_and_verified_reuse(self):
  bad=self.response([self.data[:4]]);good=lambda *a,**k:self.response([self.data])
  with patch('requests.get',return_value=bad):
   with self.assertRaises(ValueError):assets.prepare_models(acknowledge_licenses=True)
  self.assertFalse(assets.assets_present('finbert'))
  with patch('requests.get',side_effect=good) as http:assets.prepare_models(acknowledge_licenses=True);self.assertEqual(http.call_count,2)
  with patch('requests.get',side_effect=AssertionError('No redownload')):assets.prepare_models(acknowledge_licenses=True)
  self.assertTrue(assets.assets_present('finbert'))
  target=assets.model_directory('finbert')/'weights';target.write_bytes(b'x'*len(self.data))
  self.assertFalse(assets.assets_present('finbert'))
 def test_cancel_and_cross_process_mutex(self):
  with patch('requests.get',side_effect=AssertionError('No HTTP')):
   with self.assertRaises(assets.PreparationCancelled):assets.prepare_models(acknowledge_licenses=True,cancelled=lambda:True)
  from finscope.task_queue import ProcessLock
  with ProcessLock(assets.model_directory('finbert').parents[1]/'.prepare.lock'):
   with self.assertRaises(RuntimeError):assets.prepare_models(acknowledge_licenses=True)
 def test_cancel_midstream_closes_response_and_no_valid_model(self):
  stop=threading.Event();response=self.response([self.data[:2],self.data[2:]])
  with patch('requests.get',return_value=response):
   with self.assertRaises(assets.PreparationCancelled):assets.prepare_models(acknowledge_licenses=True,progress=lambda **kw:stop.set(),cancelled=stop.is_set)
  response.close.assert_called_once();self.assertFalse(assets.assets_present('finbert'))
 def test_double_click_and_restart_reuses_verified_files(self):
  started=threading.Event();release=threading.Event();task=Preparation()
  def prepare(**kw):started.set();release.wait(2)
  with patch('finscope.model_preparation.prepare_models',side_effect=prepare) as fn:
   self.assertTrue(task.start(True));started.wait(1);self.assertFalse(task.start(True));release.set();task.thread.join(3)
   self.assertEqual(fn.call_count,1);self.assertEqual(task.snapshot()['status'],'verified')
  with self.assertRaises(ValueError):task.start(False)

if __name__=='__main__':unittest.main()

class InstallationUITests(unittest.TestCase):
 def test_settings_preparation_never_downloads_on_render(self):
  from streamlit.testing.v1 import AppTest
  code="""from finscope.model_preparation import controls
controls('installation_acceptance')
"""
  with patch('requests.get',side_effect=AssertionError('No implicit download')):
   app=AppTest.from_string(code).run()
   self.assertFalse(app.exception)
   self.assertTrue(app.button(key='installation_acceptance_start').disabled)
   app.checkbox(key='installation_acceptance_licenses').check().run()
   self.assertFalse(app.button(key='installation_acceptance_start').disabled)
 def test_lmstudio_selfcheck_uses_memory_sink_and_preserves_loaded_model(self):
  from finscope.model_selfcheck import check
  from finscope.local_news import LocalNewsStore
  from test_lmstudio import LocalTransport,KEYS
  from finscope.model_providers import LMStudioProvider
  with tempfile.TemporaryDirectory() as d,patch('finscope.local_worker.resource_check'):
   store=LocalNewsStore(Path(d)/'isolated.sqlite3');transport=LocalTransport()
   result=check(KEYS[0],store,LMStudioProvider(transport))
   self.assertEqual(result['status'],'actual inference passed')
   self.assertEqual(store.list_analyses(),[])
   self.assertEqual(transport.loaded,KEYS[0])
   self.assertFalse(any('unload' in call[1] for call in transport.calls))
