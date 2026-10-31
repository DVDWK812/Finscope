"""Three source cards and one editor; all default status reads are metadata-only."""
from datetime import date,datetime,timezone
import hashlib,json
from .localized_ui import st
from .i18n import t,tr,display,Verbatim
from .news_readiness import LABELS,key_metadata,source_readiness,verify_api,latest_receipt
from .local_news import LocalIngestionService,FetchBlocked


def conditions(state,compact=False):
    labels={'primary':'Primary key','local':'Local key check','preview':'Preview permission','processing':'Storage and NLP permission',
            'quota':'Today’s request allowance','ticker':'Finnhub ticker','enabled':'Enable this source for automatic collection'}
    missing=[str(tr(labels[k])) if k!='hold' else str(tr(state['hold_reason'])) for k in state['missing']]
    return t('Missing conditions',missing=', '.join(missing)) if missing else tr('Ready')


def card_state(provider,state):
    if provider=='newsdata':return 'Manual pause'
    if state['hold_reason'] or state['quota_exhausted']:return 'Request restricted'
    return 'Ready' if state['ready'] else 'Needs configuration'


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
    with st.container(key='news_source_cards'):columns=st.columns(3)
    for column,provider in zip(columns,LABELS):
        info=key_metadata(store,provider);primary=info['primary']
        state=source_readiness(store,provider,c,target='preview',service=service)
        with column,st.container(border=True,key='news_source_card_'+provider):
            st.subheader(LABELS[provider])
            st.caption('Enabled' if provider in c['sources'] else 'Disabled')
            st.write(t('Primary summary',name=tr(primary['name']) if primary and primary['slot_id']=='legacy' else primary['name'] if primary else tr('No primary key')))
            st.caption(t('Backup count',count=info['backups']))
            st.write(card_state(provider,state))
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
        terms={'marketaux':'https://www.marketaux.com/tos','finnhub':'https://finnhub.io/terms-of-service','newsdata':'https://newsdata.io/terms'}
        accounts={'marketaux':'https://www.marketaux.com/login','finnhub':'https://finnhub.io/','newsdata':'https://newsdata.io/'}
        left,right=st.columns(2)
        with left:st.link_button('Provider terms',terms[provider])
        with right:st.link_button('Account usage',accounts[provider])
        p=c['source_permissions'].get(provider,{})
        reference=field('text_input','Usage basis','settings_permission_ref_'+provider,p.get('reference',''),max_chars=500,after_change=parameters_changed,placeholder=terms[provider],help='Use your account terms for personal preview; storage and NLP require their own permission.')
        preview=field('checkbox','Permission includes local preview','settings_preview_'+provider,p.get('preview',False),after_change=parameters_changed)
        retain=field('checkbox','Permission includes local storage','settings_retain_'+provider,p.get('retain',False),after_change=parameters_changed)
        analyze=field('checkbox','Permission includes local NLP','settings_analyze_'+provider,p.get('analyze',False),after_change=parameters_changed)
        b=c['budgets'].get(provider,{})
        day=field('date_input','Quota verification UTC date','settings_day_'+provider,date.fromisoformat(b.get('utc_day',datetime.now(timezone.utc).date().isoformat())),after_change=parameters_changed)
        remaining=int(field('number_input','FinScope request budget for this UTC day','settings_budget_'+provider,b.get('remaining',0),min_value=0,max_value=10000,after_change=parameters_changed,help='Confirm account availability first. This local budget includes existing attempts; one new test needs existing attempts plus one.'))
        topic=field('selectbox','API topic','settings_topic_'+provider,b.get('topic','technology'),options=['technology','healthcare','materials'],after_change=parameters_changed)
        symbol=field('text_input','Finnhub ticker','settings_ticker',b.get('symbol',''),max_chars=15,after_change=parameters_changed) if provider=='finnhub' else ''
        sync_profiles(c,st.session_state.get('_settings_values',{}))
    target=st.radio('Check readiness for',['preview','pipeline'],format_func=lambda k:'API preview only' if k=='preview' else 'Fetch and analyze',key='news_target_'+provider,horizontal=True)
    state=source_readiness(store,provider,c,target=target,service=service)
    st.write(conditions(state))
    preview=source_readiness(store,provider,c,target='preview',service=service)
    signature=hashlib.sha256(json.dumps([preview['keys']['primary'],c['source_permissions'].get(provider),c['budgets'].get(provider)],sort_keys=True).encode()).hexdigest()[:16]
    confirmation='news_api_confirm_'+provider+'_'+signature
    consent=st.checkbox('I confirm preview permission and one request within the verified allowance',key=confirmation)
    if st.button('Verify API once',key='news_api_verify_'+provider,disabled=not consent or not preview['ready']):
        from .news_key_ui import clear_input
        clear_input(confirmation)
        try:
            selected=preview['keys']['primary']
            report=verify_api(store,provider,c,confirmed=True,expected_selection={k:selected[k] for k in ('slot_id','credential_ref')},details=True)
            st.session_state['news_api_preview_'+provider]={'ref':{k:selected[k] for k in ('slot_id','credential_ref')},'items':report.pop('items')}
            st.session_state.pop('news_api_result_'+provider,None)
            st.session_state.pop('news_keys_'+provider+'_notice',None)
        except ValueError as error:
            st.session_state['news_api_result_'+provider]=str(error) if isinstance(error,FetchBlocked) else 'API check failed; provider holds are retained.'
        except Exception:
            st.session_state['news_api_result_'+provider]='Request outcome needs review; no automatic retry.'
        st.rerun()
    if st.session_state.get('news_api_result_'+provider):st.error(st.session_state['news_api_result_'+provider])
    receipt=latest_receipt(store,provider)
    if receipt:
        (st.success if receipt['status']=='ok' else st.error)('API check succeeded' if receipt['status']=='ok' else 'API check failed; provider holds are retained.')
        st.caption(t('API receipt',http=str(receipt['http_status']) if receipt['http_status'] is not None else tr('Not observed'),returned=receipt['returned'],previewed=receipt['previewed'],time=receipt['requested_utc']))
    previous=st.session_state.get('news_api_preview_'+provider,{})
    selected=preview['keys']['primary']
    if selected and previous.get('ref')=={k:selected[k] for k in ('slot_id','credential_ref')} and c.get('source_permissions',{}).get(provider,{}).get('preview'):
        with st.expander('News preview',expanded=False):
            for item in previous.get('items',[]):
                st.write(Verbatim(item.title));st.caption(Verbatim(item.source+' · '+(item.timestamp or item.publication_date or str(tr('Unknown time')))))
                st.text(Verbatim(item.summary or str(tr('Summary unavailable'))))
                if item.url:st.link_button('Open original article',item.url)
            process_preview(store,provider,previous.get('items',[]))


def process_preview(store,provider,items):
    """Explicit one-article handoff; a receipt alone can never supply a record."""
    if not items:return
    from .local_news import ContentRights
    from .task_queue import TaskQueue,ACTIVE
    q=TaskQueue(store);task=q.get();prefix='retained_preview_'+provider
    st.caption('Reuse this session preview without another API request. Only the selected permitted fields are saved and analyzed with local FinBERT.')
    selected=st.selectbox('Select one preview article',range(len(items)),index=None,
        format_func=lambda i:Verbatim(items[i].title),key=prefix+'_article')
    scope=st.radio('Permitted API text', ['title','title_summary'],
        format_func=lambda v:'Headline only' if v=='title' else 'Headline and API summary',key=prefix+'_scope')
    reference=st.text_input('Article storage and NLP permission reference',key=prefix+'_reference',max_chars=500)
    retain=st.checkbox('Permission covers local storage of the selected fields',key=prefix+'_retain')
    analyze=st.checkbox('Permission covers local NLP of the selected fields',key=prefix+'_analyze')
    signature=hashlib.sha256(json.dumps([items[selected].article_id if selected is not None else None,
        scope,reference,retain,analyze]).encode()).hexdigest()[:16]
    confirmation=prefix+'_confirmed_'+signature
    confirmed=st.checkbox('I confirm this article and permitted text scope',key=confirmation)
    disabled=(selected is None or not reference.strip() or not retain or not analyze or not confirmed
              or bool(task and task['status'] in ACTIVE))
    if st.button('Analyze selected preview locally',key=prefix+'_submit',disabled=disabled):
        try:
            identity,created=q.submit_preview(items[selected],ContentRights(True,retain,analyze,False,reference),scope=scope,confirmed=confirmed)
            if created:
                st.session_state[prefix+'_queued']=identity
                from .news_key_ui import clear_input
                clear_input(confirmation)
                st.rerun()
            else:st.warning('Another task is active; this preview was not submitted.')
        except ValueError:st.error('Preview processing blocked; check the selected fields, article permissions and existing restrictions.')
    if st.session_state.get(prefix+'_queued'):
        st.success('Selected preview queued for local FinBERT; no API fetch was submitted.')
        if not q.worker_alive():st.caption('Local worker is not connected. Start FinScope with launch_local.ps1; queued tasks wait without issuing requests.')
