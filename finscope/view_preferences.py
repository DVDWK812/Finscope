"""Small allowlisted view preferences, separate from pipeline configuration."""
from contextlib import closing
from datetime import date
import json
from .taxonomy import load_taxonomy,CATALOGS,node_label

PAGES=['Dashboard','Industries','Knowledge Graph','News Explorer','Settings']
ARTICLE_CONTEXTS=('explorer','industries','heatmap','heatmap_unknown','graph_related','graph_accessible','cloud_matches')


def normalize(raw,store):
    from .local_analytics import result_models
    mode=raw.get('product_taxonomy','US-BUSINESS-1')
    mode=mode if mode in CATALOGS else 'US-BUSINESS-1'
    catalog=load_taxonomy(mode)
    choices={'local_sectors':{node_label(n) for n in catalog['nodes'] if not n['parent_id']}|{'Unclassified'},
             'product_children':{n['id'] for n in catalog['nodes'] if n['parent_id']},
             'local_sources':{n.source for n in store.list_news()},'local_sentiments':{'Positive','Neutral','Negative'}}
    result={'product_taxonomy':mode}
    if raw.get('product_page') in PAGES:result['product_page']=raw['product_page']
    for key,allowed in choices.items():
        value=raw.get(key,[])
        if isinstance(value,(list,tuple)):result[key]=[v for v in value if isinstance(v,str) and v in allowed]
    dates=raw.get('local_dates')
    if isinstance(dates,(tuple,list)) and len(dates)==2:
        try:
            dates=[date.fromisoformat(str(v)) for v in dates]
            if dates[0]<=dates[1]:result['local_dates']=[d.isoformat() for d in dates]
        except ValueError:pass
    models=result_models(store.list_analyses())
    if raw.get('local_result_model') in models:result['local_result_model']=raw['local_result_model']
    if type(raw.get('local_unknown_dates')) is bool:result['local_unknown_dates']=raw['local_unknown_dates']
    ids={n.article_id for n in store.list_news()}
    saved=raw.get('selected_articles',{})
    saved=saved if isinstance(saved,dict) else {}
    result['selected_articles']={context:value for context in ARTICLE_CONTEXTS
        if isinstance(value:=raw.get(context+'_article',saved.get(context)),str) and value in ids}
    # No credentials, free text, endpoints, task configuration or request state.
    return result


def load(store):
    with closing(store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='view_preferences'").fetchone()
    return normalize(json.loads(row[0]) if row else {},store)


def save(store,values):
    value=normalize(values,store);payload=json.dumps(value,sort_keys=True)
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
        for k,v in prefs.items():
            if k=='selected_articles':
                for context,identity in v.items():state.setdefault(context+'_article',identity)
            else:state.setdefault(k,tuple(date.fromisoformat(x) for x in v) if k=='local_dates' else v)
    state['_product_preferences_loaded']=True
