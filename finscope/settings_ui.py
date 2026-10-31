"""The local product's single persistent configuration editor."""
from contextlib import closing
from datetime import date,datetime,timezone
import json
from .localized_ui import st
from .i18n import t,tr,display,Verbatim
from .settings_state import editable,save,issues,saved


def field(kind,label,key,default,*,after_change=None,**kwargs):
    values=st.session_state.setdefault('_settings_values',{})
    if key not in st.session_state:st.session_state[key]=values.get(key,default)
    def remember():
        values[key]=st.session_state[key]
        if after_change:after_change()
    value=getattr(st,kind)(label,key=key,on_change=remember,**kwargs)
    values[key]=value
    return value


def credential_editor(provider):
    from .local_credentials import credential,save_credential
    configured=bool(credential(provider));key='settings_secret_'+provider;flag=key+'_editing'
    st.caption('Key configured' if configured else 'Key not configured')
    if st.button('Change API key' if configured else 'Configure API key',key=key+'_edit'):
        st.session_state[flag]=not st.session_state.get(flag,False)
    if not st.session_state.get(flag):return
    st.text_input('API key',type='password',key=key,max_chars=500)
    def persist():
        secret=st.session_state.get(key,'')
        try:save_credential(provider,secret)
        except ValueError:
            st.session_state[key+'_error']='Credential save failed; existing credentials are unchanged.';return
        for k in (key,key+'__en',key+'__zh-CN'):
            st.session_state.pop(k,None)
        st.session_state.get('_ui_mirrors',{}).pop(key,None)
        st.session_state[flag]=False
        st.session_state.pop(key+'_error',None)
        if provider=='deepseek':
            from .external_ui import clear_confirmation
            clear_confirmation()
    st.button('Save key securely',key=key+'_save',on_click=persist,disabled=not st.session_state.get(key))
    if st.session_state.get(key+'_error'):st.error(st.session_state[key+'_error'])


def source_editor(store,c):
    from .news_source_ui import render
    render(store,c,field)


def model_editor(store,c):
    from .model_ui import controls
    values=st.session_state.setdefault('_settings_values',{})
    for key,value in [('pipeline_model',c['model']),('pipeline_lmstudio_model',c.get('model_id') if c['model']=='Local LM Studio' else None),
                      ('pipeline_ollama_model',c.get('model_id') if c['model']=='Local Ollama' else None)]:
        if key not in st.session_state:st.session_state[key]=values.get(key,value)
    options=controls('pipeline',store=store,configuration=True,saved_model=c.get('model_id',''))
    for key in ('pipeline_model','pipeline_lmstudio_model','pipeline_ollama_model'):
        if key in st.session_state:values[key]=st.session_state[key]
    if options.mode=='External API':
        st.caption(t('Automatic updates still use {model}; external API tests do not change the worker model.',model=str(display(c['model']))))
        return
    c['model']=options.mode;c['model_id']=options.model or ''
    if options.mode=='Local FinBERT':c['model_id']=''
    c.pop('result_model_key',None)
    c['taxonomy']=field('selectbox','Default classification catalog for new tasks','settings_taxonomy',c['taxonomy'],options=['US-BUSINESS-1','CSRC-JRT0020-2024'])
    c['classifier_llm']=field('checkbox','Use selected local LM Studio model to verify classification candidates','settings_classifier',c.get('classifier_llm',False),disabled=c['model']!='Local LM Studio')
    if c['model']!='Local LM Studio':c['classifier_llm']=False


def diagnostics(store,q):
    from .local_collectors import SOURCES
    with st.expander('Advanced & diagnostics',expanded=False):
        st.caption('Read-only diagnostics and retained manual actions.')
        for source in editable(q)['sources']:
            if source in SOURCES:
                s=SOURCES[source];st.write(Verbatim(s.get('attribution',source)))
                st.caption(s.get('license','Official RBA information; third-party exceptions apply'))
                st.caption(s.get('exclusions','No third-party material, media or separately restricted content'))
        with closing(store.connect()) as db:
            rows=db.execute('SELECT status,stage,counts,error,created FROM product_tasks ORDER BY rowid DESC LIMIT 10').fetchall()
        if rows:
            import pandas as pd
            st.dataframe(pd.DataFrame(rows,columns=['Status','Stage','Counts','Reason','Created UTC']),hide_index=True,width='stretch')
        with closing(store.connect()) as db:
            present=db.execute("SELECT 1 FROM sqlite_master WHERE name='deepseek_requests'").fetchone()
            requests=db.execute('SELECT kind,status,http_status,error_kind,reserved_at,hold_until FROM deepseek_requests ORDER BY reserved_at').fetchall() if present else []
        if present:
            st.caption('Independent DeepSeek ledger; unresolved outcomes and holds are retained. No automatic retry.')
            import pandas as pd
            st.dataframe(pd.DataFrame(requests,columns=['Operation','Status','HTTP','Reason','Created UTC','Hold until UTC']),hide_index=True,width='stretch')
        st.caption('Language and theme do not submit tasks. Models and source permissions are checked before fetching.')
        if st.button('Open advanced manual workspace'):
            st.session_state['advanced_manual_ui']=True;st.session_state['workspace_page']='Add news';st.rerun()
        st.link_button('Project help','https://github.com/DVDWK812/Finscope#readme')


def render(store,q):
    from .ui_preferences import language_settings
    c=st.session_state.setdefault('_settings_edit',editable(q))
    general,sources,models=st.tabs(['General','News sources','Analysis models'])
    with general:language_settings(store)
    with sources:source_editor(store,c)
    with models:model_editor(store,c)
    c['source_permissions']={k:v for k,v in c['source_permissions'].items() if k in c['sources'] or k in ('marketaux','newsdata','finnhub')}
    if c!=editable(q):st.info('Unsaved settings edits; save them in Settings before starting a task.')
    elif saved(q):st.info('Editing a saved draft; the previous pipeline will not run silently.')
    if st.button('Save settings',key='settings_save',type='primary'):
        try:
            pending=save(q,c)
            if st.session_state.get('_external_api_edit'):
                from .external_ui import save_external
                save_external(store,st.session_state['_external_api_edit'])
            st.session_state['settings_save_message']='Draft saved; review and explicitly confirm the ready-source scope before updating.' if pending else 'Settings saved. Connection checks happen separately.'
            st.rerun()
        except ValueError as error:st.error(str(error))
    if st.session_state.get('settings_save_message'):st.success(st.session_state['settings_save_message'])
    pending=issues(c,store=store)
    for reason in pending:
        if not reason.startswith('Source setup incomplete:'):st.warning(tr(reason))
    diagnostics(store,q)
