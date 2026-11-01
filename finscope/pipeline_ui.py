"""Local product shell: UI submits durable jobs, worker owns all automatic inference."""
from dataclasses import replace
from contextlib import closing
from datetime import datetime,timezone,date
import json
import pandas as pd
from .localized_ui import st
from .i18n import t,tr,display,Verbatim,node_name

from .task_queue import TaskQueue,ACTIVE
from .product_storage import ProductStorage
from .taxonomy import CATALOGS,load_taxonomy,node_label
from .product_analytics import project_news,industry_rows
from .local_analytics import evidence_graph,graph_members,model_key
from .dashboard_ui import (shared_filters,distribution_chart,timeline_chart,heatmap,related_articles,article_details)
from .chart_interactions import interactive_chart,chart_scope
from .text_processing import keywords
from .product_theme import TOKENS,COLORS,plot,brand,status_markup
from .product_presentation import article_selection,article_rows,keyword_snippets
from .view_preferences import restore_ui,save as save_view

PAGES=['Dashboard','Industries','Knowledge Graph','News Explorer','Settings']


@st.fragment(run_every=2)
def task_progress(store,show_diagnostics=True):
    if ProductStorage(store).expire():st.rerun()
    from .ui_preferences import bootstrap
    bootstrap(store)
    q=TaskQueue(store);task=q.get()
    if not task:return
    counts=task['counts'];signature=json.dumps([task['id'],task['status'],counts],sort_keys=True)
    previous=st.session_state.get('product_task_signature')
    st.session_state['product_task_signature']=signature
    st.markdown(status_markup(task['status'],task['stage'],counts),unsafe_allow_html=True)
    if task['error']:
        st.warning('Some stages need attention; completed results are retained.')
        if show_diagnostics:
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
    from .settings_state import saved,editable
    from .news_readiness import source_plan,LABELS
    from .news_source_ui import conditions
    expected=editable(q);c=saved(q) or q.config();task=q.get()
    from .batch_ui import saved_config
    from .media_batch_ui import saved as saved_media
    batch=saved_media(q.store) or saved_config(q)
    if batch:expected=batch;c=batch
    unsaved=not batch and st.session_state.get('_settings_edit',expected)!=expected
    if unsaved:st.caption('Unsaved changes')
    if st.button('Update & Analyze',type='primary',disabled=unsaved or not c or not c.get('sources') or bool(task and task['status'] in ACTIVE),key='product_update'):
        ready,blocked=source_plan(q.store,expected)
        st.session_state['_update_review']={'config':expected,'ready':ready,'blocked':blocked}
        st.session_state.pop('_product_submit_error',None)
    review=st.session_state.get('_update_review')
    if review:
        with st.container(border=True):
            st.subheader('Review update')
            st.write(t('Runnable sources',sources=', '.join(LABELS.get(p,p) for p in review['ready']) or str(tr('None'))))
            for provider,state in review['blocked'].items():
                st.caption(t('Skipped source',source=LABELS.get(provider,provider),reason=conditions(state)))
            config=review['config']
            st.write(t('Analysis model summary',model=str(display(config['model']))+(' / '+config.get('model_id','') if config.get('model_id') else '')))
            if saved(q) and not batch:st.caption('This review uses the saved draft.')
            model_ready=config['model'] in ('Local FinBERT','Local LM Studio','Local Ollama') and (config['model']=='Local FinBERT' or bool(config.get('model_id')))
            if st.button('Confirm update and analysis',key='product_confirm_update',disabled=not review['ready'] or not model_ready or unsaved or bool(task and task['status'] in ACTIVE)):
                try:
                    if batch:
                        if (saved_media(q.store) or saved_config(q))!=config:raise ValueError('Batch settings changed; review again')
                        ready,_=source_plan(q.store,config)
                        if ready!=review['ready']:raise ValueError('Source readiness changed; review again')
                        q.submit_batch('update',{**config,'sources':ready},confirmed=True)
                    else:q.submit_ready(confirmed=True,expected_sources=review['ready'],expected_config=config)
                    st.session_state.pop('_update_review',None);st.rerun()
                except ValueError as error:st.session_state['_product_submit_error']=str(error)
            if st.button('Cancel',key='product_cancel_review'):st.session_state.pop('_update_review',None);st.rerun()
            if not q.worker_alive():st.caption('Local worker is not connected. Start FinScope with launch_local.ps1; queued tasks wait without issuing requests.')
    if st.session_state.get('_product_submit_error'):st.error(st.session_state['_product_submit_error'])


def settings(store,q):
    from .settings_ui import render
    render(store,q)


def reanalyze(item,store,prefix='product'):
    q=TaskQueue(store);c=q.config();task=q.get()
    st.caption('Uses the configured worker model; preserves every historical version.')
    from .batch_records import eligibility
    if st.button('Queue reanalysis of this original',key=prefix+'_queue_reanalysis_'+item.article_id,disabled=not c or bool(task and task['status'] in ACTIVE) or not eligibility(item)[0]):
        q.submit({**c,'sources':[],'source_permissions':{},'article_ids':[item.article_id],'force_reanalysis':True});st.rerun()


def details(item,result,store,classifications,catalog,context='product',keyword=None):
    from html import escape
    c=classifications.get(item.article_id,{})
    from .media_use import scope_of,authorize as media_authorize
    scope=scope_of(item)
    if scope:
        try:media_authorize(item,('local_display',))
        except ValueError:st.info('Media text expired or its use scope is blocked.');return
        st.caption(('Recorded licence evidence' if scope['status']=='licensed' else 'User research use · applicability unverified · not publisher permission')+' · expires UTC '+scope['expires_at'])
        from urllib.parse import urlsplit
        if item.provider=='finnhub' and (urlsplit(item.url).hostname or '').endswith('finnhub.io'):
            st.caption('Finnhub supplied redirect link · reported source: '+item.source+' · original publication domain and editorial originality unverified')
    from .batch_records import eligibility,source_type,TYPES
    st.caption(TYPES[source_type(item)]+(' · '+item.document_type if item.document_type else ''))
    eligible,reason=eligibility(item)
    if not eligible:st.info('Sentiment not applicable: '+reason)
    if item.cik:
        st.write({'issuer':item.company,'ticker':item.ticker,'CIK':item.cik,
                  'filed_date':item.filed_date,'disclosed_at':item.disclosed_at,'disclosure_precision':item.disclosure_precision,
                  'issuer_reported_industry':item.issuer_industry})
        st.caption('Issuer SIC describes the issuer, not the industries discussed in this disclosure. Topic labels below require literal text evidence.')
    lookup={n['id']:n for n in catalog['nodes']}
    st.caption(Verbatim(' · '.join(node_name(lookup[v['id']]) for v in c.get('labels',[]))) or t('Unclassified'))
    def text(n):
        if not n.rights.preview:st.warning('Local preview permission is unavailable.');return
        if keyword:
            for snippet in keyword_snippets(n,keyword):
                st.caption(t('Keyword match · {v0}',v0=tr(snippet['field'])))
                st.markdown('<p class="fs-match-excerpt">'+snippet['html']+'</p>',unsafe_allow_html=True)
        content=n.body or n.summary
        if content:
            st.caption('Permitted article body' if n.body else 'Supplied summary')
            st.markdown('<div class="fs-news-copy">'+escape(content)+'</div>',unsafe_allow_html=True)
    article_details(item,result,store,context=context,background=True,content_renderer=text)
    with st.expander('Classification evidence'):
        st.json({'current':c,'history':ProductStorage(store).classification_history(item.article_id,catalog['id'])})


def article_list(news,results,store,classes,catalog,context,keyword=None):
    if not news:st.info('No matching original articles.');return
    ordered=sorted(news,key=lambda n:(n.published_day,n.article_id),reverse=True)
    with st.container(key='story_layout_'+context):
        left,right=st.columns([1.1,1.4],gap='large')
        ids=[n.article_id for n in ordered];key=context+'_article'
        # Widget cleanup on another page must not discard the logical choice.
        selections=st.session_state.setdefault('selected_articles',{})
        current=article_selection(ids,st.session_state.get(key,selections.get(context)))
        with left:
            clicked=interactive_chart('articles',{'rows':article_rows(ordered,results)},key=context+'_rows',selected=current)
            st.session_state[key]=article_selection(ids,current,clicked)
            with st.expander('Accessible article picker'):
                identity=st.selectbox('Select original article',ids,format_func=lambda k:Verbatim(next(n.title for n in ordered if n.article_id==k)),key=key)
                selections[context]=identity
        with right:
            with st.container(key='story_detail_'+context):
                details(next(n for n in ordered if n.article_id==identity),results.get(identity),store,classes,catalog,context,keyword)


def cloud(news,results,store,classes,catalog,context='cloud'):
    terms=keywords(news)
    if not terms:st.info('No keywords in this selection.');return
    clicked=interactive_chart('cloud',{'terms':terms},key=context,selected=st.session_state.get(context+'_fallback') or st.session_state.get(context+'_selected'))
    if clicked:
        st.session_state[context+'_selected']=clicked
        st.session_state[context+'_fallback']=clicked
    words=[v['term'] for v in terms]
    if st.session_state.get(context+'_fallback') not in words:st.session_state.pop(context+'_fallback',None)
    selected=st.selectbox('Accessible keyword list',words,index=None,key=context+'_fallback')
    selected=clicked or selected or st.session_state.get(context+'_selected')
    term=next((v for v in terms if v['term']==selected),None)
    st.caption('Weights count distinct originals containing the term; article text only, never model rationales.')
    if term:
        st.subheader('Keyword: '+term['term'])
        article_list([n for n in news if n.article_id in term['article_ids']],results,store,classes,catalog,context+'_matches',keyword=term['term'])


def network(news,results,store,classes,catalog):
    perspective=st.radio('Graph perspective',['Industry','Company'],horizontal=True)
    company=None
    if perspective=='Company':
        institutions={'NIST','Reserve Bank of Australia'}
        companies=sorted({e['name'] for n in news for e in classes.get(n.article_id,{}).get('entities',[]) if e['name'] not in institutions})
        company=st.selectbox('Mentioned entity',companies,index=None,format_func=Verbatim)
        if not company:st.info('No selected text-evidenced company; publisher/government institutions are not presented as companies. Issuer main business remains unverified.');return
    expanded=st.checkbox('Expand graph')
    publishers=st.checkbox('Show publisher institutions mentioned in text',value=False)
    data=evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=30 if expanded else 8,node_limit=120 if expanded else 45,company=company,show_publisher_entities=publishers)
    full=evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=len(news),node_limit=100000,company=company,show_publisher_entities=publishers)
    st.caption(f"Showing {len(data['nodes'])}/{len(full['nodes'])} nodes; {sum(n['kind']=='Article' for n in data['nodes'])} displayed originals. Edges retain text/catalog evidence; no causal or supply-chain claims.")
    scope=chart_scope('graph',data)
    if st.session_state.get('product_graph_scope')!=scope:st.session_state['product_graph_selected']=None;st.session_state['product_graph_scope']=scope
    with st.container(key='product_map'):
        clicked=interactive_chart('graph',data,key='product_graph',selected=st.session_state.get('product_graph_selected'))
    if clicked:st.session_state['product_graph_selected']=clicked
    selection=st.session_state.get('product_graph_selected')
    # Keep later component delta paths stable when selected-node details expand.
    # Moving an unchanged iframe can leave its host registration stale/blank.
    with st.container():
        if selection:
            members=graph_members(full,selection);node=next(n for n in data['nodes'] if n['id']==selection)
            st.subheader(display(node['label']) if node['kind'] in {'Sector','Subindustry','Keyword theme'} else Verbatim(node['label']))
            article_list([n for n in news if n.article_id in members],results,store,classes,catalog,'graph_related')
            with st.expander('Selected relationship evidence'):st.json([e for e in full['edges'] if e['from']==selection or e['to']==selection])
    with st.expander('Accessible graph node selector'):
        accessible=st.selectbox('Graph node',data['nodes'],index=None,format_func=lambda n:Verbatim(str(tr(n['kind']))+' · '+str(display(n['label']) if n['kind'] in {'Sector','Subindustry','Keyword theme'} else n['label'])))
        if accessible:
            ids=graph_members(full,accessible['id']);article_list([n for n in news if n.article_id in ids],results,store,classes,catalog,'graph_accessible')
    with st.container(key='product_cloud'):
        st.subheader('News keywords');cloud(news,results,store,classes,catalog)


def sector_plot(rows):
    if not rows:
        st.info('No classified business topics in this selection; unclassified articles remain in the library.')
        return
    values=[{'Industry':r['Industry'],'Sentiment':s,'Articles':r[s]} for r in rows for s in ('Positive','Neutral','Negative','Not analyzed')]
    upper=max(1,max(sum(r[s] for s in ('Positive','Neutral','Negative','Not analyzed')) for r in rows))
    plot({'data':{'values':values},'mark':{'type':'bar','cornerRadiusEnd':3},'encoding':{
        'y':{'field':'Industry','type':'nominal','title':None},'x':{'field':'Articles','type':'quantitative','title':'Distinct local originals','scale':{'domain':[0,upper]},'axis':{'tickMinStep':1}},
        'color':{'field':'Sentiment','type':'nominal','scale':{'domain':['Positive','Neutral','Negative','Not analyzed'],'range':list(COLORS)}},
        'tooltip':[{'field':'Industry'},{'field':'Sentiment'},{'field':'Articles'}]},'height':max(230,len(rows)*30)},width='stretch')


def main():
    from .product_ui import local_store
    from .product_theme import css
    st.set_page_config(page_title='FinScope | Local News Intelligence',page_icon='📈',layout='wide')
    store=local_store();q=TaskQueue(store);data=ProductStorage(store)
    from .ui_preferences import bootstrap,toolbar
    bootstrap(store);st.markdown(css(),unsafe_allow_html=True);toolbar(store)
    restore_ui(store,st.session_state)
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
    task=q.get()
    if page!='Settings' or task and task['status'] in ACTIVE:task_progress(store,page!='Settings')
    if page=='Settings':
        save_view(store,dict(st.session_state));settings(store,q);return
    for key,value in st.session_state.get('product_view_preferences',{}).items():
        if key not in st.session_state:st.session_state[key]=value
    update_button(q)
    from .batch_ui import controls
    controls(q)
    from .media_ui import controls as media_controls
    media_controls(store)
    kpis=st.container(key='product_kpis') if page=='Dashboard' else None
    c=q.config() or {};mode=st.selectbox('Classification mode (view)',list(CATALOGS),index=list(CATALOGS).index(c.get('taxonomy','US-BUSINESS-1')),key='product_taxonomy')
    catalog=load_taxonomy(mode);classes=data.classifications(mode)
    news=data.news()
    all_record_count=len(news)
    with st.expander('Development records',expanded=False):include_dev=st.checkbox('Include synthetic development records',value=False,key='product_include_dev')
    if not include_dev:news=[n for n in news if n.provider!='authored_synthetic']
    library_news=list(news);states=data.states()
    missing=sum(n.article_id not in classes for n in news)
    if missing:
        st.info(f"{missing}/{len(news)} originals have no saved classification for {mode}; industry relevance is not yet determined.")
    news=project_news(news,classes,catalog)
    current={n.article_id:n for n in news}
    analyses=[a for a in data.analyses() if a.article_id in current and (not current[a.article_id].content_version or a.provenance.get('content_sha256')==current[a.article_id].content_version)]
    parent_names=[node_label(n) for n in catalog['nodes'] if n['parent_id'] is None]+['Unclassified']
    from .local_analytics import result_models
    choices=result_models(data.analyses())
    preferred=st.session_state.get('product_preferred_model') or c.get('result_model_key')
    if preferred and preferred not in choices:choices.append(preferred)
    if preferred and 'local_result_model' not in st.session_state and 'local_result_model' not in st.session_state.get('filter_preferences',{}):
        st.session_state['local_result_model']=preferred
    import hashlib
    widget_key='product_result_model_'+hashlib.sha256(c.get('result_model_key','default').encode()).hexdigest()[:10]
    with st.container(key='product_filters'):
        news,results,start,end=shared_filters(news,analyses,sector_options=parent_names,model_choices=choices,model_widget_key=widget_key)
    from .batch_records import TYPES,source_type,analysis_status,statistics
    kind=st.selectbox('Source type scope',['all',*TYPES],format_func=lambda k:Verbatim('All types (separate counts)' if k=='all' else TYPES[k]),key='batch_source_type_filter')
    if kind!='all':news=[n for n in news if source_type(n)==kind]
    status_filter=st.multiselect('Analysis status',['Analyzed','Not analyzed','Not applicable','Permission required','Failed','Blocked'],key='batch_status_filter')
    if status_filter:news=[n for n in news if analysis_status(n,results.get(n.article_id),states) in status_filter]
    results={n.article_id:results[n.article_id] for n in news if n.article_id in results}
    children=[n for n in catalog['nodes'] if n['parent_id'] and (not st.session_state.get('local_sectors') or node_label(next(p for p in catalog['nodes'] if p['id']==n['parent_id'])) in st.session_state['local_sectors'])]
    valid=[n['id'] for n in children]
    if any(k not in valid for k in st.session_state.get('product_children',[])):st.session_state['product_children']=[k for k in st.session_state['product_children'] if k in valid]
    child_ids=st.multiselect('Subindustries',valid,format_func=lambda k:node_label(next(n for n in children if n['id']==k)),key='product_children')
    st.session_state['product_view_preferences']={k:st.session_state[k] for k in ('product_taxonomy','product_children','product_include_dev','batch_source_type_filter','batch_status_filter','batch_chart_type') if k in st.session_state}
    if child_ids:news=[n for n in news if set(child_ids)&{v['id'] for v in classes.get(n.article_id,{}).get('labels',[])}];results={n.article_id:results[n.article_id] for n in news if n.article_id in results}
    st.caption(f"{sum(n.sectors==('Unclassified',) for n in news)} unclassified originals · {len(news)-len(results)} without a current selected-model result; neither is Neutral by default.")
    st.caption('Counts below use distinct local originals and keep media, company releases, regulatory disclosures and government announcements separate.')
    st.dataframe(pd.DataFrame(statistics(news,results,classes,states)),hide_index=True,width='stretch')
    chart_news=news;chart_results=results
    kinds=[k for k in TYPES if any(source_type(n)==k for n in news)]
    if len(kinds)>1 and page!='News Explorer':
        if st.session_state.get('batch_chart_type') not in kinds:st.session_state.pop('batch_chart_type',None)
        chart_kind=st.selectbox('Chart source type',kinds,format_func=lambda k:Verbatim(TYPES[k]),key='batch_chart_type')
        chart_news=[n for n in news if source_type(n)==chart_kind];chart_results={n.article_id:results[n.article_id] for n in chart_news if n.article_id in results}
        st.caption(f'Chart denominator: {TYPES[chart_kind]} · {len(chart_news)} distinct records. Other source types are compared in the counts table.')
    rows=industry_rows(chart_news,chart_results,classes,catalog)
    visible_topic_count=sum(r['Articles']>0 for r in industry_rows(news,results,classes,catalog) if r['Parent'])
    if page=='Dashboard':
        with kpis:
            record_labels=(['Original records','Analyzed records'] if any(source_type(n)=='regulatory_disclosure' for n in news)
                           else ['Original articles','Analyzed articles'])
            for col,label,value in zip(st.columns(4),[*record_labels,'Business topics','Sources'],[len(news),len(results),visible_topic_count,len({n.source for n in news})]):
                with col:st.metric(label,value)
            from .batch_records import eligibility
            for col,label,value in zip(st.columns(4),['Local total records','Media news records','Regulatory disclosures','Analyzable records'],
                [all_record_count,sum(source_type(n)=='media_news' for n in library_news),sum(source_type(n)=='regulatory_disclosure' for n in library_news),sum(eligibility(n)[0] for n in news)]):
                with col:st.metric(label,value)
            if not include_dev and all_record_count>len(library_news):st.caption(f'{all_record_count-len(library_news)} authored development records are excluded from real-source counts and charts.')
        if not news:
            st.info('No real originals match these filters. Set sources or widen the date range.')
            save_view(store,dict(st.session_state));return
        with st.container(key='product_dashboard_charts'):
            left,right=st.columns([1.5,1])
            with left:
                with st.container(key='product_chart_sector'):
                    st.subheader('Industry sentiment');sector_plot([r for r in rows if not r['Parent'] and r['Articles']])
            with right:
                with st.container(key='product_chart_mix'):
                    st.subheader('Text sentiment')
                    if chart_results:distribution_chart(chart_results)
                    else:st.info('No selected-model results; missing analysis is not Neutral.')
            with st.container(key='product_chart_time'):
                st.subheader('News over time');timeline_chart(chart_news,chart_results,start,end)
            with st.container(key='product_chart_heatmap'):
                heatmap(chart_news,chart_results,start,end,store,sectors_override=parent_names,background=True)
    elif page=='Industries':
        sector_plot([r for r in rows if r['Articles'] and (r['ID'] in child_ids if child_ids else True)])
        visible=[r for r in rows if r['Articles'] and (r['ID'] in child_ids if child_ids else True)]
        if visible:
            st.dataframe(pd.DataFrame([{'Industry':r['Industry'],'Articles':r['Articles'],'Analyzed':r['Articles']-r['Not analyzed'],
                **{k:r[k] for k in ('Positive','Neutral','Negative','Not analyzed')}} for r in visible]),hide_index=True,width='stretch')
        else:st.info('No saved industry assignments in this selection; originals awaiting classification remain below.')
        st.caption('Parent counts deduplicate article IDs across child topics. Unknown sector is not CSRC S/91.')
        article_list(chart_news,chart_results,store,classes,catalog,'industries')
    elif page=='Knowledge Graph':network(chart_news,chart_results,store,classes,catalog)
    else:article_list(news,results,store,classes,catalog,'explorer')
    save_view(store,dict(st.session_state))
