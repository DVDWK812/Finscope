"""No per-test vault patch: omissions must remain safe by default."""
import ctypes
from contextlib import redirect_stdout, closing
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from finscope import test_safety as safety
from finscope.credential_store import PROVIDERS, MemoryCredentialStore
from finscope.local_credentials import credential, credential_store, environment_credentials, project_env_path, save_credential
from finscope.windows_credentials import WindowsCredentialStore


class CredentialIsolationTests(unittest.TestCase):
    def test_discovery_default_is_empty_memory_and_temporary_env(self):
        self.assertTrue(safety.active())
        self.assertIsInstance(credential_store(), MemoryCredentialStore)
        self.assertEqual(environment_credentials(), {})
        safety.require_test_path(project_env_path())
        self.assertNotEqual(project_env_path(), safety.PROJECT / '.env')
        self.assertTrue(all(not credential(p) for p in PROVIDERS))

    def test_plain_project_discovery_finds_protected_tests_without_start_directory_flags(self):
        suite = unittest.TestLoader().discover(str(safety.PROJECT),pattern='test_credential_isolation.py')
        self.assertGreater(suite.countTestCases(),0)

    def test_automatic_case_scopes_reset_fake_keys_without_touching_outer_case(self):
        save_credential('marketaux','AUTHORED-OUTER')
        class First(unittest.TestCase):
            def runTest(inner):
                inner.assertEqual(credential('marketaux'),'')
                save_credential('marketaux','AUTHORED-INNER')
        class Second(unittest.TestCase):
            def runTest(inner):inner.assertEqual(credential('marketaux'),'')
        result=unittest.TestResult();unittest.TestSuite([First(),Second()]).run(result)
        self.assertTrue(result.wasSuccessful(),result.errors)
        self.assertEqual(credential('marketaux'),'AUTHORED-OUTER')

    def test_omitted_mock_is_blocked_before_native_loader_or_any_api(self):
        api = Mock()
        with patch('finscope.windows_credentials.c.WinDLL', create=True, return_value=api) as loader:
            for action in (lambda: WindowsCredentialStore().read('marketaux'),
                           lambda: WindowsCredentialStore().write('marketaux', 'AUTHORED-TEST-ONLY')):
                with self.assertRaisesRegex(safety.TestIsolationError, 'before system API'):
                    action()
        loader.assert_not_called()
        api.CredReadW.assert_not_called(); api.CredWriteW.assert_not_called()
        api.CredDeleteW.assert_not_called(); api.CredEnumerateW.assert_not_called()

    def test_direct_unmocked_dll_access_is_also_blocked_before_loading(self):
        with self.assertRaisesRegex(safety.TestIsolationError, 'before loading'):
            ctypes.CDLL('Advapi32')

    def test_env_and_production_database_paths_fail_before_file_or_sql_access(self):
        from finscope.local_news import LocalNewsStore
        with patch('finscope.local_credentials.environment_credentials', wraps=environment_credentials):
            with self.assertRaises(safety.TestIsolationError):
                environment_credentials(safety.PROJECT / '.env', reader=Mock())
        for action in (lambda: (safety.PROJECT / '.env').read_bytes(),
                       lambda: sqlite3.connect(safety.PROJECT / 'reports/finscope_local.sqlite3'),
                       lambda: LocalNewsStore(safety.PROJECT / 'reports/finscope_local.sqlite3'),
                       lambda: os.scandir(safety.PROJECT / 'reports'),
                       lambda: os.remove(safety.PROJECT / 'reports/never-delete.sqlite3')):
            with self.assertRaises(safety.TestIsolationError): action()

    def test_aliases_to_production_data_are_not_allowed(self):
        # Existing workspace junctions resolve to the same protected root. No
        # junction/symlink is created and no production content is opened.
        target = (safety.PROJECT / 'reports').resolve() / 'finscope_local.sqlite3'
        with self.assertRaises(safety.TestIsolationError): target.read_bytes()
        with self.assertRaises(safety.TestIsolationError):
            sqlite3.connect('file:' + str(target) + '?mode=ro', uri=True)

    def test_temporary_sqlite_file_uri_is_allowed_without_allowing_production_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'authored.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE authored(id INTEGER)'); db.commit()
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM authored').fetchone()[0],0)

    def test_directory_relative_cleanup_resolves_temporary_path_and_still_blocks_production(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'.env';target.write_text('AUTHORED_ONLY=YES')
            if os.name=='posix':
                descriptor=os.open(directory,os.O_RDONLY)
                try:os.unlink('.env',dir_fd=descriptor)
                finally:os.close(descriptor)
                self.assertFalse(target.exists())
            with patch('finscope.test_safety._directory_fd_path',return_value=directory):
                safety._audit('os.remove',('.env',123))
                with self.assertRaises(safety.TestIsolationError):
                    safety._audit('os.remove',(str(safety.PROJECT/'.env'),123))

    def test_provider_fake_keys_and_literal_env_do_not_override_each_other(self):
        project_env_path().write_text('OPENAI_API_KEY=AUTHORED-ENV-OPENAI\nFINNHUB_API_KEY=AUTHORED-ENV-FINNHUB\n', encoding='utf-8')
        for provider in PROVIDERS: save_credential(provider, 'AUTHORED-VAULT-' + provider)
        save_credential('marketaux', 'AUTHORED-CHANGED-MARKETAUX')
        self.assertEqual(credential('marketaux'), 'AUTHORED-CHANGED-MARKETAUX')
        for p in PROVIDERS[1:]: self.assertEqual(credential(p), 'AUTHORED-VAULT-' + p)
        self.assertEqual(environment_credentials()['OPENAI_API_KEY'], 'AUTHORED-ENV-OPENAI')
        self.assertNotIn('AUTHORED', repr(credential_store()))

    def test_diagnostics_and_failures_never_load_native_api_or_echo_fake_secrets(self):
        from finscope.connection_diagnostics import credential_report
        secret = 'AUTHORED-SECRET-NOT-FOR-OUTPUT'
        save_credential('openai', secret)
        stream = io.StringIO()
        with patch('finscope.windows_credentials.c.WinDLL', create=True) as loader, redirect_stdout(stream):
            result = credential_report('openai')
            with self.assertRaises(ValueError) as error: save_credential('unknown', secret)
        self.assertTrue(result['present']); self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn(secret, str(error.exception)); self.assertNotIn(secret, stream.getvalue())
        loader.assert_not_called()

    def test_python_subprocess_inherits_guards_even_from_another_working_directory(self):
        code = '''
import json
from unittest.mock import Mock,patch
from finscope import test_safety as s
from finscope.local_credentials import credential,project_env_path
from finscope.windows_credentials import WindowsCredentialStore
with patch('finscope.windows_credentials.c.WinDLL',create=True) as native:
    try: WindowsCredentialStore().write('marketaux','AUTHORED-CHILD-KEY')
    except s.TestIsolationError: blocked=True
    else: blocked=False
    print(json.dumps({'active':s.active(),'blocked':blocked,'native_calls':native.call_count,'empty':not credential('marketaux')}))
'''
        save_credential('marketaux', 'AUTHORED-PARENT-ONLY')
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-c', code], cwd=folder, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'active':True,'blocked':True,'native_calls':0,'empty':True})
        self.assertEqual(credential('marketaux'), 'AUTHORED-PARENT-ONLY')

    def test_subprocess_cannot_silently_drop_bootstrap_or_ignore_site(self):
        for kwargs, flags in (({'env':{}}, []), ({}, ['-S']), ({}, ['-I'])):
            with self.assertRaises(safety.TestIsolationError):
                subprocess.run([sys.executable,*flags,'-c','raise AssertionError("Must not run")'], **kwargs)

    def test_reset_and_cleanup_only_dispose_fake_state(self):
        # A simulated production API sentinel is never consulted or changed.
        production = {'FinScope local / marketaux':'SIMULATED-PRODUCTION-VALUE'}
        api = Mock(); api.entries = dict(production)
        with patch('finscope.windows_credentials.c.WinDLL', create=True, return_value=api):
            first = MemoryCredentialStore(); first.write('marketaux','AUTHORED-EPHEMERAL')
            del first
            self.assertEqual(MemoryCredentialStore().read('marketaux'), '')
        self.assertEqual(api.entries, production)
        api.CredReadW.assert_not_called(); api.CredWriteW.assert_not_called(); api.CredDeleteW.assert_not_called()

    def test_native_credential_symbols_exist_only_in_adapter(self):
        for path in (safety.PROJECT / 'finscope').glob('*.py'):
            if path.name in ('windows_credentials.py','test_safety.py'): continue
            text = path.read_text(encoding='utf-8')
            self.assertFalse(any(name in text for name in ('CredReadW','CredWriteW','CredDeleteW','CredEnumerateW')),path.name)


class CredentialUIIsolationTests(unittest.TestCase):
    def test_save_and_modify_key_without_vault_patches_only_changes_memory(self):
        from streamlit.testing.v1 import AppTest
        from finscope.local_news import LocalNewsStore
        store = LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']); store.set_setting('guide_completed', True)
        with patch('finscope.windows_credentials.c.WinDLL', create=True) as native:
            app = AppTest.from_file(str(safety.PROJECT / 'streamlit_app.py'), default_timeout=20)
            app.session_state['product_page'] = 'Settings'; app.run()
            app.multiselect(key='settings_sources').set_value(['marketaux']).run()
            app.button(key='settings_edit_marketaux').click().run()
            for value in ('AUTHORED-UI-FIRST', 'AUTHORED-UI-REPLACEMENT'):
                app.button(key='settings_secret_marketaux_edit').click().run()
                app.text_input(key='settings_secret_marketaux').set_value(value).run()
                app.button(key='settings_secret_marketaux_save').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(credential('marketaux'), value)
                self.assertNotIn('settings_secret_marketaux', app.session_state)
            self.assertNotIn(b'AUTHORED-UI',store.path.read_bytes())
            native.assert_not_called()

    def test_key_save_error_redacts_exception_and_keeps_fake_existing_value(self):
        from streamlit.testing.v1 import AppTest
        from finscope.local_news import LocalNewsStore
        store = LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']); store.set_setting('guide_completed', True)
        save_credential('marketaux', 'AUTHORED-PRIOR-KEY')
        app = AppTest.from_file(str(safety.PROJECT / 'streamlit_app.py'), default_timeout=20)
        app.session_state['product_page']='Settings'; app.run()
        app.multiselect(key='settings_sources').set_value(['marketaux']).run()
        app.button(key='settings_edit_marketaux').click().run()
        app.button(key='settings_secret_marketaux_edit').click().run()
        app.text_input(key='settings_secret_marketaux').set_value('AUTHORED-NEW-KEY').run()
        with patch.object(credential_store(), 'write', side_effect=ValueError('AUTHORED-NEW-KEY')):
            app.button(key='settings_secret_marketaux_save').click().run()
        self.assertFalse(app.exception); self.assertEqual(credential('marketaux'),'AUTHORED-PRIOR-KEY')
        self.assertTrue(app.error); self.assertFalse(any('AUTHORED' in e.value for e in app.error))


if __name__ == '__main__': unittest.main()
