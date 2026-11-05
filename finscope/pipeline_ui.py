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
from .view_preferences import restore_ui,save as persist_view,remember_page,activate_page,PAGES


def save_view(store,values=None):
    remember_page(st.session_state)
    snapshot=st.session_state.get('_library_snapshot')
    context=(snapshot['news'],snapshot['analyses']) if snapshot else None
    persist_view(store,dict(st.session_state),context=context)


def view_compute(name,news,results,options,compute):
    """Bounded session memo, cleared by live data/rights/expiry/model checks."""
    from .ui_preferences import language
    import hashlib
    snapshot=st.session_state.get('_library_snapshot')
    if snapshot is None:return compute()
    signature=hashlib.sha256(repr((name,language(),[(n.article_id,n.content_version,n.sectors) for n in news],
                    [(k,a.analysis_id) for k,a in results.items()],options)).encode()).hexdigest()
    cache=snapshot['computed']
    if signature not in cache:
        if len(cache)>=24:cache.pop(next(iter(cache)))
        cache[signature]=compute()
    return cache[signature]


def go(page,task_id=None):
    st.session_state['product_page']=None if page=='Home' else page
    if task_id:
        st.session_state['results_task']=task_id
        st.session_state['explorer_task_scope']=True


def task_message(task):
    status=task['status'];stage=task['stage']
    if status=='queued':return 'Queued','Waiting for the local worker. You can leave this page.'
    if status=='running':
        if task.get('cancel'):return 'Pausing','Waiting for the current safe checkpoint. Saved results are retained.'
        if stage.startswith('loading:'):return 'Loading','Loading the selected local model and preparing the first result.'
        label=('Preparing' if stage in ('checking saved records','preflight') else
               'Collecting' if any(v in stage for v in ('collection','fetch:')) else
               'Classifying' if any(v in stage for v in ('classif','candidates')) else
               'Saving' if stage.startswith('saving:') else 'Analyzing')
        return label,'The worker is processing this task. You can switch pages without submitting again.'
    if status in ('blocked','interrupted','cancelled'):
        return ('Blocked' if status=='blocked' else 'Paused'),'Review the reason below. Resolve it in Settings, then explicitly resume this task.'
    if status=='partial_failed':return 'Failed / partial results','Open this task’s results to inspect completed records. Review the failure before resuming.'
    return 'Completed','Open this task’s results. Reused results are listed separately from new inference.'


def task_stage(stage):
    labels={'batch finished':'Completed','finished':'Completed','checking saved records':'Preparing',
            'preflight':'Preparing','collection preflight':'Collecting','batch interrupted':'Failed / partial results',
            'analysis paused; collection retained':'Paused','cancelled; saved stages retained':'Paused',
            'cancelled':'Paused','recovering batch checkpoints':'Queued','collection saved; no model loaded':'Completed'}
    if stage in labels:return tr(labels[stage])
    prefix,separator,target=stage.partition(':')
    prefixes={'loading':'Loading','processing':'Analyzing','classification':'Classifying','classify':'Classifying',
              'sentiment':'Analyzing','collection':'Collecting','fetch':'Collecting','saving':'Saving','text / save':'Saving'}
    if separator and prefix in prefixes:return str(tr(prefixes[prefix]))+' · '+str(tr(target.strip()))
    return tr(stage)


@st.fragment(run_every=2)
def task_progress(store,show_diagnostics=True):
    if ProductStorage(store).expire():st.rerun()
    from .ui_preferences import bootstrap
    bootstrap(store)
    q=TaskQueue(store);task=q.get()
    if not task:
        if show_diagnostics:st.caption('No task yet. Update news or analyze saved records below.')
        return
    counts=task['counts'];signature=json.dumps([task['id'],task['status'],counts],sort_keys=True)
    previous=st.session_state.get('product_task_signature')
    st.session_state['product_task_signature']=signature
    # Refresh the entry form once at the terminal transition so disabled inputs
    # become usable. Running-stage/count polling only rerenders this fragment.
    if show_diagnostics and previous:
        prior=json.loads(previous)
        if prior[0]==task['id'] and prior[1] in ACTIVE and task['status'] not in ACTIVE:st.rerun()
    label,next_step=task_message(task)
    if not show_diagnostics:
        st.caption(t('Background task: {status}. Open News Update for progress and controls.',status=tr(label)))
        if previous and signature!=previous and task['status'] not in ACTIVE:st.session_state['_results_changed']=True
        if st.session_state.get('_results_changed'):
            if st.button('Refresh saved results',key='refresh_task_results'):
                st.session_state['_results_changed']=False;st.rerun()
        return
    st.subheader(t('Task status: {status}',status=tr(label)))
    st.write(next_step)
    if task['status'] in ACTIVE:st.caption(t('Current stage: {stage}',stage=task_stage(task['stage'])))
    receipts=q.outcomes(task['id'])
    total=counts.get('total')
    if total is None and task['snapshot'].get('article_ids') and not task['snapshot'].get('operation'):
        total=len(task['snapshot']['article_ids'])
    if type(total) is int and total>0:
        processed=min(total,counts.get('processed',len(receipts)))
        st.progress(processed/total,text=t('Records checked: {done}/{total} (includes reuse, skipped and failed records)',done=processed,total=total))
    else:st.caption('A reliable total is not available yet; no completion percentage is shown.')
    st.caption(t('New inference: {new} · Valid results reused: {reused} · Failed: {failed} · Skipped: {skipped}',
                 new=counts.get('analyzed',0),reused=counts.get('reused',sum(r['state']=='reused' for r in receipts.values())),failed=counts.get('failed',0),skipped=counts.get('skipped',0)))
    with st.expander('Task details',expanded=False):
        st.caption(t('Task {identity} · submitted {created}',identity=task['id'][:8],created=task['created']))
        st.caption(t('New originals: {new} · Existing originals: {duplicates} · Classified: {classified}',
                     new=counts.get('new',0),duplicates=counts.get('duplicates',0),classified=counts.get('classified',0)))
        st.caption(t('Current stage: {stage}',stage=task_stage(task['stage'])))
    if task['error']:
        st.warning(task['error'])
    if not q.worker_alive() and task['status'] in ACTIVE:st.warning('The local worker is not connected. Ask the facilitator to start it; do not submit again.')
    if task['status'] in ACTIVE:
        if st.button('Pause task',key='product_cancel',disabled=bool(task.get('cancel'))):q.cancel(task['id']);st.rerun()
    elif task['status'] in {'blocked','interrupted','cancelled','partial_failed'}:
        if st.button('Resume completed stages safely',key='product_resume'):
            try:q.resume(task['id']);st.rerun()
            except ValueError as error:st.warning(str(error))
        st.caption('Resume never reissues a failed/unknown source or inference request; successful checkpoints are reused.')
    if st.button('View this task’s results',key='task_results',on_click=go,args=('News Explorer',task['id'])):
        st.rerun()


def home(store,q):
    from html import escape
    from .product_presentation import HOME_GUIDE_STEPS,HOME_CAPABILITIES,HOME_SOURCE_CARDS,HOME_MODEL_CARDS
    from .product_theme import home_styles,home_workflow,home_capabilities
    st.markdown(home_styles(),unsafe_allow_html=True)
    st.caption('LOCAL-FIRST FINANCIAL INTELLIGENCE')
    intro,workflow=st.columns([1.05,1],gap='large')
    with intro:
        st.markdown('<section class="fs-hero"><h1>'+escape(tr('Financial news.'))+'<br><span class="fs-hero-accent">'+escape(tr('A clearer perspective.'))+'</span></h1><p>'+escape(tr('Collect permitted financial text, classify its topics, analyze sentiment and inspect originals in a persistent local workspace.'))+'</p></section>',unsafe_allow_html=True)
        left,right=st.columns(2)
        with left:st.button('Analyze existing records',type='primary',on_click=go,args=('News Update',),key='home_analyze',width='stretch')
        with right:st.button('View results',on_click=go,args=('News Explorer',),key='home_results',width='stretch')
        st.caption('Sentiment describes the text. It is not a price forecast or investment advice.')
    steps=(('sources','News Update','Choose sources, permissions and current budgets, or select permitted saved records.'),
           HOME_GUIDE_STEPS[1],HOME_GUIDE_STEPS[2],
           ('inspect','Dashboard','Inspect Industries, Knowledge Graph and News Explorer. Each page keeps its filters and selected record.'))
    with workflow:st.markdown(home_workflow(steps,compact=True),unsafe_allow_html=True)
    st.subheader('Local Product Capabilities')
    st.markdown(home_capabilities(HOME_CAPABILITIES),unsafe_allow_html=True)
    st.caption('Local defaults and configured integrations have different evidence scopes. DeepSeek is an authored-text interface test; repeated-load stability remains unverified.')
    st.subheader('How FinScope works')
    st.caption('News Update contains collection and offline analysis. Settings contains language, model management and diagnostics. Saving settings or changing filters does not collect news or run inference.')
    def cards(values):
        for title,copy in values:
            st.markdown('<article class="fs-feature"><h3>'+escape(tr(title))+'</h3><p>'+escape(tr(copy))+'</p></article>',unsafe_allow_html=True)
    with st.expander('Sources, collection modes and permissions',expanded=False):
        st.write('Broad Financial News is the default, without company or industry query filters. Selected media uses six publisher filters and Latest news only; Company Tracking uses a saved watchlist. These are collection scopes, not inferred article industries.')
        cards(HOME_SOURCE_CARDS)
        st.caption('Batches are bounded. Failed or unknown requests do not automatically retry or rotate keys; dated budgets do not renew themselves. No arbitrary-site crawl, universal full text, exhaustive coverage or unrestricted publisher rights is promised.')
    with st.expander('Models, topics and provenance',expanded=False):
        cards(HOME_MODEL_CARDS)
        st.write('DeepSeek has a controlled three-authored-text interface test; it is not the automatic real-news pipeline or an accuracy evaluation. A response alias is not a fixed weight revision.')
        st.caption('Repeated-load stability remains unverified: the later multi-round attempt was blocked by resource preflight before inference. Starting a local service or listing models is not loading a model.')
    with st.expander('Advanced collection and saved-record analysis',expanded=False):
        st.write('News Update includes collect-only and saved-record offline analysis. Persistent tasks retain checkpoints; continuation still checks expiry, permissions, model readiness and failed or unknown dispatch holds.')
        st.caption('Unknown account balance, Unclassified text and not-applicable analysis are distinct states. They are not zero quota, a company-industry guess or Neutral sentiment.')


def analysis_entry(store,q):
    from .batch_ui import saved_config
    from .source_policies import authorize
    from .batch_config import DEFAULT
    from copy import deepcopy
    c=deepcopy(saved_config(q) or q.config() or DEFAULT)
    # Offline entry carries only model/classification choices, never collection settings.
    c={k:v for k,v in c.items() if k in {'model','model_id','taxonomy','classifier_llm','classifier_options'}}
    c.update(sources=[],limit=300)
    st.caption('Use saved text only. No news request is made.')
    st.caption(t('Analysis model summary',model=str(tr(c['model']))+(' / '+c.get('model_id','') if c.get('model_id') else '')))
    items=ProductStorage(store).news();allowed={};blocked=0
    for item in items:
        try:authorize(item,('retain','local_display','local_classification','local_sentiment'))
        except ValueError:blocked+=1;continue
        allowed[item.article_id]=item
    task=q.get();active=bool(task and task['status'] in ACTIVE)
    selected=st.session_state.setdefault('_analysis_selection',list(allowed)[:300])
    st.session_state['offline_articles']=[identity for identity in selected if identity in allowed]
    def remember():
        st.session_state['_analysis_selection']=list(st.session_state['offline_articles'])
    with st.expander('Select saved records',expanded=False):
        ids=st.multiselect('Saved records to analyze',list(allowed),format_func=lambda k:Verbatim(allowed[k].title+' ['+k[:8]+']'),
                           key='offline_articles',on_change=remember,disabled=active)
    if blocked:st.info(t('{count} records need permission review or have expired. Review them in Settings.',count=blocked))
    if not allowed:st.info('No permitted saved records are available. Ask the facilitator to prepare samples, or use Settings to add permitted records.')
    review=json.dumps([c,[(identity,allowed[identity].content_version,allowed[identity].rights.reference) for identity in ids]],sort_keys=True)
    if st.session_state.get('_offline_review')!=review:
        st.session_state['_offline_review']=review
        st.session_state['offline_confirm']=False
        st.session_state.get('_ui_mirrors',{}).pop('offline_confirm',None)
    st.write(t('Selected records: {count}. Existing valid results will be reused; missing results will be analyzed.',count=len(ids)))
    ready=st.checkbox('I confirm local analysis of these selected records under their recorded permissions',key='offline_confirm',disabled=active)
    if active:st.caption('A task is already active. Follow its progress above or view saved results.')
    elif not ready:st.caption('Analysis is blocked until you confirm the selected scope. You can still view saved results.')
    if st.button('Confirm and start analysis',type='primary',key='offline_submit',disabled=active or not ready or not 1<=len(ids)<=300):
        try:
            # Re-read rights and versions at submission, not just when opening the page.
            current={n.article_id:n for n in ProductStorage(store).news()}
            for identity in ids:
                item=current.get(identity)
                if not item or item.content_version!=allowed[identity].content_version:raise ValueError('Records changed; review the selection again.')
                authorize(item,('retain','local_display','local_classification','local_sentiment'))
            identity,_=q.submit_batch('analyze',c,confirmed=True,article_ids=ids)
            st.session_state['results_task']=identity
            st.session_state['_offline_review']=None
            st.rerun()
        except ValueError as error:st.error(str(error))


def task_results(store,q):
    with closing(store.connect()) as db:
        tasks=db.execute('SELECT id,created FROM product_tasks ORDER BY rowid DESC LIMIT 30').fetchall()
    if not tasks:
        st.info('No analysis task has been submitted yet.')
        st.button('Analyze existing records',on_click=go,args=('News Update',),key='results_analyze')
    else:
        choices=dict(tasks)
        if st.session_state.get('results_task') not in choices:st.session_state['results_task']=tasks[0][0]
        identity=st.selectbox('Analysis task',list(choices),format_func=lambda k:Verbatim(choices[k]+' · '+k[:8]),key='results_task')
        task=q.get(identity);data=ProductStorage(store);ids=set(q.result_scope(task))
        from .source_policies import authorize
        news=[]
        for item in data.news():
            if item.article_id not in ids:continue
            try:authorize(item,('retain','local_display'))
            except ValueError:continue
            news.append(item)
        results=data.task_results(q,task);receipts=q.outcomes(identity)
        st.write(t('This task: {total} selected · {valid} current results available',total=len(ids),valid=len(results)))
        fresh=sum(receipts.get(k,{}).get('state')=='new' for k in results)
        st.caption(t('Result origins: {new} new · {reused} reused · {missing} without a current result',
                     new=fresh,reused=len(results)-fresh,missing=len(ids)-len(results)))
        if results:st.caption(t('Results model: {model}',model='; '.join(sorted({model_key(a) for a in results.values()}))))
        if len(results)<len(ids):st.info('Pending, blocked, expired or changed records are not shown as successful results. See the task status and record details.')
        with st.expander('Result origins and counts',expanded=False):
            st.dataframe(pd.DataFrame([{'Title':n.title,'Result origin':('New inference' if receipts.get(n.article_id,{}).get('state')=='new' else 'Reused result') if n.article_id in results else 'No current result',
                        'Sentiment':results[n.article_id].label if n.article_id in results else 'Not analyzed'} for n in news]),hide_index=True)
        catalog=load_taxonomy(task['snapshot'].get('taxonomy','US-BUSINESS-1'))
        article_list(news,results,store,data.classifications(catalog['id']),catalog,'task_results')
    if st.button('Browse all saved records',key='results_library'):
        st.session_state['explorer_task_scope']=False;st.rerun()


def update_button(q):
    from .settings_state import saved,editable
    from .news_readiness import source_plan,LABELS
    from .news_source_ui import conditions
    expected=editable(q);c=saved(q) or q.config();task=q.get()
    from .batch_ui import saved_config
    from .media_batch_ui import saved as saved_media
    batch=saved_media(q.store) or saved_config(q)
    if batch:expected=batch;c=batch
    st.caption(t('Saved sources: {sources}',sources=', '.join(LABELS.get(p,p) for p in (c or {}).get('sources',[])) or str(tr('None'))))
    if c:st.caption(t('Analysis model summary',model=str(display(c['model']))+(' / '+c.get('model_id','') if c.get('model_id') else '')))
    if not c or not c.get('sources'):st.caption('Set sources, permissions and budget in Advanced configuration before updating.')
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
    if st.session_state.get('product_page')!='News Update':
        def open_reanalysis():
            st.session_state['_reanalysis_article']=item.article_id
            go('News Update')
        st.button('Open reanalysis in News Update',key=prefix+'_open_reanalysis',on_click=open_reanalysis)
        return
    q=TaskQueue(store);c=q.config();task=q.get()
    st.caption('Uses the configured worker model; preserves every historical version.')
    from .batch_records import eligibility
    confirmed=st.checkbox('I confirm reanalysis of this original',key=prefix+'_confirm_reanalysis_'+item.article_id)
    if st.button('Queue reanalysis of this original',key=prefix+'_queue_reanalysis_'+item.article_id,disabled=not confirmed or not c or bool(task and task['status'] in ACTIVE) or not eligibility(item)[0]):
        q.submit({**c,'sources':[],'source_permissions':{},'article_ids':[item.article_id],'force_reanalysis':True});st.rerun()


def details(item,result,store,classifications,catalog,context='product',keyword=None):
    from html import escape
    c=classifications.get(item.article_id,{})
    if c.get('classifier_version','').startswith('semantic-'):
        st.caption('Topic classifier: '+c['classifier_version']+' · '+c.get('status','')+(' · '+c['unclassified_reason'] if c.get('unclassified_reason') else ''))
    from .media_use import scope_of,authorize as media_authorize
    scope=scope_of(item)
    if scope:
        try:media_authorize(item,('local_display',))
        except ValueError:st.info('Media text expired or its use scope is blocked.');return
        st.caption(('Recorded licence evidence' if scope['status']=='licensed' else 'User research use · applicability unverified · not publisher permission')+' · expires UTC '+scope['expires_at'])
        from .publisher_attribution import attribution
        a=attribution(item)
        st.caption('Collection: '+a['collection_service']+' · Supplier-reported source: '+a['supplier_reported_source']+' · Linked publisher: '+a['linked_publisher'])
        st.caption('Supplied link domain: '+a['link_domain'])
        st.caption(a['verification']+' · Editorial originality: unverified')
        if a['explicit_wire_credit']:st.caption('Supplied wire credit: '+a['explicit_wire_credit']+'; no direct wire licence or original authorship inferred')
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
        if scope:
            from .expiring_media import partition
            part=partition(store)
            with closing(part.connect()) as db:
                part.check(item,db)
                reviews=[json.loads(row[0]) for row in db.execute('SELECT payload FROM product_classification_reviews WHERE article_id=? AND cache_key=? ORDER BY created',(item.article_id,c.get('cache_key','')))]
            if reviews:st.json({'engineering_diagnosis_not_independent_labels':reviews})


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
            st.caption(t('Original records: {count}',count=len(ordered)))
            clicked=interactive_chart('articles',{'rows':article_rows(ordered,results)},key=context+'_rows',selected=current)
            st.session_state[key]=article_selection(ids,current,clicked)
            with st.expander('Accessible article picker'):
                identity=st.selectbox('Select original article',ids,format_func=lambda k:Verbatim(next(n.title for n in ordered if n.article_id==k)),key=key)
                selections[context]=identity
        with right:
            st.caption('Selected original')
            with st.container(key='story_detail_'+context):
                details(next(n for n in ordered if n.article_id==identity),results.get(identity),store,classes,catalog,context,keyword)


def cloud(news,results,store,classes,catalog,context='cloud'):
    terms=view_compute('keywords',news,{},(),lambda:keywords(news))
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
    perspective=st.radio('Graph perspective',['Industry','Company'],horizontal=True,key='graph_perspective')
    company=None
    if perspective=='Company':
        institutions={'NIST','Reserve Bank of Australia'}
        companies=sorted({e['name'] for n in news for e in classes.get(n.article_id,{}).get('entities',[]) if e['name'] not in institutions})
        company=st.selectbox('Mentioned entity',companies,index=None,format_func=Verbatim,key='graph_company')
        if not company:st.info('No selected text-evidenced company; publisher/government institutions are not presented as companies. Issuer main business remains unverified.');return
    with st.expander('Graph options and interpretation',expanded=False):
        expanded=st.checkbox('Expand graph',key='graph_expanded')
        publishers=st.checkbox('Show publisher institutions mentioned in text',value=False,key='graph_publishers')
        st.caption('Edges retain text/catalog evidence; no causal or supply-chain claims.')
    data=view_compute('graph',news,results,(catalog['id'],expanded,company,publishers),lambda:evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=30 if expanded else 8,node_limit=120 if expanded else 45,company=company,show_publisher_entities=publishers))
    full=view_compute('graph-full',news,results,(catalog['id'],company,publishers),lambda:evidence_graph(news,results,classifications=classes,taxonomy=catalog,article_limit=len(news),node_limit=100000,company=company,show_publisher_entities=publishers))
    st.caption(t('Graph coverage: {shown}/{total} nodes · {articles} originals',shown=len(data['nodes']),total=len(full['nodes']),articles=sum(n['kind']=='Article' for n in data['nodes'])))
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
    with st.expander('News keywords',expanded=False):
        with st.container(key='product_cloud'):cloud(news,results,store,classes,catalog)


def sector_plot(rows,empty_message='No classified business topics in this selection; unclassified articles remain in the library.'):
    if not rows:
        st.info(empty_message)
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
    with st.sidebar:
        st.markdown(brand(),unsafe_allow_html=True)
        st.button('Home',on_click=go,args=('Home',),key='home_navigation',width='stretch')
        if st.session_state.get('product_page') not in PAGES[1:]:st.session_state['product_page']=None
        page=st.radio('Workspace',PAGES[1:],key='product_page',index=None,width='stretch') or 'Home'
        st.caption('Local SQLite · persistent originals and model history')
    st.title(page)
    activate_page(st.session_state,page)
    task=q.get()
    if page!='Settings' or task and task['status'] in ACTIVE:task_progress(store,page=='News Update')
    if page=='Settings':
        settings(store,q)
        save_view(store);return
    if page=='Home':
        home(store,q);save_view(store);return
    if page=='News Update':
        with st.container(key='update_actions'):
            update,offline=st.columns(2,gap='large')
            with update:
                with st.container(border=True):
                    st.subheader('Update news')
                    st.caption('Collect from saved sources, then analyze permitted text.')
                    update_button(q)
            with offline:
                with st.container(border=True):
                    st.subheader('Analyze saved records')
                    analysis_entry(store,q)
        st.button('View results',on_click=go,args=('News Explorer',),key='analysis_results')
        selected=st.session_state.get('_reanalysis_article')
        if selected:
            item=next((n for n in data.news() if n.article_id==selected),None)
            if item:
                with st.expander('Reanalyze this original',expanded=True):
                    st.write(Verbatim(item.title));reanalyze(item,store)
        from .settings_ui import render as configuration
        from .batch_ui import controls
        from .media_ui import controls as media_controls
        with st.expander('Advanced configuration',expanded=False):
            with st.expander('News collection configuration',expanded=False):
                configuration(store,q,section_override='sources')
            controls(q)
            media_controls(store)
        save_view(store);return
    if page=='News Explorer' and st.session_state.get('explorer_task_scope'):
        task_results(store,q);save_view(store);return
    for key,value in st.session_state.get('product_view_preferences',{}).items():
        if key not in st.session_state:st.session_state[key]=value
    def reset_page():
        from .view_preferences import view_key
        for key in list(st.session_state):
            if view_key(key.split('__')[0]):st.session_state.pop(key,None)
        for key in list(st.session_state.get('_ui_mirrors',{})):
            if view_key(key):st.session_state['_ui_mirrors'].pop(key,None)
        # Explicit values also clear React's retained widget display after Reset.
        # Deleting a key alone can leave the old text/selection on screen.
        st.session_state.update(local_search='',product_taxonomy=(q.config() or {}).get('taxonomy','US-BUSINESS-1'))
        st.session_state.setdefault('page_views',{})[page]={}
    kpis=st.container(key='product_kpis') if page=='Dashboard' else None
    with st.container(key='analysis_toolbar'):
        search,reset=st.columns([3,1],vertical_alignment='bottom')
        search_slot=search.container()
        with reset:st.button('Reset filters',on_click=reset_page,key='reset_page_filters',width='stretch')
    with st.expander('Filters and model',expanded=False):
        st.caption('Filters apply only to this page and are kept when you return.')
        c=q.config() or {};mode=st.selectbox('Classification mode (view)',list(CATALOGS),index=list(CATALOGS).index(c.get('taxonomy','US-BUSINESS-1')),key='product_taxonomy')
        catalog=load_taxonomy(mode)
        with search_slot,st.spinner('Loading saved records and checking current permissions…'):
            snapshot=data.view_snapshot(st.session_state,mode)
        classes=snapshot['classes'][mode]
        from .classification_scheme import selected as selected_scheme,cache_key as classifier_key
        scheme=selected_scheme(store) if mode=='US-BUSINESS-1' else None
        signature=classifier_key(scheme) if scheme else 'legacy-rules'
        if st.session_state.get('_classification_view_key')!=signature:
            for key in ('product_children','local_sectors','graph_selected','industry_selected','heatmap_selected'):
                st.session_state.pop(key,None)
                st.session_state.get('_ui_mirrors',{}).pop(key,None)
                for presentation in list(st.session_state):
                    if presentation.startswith(key+'__'):st.session_state.pop(presentation,None)
            st.session_state['_classification_view_key']=signature
        if scheme:st.caption('Finite-media classification version: '+signature+' · sentiment history unchanged')
        news=snapshot['news']
        all_record_count=len(news)
        with st.expander('Development records',expanded=False):include_dev=st.checkbox('Include synthetic development records',value=False,key='product_include_dev')
        if not include_dev:news=[n for n in news if n.provider!='authored_synthetic']
        library_news=list(news);states=snapshot['states']
        missing=sum(n.article_id not in classes for n in news)
        if missing:
            st.info(f"{missing}/{len(news)} originals have no saved classification for {mode}; industry relevance is not yet determined.")
        news=view_compute('project',news,{},mode,lambda:project_news(news,classes,catalog))
        current={n.article_id:n for n in news}
        analyses=data.visible_analyses(news,snapshot['analyses'])
        parent_names=[node_label(n) for n in catalog['nodes'] if n['parent_id'] is None]+['Unclassified']
        from .local_analytics import result_models
        choices=result_models(analyses)
        preferred=st.session_state.get('product_preferred_model') or c.get('result_model_key')
        if preferred and preferred not in choices:choices.append(preferred)
        if preferred and 'local_result_model' not in st.session_state and 'local_result_model' not in st.session_state.get('filter_preferences',{}):
            st.session_state['local_result_model']=preferred
        import hashlib
        widget_key='product_result_model_'+hashlib.sha256(c.get('result_model_key','default').encode()).hexdigest()[:10]
        with st.container(key='product_filters'):
            news,results,start,end=shared_filters(news,analyses,sector_options=parent_names,model_choices=choices,model_widget_key=widget_key,search_container=search_slot)
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
    unclassified=sum(n.sectors==('Unclassified',) for n in news)
    statuses={n.article_id:analysis_status(n,results.get(n.article_id),states) for n in news}
    not_applicable=sum(v=='Not applicable' for v in statuses.values())
    if page=='Dashboard':st.caption(t('{unclassified} Unclassified · {na} Not applicable',unclassified=unclassified,na=not_applicable))
    else:st.caption(t('Selection: {records} records · {analyzed} analyzed · {unclassified} Unclassified · {na} Not applicable',
                     records=len(news),analyzed=len(results),unclassified=unclassified,na=not_applicable))
    st.caption(t('Results model: {model}',model=str(display(st.session_state.get('local_result_model','')))))
    active=[label for key,label in (('local_sectors','Sectors'),('local_sources','Sources'),('local_sentiments','Sentiment'),
            ('product_children','Subindustries'),('batch_status_filter','Analysis status')) if st.session_state.get(key)]
    if kind!='all':active.append('Source type scope')
    dates=sorted(n.published_day for n in library_news if n.published_day)
    if dates and (start.isoformat(),end.isoformat())!=(dates[0],dates[-1]):active.append('Date range')
    if not st.session_state.get('local_unknown_dates',True):active.append('Exclude unknown publication dates')
    if include_dev:active.append('Development records')
    if active:st.caption(t('Active filters: {filters}',filters=' · '.join(str(tr(v)) for v in active)))
    attention={label:sum(v==label for v in statuses.values())
               for label in ('Permission required','Failed','Blocked')}
    if any(attention.values()):st.warning(' · '.join(str(tr(label))+': '+str(count) for label,count in attention.items() if count))
    coverage=st.expander('Data coverage and counts',expanded=False)
    with coverage:
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
    rows=view_compute('industry',chart_news,chart_results,mode,lambda:industry_rows(chart_news,chart_results,classes,catalog)) if page in ('Dashboard','Industries') else []
    visible_topic_count=(sum(r['Articles']>0 for r in view_compute('industry',news,results,mode,lambda:industry_rows(news,results,classes,catalog)) if r['Parent']) if page=='Dashboard' else 0)
    if page=='Dashboard':
        with kpis:
            record_labels=(['Original records','Analyzed records'] if any(source_type(n)=='regulatory_disclosure' for n in news)
                           else ['Original articles','Analyzed articles'])
            for col,label,value in zip(st.columns(4),[*record_labels,'Business topics','Sources'],[len(news),len(results),visible_topic_count,len({n.source for n in news})]):
                with col:st.metric(label,value)
        with coverage:
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
        with st.container(key='product_chart_sector'):
            st.subheader('Industry sentiment')
            sector_plot([r for r in rows if r['Articles'] and (r['ID'] in child_ids if child_ids else True)],
                        empty_message='No saved industry assignments in this selection; originals awaiting classification remain below.')
        visible=[r for r in rows if r['Articles'] and (r['ID'] in child_ids if child_ids else True)]
        if visible:
            with st.expander('Industry counts and definitions',expanded=False):
                st.dataframe(pd.DataFrame([{'Industry':r['Industry'],'Articles':r['Articles'],'Analyzed':r['Articles']-r['Not analyzed'],
                    **{k:r[k] for k in ('Positive','Neutral','Negative','Not analyzed')}} for r in visible]),hide_index=True,width='stretch')
                st.caption('Parent counts deduplicate article IDs across child topics. Unknown sector is not CSRC S/91.')
        st.subheader('Original records')
        article_list(chart_news,chart_results,store,classes,catalog,'industries')
    elif page=='Knowledge Graph':network(chart_news,chart_results,store,classes,catalog)
    else:
        st.subheader('Original records')
        article_list(news,results,store,classes,catalog,'explorer')
    save_view(store,dict(st.session_state))
