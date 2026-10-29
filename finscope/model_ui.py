"""Shared explicit model controls for a run or an individual original."""
from dataclasses import dataclass, field, replace

import streamlit as st

from .api_sources import local_credentials
from .model_providers import ExternalLLMProvider, FinBERTProvider, ModelError, OllamaProvider, OPENAI_MODELS

MODES = ["Local FinBERT", "Local Ollama", "External LLM API"]


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


def controls(prefix="analysis"):
    default=st.session_state.get("default_analysis_mode",MODES[0])
    key="analysis_model" if prefix=="analysis" else prefix+"_model"
    mode=st.selectbox("Analysis model",MODES,index=MODES.index(default),key=key)
    if prefix=="analysis":
        st.session_state["default_analysis_mode"]=mode
    options=RunSettings(mode)
    if mode=="Local FinBERT":
        from .model_assets import assets_present
        options.ready=all(assets_present(kind) for kind in ("finbert","minilm"))
        st.caption("Pinned CPU FinBERT + MiniLM · No API key · Genuine three-class probabilities")
        if not options.ready:
            st.info("Prepare the pinned models from Analyze before running FinBERT.")
    elif mode=="Local Ollama":
        st.caption("Installed local GGUF models at 127.0.0.1:11434 only. No model pull, remote tag or public endpoint.")
        if st.button("List installed Ollama models",key=prefix+"_ollama_list"):
            try:
                st.session_state["installed_ollama_models"]=OllamaProvider().installed_models()
            except ModelError as error:
                st.error(str(error))
        installed=st.session_state.get("installed_ollama_models",{})
        options.model=st.selectbox("Installed local model",list(installed),index=None,key=prefix+"_ollama_model")
        options.ready=bool(options.model)
        if not installed:
            st.info("Start your installed Ollama service and prepare a licensed local model yourself, then list it here.")
    else:
        options.model=st.selectbox("Supported OpenAI model",OPENAI_MODELS,key=prefix+"_openai_model")
        options.api_key=st.text_input("OpenAI API key",type="password",max_chars=500,key=prefix+"_openai_key")
        options.use_env=st.checkbox("Use local .env OPENAI_API_KEY when empty",value=True,key=prefix+"_openai_env")
        with st.expander("External transmission permission",expanded=False):
            options.permission_reference=st.text_input("Permission reference covering local use and external transmission",max_chars=300,key=prefix+"_external_ref")
            options.external_rights=st.checkbox("My permission covers sending these selected texts to OpenAI",key=prefix+"_external_rights")
        options.consent=st.checkbox("Send the selected permitted headline/summary text to OpenAI when I click Run",key=prefix+"_send_consent")
        st.caption("Optional paid API. One request/article; at most 10 articles/run. No tools or publisher fetching. "
                   "Labels/rationales are model-generated, without calibrated probabilities. API provider retention policies apply; store=false is requested.")
        options.ready=options.consent
    return options


def execute(item,store,settings):
    if settings.mode=="Local FinBERT":
        from streamlit_app import cached_pipeline
        return FinBERTProvider(cached_pipeline).analyze(item,store)
    if settings.mode=="Local Ollama":
        return OllamaProvider().analyze(item,store,model=settings.model)
    if settings.mode!="External LLM API":
        raise ModelError("Choose a supported analysis mode")
    credential=settings.api_key or (local_credentials().get("OPENAI_API_KEY") if settings.use_env else None)
    if settings.external_rights and settings.permission_reference.strip():
        if credential and credential in settings.permission_reference:
            raise ModelError("A permission reference must not contain credentials")
        updated=replace(item.rights,external=True,reference=settings.permission_reference)
        store.update_rights(item.article_id,updated)
        item=replace(item,rights=updated)
    return ExternalLLMProvider().analyze(item,store,api_key=credential,model=settings.model,consent=settings.consent)
