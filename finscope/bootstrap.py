"""Windows first install. Standard library only; no provider/model imports."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def preflight(root=ROOT):
    if sys.platform!='win32' or platform.machine().lower() not in ('amd64','x86_64') or sys.maxsize<=2**32:
        raise RuntimeError('Use Windows x64 and 64-bit Python 3.11 or 3.12')
    if sys.version_info[:2] not in ((3,11),(3,12)):
        raise RuntimeError('Validated Python versions: 3.11 (CI), 3.12 (local model runtime)')
    with tempfile.TemporaryFile(dir=root):pass
    free=shutil.disk_usage(root).free
    if free<8*1024**3:raise RuntimeError('At least 8 GiB free disk space required for environment and base models')
    return {'python':platform.python_version(),'free_gib':round(free/1024**3,2),'root_writable':True}


def dependency_check():
    import streamlit,torch,transformers,safetensors,tokenizers,requests,pandas,dotenv,psutil
    from .finbert_backend import runtime_versions
    runtime_versions()


def install(root=ROOT,run=subprocess.run):
    preflight(root)
    from .task_queue import ProcessLock
    with ProcessLock(root/'.install.lock'):
        env=root/'.venv-ai';python=env/'Scripts/python.exe'
        if not python.exists():run([sys.executable,'-m','venv',str(env)],check=True)
        # Re-enter the created interpreter: an interrupted pip run is safely repeatable.
        run([str(python),'-m','pip','install','-r',str(root/'requirements-install.txt')],cwd=root,check=True)
        run([str(python),'-m','pip','check'],cwd=root,check=True)
        run([str(python),'-m','finscope.bootstrap','--check-dependencies'],cwd=root,check=True)
        (env/'finscope-installed.json').write_text(json.dumps({'python':platform.python_version(),'requirements':'requirements-install.txt'}))
    return python


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--check-dependencies',action='store_true')
    args=parser.parse_args()
    if args.check_dependencies:dependency_check()
    elif args.check:print(json.dumps(preflight()))
    else:install()
