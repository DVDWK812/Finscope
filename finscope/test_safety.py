"""Fail-closed regression guards against accidental real test I/O.

Not a security sandbox for hostile Python/native code. Activated before test
discovery and inherited by Python subprocesses; no real credentials are loaded.
"""
import functools
import os
from pathlib import Path
import sys
import tempfile
import threading

PROJECT = Path(__file__).resolve().parents[1]
_root = None
_case = None
_memory = None
_temporary = None
_protected = ()
_checking = threading.local()


class TestIsolationError(RuntimeError):
    """A safe, credential-free diagnostic raised before real I/O."""


def requested():
    args = [str(v).lower() for v in getattr(sys, 'orig_argv', sys.argv)]
    return (bool(_root) or os.environ.get('FINSCOPE_TESTING') == '1'
            or any(v in ('unittest', 'pytest') or Path(v).name.startswith('test_') for v in args)
            or 'streamlit.testing.v1' in sys.modules or 'unittest.__main__' in sys.modules)


def active():
    activate_if_requested()
    return _root is not None


def _normal(path):
    return os.path.normcase(os.path.realpath(os.fsdecode(path)))


def _within(path, parent):
    return path == parent or path.startswith(parent + os.sep)


def require_test_path(path):
    if not active() or path == ':memory:':
        return
    if not _within(_normal(path), _normal(_root)):
        raise TestIsolationError('Test isolation blocked a path outside its temporary directory')


def forbid_system_credentials():
    if active():
        raise TestIsolationError('Test isolation blocked real Windows credential access before system API loading')


def case_directory():
    return _case if active() else None


def data_path(*parts):
    return (case_directory() or PROJECT).joinpath(*parts)


def fake_credentials():
    global _memory
    if not active():
        return None
    if _memory is None:
        from .credential_store import MemoryCredentialStore
        _memory = MemoryCredentialStore()
    return _memory


def _directory_fd_path(descriptor):
    for prefix in ('/proc/self/fd', '/dev/fd'):
        try:
            return os.readlink(prefix + '/' + str(descriptor))
        except OSError:
            pass
    raise TestIsolationError('Test isolation could not resolve a directory descriptor safely')


def _check_path(path, dir_fd=None):
    if not isinstance(path, (str, bytes, os.PathLike)) or path == ':memory:':
        return
    name = os.fsdecode(path)
    if dir_fd not in (None, -1) and not os.path.isabs(name):
        name = os.path.join(_directory_fd_path(dir_fd), name)
    if name.startswith('file:'):
        from urllib.parse import unquote, urlsplit
        parts = urlsplit(name)
        name = unquote(parts.path)
        if parts.netloc and parts.netloc != 'localhost':
            name = '//' + parts.netloc + name
        elif os.name == 'nt' and len(name) > 2 and name[0] == '/' and name[2] == ':':
            name = name[1:]
    normal = _normal(name)
    if _within(normal, _normal(_root)):
        return
    if (any(_within(normal, parent) for parent in _protected)
            or Path(normal).name == '.env' or Path(normal).suffix in ('.sqlite3', '.sqlite', '.db')):
        raise TestIsolationError('Test isolation blocked production credentials or data before filesystem access')


def _audit(event, args):
    if not _root or getattr(_checking, 'busy', False):
        return
    _checking.busy = True
    try:
        if event in ('open', 'sqlite3.connect', 'os.listdir', 'os.scandir', 'shutil.rmtree'):
            _check_path(args[0])
        elif event in ('os.remove', 'os.rmdir'):
            _check_path(args[0],args[1])
        elif event == 'os.mkdir':
            _check_path(args[0],args[2])
        elif event in ('os.rename', 'os.link'):
            _check_path(args[0],args[2]); _check_path(args[1],args[3])
        elif event == 'os.symlink':
            _check_path(args[0]); _check_path(args[1],args[2])
        elif event == 'ctypes.dlopen' and 'advapi32' in str(args[0]).lower():
            raise TestIsolationError('Test isolation blocked the Windows credential DLL before loading')
        elif event.startswith('ctypes.dlsym') and str(args[-1]).startswith(('CredRead', 'CredWrite', 'CredDelete', 'CredEnumerate')):
            raise TestIsolationError('Test isolation blocked a native credential symbol')
        elif event in ('socket.connect', 'socket.getaddrinfo'):
            # Windows asyncio builds its private wake-up socketpair using an
            # ephemeral loopback connection. This is not a provider connection.
            caller = sys._getframe(1)
            socketpair = (event == 'socket.connect' and caller.f_code.co_name == 'socketpair'
                          and caller.f_globals.get('__name__') == 'socket')
            if not socketpair:
                raise TestIsolationError('Test isolation blocked unmocked network access')
        elif event == 'subprocess.Popen':
            executable, command, cwd, env = args
            if cwd is not None: _check_path(cwd)
            child_env = os.environ if env is None else env
            if (child_env.get('FINSCOPE_TESTING') != '1'
                    or child_env.get('FINSCOPE_TEST_ROOT') != str(_root)
                    or str(PROJECT) not in child_env.get('PYTHONPATH', '').split(os.pathsep)):
                raise TestIsolationError('Test subprocess must inherit credential and data isolation')
            arguments = command if isinstance(command, (list, tuple)) else str(command).split()
            program = str(executable or (arguments[0] if arguments else '')).lower()
            if 'python' in program and any(str(v).strip('"') in ('-S', '-I', '-E') for v in arguments):
                raise TestIsolationError('Test subprocess cannot disable its isolation bootstrap')
    finally:
        _checking.busy = False


def _set_case(path):
    global _case
    _case = path
    path.mkdir(parents=True, exist_ok=True)
    (path / '.env').touch(exist_ok=True)
    os.environ['FINSCOPE_TEST_CASE'] = str(path)
    os.environ['FINSCOPE_LOCAL_DB'] = str(path / 'news.sqlite3')
    os.environ['FINSCOPE_DEMO_DB_PATH'] = str(path / 'demo.sqlite3')


def activate_if_requested(*, force=False):
    global _root, _case, _temporary, _protected
    if _root is not None or (not force and not requested()):
        return
    inherited = os.environ.get('FINSCOPE_TEST_ROOT')
    if inherited:
        candidate = Path(inherited).resolve()
        if not candidate.name.startswith('finscope-tests-') or not (candidate / '.finscope-test-root').is_file():
            raise TestIsolationError('Invalid inherited test isolation directory')
        _root = candidate
    else:
        _temporary = tempfile.TemporaryDirectory(prefix='finscope-tests-')
        _root = Path(_temporary.name).resolve()
        (_root / '.finscope-test-root').touch()
    roots = {PROJECT, (PROJECT / 'reports').resolve().parent}
    _protected = tuple(_normal(p / name) for p in roots for name in ('reports', 'models', 'evaluation', '.env'))
    os.environ['FINSCOPE_TESTING'] = '1'
    os.environ['FINSCOPE_TEST_ROOT'] = str(_root)
    paths = os.environ.get('PYTHONPATH', '').split(os.pathsep)
    os.environ['PYTHONPATH'] = os.pathsep.join(dict.fromkeys([str(PROJECT), *[p for p in paths if p]]))
    for name in ('MARKETAUX_API_KEY', 'NEWSDATA_API_KEY', 'FINNHUB_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
        os.environ.pop(name, None)
    tempfile.tempdir = str(_root)
    inherited_case = os.environ.get('FINSCOPE_TEST_CASE')
    _set_case(Path(inherited_case) if inherited_case and _within(_normal(inherited_case), _normal(_root)) else _root / 'session')
    sys.addaudithook(_audit)
    install_unittest_boundary()


def install_unittest_boundary():
    """Also cover programmatic unittest runners, without changing product mode."""
    import unittest
    original = unittest.TestCase.run
    if not getattr(original, '_finscope_isolated', False):
        @functools.wraps(original)
        def isolated_run(test, result=None):
            global _memory
            activate_if_requested(force=True)
            previous_case, previous_memory = _case, _memory
            _memory = None
            with tempfile.TemporaryDirectory(prefix='case-', dir=_root) as directory:
                _set_case(Path(directory))
                try:
                    return original(test, result)
                finally:
                    _memory = previous_memory
                    _set_case(previous_case)
        isolated_run._finscope_isolated = True
        unittest.TestCase.run = isolated_run
