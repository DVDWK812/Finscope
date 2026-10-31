"""Explicit external-provider controls, separate from the automatic local worker."""
from contextlib import closing
import json
from .localized_ui import st
from .i18n import t,Verbatim
from .model_providers import DeepSeekProvider,ModelError,OPENAI_MODELS
from .external_tests import DeepSeekLedger,authored_samples,run_authored_test,SCOPE


def saved_external(store):
    with closing(store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='external_api_settings'").fetchone()
    return json.loads(row[0]) if row else {'provider':'openai','models':{'openai':OPENAI_MODELS[0],'deepseek':''}}


def save_external(store,config):
    from .local_credentials import credential,PROVIDERS
    if (not isinstance(config,dict) or set(config)!={'provider','models'} or config['provider'] not in ('openai','deepseek')
            or not isinstance(config['models'],dict) or set(config['models'])!={'openai','deepseek'}
            or any(not isinstance(value,str) or value and not DeepSeekProvider.identifier(value) for value in config['models'].values())):
        raise ValueError('Invalid external model settings')
    payload=json.dumps(config)
    if any(secret and len(secret)>5 and secret in payload for p in PROVIDERS if (secret:=credential(p))):
        raise ValueError('Credential text cannot be stored in task configuration')
    with closing(store.connect()) as db:
        db.execute("INSERT OR REPLACE INTO product_settings VALUES ('external_api_settings',?)",(payload,));db.commit()


def open_manual_openai():
    st.session_state['advanced_manual_ui']=True;st.session_state['workspace_page']='Analyze'
    st.session_state['analysis_model']='OpenAI API';st.session_state['default_analysis_mode']='OpenAI API'
    st.rerun()


def clear_confirmation():
    st.session_state.pop('_deepseek_confirmation_scope',None)
    for name in ('deepseek_test_consent','deepseek_test_consent__en','deepseek_test_consent__zh-CN'):
        st.session_state[name]=False
    st.session_state.get('_ui_mirrors',{}).pop('deepseek_test_consent',None)


def render(store):
    from .settings_ui import credential_editor,field
    from .local_credentials import credential
    c=st.session_state.setdefault('_external_api_edit',saved_external(store))
    c['provider']=field('selectbox','External API provider','external_provider',c['provider'],options=['openai','deepseek'],after_change=clear_confirmation,format_func=lambda v:Verbatim('OpenAI' if v=='openai' else 'DeepSeek'))
    credential_editor(c['provider'])
    if c['provider']=='openai':
        c['models']['openai']=field('selectbox','Supported OpenAI model','settings_openai_model',c['models']['openai'],options=OPENAI_MODELS,format_func=Verbatim)
        st.caption('OpenAI remains an explicit manual action with per-text permissions and sending confirmation.')
        st.button('Open manual OpenAI analysis',key='settings_openai_manual',on_click=open_manual_openai)
        return
    ledger=DeepSeekLedger(store);provider=DeepSeekProvider();key=credential('deepseek')
    rows=ledger.rows();models=ledger.cached_models() or []
    stopped=any(r['status'] in ('pending','unknown','failed','invalid') for r in rows)
    if not key:st.info('Waiting for a locally configured DeepSeek key.')
    if key and ledger.cached_models() is not None and not models:st.info('DeepSeek returned an empty model list; inference is unavailable.')
    if stopped:st.error('DeepSeek test stopped after an error; no automatic retry or further samples.')
    if st.button('Check connection (model list only)',key='deepseek_connect',disabled=not key or stopped):
        try:
            models=provider.models(store,api_key=key,explicit=True)
            st.session_state.pop('deepseek_ui_error',None)
            st.session_state['deepseek_connection_note']='Model-list check saved; further clicks reuse it without sending text.'
        except ModelError as error:st.session_state['deepseek_ui_error']=str(error)
        st.rerun()
    if st.session_state.get('deepseek_connection_note'):st.caption(st.session_state['deepseek_connection_note'])
    options=[m['id'] for m in models]
    locked_model=next((r['request_model'] for r in rows if r['kind']=='inference'),None)
    selected=c['models']['deepseek']
    if locked_model:selected=locked_model
    if selected and selected not in options:options.append(selected)
    c['models']['deepseek']=field('selectbox','DeepSeek model ID','settings_deepseek_model',selected or None,
        options=options,index=None,disabled=bool(locked_model) or not models,format_func=Verbatim,after_change=clear_confirmation) or ''
    budget=int(st.number_input('Maximum inferences for this action',min_value=1,max_value=3,value=3,key='deepseek_test_budget',on_change=clear_confirmation))
    with st.expander('Texts to send: authored financial samples'):
        st.caption('Only these fictional texts are sent. The real-news library is excluded.')
        for item in authored_samples():st.subheader(Verbatim(item.title));st.text(Verbatim(item.summary))
    def record_confirmation():
        st.session_state['_deepseek_confirmation_scope']=(st.session_state.get('settings_deepseek_model'),st.session_state.get('deepseek_test_budget',3))
    confirmed=st.checkbox('I confirm this action may send the displayed authored texts to DeepSeek, up to the stated paid inference limit.',
        key='deepseek_test_consent',on_change=record_confirmation,disabled=not key or not models or stopped)
    def run():
        consent=st.session_state.get('deepseek_test_consent') is True
        scope=st.session_state.get('_deepseek_confirmation_scope')
        selected=st.session_state.get('settings_deepseek_model');limit=st.session_state.get('deepseek_test_budget',3)
        clear_confirmation()
        try:
            if not consent or scope!=(selected,limit):raise ModelError('Confirm this test action and a budget of at most three inferences.',kind='consent_required')
            run_authored_test(store,provider,api_key=credential('deepseek'),model=selected,confirmed=True,budget=limit)
            st.session_state.pop('deepseek_ui_error',None)
        except ModelError as error:st.session_state['deepseek_ui_error']=str(error)
    st.button('Run controlled DeepSeek test',key='deepseek_run',type='primary',on_click=run,
        disabled=not confirmed or not key or not models or not c['models']['deepseek'] or stopped)
    if st.session_state.get('deepseek_ui_error'):st.error(st.session_state['deepseek_ui_error'])
    st.caption('Interface validation only; three authored examples are not an accuracy evaluation. Model aliases are not fixed weight versions.')
    st.caption(t('DeepSeek requests: model lists {models}/1 · inferences {inferences}/3',models=sum(r['kind']=='models' for r in rows),inferences=sum(r['kind']=='inference' for r in rows)))
    histories=[a for a in store.list_analyses() if a.provenance.get('test_scope')==SCOPE]
    if histories:
        from .dashboard_ui import article_details
        by_id={n.article_id:n for n in store.list_news()}
        identity=st.selectbox('Test result history',list(dict.fromkeys(a.article_id for a in histories)),format_func=lambda i:Verbatim(by_id[i].title),key='deepseek_history')
        matching=[a for a in histories if a.article_id==identity]
        model=st.selectbox('Results model',list(dict.fromkeys(a.model_id for a in matching)),format_func=Verbatim,key='deepseek_history_model')
        result=next(a for a in reversed(matching) if a.model_id==model)
        article_details(by_id[identity],result,store,context='deepseek_test',background=True,allow_reanalysis=False)
