"""Three source cards and one editor; all default status reads are metadata-only."""
from datetime import date,datetime,timezone
import hashlib,json
from .localized_ui import st
from .i18n import t,tr,display,Verbatim
from .news_readiness import LABELS,LOCAL,API,CONDITIONS,key_metadata,source_readiness,verify_api,storage_label
from .local_news import LocalIngestionService,FetchBlocked


def conditions(state,compact=False):
    def names(keys):
        return ', '.join(str(tr(CONDITIONS[k])) for k in keys) or str(tr('None'))
    missing=names(state['missing'])
    if state['hold_reason']:missing+=' · '+str(tr(state['hold_reason']))
    if compact:return t('Readiness count',done=len(state['complete']),total=len(state['complete'])+len(state['missing']),missing=missing)
    return t('Conditions summary',done=names(state['complete']),missing=missing)


def sync_profiles(c,values):
    """Keep disabled-source parameters without enabling or dispatching it."""
    for provider in LABELS:
        ref='settings_permission_ref_'+provider
        if ref not in values:continue
        prior=c['source_permissions'].get(provider,{})
        p=dict(preview=bool(values.get('settings_preview_'+provider,prior.get('preview',False))),retain=bool(values.get('settings_retain_'+provider,prior.get('retain',False))),
               analyze=bool(values.get('settings_analyze_'+provider,prior.get('analyze',False))),external=False,reference=values[ref])
        if provider in c['source_permissions'] or any(p.values()):c['source_permissions'][provider]=p
        prior=c['budgets'].get(provider,{})
        day=values.get('settings_day_'+provider,date.fromisoformat(prior.get('utc_day',datetime.now(timezone.utc).date().isoformat())))
        b=dict(utc_day=day.isoformat(),remaining=int(values.get('settings_budget_'+provider,prior.get('remaining',0))),topic=values.get('settings_topic_'+provider,prior.get('topic','technology')),symbol=values.get('settings_ticker',prior.get('symbol','')) if provider=='finnhub' else '')
        if provider in c['budgets'] or b['remaining'] or b['symbol'] or b['topic']!='technology':c['budgets'][provider]=b


def render(store,c,field):
    from .local_collectors import SOURCES
    service=LocalIngestionService(store)
    sync_profiles(c,st.session_state.get('_settings_values',{}))
    st.caption('Source cards use saved metadata; opening this page does not read credentials or test APIs.')
    with st.container(key='news_source_cards'):columns=st.columns(3)
    for column,provider in zip(columns,LABELS):
        info=key_metadata(store,provider);primary=info['primary']
        state=source_readiness(store,provider,c,service=service)
        with column,st.container(border=True,key='news_source_card_'+provider):
            st.subheader(LABELS[provider])
            st.caption('Enabled' if provider in c['sources'] else 'Disabled')
            st.write(t('Primary summary',name=tr(primary['name']) if primary and primary['slot_id']=='legacy' else primary['name'] if primary else tr('No primary key')))
            st.caption(t('Backup count',count=info['backups']))
            st.caption(t('Local status summary',state=tr(storage_label(primary)) if primary else tr('Missing locally')))
            st.caption(t('API status summary',state=tr(API[primary['api_state']]) if primary else tr('Not tested')))
            st.write('Automatic collection ready' if state['ready'] else 'Automatic collection not ready')
            st.caption(conditions(state,compact=True))
            if st.button('Manage',key='settings_edit_'+provider):
                st.session_state['settings_edit_source']=provider
    with st.expander('Collection settings',expanded=False):
        registered=[k for k,v in SOURCES.items() if v.get('enabled',True)]
        local=field('multiselect','Local news sources','settings_collectors',[s for s in c['sources'] if s in SOURCES],
                    options=registered,format_func=lambda k:SOURCES[k].get('label',k))
        c['sources']=[*local,*[p for p in LABELS if p in c['sources']]]
        c['limit']=int(field('number_input','Records per source','settings_limit',c['limit'],min_value=1,max_value=20))
        for source in local:
            s=SOURCES[source]
            st.write(Verbatim(str(display(s.get('label',source)))))
            if st.button('Modify configuration',key='settings_edit_'+source):st.session_state['settings_edit_source']=source
    provider=st.session_state.get('settings_edit_source')
    if provider not in LABELS:
        if provider in SOURCES:
            s=SOURCES[provider];st.subheader(s['label']);st.caption(s['scope'])
            st.link_button('Source use policy',s.get('terms_url','https://www.rba.gov.au/copyright/'))
        return
    st.subheader(t('Configure {source}',source=LABELS[provider]))
    def enabled_change():
        if st.session_state['settings_enable_'+provider] and provider not in c['sources']:c['sources'].append(provider)
        elif not st.session_state['settings_enable_'+provider]:c['sources']=[p for p in c['sources'] if p!=provider]
    field('checkbox','Enable this source for automatic collection','settings_enable_'+provider,provider in c['sources'],after_change=enabled_change)
    from .news_key_ui import render as keys
    keys(store,provider)
    def parameters_changed():sync_profiles(c,st.session_state.get('_settings_values',{}))
    with st.expander('Permissions and request parameters',expanded=False):
        p=c['source_permissions'].get(provider,{})
        reference=field('text_input','Storage/NLP permission reference','settings_permission_ref_'+provider,p.get('reference',''),max_chars=500,after_change=parameters_changed)
        preview=field('checkbox','Permission includes local preview','settings_preview_'+provider,p.get('preview',False),after_change=parameters_changed)
        retain=field('checkbox','Permission includes local storage','settings_retain_'+provider,p.get('retain',False),after_change=parameters_changed)
        analyze=field('checkbox','Permission includes local NLP','settings_analyze_'+provider,p.get('analyze',False),after_change=parameters_changed)
        b=c['budgets'].get(provider,{})
        day=field('date_input','Quota verification UTC date','settings_day_'+provider,date.fromisoformat(b.get('utc_day',datetime.now(timezone.utc).date().isoformat())),after_change=parameters_changed)
        remaining=int(field('number_input','Verified request allowance for this UTC day (existing attempts count against it)','settings_budget_'+provider,b.get('remaining',0),min_value=0,max_value=10000,after_change=parameters_changed))
        topic=field('selectbox','API topic','settings_topic_'+provider,b.get('topic','technology'),options=['technology','healthcare','materials'],after_change=parameters_changed)
        symbol=field('text_input','Finnhub ticker','settings_ticker',b.get('symbol',''),max_chars=15,after_change=parameters_changed) if provider=='finnhub' else ''
        sync_profiles(c,st.session_state.get('_settings_values',{}))
    target=st.radio('Check readiness for',['preview','pipeline'],format_func=lambda k:'API preview only' if k=='preview' else 'Fetch and analyze',key='news_target_'+provider,horizontal=True)
    state=source_readiness(store,provider,c,target=target,service=service)
    st.write(conditions(state))
    preview=source_readiness(store,provider,c,target='preview',service=service)
    st.caption('API verification checks the primary key once and may consume one request. No model runs and no articles are saved.')
    signature=hashlib.sha256(json.dumps([preview['keys']['primary'],c['source_permissions'].get(provider),c['budgets'].get(provider)],sort_keys=True).encode()).hexdigest()[:16]
    confirmation='news_api_confirm_'+provider+'_'+signature
    consent=st.checkbox('I confirm preview permission and one request within the verified allowance',key=confirmation)
    if st.button('Verify API once',key='news_api_verify_'+provider,disabled=not consent or not preview['ready']):
        from .news_key_ui import clear_input
        clear_input(confirmation)
        try:
            selected=preview['keys']['primary']
            status,count=verify_api(store,provider,c,confirmed=True,expected_selection={k:selected[k] for k in ('slot_id','credential_ref')})
            st.session_state['news_api_result_'+provider]=('API check succeeded' if status=='ok' else 'API check failed; provider holds are retained.')
            st.session_state.pop('news_keys_'+provider+'_notice',None)
        except ValueError as error:
            st.session_state['news_api_result_'+provider]=str(error) if isinstance(error,FetchBlocked) else 'API check failed; provider holds are retained.'
        st.rerun()
    if st.session_state.get('news_api_result_'+provider):st.info(st.session_state['news_api_result_'+provider])
