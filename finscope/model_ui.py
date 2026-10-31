"""Shared explicit model controls for a run or an individual original."""
from dataclasses import dataclass, field, replace
from contextlib import closing
from datetime import datetime

from .localized_ui import st
from .i18n import t,tr,display,Verbatim,node_name

from .api_sources import local_credentials
from .model_providers import (ExternalLLMProvider, FinBERTProvider, LMStudioProvider, ModelError,
                              OllamaProvider, OPENAI_MODELS, lmstudio_revision)

MODES = ["Local FinBERT", "Local LM Studio", "Local Ollama", "OpenAI API"]


@dataclass
class RunSettings:
    mode: str
    model: str | None = None
    api_key: str = field(default="",repr=False)
    use_env: bool = True
    consent: bool = False
    external_rights: bool = False
    permission_reference: str = ""
    ready: bool = True

    def result_key(self):
        from .model_assets import manifest
        if self.mode == "Local FinBERT":
            info = manifest("finbert")
            return f"FinBERT · {info['model_id']} · {info['revision']}"
        if self.mode == "OpenAI API":
            return f"External LLM · openai/{self.model} · {self.model}"
        if self.mode == 'Local LM Studio':
            model=st.session_state.get('lmstudio_models',{}).get(self.model)
            return f"Local LM Studio · {model['model_id']} · {lmstudio_revision(model)}" if model else 'Local LM Studio · No selected model'
        digest = st.session_state.get("installed_ollama_models", {}).get(self.model, "")
        return f"Local Ollama · {self.model} · {digest}"


def external_status(store):
    from .local_news import utcnow
    with closing(store.connect()) as db:
        rows=db.execute("SELECT status,hold_until,completed_at FROM local_model_requests WHERE backend='openai' ORDER BY reserved_at").fetchall()
    if any(status=='pending' for status,_,_ in rows):
        return 'Paused · Previous request outcome unknown; review local model ledger', True
    if any(hold and datetime.fromisoformat(hold)>utcnow() for _,hold,_ in rows):
        return 'Paused · External model Retry-After hold is active', True
    if rows:
        status,_,stamp=rows[-1]
        return ('Available · Last request succeeded: ' if status=='ok' else 'Failed · Last request failed: ')+(stamp or 'unknown time'),False
    return 'Untested · No successful connection check',False


def controls(prefix="analysis", *, store=None,configuration=False,saved_model=''):
    default=st.session_state.get("default_analysis_mode",MODES[0])
    key="analysis_model" if prefix=="analysis" else prefix+"_model"
    modes=[*MODES[:-1],'External API'] if configuration else MODES
    if configuration and st.session_state.get(key)=='OpenAI API':st.session_state[key]='External API'
    mode=st.selectbox('Model settings' if configuration else "Analysis model",modes,index=modes.index(default) if default in modes else 0,key=key)
    if prefix=="analysis":
        st.session_state["default_analysis_mode"]=mode
    options=RunSettings(mode)
    if mode=="Local FinBERT":
        from .model_assets import assets_present
        options.ready=all(assets_present(kind) for kind in ("finbert","minilm"))
        st.caption("Available · Local model files present · No API key" if options.ready else "Not configured · Local model files missing")
        if not options.ready:
            st.info("Prepare the pinned models from Analyze before running FinBERT.")
    elif mode=='Local LM Studio':
        lmstudio_controls(prefix,options,store=store,saved_model=saved_model if configuration else '')
    elif mode=="Local Ollama":
        state = st.session_state.get("ollama_status", "Untested · List models to check localhost:11434")
        st.caption(state)
        if st.button("List installed Ollama models",key=prefix+"_ollama_list"):
            try:
                inventory=OllamaProvider().inventory()
                st.session_state["installed_ollama_models"]=inventory['models']
                st.session_state["ollama_status"] = (
                    f"Available · {len(inventory['models'])} compatible local models; {inventory['filtered']} remote/invalid/incompatible entries excluded" if inventory['models'] else
                    "Unavailable · Installed models were filtered: require local GGUF weights, a valid digest and no remote/cloud origin" if inventory['total'] else
                    "Available service · No installed models; no inference is possible")
                st.rerun()
            except ModelError as error:
                st.session_state["installed_ollama_models"] = {}
                st.session_state["ollama_status"] = "Failed · " + str(error)
                st.rerun()
        installed=st.session_state.get("installed_ollama_models",{})
        choices=list(installed)
        previous=st.session_state.get(prefix+'_ollama_model') or (saved_model if configuration else None)
        if previous and previous not in choices:choices.append(previous)
        options.model=st.selectbox("Installed local model",choices,index=None,key=prefix+"_ollama_model")
        options.ready=bool(options.model in installed)
        if not installed:
            st.info("Ollama requires its own running service and compatible weights. LM Studio models are separate; FinBERT remains available independently.")
    else:
        if configuration:
            from .external_ui import render
            render(store)
            return options
        options.model=st.selectbox("Supported OpenAI model",OPENAI_MODELS,key=prefix+"_openai_model")
        from .local_credentials import credential
        configured=bool(credential('openai'))
        st.caption('Key configured' if configured else 'Key not configured')
        if st.button('Open product settings',key=prefix+'_openai_settings'):
            st.session_state['advanced_manual_ui']=False;st.session_state['product_page']='Settings';st.rerun()
        with st.expander("External transmission permission",expanded=False):
            options.permission_reference=st.text_input("Permission reference covering local use and external transmission",max_chars=300,key=prefix+"_external_ref")
            options.external_rights=st.checkbox("My permission covers sending these selected texts to OpenAI",key=prefix+"_external_rights")
        options.consent=st.checkbox("Send the selected permitted headline/summary text to OpenAI when I click Run",key=prefix+"_send_consent")
        status,blocked=external_status(store) if store else ('Untested · No successful connection check',False)
        st.caption(status if configured else 'Not configured · OpenAI API key required')
        st.caption("Optional paid transmission: one headline/summary request per article, at most 10/run; store=false requested, provider retention policies apply.")
        options.ready=configured and options.consent and not blocked
    return options


def lmstudio_controls(prefix,options,*,store=None,saved_model=''):
    reason=st.session_state.get('lmstudio_connection_error')
    st.caption(Verbatim(str(tr('Failed'))+' · '+str(tr(reason))) if reason else st.session_state.get('lmstudio_status','Service not checked.'))
    if st.session_state.get('lmstudio_operation_error'):
        st.error('Last model action: '+st.session_state['lmstudio_operation_error'])
    connected=st.session_state.get('lmstudio_connected',False)
    action='Refresh models' if connected else 'Start service & refresh models'
    if st.button(action,key=prefix+'_lmstudio_refresh'):
        try:
            if connected:refresh_lmstudio()
            else:
                from .lmstudio_runtime import start_service
                with st.spinner('Starting local service; no model will be loaded…'):
                    report=start_service(store,explicit=True,transport=LMStudioProvider().transport)
                st.session_state['lmstudio_start_report']={k:v for k,v in report.items() if k!='models'}
                refresh_lmstudio(report['models'])
        except ModelError as error:
            st.session_state['lmstudio_connected']=False
            st.session_state['lmstudio_connection_error']=str(error)
            st.session_state['lmstudio_status']='Failed · '+str(error)
        st.rerun()
    models=st.session_state.get('lmstudio_models',{})
    key=prefix+'_lmstudio_model'
    previous=st.session_state.get(key) or saved_model
    choices=list(models)
    if previous and previous not in choices:choices.append(previous)
    if previous and key not in st.session_state:st.session_state[key]=previous
    options.model=st.selectbox('Downloaded LM Studio model',choices,index=None,key=key,
        help='Actual local model keys from LM Studio; selecting never loads or infers.')
    options.ready=False
    selected=models.get(options.model)
    if not selected:
        connected=st.session_state.get('lmstudio_connected',False)
        st.info('Saved selection is absent from the downloaded catalog.' if connected and options.model else
                'Connected · No downloaded local LLMs.' if connected and not models else
                'Saved model selection retained; service and model readiness are unverified.' if options.model else
                'Choose a downloaded model above; selection never loads or infers.')
        return
    connected=st.session_state.get('lmstudio_connected',True)
    st.caption('Loaded · API exposed; inference requires Run' if connected and selected['callable'] else 'Not loaded · cannot infer' if connected else 'Saved model selection retained; service and model readiness are unverified.')
    with st.expander('Model details'):
        st.caption(f"Downloaded · {selected['format'].upper()} / {selected['quantization']} · {selected['size_bytes']/1e9:.2f} GB")
        from .lmstudio_runtime import gpu_ratio
        st.caption(f"Safe load: context 2048, one prediction, {float(gpu_ratio(selected)):.0%} GPU offload; estimate and free RAM/VRAM checked first.")
        startup=st.session_state.get('lmstudio_start_report')
        if startup:st.caption(Verbatim(startup['cli_version']))
        report=st.session_state.get('lmstudio_last_load',{})
        if isinstance(report,dict) and report.get('model_key')==selected['key'] and report.get('estimate'):
            estimate,snapshot=report['estimate'],report['resources_before_load']
            st.caption(f"Estimate: GPU {estimate['gpu_bytes']/1024**3:.2f} GiB / total {estimate['total_bytes']/1024**3:.2f} GiB · context {estimate['context_length']}")
            st.caption(f"Available before load: RAM {snapshot['ram_available']/1024**3:.2f} GiB / VRAM {snapshot['gpu_available']/1024**3:.2f} GiB · one model, one prediction")
    if not connected:return
    others=[m for k,m in models.items() if k!=options.model and m['loaded']]
    for other in others:
        st.info('Another model is loaded: '+other['key']+'. Unload it explicitly before loading the selection.')
        if st.button('Unload '+other['key'],key=prefix+'_lmstudio_unload_'+other['key'],disabled=model_busy(store)):
            lmstudio_action(lambda:LMStudioProvider().unload(other['key'],explicit=True,store=store))
    if selected['loaded']:
        if st.button('Unload selected LM Studio model',key=prefix+'_lmstudio_unload',disabled=model_busy(store)):
            lmstudio_action(lambda:LMStudioProvider().unload(options.model,explicit=True,store=store))
    else:
        if st.button('Load selected LM Studio model',disabled=bool(others) or model_busy(store) or not connected,key=prefix+'_lmstudio_load'):
            lmstudio_action(lambda:LMStudioProvider().load(options.model,explicit=True,store=store))
    options.ready=bool(connected and selected['callable'])


def refresh_lmstudio(models=None):
    from .local_news import utcnow
    if models is None:models=LMStudioProvider().inventory()
    st.session_state['lmstudio_models']=models
    st.session_state['lmstudio_connected']=True
    st.session_state.pop('lmstudio_connection_error',None)
    st.session_state.pop('lmstudio_operation_error',None)
    st.session_state['lmstudio_status']=f"Available local service · {len(models)} downloaded local LLMs · checked {utcnow().strftime('%H:%M:%S UTC')}"


def model_busy(store):
    if not store:return False
    from .task_queue import TaskQueue,ACTIVE
    task=TaskQueue(store).get()
    return bool(task and task['status'] in ACTIVE)


def lmstudio_action(action):
    try:
        with st.spinner('Checking local resources and updating the selected model…'):
            report=action()
            st.session_state['lmstudio_last_load']=report
            refresh_lmstudio()
    except ModelError as error:
        st.session_state['lmstudio_operation_error']=str(error)
        st.error(str(error))
        return
    st.rerun()


def execute(item,store,settings):
    if settings.mode in ('Local LM Studio','Local Ollama') and model_busy(store):
        raise ModelError('Worker is using the model; loading, unloading and switching are paused.',kind='worker_owns_model')
    if settings.mode=="Local FinBERT":
        # Advanced manual screens must not load a second copy beside the worker.
        from .task_queue import TaskQueue
        if TaskQueue(store).worker_alive():
            raise ModelError('The local worker owns FinBERT. Return to the automatic News Explorer and queue reanalysis of this original.',kind='worker_owns_model')
        from streamlit_app import cached_pipeline
        return FinBERTProvider(cached_pipeline).analyze(item,store)
    if settings.mode=="Local Ollama":
        return OllamaProvider().analyze(item,store,model=settings.model)
    if settings.mode=='Local LM Studio':
        return LMStudioProvider().analyze(item,store,model=settings.model)
    if settings.mode!="OpenAI API":
        raise ModelError("Choose a supported analysis mode")
    from .local_credentials import credential as stored_credential
    credential=settings.api_key or (stored_credential('openai') if settings.use_env else None)
    if settings.external_rights and settings.permission_reference.strip():
        if credential and credential in settings.permission_reference:
            raise ModelError("A permission reference must not contain credentials")
        updated=replace(item.rights,external=True,reference=settings.permission_reference)
        store.update_rights(item.article_id,updated)
        item=replace(item,rights=updated)
    return ExternalLLMProvider().analyze(item,store,api_key=credential,model=settings.model,consent=settings.consent)
