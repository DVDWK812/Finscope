"""Shared explicit model controls for a run or an individual original."""
from dataclasses import dataclass, field, replace
from contextlib import closing
from datetime import datetime

import streamlit as st

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


def controls(prefix="analysis", *, store=None):
    default=st.session_state.get("default_analysis_mode",MODES[0])
    key="analysis_model" if prefix=="analysis" else prefix+"_model"
    mode=st.selectbox("Analysis model",MODES,index=MODES.index(default) if default in MODES else 0,key=key)
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
        lmstudio_controls(prefix,options)
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
        if st.session_state.get(prefix+'_ollama_model') not in installed:
            st.session_state.pop(prefix+'_ollama_model',None)
        options.model=st.selectbox("Installed local model",list(installed),index=None,key=prefix+"_ollama_model")
        options.ready=bool(options.model)
        if not installed:
            st.info("Ollama requires its own running service and compatible weights. LM Studio models are separate; FinBERT remains available independently.")
    else:
        options.model=st.selectbox("Supported OpenAI model",OPENAI_MODELS,key=prefix+"_openai_model")
        options.api_key=st.text_input("OpenAI API key",type="password",max_chars=500,key=prefix+"_openai_key")
        options.use_env=st.checkbox("Use local .env OPENAI_API_KEY when empty",value=True,key=prefix+"_openai_env")
        with st.expander("External transmission permission",expanded=False):
            options.permission_reference=st.text_input("Permission reference covering local use and external transmission",max_chars=300,key=prefix+"_external_ref")
            options.external_rights=st.checkbox("My permission covers sending these selected texts to OpenAI",key=prefix+"_external_rights")
        options.consent=st.checkbox("Send the selected permitted headline/summary text to OpenAI when I click Run",key=prefix+"_send_consent")
        credential=options.api_key or (local_credentials().get("OPENAI_API_KEY") if options.use_env else None)
        status,blocked=external_status(store) if store else ('Untested · No successful connection check',False)
        st.caption(status if credential else 'Not configured · OpenAI API key required')
        st.caption("Optional paid transmission: one headline/summary request per article, at most 10/run; store=false requested, provider retention policies apply.")
        options.ready=bool(credential) and options.consent and not blocked
    return options


def lmstudio_controls(prefix,options):
    st.caption(st.session_state.get('lmstudio_status','Untested · Refresh models to check 127.0.0.1:1234'))
    if st.button('Refresh LM Studio models',key=prefix+'_lmstudio_refresh'):
        try:
            refresh_lmstudio()
        except ModelError as error:
            st.session_state['lmstudio_models']={}
            st.session_state['lmstudio_status']='Failed · '+str(error)
        st.rerun()
    models=st.session_state.get('lmstudio_models',{})
    key=prefix+'_lmstudio_model'
    if st.session_state.get(key) not in models:st.session_state.pop(key,None)
    options.model=st.selectbox('Downloaded LM Studio model',list(models),index=None,key=key,
        format_func=lambda k:k+' · '+models[k]['quantization'],help='Actual local model keys from LM Studio; selecting never loads or infers.')
    options.ready=False
    selected=models.get(options.model)
    if not selected:
        st.info('Start the installed LM Studio server on 127.0.0.1:1234, then refresh. No model download is performed.')
        return
    st.caption(f"Downloaded · {selected['format'].upper()} / {selected['quantization']} · {selected['size_bytes']/1e9:.2f} GB · "+
               ('Loaded · API exposed; inference requires Run' if selected['callable'] else 'Loaded · not exposed by /v1/models' if selected['loaded'] else 'Not loaded · cannot infer'))
    others=[m for k,m in models.items() if k!=options.model and m['loaded']]
    for other in others:
        st.info('Another model is loaded: '+other['key']+'. Unload it explicitly before loading the selection.')
        if st.button('Unload '+other['key'],key=prefix+'_lmstudio_unload_'+other['key']):
            lmstudio_action(lambda:LMStudioProvider().unload(other['key'],explicit=True))
    if selected['loaded']:
        if st.button('Unload selected LM Studio model',key=prefix+'_lmstudio_unload'):
            lmstudio_action(lambda:LMStudioProvider().unload(options.model,explicit=True))
    else:
        st.caption('Safe load: context 2048, one prediction, 50% GPU offload; estimate and free RAM/VRAM checked first.')
        if st.button('Load selected LM Studio model',disabled=bool(others),key=prefix+'_lmstudio_load'):
            lmstudio_action(lambda:LMStudioProvider().load(options.model,explicit=True))
    options.ready=bool(selected['callable'])
    report=st.session_state.get('lmstudio_last_load',{})
    if isinstance(report,dict) and report.get('estimate'):
        with st.expander('LM Studio load resources'):
            estimate,snapshot=report['estimate'],report['resources_before_load']
            st.caption(f"Estimate: GPU {estimate['gpu_bytes']/1024**3:.2f} GiB / total {estimate['total_bytes']/1024**3:.2f} GiB · context {estimate['context_length']}")
            st.caption(f"Available before load: RAM {snapshot['ram_available']/1024**3:.2f} GiB / VRAM {snapshot['gpu_available']/1024**3:.2f} GiB · one model, one prediction")


def refresh_lmstudio():
    from .local_news import utcnow
    models=LMStudioProvider().inventory()
    st.session_state['lmstudio_models']=models
    st.session_state['lmstudio_status']=f"Available local service · {len(models)} downloaded local LLMs · checked {utcnow().strftime('%H:%M:%S UTC')}"


def lmstudio_action(action):
    try:
        with st.spinner('Checking local resources and updating the selected model…'):
            report=action()
            st.session_state['lmstudio_last_load']=report
            refresh_lmstudio()
    except ModelError as error:
        st.session_state['lmstudio_status']='Failed · '+str(error)
        st.error(str(error))
        return
    st.rerun()


def execute(item,store,settings):
    if settings.mode=="Local FinBERT":
        from streamlit_app import cached_pipeline
        return FinBERTProvider(cached_pipeline).analyze(item,store)
    if settings.mode=="Local Ollama":
        return OllamaProvider().analyze(item,store,model=settings.model)
    if settings.mode=='Local LM Studio':
        return LMStudioProvider().analyze(item,store,model=settings.model)
    if settings.mode!="OpenAI API":
        raise ModelError("Choose a supported analysis mode")
    credential=settings.api_key or (local_credentials().get("OPENAI_API_KEY") if settings.use_env else None)
    if settings.external_rights and settings.permission_reference.strip():
        if credential and credential in settings.permission_reference:
            raise ModelError("A permission reference must not contain credentials")
        updated=replace(item.rights,external=True,reference=settings.permission_reference)
        store.update_rights(item.article_id,updated)
        item=replace(item,rights=updated)
    return ExternalLLMProvider().analyze(item,store,api_key=credential,model=settings.model,consent=settings.consent)
