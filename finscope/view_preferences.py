"""Small allowlisted view preferences, separate from pipeline configuration."""
from contextlib import closing
from datetime import date
import json
from .taxonomy import load_taxonomy,CATALOGS,node_label

PAGES=['Home','News Update','Dashboard','Industries','Knowledge Graph','News Explorer','Settings']
ARTICLE_CONTEXTS=('explorer','industries','heatmap','heatmap_unknown','graph_related','graph_accessible','cloud_matches','task_results')
VIEW_KEYS=('local_dates','local_sectors','local_search','local_sources','local_sentiments',
           'local_unknown_dates','local_result_model','filter_preferences','product_view_preferences',
           'product_taxonomy','product_children','product_include_dev','batch_source_type_filter',
           'batch_status_filter','batch_chart_type','_classification_view_key','product_graph_selected',
           'product_graph_scope','graph_perspective','graph_company','graph_expanded','graph_publishers',
           'cloud_selected','cloud_fallback','heatmap_measure','heatmap_selected','heatmap_scope')


def view_key(key):
    return key in VIEW_KEYS or key.startswith('product_result_model_') or key in {c+'_article' for c in ARTICLE_CONTEXTS}


def remember_page(state):
    from copy import deepcopy
    page=state.get('_active_view_page')
    if page:state.setdefault('page_views',{})[page]={k:deepcopy(v) for k,v in state.items() if view_key(k)}


def activate_page(state,page):
    """Swap page-local widget values before rendering, retaining logical copies."""
    from copy import deepcopy
    if state.get('_active_view_page')==page:return
    remember_page(state)
    for key in list(state):
        if view_key(key.split('__')[0]):state.pop(key,None)
    mirrors=state.get('_ui_mirrors',{})
    for key in list(mirrors):
        if view_key(key):mirrors.pop(key,None)
    for key,value in state.get('page_views',{}).get(page,{}).items():state[key]=deepcopy(value)
    state['_active_view_page']=page


def normalize(raw,store,*,nested=False,context=None):
    from .local_analytics import result_models
    if context is None:context=(store.list_news(),store.list_analyses())
    mode=raw.get('product_taxonomy','US-BUSINESS-1')
    mode=mode if mode in CATALOGS else 'US-BUSINESS-1'
    catalog=load_taxonomy(mode)
    aliases={value:node_label(n) for n in catalog['nodes'] if not n['parent_id']
             for value in (n['id'],n['name_en'],n['name_zh'],node_label(n))}
    choices={'local_sectors':{node_label(n) for n in catalog['nodes'] if not n['parent_id']}|{'Unclassified'},
             'product_children':{n['id'] for n in catalog['nodes'] if n['parent_id']},
             'local_sources':{n.source for n in context[0]},'local_sentiments':{'Positive','Neutral','Negative'}}
    result={'product_taxonomy':mode}
    from .batch_records import TYPES
    for key in ('batch_source_type_filter','batch_chart_type'):
        if raw.get(key) in {'all',*TYPES}:result[key]=raw[key]
    statuses={'Analyzed','Not analyzed','Not applicable','Permission required','Failed','Blocked'}
    if isinstance(raw.get('batch_status_filter'),list):
        result['batch_status_filter']=[v for v in raw['batch_status_filter'] if v in statuses]
    if raw.get('product_page') in PAGES:result['product_page']=raw['product_page']
    for key,allowed in choices.items():
        value=raw.get(key,[])
        if isinstance(value,(list,tuple)):
            if key=='local_sectors':value=[aliases.get(v,v) if isinstance(v,str) else v for v in value]
            result[key]=[v for v in value if isinstance(v,str) and v in allowed]
    dates=raw.get('local_dates')
    if isinstance(dates,(tuple,list)) and len(dates)==2:
        try:
            dates=[date.fromisoformat(str(v)) for v in dates]
            if dates[0]<=dates[1]:result['local_dates']=[d.isoformat() for d in dates]
        except ValueError:pass
    models=result_models(context[1])
    if raw.get('local_result_model') in models:result['local_result_model']=raw['local_result_model']
    if type(raw.get('local_unknown_dates')) is bool:result['local_unknown_dates']=raw['local_unknown_dates']
    ids={n.article_id for n in context[0]}
    saved=raw.get('selected_articles',{})
    saved=saved if isinstance(saved,dict) else {}
    result['selected_articles']={context:value for context in ARTICLE_CONTEXTS
        if isinstance(value:=raw.get(context+'_article',saved.get(context)),str) and value in ids}
    if type(raw.get('product_include_dev')) is bool:result['product_include_dev']=raw['product_include_dev']
    if not nested and isinstance(raw.get('page_views'),dict):
        result['page_views']={page:normalize(values,store,nested=True,context=context) for page,values in raw['page_views'].items()
                              if page in PAGES and isinstance(values,dict)}
    # No credentials, free text, endpoints, task configuration or request state.
    return result


def load(store):
    with closing(store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='view_preferences'").fetchone()
    return normalize(json.loads(row[0]) if row else {},store)


def save(store,values,*,context=None):
    value=normalize(values,store,context=context);payload=json.dumps(value,sort_keys=True)
    with closing(store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='view_preferences'").fetchone()
        if not row or row[0]!=payload:
            db.execute("INSERT OR REPLACE INTO product_settings VALUES ('view_preferences',?)",(payload,));db.commit()


def restore_ui(store,state):
    if state.get('_product_preferences_loaded'):return
    prefs=load(store)
    # Do not replace the configured taxonomy on a first launch without saved views.
    with closing(store.connect()) as db:exists=db.execute("SELECT 1 FROM product_settings WHERE name='view_preferences'").fetchone()
    if exists:
        views=prefs.get('page_views') or {'Dashboard':{k:v for k,v in prefs.items() if k!='product_page'}}
        for values in views.values():
            if 'local_dates' in values:values['local_dates']=tuple(date.fromisoformat(x) for x in values['local_dates'])
            for context,identity in values.pop('selected_articles',{}).items():values.setdefault(context+'_article',identity)
        state.setdefault('page_views',views)
        if 'product_page' in prefs:state.setdefault('product_page',prefs['product_page'])
    state['_product_preferences_loaded']=True
