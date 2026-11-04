"""Stage observations contain metrics only, never source text or model outputs."""
import os
from uuid import uuid4


class StageResources:
    def __init__(self,worker,identity):
        self.worker=worker;self.identity=identity;self.active=None;self.encoder=None;self.recovered=False;self.observations=0

    def timed(self,name,fn,*args,**kwargs):
        from .batch_timing import Timing
        timing=getattr(self.worker,'batch_timing',None)
        return timing.call(name,fn,*args,**kwargs) if isinstance(timing,Timing) else fn(*args,**kwargs)

    def snapshot(self):
        backend=self.worker.backend
        result={'finbert_owned_child_pid':getattr(backend,'pid',None),
                'finbert_owned_child_alive':bool(getattr(backend,'alive',False)),
                'lmstudio_owner':'external_not_managed'}
        if os.environ.get('FINSCOPE_TESTING')=='1':
            result['measurement']='unavailable_in_offline_test';return result
        from .resource_diagnostics import processes,gpu_processes
        owned={os.getpid():'worker'}
        for obj,role in ((backend,'finbert_owned'),(self.encoder,'minilm_owned')):
            if getattr(obj,'pid',None):owned[obj.pid]=role
        result.update(self.timed('process_gpu_observation',processes,owned))
        result['gpu_processes']=self.timed('process_gpu_observation',gpu_processes,{p['pid'] for p in result['processes']})
        from .lmstudio_runtime import system_resources
        try:result.update(self.timed('resource_measurement',system_resources));result['measurement']='actual'
        except Exception:result['measurement']='unavailable'
        from .model_providers import LMStudioProvider
        try:result['lmstudio_resident_models']=[m['model_id'] for m in self.timed('model_state',LMStudioProvider().inventory).values() if m['callable']]
        except Exception:result['lmstudio_resident_models']='unknown'
        return result

    def observe(self,edge):
        self.observations+=1
        self.worker.queue.save_step(self.identity,'stage_resources:'+self.active+':'+str(self.observations)+':'+edge,'ok',self.snapshot())

    def begin(self,name):
        self.end()
        self.active=name+':'+uuid4().hex;self.recovered=False
        self.observe('before')
        # Only this worker's backend is owned; no LM Studio unload or other PID.
        self.worker.release_sentiment_backend()
        self.observe('ready')

    def end(self):
        if self.active:
            try:self.observe('before_release')
            finally:
                try:
                    if self.encoder:
                        self.encoder.close()
                        self.observe('minilm_exit_verified' if self.encoder.exit_verified or self.encoder.pid is None else 'minilm_exit_unknown')
                finally:
                    self.encoder=None
                    try:self.worker.release_sentiment_backend()
                    finally:
                        try:self.observe('after')
                        finally:self.active=None

    def check_resources(self,mode,*,loading=False):
        from .model_providers import ModelError
        try:return self.timed('resource_guard',self.worker.resources,mode,loading=loading)
        except ModelError:
            if self.recovered:raise
            self.recovered=True
            self.observe('pressure_before')
            # Only idle FinBERT is releasable here, never the external classifier.
            if self.worker.backend is not None:
                self.worker.release_sentiment_backend()
                loading=mode=='Local FinBERT'
            self.observe('pressure_after')
            return self.timed('resource_guard',self.worker.resources,mode,loading=loading)

    def classifier_resources(self,kind,encoder):
        from .model_providers import ModelError
        from .semantic_classifier import ClassifierPrerequisite
        try:return self.check_resources('Local LM Studio' if kind=='LM Studio' else 'Local FinBERT',loading=kind!='LM Studio' and not getattr(encoder,'alive',False))
        except ModelError as error:
            blocked=ClassifierPrerequisite(str(error));blocked.resources=getattr(error,'resources',None)
            raise blocked from error
