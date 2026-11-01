"""Bounded official-API collection phase for the existing durable BatchRunner."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import re
import time
from .media_use import validate as validate_scope, apply as apply_scope


def validate(options):
    fields={'source','scope','batch_id','max_requests','per_request','plan_limit','utc_day','total_day_budget','symbol','days'}
    if not isinstance(options,dict) or not fields<=set(options) or set(options)-fields-{'watchlist'}:
        raise ValueError('Invalid media batch scope')
    d=dict(options)
    if d['source'] not in {'marketaux','finnhub'}:raise ValueError('Choose an official supported news API')
    d['scope']=validate_scope(d['scope'])
    if d['scope']['source']!=d['source']:raise ValueError('Source and use scope differ')
    if not isinstance(d['batch_id'],str) or not re.fullmatch('[0-9a-f]{32}',d['batch_id']):raise ValueError('Save a new explicit batch confirmation')
    for key,minimum,maximum in [('max_requests',1,50),('per_request',1,300),('total_day_budget',1,10000),('days',1,30)]:
        if type(d[key]) is not int or not minimum<=d[key]<=maximum:raise ValueError('Invalid bounded '+key)
    if d['max_requests']>d['total_day_budget']:raise ValueError('Batch exceeds confirmed application budget')
    if d['plan_limit'] not in (3,20,50,100):raise ValueError('Record the actual Marketaux plan cap')
    if d['source']=='marketaux' and d['per_request']>d['plan_limit']:raise ValueError('Marketaux request exceeds the plan article cap')
    if 'watchlist' in d:
        from .media_watchlist import validate as watchlist,units
        d['watchlist']=watchlist(d['watchlist'])
        if d['max_requests']>len(units(d)):raise ValueError('One request per selected watchlist query; no automatic repetition')
    elif d['source']=='finnhub' and d['max_requests']!=1:raise ValueError('One company-news response is reused; no repeated three-record requests')
    if not isinstance(d['symbol'],str) or (d['source']=='finnhub' and 'watchlist' not in d and not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',d['symbol'])):raise ValueError('Choose the Finnhub company ticker')
    datetime.strptime(d['utc_day'],'%Y-%m-%d')
    return d


def preflight(store,options,*,service=None,ignore_spacing=False):
    from .local_news import LocalIngestionService
    from .news_readiness import key_metadata
    d=validate(options);service=service or LocalIngestionService(store)
    from .media_use import enforce_decision
    enforce_decision(store,d['scope'])
    now=service.clock().astimezone(timezone.utc)
    if d['utc_day']!=now.date().isoformat():raise ValueError('Current UTC-day budget confirmation expired; not renewed automatically')
    primary=key_metadata(store,d['source'])['primary']
    if not primary or not primary['enabled'] or primary['deletion_pending'] or primary['api_state']=='authentication':raise ValueError('Select an enabled primary news credential')
    with closing(store.connect()) as db:
        rows=db.execute('SELECT reserved_at,completed_at,status,hold_until FROM local_requests WHERE provider=? ORDER BY reserved_at',(d['source'],)).fetchall()
    used=sum(r[0][:10]==d['utc_day'] for r in rows)
    if d['total_day_budget']-used<d['max_requests']:raise ValueError('Confirm remaining account quota and an application budget covering this bounded batch')
    try:service._check_holds(d['source'],now,rows,daily_cap=d['total_day_budget'])
    except ValueError as error:
        if not ignore_spacing or 'Wait at least 60 seconds' not in str(error):raise
    return {'used':used,'remaining':d['total_day_budget']-used,'primary_name':primary['name']}


def existing_collection(store,batch_id):
    with closing(store.connect()) as db:
        return any(json.loads(s).get('media_batch',{}).get('batch_id')==batch_id
                   and json.loads(s).get('operation')!='analyze'
                   for s, in db.execute('SELECT snapshot FROM product_tasks'))


def collect(worker,task,persist,check):
    """Commit each received text before recording a successful request stage.

    Only IDs/response metrics go to the permanent queue. Failed/pending requests
    never dispatch again on resume; already committed text remains analyzable.
    """
    from .local_news import LocalIngestionService,ContentRights,FetchBlocked
    from .news_keys import NewsKeyRegistry,CURRENT
    from .api_sources import MarketauxFilters
    from .media_use import authorize
    from .task_queue import Cancelled
    c=task['snapshot'];d=validate(c['media_batch']);q=worker.queue;identity=task['id']
    source=d['source'];collected=[];errors=[]
    before=datetime.fromisoformat(task['created']).astimezone(timezone.utc)
    service=LocalIngestionService(worker.store)
    planned=[];existing=set()
    if d.get('watchlist'):
        from .media_watchlist import plan,commit
        checkpoint=q.step(identity,'media_query_plan')
        if not checkpoint:
            value=dict(queries=plan(worker.store,d,before),existing_ids=[n.article_id for n in worker.data.news()])
            q.save_step(identity,'media_query_plan','ok',value);checkpoint=('ok',value)
        planned=checkpoint[1]['queries'];existing=set(checkpoint[1]['existing_ids'])
    for page in range(d['max_requests']):
        key='media_request:'+str(page+1);step=q.step(identity,key)
        if step:
            collected.extend(step[1].get('article_ids',[]))
            if step[0]!='ok':
                errors.append('Earlier API dispatch/persistence outcome requires review; no retry')
                for n in worker.data.news():
                    try:origin=json.loads(n.provenance)
                    except ValueError:continue
                    if origin.get('capture_task_id')==identity:collected.append(n.article_id)
                break
            if planned and step[1].get('query'):
                commit(worker.store,d,step[1]['query'],published=step[1]['published'],received=step[1]['raw_count'],accepted=step[1]['saved'])
            continue
        if len(set(collected))>=c['limit']:break
        check()
        from .media_use import enforce_decision
        enforce_decision(worker.store,d['scope'])
        # The existing 60-second spacing remains a guard, not a failed request.
        while True:
            check();validate_scope(d['scope'])
            if service.clock().date().isoformat()!=d['utc_day']:raise FetchBlocked('UTC budget expired during batch; no renewal')
            with closing(worker.store.connect()) as db:
                row=db.execute('SELECT reserved_at,completed_at FROM local_requests WHERE provider=? ORDER BY rowid DESC LIMIT 1',(source,)).fetchone()
            wait=60-(service.clock()-datetime.fromisoformat(row[1] or row[0])).total_seconds() if row else 0
            if wait<=0:break
            q.update(identity,stage='waiting for existing provider spacing')
            time.sleep(min(1,wait))
        with closing(worker.store.connect()) as db:
            used=db.execute('SELECT count(*) FROM local_requests WHERE provider=? AND substr(reserved_at,1,10)=?',(source,d['utc_day'])).fetchone()[0]
        if used>=d['total_day_budget']:raise FetchBlocked('Confirmed application/account budget exhausted')
        q.save_step(identity,key,'pending',{'article_ids':[]})
        ids=[]
        try:
            amount=min(d['per_request'],c['limit']-len(set(collected)))
            previous_versions={n.article_id:n.content_version for n in worker.data.news()}
            initial_new=task['counts'].get('new',0)
            query={**planned[page], 'operation_id':identity+':'+str(page),'requested':amount} if planned else None
            if worker.fetch_override:
                rows=worker.fetch_override(source,{**c,'limit':amount},check)
                result=None
            else:
                kwargs={}
                if source=='marketaux':
                    kwargs=dict(marketaux_plan_limit=d['plan_limit'],marketaux_page=query['page'] if query else page+1,marketaux_before=query['before'] if query else before.isoformat(),
                        marketaux_filters=MarketauxFilters(tuple(d['scope']['domains']),tuple(query['symbols']) if query else (),tuple(query['industries']) if query else (),published_after=query['after'] if query else (before-timedelta(days=d['days'])).isoformat()))
                symbol=query['symbols'][0] if query and source=='finnhub' else d['symbol']
                days=min(30,max(1,(service.clock()-datetime.fromisoformat(query['after'])).days+1)) if query and source=='finnhub' else d['days']
                result,rows=NewsKeyRegistry(worker.store).fetch(service,source,'technology',
                    selection=c.get('news_key_slots',{}).get(source,CURRENT),
                    rights=ContentRights(True,False,False,False,'Source-level batch access; text use basis recorded separately'),
                    remaining=d['total_day_budget']-used,days=days,symbol=symbol or None,
                    explicit=True,limit=amount,application_daily_cap=d['total_day_budget'],**kwargs)
                if result.status!='ok':raise FetchBlocked('API response failed; original receipt/hold retained; no retry')
            for raw in rows[:amount]:
                check();n=apply_scope(raw,d['scope']);origin=json.loads(n.provenance)
                origin.update(capture_task_id=identity,api_page=page+1)
                if query:origin['query_cohort']={k:query[k] for k in ('group','symbols','industries','after','before','page')}
                n=replace(n,provenance=json.dumps(origin,ensure_ascii=False))
                authorize(n,('retain','local_display'));saved=persist(n)
                if saved:ids.append(saved)
            collected.extend(ids)
            receipt={'article_ids':ids,'http_status':result.http_status if result else None,
                'raw_count':result.raw_count if result else len(rows),'saved':len(ids),
                'new':task['counts'].get('new',0)-initial_new}
            current_versions={n.article_id:n.content_version for n in worker.data.news()}
            receipt.update(duplicates=len(ids)-receipt['new'],changed=sum(k in previous_versions and previous_versions[k]!=current_versions.get(k) for k in set(ids)))
            if query:
                if len(ids)!=len(rows[:amount]):raise FetchBlocked('Some returned records could not be saved; query watermark unchanged')
                receipt.update(query=query,published=[n.timestamp for n in rows[:amount] if n.timestamp])
            q.save_step(identity,key,'ok',receipt)
            if query:commit(worker.store,d,query,published=receipt['published'],received=receipt['raw_count'],accepted=len(ids))
            if not planned and (not rows or source=='finnhub'):break
        except Cancelled:
            q.save_step(identity,key,'failed',{'article_ids':ids,'reason':'Cancelled after dispatch; no automatic repeat'})
            raise
        except Exception:
            q.save_step(identity,key,'failed',{'article_ids':ids,'reason':'API capture/persistence failed; no automatic retry'})
            collected.extend(ids);errors.append('API capture or persistence failed; committed records retained')
            break
    return [v for v in dict.fromkeys(collected) if v not in existing],errors
