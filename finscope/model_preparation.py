"""One cancellable preparation task per app process; file lock covers other processes."""
import threading
from .model_assets import prepare_models, PreparationCancelled


class Preparation:
    def __init__(self):
        self.lock=threading.Lock();self.cancel_event=threading.Event()
        self.state={'status':'idle','done':0,'total':1};self.thread=None

    def snapshot(self):
        with self.lock:return dict(self.state)

    def start(self, accepted):
        if accepted is not True:raise ValueError('Confirm model licences first')
        with self.lock:
            if self.thread and self.thread.is_alive():return False
            self.cancel_event.clear();self.state={'status':'running','done':0,'total':1}
            self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
            return True

    def update(self,**values):
        with self.lock:self.state.update(values)

    def run(self):
        try:
            prepare_models(acknowledge_licenses=True,progress=self.update,cancelled=self.cancel_event.is_set)
            self.update(status='verified')
        except PreparationCancelled:self.update(status='cancelled')
        except Exception as error:
            # Do not display network exception URLs or configuration.
            self.update(status='failed',error=type(error).__name__)

    def cancel(self):self.cancel_event.set()


task=Preparation()


def controls(prefix='prepare'):
    from .localized_ui import st
    from .model_assets import manifest
    with st.expander('Download and verify FinBERT + MiniLM'):
        was_running=task.snapshot()['status']=='running'
        for kind in ('finbert','minilm'):
            spec=manifest(kind)
            st.caption(f"{spec['model_id']} · {spec['revision']} · {sum(v['size'] for v in spec['files'].values())/1e6:.1f} MB")
        st.markdown('[FinBERT licence](https://huggingface.co/ProsusAI/finbert) · [MiniLM licence](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)')
        accepted=st.checkbox('Accept FinBERT CC BY-NC-SA 4.0 and MiniLM Apache-2.0 for noncommercial use',key=prefix+'_licenses')
        if st.button('Download and verify FinBERT + MiniLM',key=prefix+'_start',disabled=not accepted or task.snapshot()['status']=='running'):
            task.start(accepted);st.rerun()
        if st.button('Cancel model preparation',key=prefix+'_cancel',disabled=task.snapshot()['status']!='running'):
            task.cancel()
        st.caption('Verified files are reused. Interrupted files restart on the next explicit attempt. Cancel takes effect between chunks or after the bounded network timeout. Refresh never starts a download.')
        @st.fragment(run_every=2)
        def progress():
            state=task.snapshot()
            if was_running and state['status']!='running':st.rerun(scope='app')
            st.progress(min(1.,state['done']/max(1,state['total'])),text=state['status'])
            if state.get('file'):st.caption(state['file'])
            if state['status']=='failed':st.info('Preparation failed ('+state['error']+'). Check disk/network and explicitly retry; no partial model can be used.')
        progress()
