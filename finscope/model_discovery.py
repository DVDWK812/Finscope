"""Process-lifetime, read-only LM Studio discovery shared by Streamlit sessions."""
from copy import deepcopy
from datetime import datetime,timezone
import threading
from .model_providers import LMStudioProvider,ModelError


class Discovery:
    def __init__(self,inventory=None):
        self.inventory=inventory or (lambda:LMStudioProvider().inventory())
        self.lock=threading.RLock();self.operation=threading.Lock();self.started=False
        self.state={'generation':0,'status':'not_checked','models':{},'checked_at':None,'success_at':None,'scans':0,'stale':False}

    def snapshot(self):
        with self.lock:return deepcopy(self.state)

    def ensure_started(self):
        with self.lock:
            if self.started:return
            self.started=True;self.state['status']='checking'
            self.thread=threading.Thread(target=self.refresh,daemon=True);self.thread.start()

    def publish(self,models=None,error=None):
        stamp=datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.started=True;self.state['generation']+=1;self.state['checked_at']=stamp
            if error is None:
                self.state.update(models=deepcopy(models),status='ready' if models else 'empty',success_at=stamp,stale=False)
            else:
                status=('authentication_failed' if getattr(error,'status',None) in (401,403) or getattr(error,'kind',None)=='authentication'
                        else 'service_not_running' if getattr(error,'kind',None)=='connection_refused'
                        else 'timeout' if getattr(error,'kind',None)=='timeout' else 'detection_failed')
                self.state.update(status=status,stale=self.state['success_at'] is not None)
            return deepcopy(self.state)

    def refresh(self):
        with self.operation:
            with self.lock:self.state['scans']+=1
            try:return self.publish(self.inventory())
            except Exception as error:return self.publish(error=error)


discovery=Discovery()


def sync_session(state):
    snapshot=discovery.snapshot()
    if state.get('_lm_discovery_generation')!=snapshot['generation']:
        state['_lm_discovery_generation']=snapshot['generation']
        state['lmstudio_models']=snapshot['models']
        state['lmstudio_connected']=snapshot['status'] in ('ready','empty')
        state['lmstudio_status']=(f"Discovery: {snapshot['status']} · checked UTC {snapshot['checked_at'] or 'pending'}"
                                 + (f" · OLD RESULT from {snapshot['success_at']}" if snapshot['stale'] else ''))
        state.pop('lmstudio_connection_error',None)
    return snapshot


def startup_ui():
    from .localized_ui import st
    from .test_safety import active
    # Offline AppTest must explicitly inject a fake Discovery for its tests.
    if active():return
    discovery.ensure_started()
    sync_session(st.session_state)
    @st.fragment(run_every=2)
    def completion():
        if discovery.snapshot()['generation']!=st.session_state.get('_lm_discovery_generation'):
            st.rerun(scope='app')
    completion()
