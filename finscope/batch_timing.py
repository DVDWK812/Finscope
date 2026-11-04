"""Exclusive metric-only durations, with nesting removed from parent buckets."""
from collections import defaultdict
from datetime import datetime,timezone
from time import perf_counter


class Timing:
    def __init__(self,clock=perf_counter):
        self.clock=clock;self.start=clock();self.seconds=defaultdict(float);self.calls=defaultdict(int);self.stack=[]
    def call(self,name,fn,*args,**kwargs):
        frame=[self.clock(),0.];self.stack.append(frame)
        try:return fn(*args,**kwargs)
        finally:
            elapsed=self.clock()-frame[0];self.stack.pop()
            self.seconds[name]+=max(0.,elapsed-frame[1]);self.calls[name]+=1
            if self.stack:self.stack[-1][1]+=elapsed
    def report(self,created):
        elapsed=self.clock()-self.start
        return {'execution_seconds':round(elapsed,6),'exclusive_seconds':{k:round(v,6) for k,v in self.seconds.items()},
                'calls':dict(self.calls),'other_seconds':round(max(0.,elapsed-sum(self.seconds.values())),6),
                'queue_wait_seconds':self.queue_wait,
                'scope':'This attempt only; queue wait is created-to-dispatch and may include intentional waiting; uninstrumented work is other'}
    def set_queue_wait(self,created):
        try:self.queue_wait=max(0.,(datetime.now(timezone.utc)-datetime.fromisoformat(created)).total_seconds())
        except (ValueError,TypeError):self.queue_wait=None


class Measured:
    def __init__(self,target,timing):self.target=target;self.timing=timing
    def __getattr__(self,name):
        value=getattr(self.target,name)
        if not callable(value):return value
        category='cache_lookup' if name in ('cached','classification') else 'database_and_storage'
        return lambda *a,**kw:self.timing.call(category,value,*a,**kw)
