"""Local product shell: UI submits durable jobs, worker owns all automatic inference."""
from dataclasses import replace
from contextlib import closing
from datetime import datetime,timezone,date
import json
import pandas as pd
import streamlit as st

from .task_queue import TaskQueue,ACTIVE
from .product_storage import ProductStorage
from .taxonomy import CATALOGS,load_taxonomy,node_label
from .product_analytics import project_news,industry_rows
from .local_analytics import evidence_graph,graph_members,model_key
from .dashboard_ui import (shared_filters,distribution_chart,timeline_chart,heatmap,related_articles,article_details)
from .chart_interactions import interactive_chart,chart_scope
from .text_processing import keywords
from .product_theme import TOKENS,COLORS,plot,brand,status_markup

PAGES=['Dashboard','Industries','Knowledge Graph','News Explorer','Settings']


@st.fragment(run_every=2)
def task_progress(store):
    q=TaskQueue(store);task=q.get()
    if not task:return
    counts=task['counts'];signature=json.dumps([task['id'],task['status'],counts],sort_keys=True)
    previous=st.session_state.get('product_task_signature')
    st.session_state['product_task_signature']=signature
    st.markdown(status_markup(task['status'],task['stage'],counts),unsafe_allow_html=True)
    if task['error']:
        st.warning('Some stages need attention; completed results are retained.')
        with st.expander('Task diagnostics'):st.write(task['error'])
    if not q.worker_alive() and task['status'] in ACTIVE:st.warning('Worker heartbeat unavailable. Launch through launch_local.ps1; a running task is identified as interrupted on worker restart.')
    if task['status'] in ACTIVE:
        if st.button('Stop task',key='product_cancel'):q.cancel(task['id']);st.rerun(scope='fragment')
    elif task['status'] in {'blocked','interrupted','cancelled','partial_failed'}:
        if st.button('Resume completed stages safely',key='product_resume'):
            q.resume(task['id']);st.rerun()
        st.caption('Resume never reissues a failed/unknown source or inference request; successful checkpoints are reused.')
    if previous and signature!=previous:
        # Full rerender reloads SQL populations without resetting widget filters.
        with closing(store.connect()) as db:
            st.session_state['new_news_ids']=[r[0] for r in db.execute('SELECT article_id FROM product_content WHERE created>=?',(task['created'],))]
        st.rerun()


def update_button(q):
    c=q.config();task=q.get()
    st.button('更新并分析',type='primary',disabled=not c or bool(task and task['status'] in ACTIVE),on_click=lambda:q.submit(),key='product_update')
    if c:st.caption(', '.join(c['sources'])+' · '+c['model']+(' / '+c.get('model_id','') if c.get('model_id') else '')+f" · ≤{c['limit']} records/source")
    else:st.info('Complete source and local model setup in Settings once, then use 更新并分析.')
    if not q.worker_alive():st.caption('Local worker is not connected. Start FinScope with launch_local.ps1; queued tasks wait without issuing requests.')
    if c:
        from .local_collectors import SOURCES
        from .local_news import LocalIngestionService
        service=LocalIngestionService(q.store)
        for source in c['sources']:
            bucket=SOURCES.get(source,{}).get('bucket','rba' if source.startswith('rba_') else source)
            status=service.source_status(bucket,configured=True)
            if status.blocked:st.warning(source+' · '+status.reason+'; other permitted sources can continue.')


def settings(store,q):
    from .local_collectors import SOURCES
    from .local_news import ContentRights
    from .model_ui import controls
    from .local_credentials import vault_key,credential
    from .api_sources import project_env_path
    from .product_ui import about
    c=q.config() or {'sources':['nist_rss','abs_html'],'model':'Local FinBERT','model_id':'','taxonomy':'US-BUSINESS-1','limit':6,'budgets':{},'source_permissions':{},'classifier_llm':False}
    st.subheader('Automatic processing')
    choices=[k for k,v in SOURCES.items() if v.get('enabled',True)]+['marketaux','newsdata','finnhub']
    sources=st.multiselect('Enabled sources',choices,default=c['sources'],format_func=lambda k:SOURCES.get(k,{}).get('label',k))
    limit=st.number_input('Maximum parsed records per source',min_value=1,max_value=20,value=c['limit'])
    budgets={};permissions={}
    for source in sources:
        with st.expander('Source · '+source):
            if source in SOURCES:
                s=SOURCES[source];st.caption(s['scope']);st.write(s.get('license','RBA official information: source-level local text permission, third-party exceptions apply'))
                from .local_news import LocalIngestionService
                status=LocalIngestionService(store).source_status(s.get('bucket','rba'),configured=True)
                st.caption(status.state+' · '+status.reason)
                st.caption(s.get('attribution','Source: Reserve Bank of Australia')+' · '+s.get('exclusions','No third-party material, media or separately restricted content'))
                st.caption(f"HTTP/action ≤{s.get('body_http_budget',s.get('http_budget',2))}; body pages ≤{s.get('body_limit',0)}; no retries/pagination. Existing 60-second spacing / 3 actions per UTC day remain.")
                if s.get('terms_url'):st.link_button('Source use policy',s['terms_url'])
            else:
                if source=='newsdata':st.warning('NewsData is manually paused in code; enabling it cannot remove that pause.')
                st.caption('Worker credentials: Windows Credential Manager, then project .env. Never part of a job snapshot.')
                st.text(str(project_env_path()))
                st.caption('Credential read: '+('yes' if credential(source) else 'no'))
                secret=st.text_input(source+' API key',type='password',key='product_secret_'+source,max_chars=500)
                if st.button('Save '+source+' key to Windows Credential Manager',disabled=not secret,key='vault_'+source):
                    vault_key(source,secret);st.success('Saved in Windows Credential Manager; existing .env unchanged.')
                old=c.get('source_permissions',{}).get(source,{})
                reference=st.text_input('Storage/NLP permission reference',value=old.get('reference',''),max_chars=500,key='permission_ref_'+source)
                preview=st.checkbox('Permission includes local preview',value=old.get('preview',False),key='permission_preview_'+source)
                retain=st.checkbox('Permission includes local storage',value=old.get('retain',False),key='permission_retain_'+source)
                nlp=st.checkbox('Permission includes local NLP',value=old.get('analyze',False),key='permission_nlp_'+source)
                permissions[source]=dict(preview=preview,retain=retain,analyze=nlp,external=False,reference=reference)
                b=c.get('budgets',{}).get(source,{})
                day=st.date_input('Quota verification UTC date',value=date.fromisoformat(b.get('utc_day',datetime.now(timezone.utc).date().isoformat())),key='budget_day_'+source)
                remaining=st.number_input('Verified request allowance for this UTC day (existing attempts count against it)',0,10000,b.get('remaining',0),key='budget_'+source)
                topic=st.selectbox('API topic',['technology','healthcare','materials'],index=['technology','healthcare','materials'].index(b.get('topic','technology')),key='topic_'+source)
                symbol=st.text_input('Finnhub ticker',value=b.get('symbol',''),max_chars=15,key='symbol_'+source) if source=='finnhub' else ''
                budgets[source]=dict(utc_day=day.isoformat(),remaining=int(remaining),topic=topic,symbol=symbol)
    st.session_state.setdefault('pipeline_model',c['model'])
    if c['model']=='Local LM Studio' and c.get('model_id') in st.session_state.get('lmstudio_models',{}):
        if not st.session_state.get('pipeline_lmstudio_model'):st.session_state['pipeline_lmstudio_model']=c['model_id']
    if c['model']=='Local Ollama' and c.get('model_id') in st.session_state.get('installed_ollama_models',{}):
        st.session_state.setdefault('pipeline_ollama_model',c['model_id'])
    options=controls('pipeline',store=store)
    if options.mode=='OpenAI API':st.info('Paid transmission remains a separate explicit advanced action; automatic background runs accept local models only.')
    taxonomy=st.selectbox('Classification mode',list(CATALOGS),index=list(CATALOGS).index(c['taxonomy']),format_func=lambda k:'US business · 11 / 56' if k=='US-BUSINESS-1' else 'CSRC JR/T 0020—2024 · 19 / 91')
    enhanced=st.checkbox('Use selected local LM Studio model to verify classification candidates',value=c.get('classifier_llm',False),disabled=options.mode!='Local LM Studio')
    st.caption('English sentiment is verified; other languages stay unsupported until a suitable selected model is explicitly verified. Text sentiment is not a stock-return forecast.')
    if st.button('Save automatic configuration',disabled=not sources or not options.ready or options.mode=='OpenAI API'):
        try:
            q.configure(dict(sources=sources,model=options.mode,model_id=options.model or '',taxonomy=taxonomy,limit=int(limit),classifier_llm=enhanced,source_permissions=permissions,budgets=budgets,result_model_key=options.result_key()))
            st.session_state['product_taxonomy']=taxonomy
            family={'Local FinBERT':'FinBERT','Local LM Studio':'Local LM Studio','Local Ollama':'Local Ollama'}[options.mode]
            matching=[a for a in store.list_analyses() if a.family==family and (not options.model or a.model_id==options.model)]
            selected_key=model_key(matching[-1]) if matching else options.result_key()
            st.session_state['local_result_model']=selected_key
            st.session_state.setdefault('filter_preferences',{})['local_result_model']=selected_key
            st.session_state['product_preferred_model']=selected_key
            st.success('Configuration saved. Use 更新并分析 on any results page.')
        except ValueError as error:st.error(str(error))
    with st.expander('Help / methods / diagnostics'):
        about()
        with closing(store.connect()) as db:
            history=db.execute('SELECT status,stage,counts,error,created FROM product_tasks ORDER BY rowid DESC LIMIT 20').fetchall()
        if history:st.dataframe(pd.DataFrame(history,columns=['Status','Stage','Counts','Reason','Created UTC']),hide_index=True,width='stretch')
    with st.expander('Advanced approved text and manual provider preview'):
        st.caption('Retained manual preview, approved text and explicit external-model actions.')
        if st.button('Open advanced manual workspace'):
            st.session_state['advanced_manual_ui']=True;st.session_state['workspace_page']='Add news';st.rerun()


def reanalyze(item,store,prefix='product'):
    q=TaskQueue(store);c=q.config();task=q.get()
    st.caption('Uses the configured worker model; preserves every historical version.')
    if st.button('Queue reanalysis of this original',key=prefix+'_queue_reanalysis_'+item.article_id,disabled=not c or bool(task and task['status'] in ACTIVE) or not item.rights.analyze):
        q.submit({**c,'sources':[],'source_permissions':{},'article_ids':[item.article_id],'force_reanalysis':True});st.rerun()


def details(item,result,store,classifications,catalog,context='product'):
    c=classifications.get(item.article_id,{})
    lookup={n['id']:n for n in catalog['nodes']}
    st.caption(' · '.join(node_label(lookup[v['id']]) for v in c.get('labels',[])) or 'Unclassified / 二级未知')
    article_details(item,result,store,context=context,background=True)
    if item.body:
        with st.expander('Permitted locally saved article body'):st.text(item.body)
    if result and result.provenance.get('span_end'):
        p=result.provenance;st.caption(f"Analyzed {p.get('analysis_basis')} characters {p.get('span_start')}–{p.get('span_end')} / {p.get('source_characters')}; {p.get('aggregation')}")
    with st.expander('Classification evidence'):
        st.json({'current':c,'history':ProductStorage(store).classification_history(item.article_id,catalog['id'])})


def article_list(news,results,store,classes,catalog,context):
    if not news:st.info('No matching original articles.');return
    ordered=sorted(news,key=lambda n:(n.published_day,n.article_id),reverse=True)
    left,right=st.columns([1,1.4])
    with left:
        ids=[n.article_id for n in ordered]
        key=context+'_article'
        if st.session_state.get(key) not in ids:st.session_state.pop(key,None)
        identity=st.selectbox('Select original article',ids,format_func=lambda k:next(n.title for n in ordered if n.article_id==k),key=key)
        st.dataframe(pd.DataFrame([{'Title':n.title,'Source':n.source,'Published':n.published_day or 'Unknown','Sentiment':results[n.article_id].label if n.article_id in results else 'Not analyzed'} for n in ordered]),hide_index=True,width='stretch')
    with right:details(next(n for n in ordered if n.article_id==identity),results.get(identity),store,classes,catalog,context)


def cloud(news,results,store,classes,catalog,context='cloud'):
    terms=keywords(news)
    if not terms:st.info('No keywords in this selection.');return
    clicked=interactive_chart('cloud',{'terms':terms},key=context,selected=st.session_state.get(context+'_selected'))
    if clicked:st.session_state[context+'_selected']=clicked
    words=[v['term'] for v in terms]
    if st.session_state.get(context+'_fallback') not in words:st.session_state.pop(context+'_fallback',None)
    selected=st.selectbox('Accessible keyword list',words,index=None,key=context+'_fallback')
    selected=clicked or selected or st.session_state.get(context+'_selected')
    term=next((v for v in terms if v['term']==selected),None)
    st.caption('Weights count distinct originals containing the term; article text only, never model rationales.')
    if term:
        st.subheader('Keyword: '+term['term'])
        article_list([n for n in news if n.article_id in term['article_ids']],results,store,classes,catalog,context+'_matches')


def network(news,results,store,classes,catalog):
    perspective=st.radio('Graph perspective',['Industry','Company'],horizontal=True)
    company=None
    if perspective=='Company':
        institutions={'NIST','Reserve Bank of Australia'}
        companies=sorted({e['name'] for n in news for e in classes.get(n.article_id,{}).get('entities',[]) if e['name'] not in institutions})
        company=st.selectbox('Mentioned entity',companies,index=None)
        if not company:st.info('No selected text-evidenced company; publisher/government institutions are not presented as companies. Issuer main business remains unverified.');return
    expanded=st.checkbox('Expand graph')
    publishers=st.checkbox('Show publisher institutions mentioned in text',value=False)
    data=evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=30 if expanded else 8,node_limit=120 if expanded else 45,company=company,show_publisher_entities=publishers)
    full=evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=len(news),node_limit=100000,company=company,show_publisher_entities=publishers)
    st.caption(f"Showing {len(data['nodes'])}/{len(full['nodes'])} nodes; {sum(n['kind']=='Article' for n in data['nodes'])} displayed originals. Edges retain text/catalog evidence; no causal or supply-chain claims.")
    scope=chart_scope('graph',data)
    if st.session_state.get('product_graph_scope')!=scope:st.session_state['product_graph_selected']=None;st.session_state['product_graph_scope']=scope
    clicked=interactive_chart('graph',data,key='product_graph',selected=st.session_state.get('product_graph_selected'))
    if clicked:st.session_state['product_graph_selected']=clicked
    selection=st.session_state.get('product_graph_selected')
    # Keep later component delta paths stable when selected-node details expand.
    # Moving an unchanged iframe can leave its host registration stale/blank.
    with st.container():
        if selection:
            members=graph_members(full,selection);node=next(n for n in data['nodes'] if n['id']==selection)
            st.subheader(node['label'])
            article_list([n for n in news if n.article_id in members],results,store,classes,catalog,'graph_related')
            with st.expander('Selected relationship evidence'):st.json([e for e in full['edges'] if e['from']==selection or e['to']==selection])
    with st.expander('Accessible graph node selector'):
        accessible=st.selectbox('Graph node',data['nodes'],index=None,format_func=lambda n:n['kind']+' · '+n['label'])
        if accessible:
            ids=graph_members(full,accessible['id']);article_list([n for n in news if n.article_id in ids],results,store,classes,catalog,'graph_accessible')
    st.subheader('News keywords');cloud(news,results,store,classes,catalog)


def sector_plot(rows):
    if not rows:
        st.info('No classified business topics in this selection; unclassified articles remain in the library.')
        return
    values=[{'Industry':r['Industry'],'Sentiment':s,'Articles':r[s]} for r in rows for s in ('Positive','Neutral','Negative','Not analyzed')]
    upper=max(1,max(sum(r[s] for s in ('Positive','Neutral','Negative','Not analyzed')) for r in rows))
    plot({'data':{'values':values},'mark':{'type':'bar','cornerRadiusEnd':3},'encoding':{
        'y':{'field':'Industry','type':'nominal','title':None},'x':{'field':'Articles','type':'quantitative','title':'Distinct local originals','scale':{'domain':[0,upper]}},
        'color':{'field':'Sentiment','type':'nominal','scale':{'domain':['Positive','Neutral','Negative','Not analyzed'],'range':COLORS}},
        'tooltip':[{'field':'Industry'},{'field':'Sentiment'},{'field':'Articles'}]},'height':max(230,len(rows)*30)},width='stretch')


def main():
    from .product_ui import local_store
    from .product_theme import css
    st.set_page_config(page_title='FinScope | Local News Intelligence',page_icon='📈',layout='wide');st.markdown(css(),unsafe_allow_html=True)
    store=local_store();q=TaskQueue(store);data=ProductStorage(store)
    if not store.setting('guide_completed',False):
        st.title('Welcome to FinScope')
        for column,title,text in zip(st.columns(4),['Configure once','Update and analyze','Explore industries','Inspect originals'],
            ['Choose sources, permissions, current quota and a local model in Settings.',
             'One button submits a persistent worker task; closing the tab does not stop it.',
             'Use shared publication dates, two-level industries and one results model.',
             'Inspect text, evidence and model history; open the original link.']):
            with column:st.subheader(title);st.write(text)
        if st.button('Get Started',type='primary'):
            store.set_setting('guide_completed',True);st.session_state['product_page']='Settings';st.rerun()
        return
    with st.sidebar:
        st.markdown(brand(),unsafe_allow_html=True)
        page=st.radio('Workspace',PAGES,key='product_page',label_visibility='collapsed',width='stretch')
        st.caption('Local SQLite · persistent originals and model history')
    st.title(page)
    task_progress(store)
    if page=='Settings':settings(store,q);return
    for key,value in st.session_state.get('product_view_preferences',{}).items():
        if key not in st.session_state:st.session_state[key]=value
    update_button(q)
    c=q.config() or {};mode=st.selectbox('Classification mode (view)',list(CATALOGS),index=list(CATALOGS).index(c.get('taxonomy','US-BUSINESS-1')),key='product_taxonomy')
    catalog=load_taxonomy(mode);classes=data.classifications(mode)
    news=data.news()
    with st.expander('Development records',expanded=False):include_dev=st.checkbox('Include synthetic development records',value=False,key='product_include_dev')
    if not include_dev:news=[n for n in news if n.provider!='authored_synthetic']
    news=project_news(news,classes,catalog)
    current={n.article_id:n for n in news}
    analyses=[a for a in store.list_analyses() if a.article_id in current and (not current[a.article_id].content_version or a.provenance.get('content_sha256')==current[a.article_id].content_version)]
    parent_names=[node_label(n) for n in catalog['nodes'] if n['parent_id'] is None]+['Unclassified']
    from .local_analytics import result_models
    choices=result_models(store.list_analyses())
    preferred=st.session_state.get('product_preferred_model') or c.get('result_model_key')
    if preferred and preferred not in choices:choices.append(preferred)
    if preferred and 'local_result_model' not in st.session_state and 'local_result_model' not in st.session_state.get('filter_preferences',{}):
        st.session_state['local_result_model']=preferred
    import hashlib
    widget_key='product_result_model_'+hashlib.sha256(c.get('result_model_key','default').encode()).hexdigest()[:10]
    news,results,start,end=shared_filters(news,analyses,sector_options=parent_names,model_choices=choices,model_widget_key=widget_key)
    children=[n for n in catalog['nodes'] if n['parent_id'] and (not st.session_state.get('local_sectors') or node_label(next(p for p in catalog['nodes'] if p['id']==n['parent_id'])) in st.session_state['local_sectors'])]
    valid=[n['id'] for n in children]
    if any(k not in valid for k in st.session_state.get('product_children',[])):st.session_state['product_children']=[k for k in st.session_state['product_children'] if k in valid]
    child_ids=st.multiselect('Subindustries',valid,format_func=lambda k:node_label(next(n for n in children if n['id']==k)),key='product_children')
    st.session_state['product_view_preferences']={k:st.session_state[k] for k in ('product_taxonomy','product_children','product_include_dev') if k in st.session_state}
    if child_ids:news=[n for n in news if set(child_ids)&{v['id'] for v in classes.get(n.article_id,{}).get('labels',[])}];results={n.article_id:results[n.article_id] for n in news if n.article_id in results}
    st.caption(f"{sum(n.sectors==('Unclassified',) for n in news)} unclassified originals · {len(news)-len(results)} without a current selected-model result; neither is Neutral by default.")
    rows=industry_rows(news,results,classes,catalog)
    if page=='Dashboard':
        with st.container(key='product_kpis'):
            for col,label,value in zip(st.columns(4),['Original articles','Analyzed articles','Business topics','Sources'],[len(news),len(results),sum(r['Articles']>0 for r in rows if r['Parent']),len({n.source for n in news})]):col.metric(label,value)
        if not news:st.info('No real originals match these filters. Set sources or widen the date range.');return
        with st.container(key='product_dashboard_charts'):
            left,right=st.columns([1.5,1])
            with left:
                with st.container(key='product_chart_sector'):
                    st.subheader('Industry sentiment');sector_plot([r for r in rows if not r['Parent'] and r['Articles']])
            with right:
                with st.container(key='product_chart_mix'):
                    st.subheader('Text sentiment')
                    if results:distribution_chart(results)
                    else:st.info('No selected-model results; missing analysis is not Neutral.')
            with st.container(key='product_chart_time'):
                st.subheader('News over time');timeline_chart(news,results,start,end)
            with st.container(key='product_chart_heatmap'):
                heatmap(news,results,start,end,store,sectors_override=parent_names,background=True)
    elif page=='Industries':
        sector_plot([r for r in rows if r['Articles'] and (r['ID'] in child_ids if child_ids else True)])
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.caption('Parent counts deduplicate article IDs across child topics. Unknown sector is not CSRC S/91.')
        article_list(news,results,store,classes,catalog,'industries')
    elif page=='Knowledge Graph':network(news,results,store,classes,catalog)
    else:article_list(news,results,store,classes,catalog,'explorer')
