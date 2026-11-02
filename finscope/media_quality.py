"""Aggregate live media quality without requests, inference or copied text."""
from collections import Counter
from contextlib import closing
import json
from .media_use import scope_of
from .publisher_attribution import attribution


def validation_type(response,text):
    try:
        choice=response['choices'][0];out=json.loads(choice['message']['content'])
    except (KeyError,IndexError,TypeError,ValueError):return 'json_or_envelope_invalid'
    if not isinstance(out,dict) or set(out)!={'labels','unclassified_reason'} or not isinstance(out['labels'],list):return 'json_contract_invalid'
    labels=out['labels'];reason=out['unclassified_reason']
    if len(labels)>4 or reason not in ('','text_insufficient','macro_non_industry','no_sector_evidence','ambiguous_activity'):return 'json_contract_invalid'
    if choice.get('finish_reason')!='stop' or not labels and not reason or labels and reason:return 'json_contract_invalid'
    if not labels:return 'semantic_rejection' if reason in {'text_insufficient','macro_non_industry','no_sector_evidence','ambiguous_activity'} else 'json_contract_invalid'
    from .taxonomy import load_taxonomy
    legal={n['id'] for n in load_taxonomy()['nodes']}
    if any(not isinstance(v,dict) or set(v)!={'id','quote','reason'} or not isinstance(v['id'],str) or v['id'] not in legal
           or not isinstance(v['reason'],str) or not 12<=len(v['reason'])<=400 for v in labels):return 'json_contract_invalid'
    if any(not isinstance(v['quote'],str) or not v['quote'] or v['quote'] not in text for v in labels):return 'evidence_mismatch'
    return 'schema_and_literal_evidence_valid_semantics_not_rejudged'


def failed_diagnostics(store):
    from .product_storage import ProductStorage
    from .expiring_media import partition
    from .semantic_classifier import text_of
    data=ProductStorage(store);classes=data.classifications('US-BUSINESS-1');part=partition(store);result=[]
    if not part:return result
    with closing(part.connect()) as db:
        for n in data.news():
            c=classes.get(n.article_id,{})
            if not scope_of(n) or c.get('status')!='failed':continue
            row=db.execute("SELECT payload FROM product_classifier_calls WHERE article_id=? AND stage LIKE 'semantic_review:%' AND status='ok' ORDER BY rowid DESC LIMIT 1",(n.article_id,)).fetchone()
            if not row:row=db.execute("SELECT payload FROM product_classifier_calls WHERE article_id=? AND stage='semantic_decision' AND status='ok' ORDER BY rowid DESC LIMIT 1",(n.article_id,)).fetchone()
            kind=validation_type(json.loads(row[0]).get('output'),text_of(n)) if row else 'dispatch_or_output_unavailable'
            result.append(dict(article_id=n.article_id,type=kind,read_only=True,retried=False))
    return result


def statistics(store,article_ids=None):
    from .product_storage import ProductStorage
    from .batch_config import finbert_cache_key
    data=ProductStorage(store);news=[n for n in data.news() if scope_of(n) and (article_ids is None or n.article_id in article_ids)]
    classes=data.classifications('US-BUSINESS-1');states=data.states();groups={}
    for n in news:
        p=json.loads(n.provenance);a=attribution(n);key=(a['collection_service'],a['supplier_reported_source'],a['linked_publisher'])
        g=groups.setdefault(key,dict(service=key[0],reported_source=key[1],linked_publisher=key[2],originality='unverified',
            records=0,titles=0,title_characters=0,summaries=0,summary_characters=0,title_only=0,classified=0,
            unclassified=0,classifier_failed=0,classification_pending=0,finbert=0,sentiment_failed=0,sentiment_pending=0,sentiment_not_applicable=0,nlp_not_authorized=0,
            publisher_domains=set(),link_domains=set(),query_symbols=set(),supplier_entity_symbols=set(),query_symbol_records=Counter(),supplier_entity_records=Counter(),text_mentioned_entities=Counter(),query_groups=Counter(),parent_topics=Counter(),child_topics=Counter(),basis_statuses=Counter()))
        g['records']+=1;g['titles']+=bool(n.title);g['title_characters']+=len(n.title);g['summaries']+=bool(n.summary);g['summary_characters']+=len(n.summary);g['title_only']+=not bool(n.summary)
        if a['publisher_domain']:g['publisher_domains'].add(a['publisher_domain'])
        if a['link_domain']:g['link_domains'].add(a['link_domain'])
        cohort=p.get('query_cohort',{});g['query_symbols'].update(cohort.get('symbols',[]) or ([n.company] if n.provider=='finnhub' and n.company else []))
        if cohort.get('group'):g['query_groups'][cohort['group']]+=1
        g['supplier_entity_symbols'].update(e['symbol'] for e in p.get('api_record',{}).get('entities',[]) if e.get('symbol'))
        g['query_symbol_records'].update(set(cohort.get('symbols',[]) or ([n.company] if n.provider=='finnhub' and n.company else [])))
        g['supplier_entity_records'].update({e['symbol'] for e in p.get('api_record',{}).get('entities',[]) if e.get('symbol')})
        c=classes.get(n.article_id,{})
        g['text_mentioned_entities'].update({e['name'] for e in c.get('entities',[]) if e.get('name') and e.get('evidence')})
        bucket='classified' if c.get('labels') else 'classifier_failed' if c.get('status')=='failed' else 'unclassified' if c else 'classification_pending'
        g[bucket]+=1
        for label in c.get('labels',[]):g['child_topics' if label['parent_id'] else 'parent_topics'][label['id']]+=1
        permitted=n.rights.analyze;g['nlp_not_authorized']+=not permitted
        done=permitted and bool(data.cached(n,finbert_cache_key()));g['finbert']+=done
        state=states.get((n.article_id,n.content_version),{})
        failed=not done and state.get('analysis')=='failed' and state.get('reason','').startswith('Model output failed')
        na=not done and state.get('analysis')=='not_applicable'
        g['sentiment_failed']+=failed;g['sentiment_not_applicable']+=na;g['sentiment_pending']+=permitted and not done and not failed and not na
        g['basis_statuses'][scope_of(n)['status']]+=1
    result=[]
    for g in groups.values():
        result.append({k:sorted(v) if isinstance(v,set) else dict(v) if isinstance(v,Counter) else v for k,v in g.items()})
    return result


def batch_receipts(store,task_id):
    with closing(store.connect()) as db:rows=db.execute("SELECT status,payload FROM product_steps WHERE task_id=? AND step LIKE 'media_request:%'",(task_id,)).fetchall()
    values=[json.loads(p) for state,p in rows if state=='ok'];accepted=sum(v.get('saved',0) for v in values);duplicates=sum(v.get('duplicates',0) for v in values)
    return dict(request_stages=len(rows),successful_requests=len(values),failed_or_unknown=len(rows)-len(values),
        accepted_observations=accepted,new=sum(v.get('new',0) for v in values),duplicates=duplicates,
        duplicate_ratio=duplicates/accepted if accepted else None,changed=sum(v.get('changed',0) for v in values),
        raw_returned=sum(v.get('raw_count',0) for v in values),normalized=sum(v.get('normalized_count',0) for v in values),
        pagination_stops=[v['pagination_stop'] for v in values if v.get('pagination_stop')],
        http_statuses=dict(Counter(str(v.get('http_status')) for v in values)))
