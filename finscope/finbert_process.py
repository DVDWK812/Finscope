"""Task-owned, bounded FinBERT process. Text travels over pipes, never files."""
import json
import math
import queue
import subprocess
import sys
import threading
import time

from .model_assets import manifest


class ProcessFinBERT:
    module="finscope.finbert_process"

    def __init__(self, *, check=lambda: None, timeout=120, observe=lambda edge:None):
        self.manifest=manifest('finbert');self.check=check;self.timeout=timeout
        self.process=None;self.responses=queue.Queue();self.reader=None;self.calls=0;self.observe=observe;self.closed=False;self.exit_verified=False

    @property
    def pid(self):return self.process.pid if self.process else None

    @property
    def alive(self):return self.process is not None and self.process.poll() is None

    def _read(self):
        try:
            while True:
                line=self.process.stdout.readline(1024*1024+1)
                self.responses.put(line)
                if not line or len(line)>1024*1024:return
        except (OSError,ValueError):self.responses.put('')

    def predict(self,texts):
        try:return self._predict(texts)
        except BaseException:
            self.close();raise

    def _predict(self,texts):
        if not isinstance(texts,list) or len(texts)!=1 or not isinstance(texts[0],str) or not 0<len(texts[0])<=2000:
            raise ValueError('Bounded single-text FinBERT input required')
        data=self.exchange(texts)
        if data['model_id']!=self.manifest['model_id'] or data['revision']!=self.manifest['revision']:raise ValueError('Pinned model mismatch')
        scores=data['scores']
        if len(scores)!=1 or set(scores[0])!={'positive','negative','neutral'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in scores[0].values()) or abs(sum(scores[0].values())-1)>.001:
            raise ValueError('Invalid FinBERT scores')
        return scores

    def exchange(self,texts):
        self.check()
        if self.closed:raise ValueError('Owned model process is closed')
        if self.calls>=600:raise ValueError('Task inference limit reached')
        if self.process is None:
            self.observe('before_load')
            self.process=subprocess.Popen([sys.executable,'-m',self.module,'--persistent'],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()
        try:
            self.calls+=1
            self.process.stdin.write(json.dumps({'texts':texts})+'\n');self.process.stdin.flush()
            deadline=time.monotonic()+self.timeout
            while True:
                self.check()
                if time.monotonic()>=deadline:raise TimeoutError('Owned model inference timed out')
                try:line=self.responses.get(timeout=.1);break
                except queue.Empty:continue
            if not line or len(line)>1024*1024:raise ValueError('Owned model process failed')
            data=json.loads(line)
            self.observe('resident')
            return data
        except BaseException:
            self.close();raise

    def close(self):
        process=self.process
        if process is None or self.closed:return
        # Windows venv launchers may own a separate Python child. Track only
        # descendants of our Popen handle, never processes selected by name.
        import psutil
        try:descendants=psutil.Process(process.pid).children(recursive=True) if process.poll() is None else []
        except psutil.NoSuchProcess:descendants=[]
        try:process.stdin.close()
        except (OSError,ValueError):pass
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
        _,remaining=psutil.wait_procs(descendants,timeout=2)
        for child in remaining:
            try:child.terminate()
            except psutil.NoSuchProcess:pass
        _,remaining=psutil.wait_procs(remaining,timeout=2)
        for child in remaining:
            try:child.kill()
            except psutil.NoSuchProcess:pass
        _,remaining=psutil.wait_procs(remaining,timeout=2)
        if self.reader:self.reader.join(timeout=2)
        if not self.reader or not self.reader.is_alive():process.stdout.close()
        self.exit_verified=process.poll() is not None and not remaining and (not self.reader or not self.reader.is_alive())
        self.closed=True
        self.observe('exited')
        if not self.exit_verified:raise RuntimeError('Owned model exit could not be verified')


def main():
    backend=None
    try:
        for _ in range(600):
            line=sys.stdin.readline(20000)
            if not line:return 0
            data=json.loads(line);texts=data['texts']
            if set(data)!={'texts'} or not isinstance(texts,list) or len(texts)!=1 or not isinstance(texts[0],str) or not 0<len(texts[0])<=2000:raise ValueError()
            if backend is None:
                from .finbert_backend import LocalFinBERTBackend
                from .model_assets import model_directory
                backend=LocalFinBERTBackend.from_snapshot(model_directory('finbert'),accept_weight_license=True)
            scores=backend.predict(texts)
            print(json.dumps(dict(scores=scores,model_id=backend.manifest['model_id'],revision=backend.manifest['revision'])),flush=True)
        return 0
    except Exception:return 2


if __name__=='__main__':raise SystemExit(main())
