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
    if not isinstance(options,dict) or not fields<=set(options) or set(options)-fields-{'watchlist','mode','window_end','strategy','acquisition_mode','media_choices'}:
        raise ValueError('Invalid media batch scope')
    d=dict(options)
    mode=d.get('mode','company' if d.get('watchlist') else 'broad')
    if mode not in ('broad','company'):raise ValueError('Unknown collection mode')
    if mode=='broad' and d.get('watchlist'):raise ValueError('Broad mode cannot inherit a company watchlist')
    if d.get('window_end'):
        if mode!='broad' or d['source']!='marketaux':raise ValueError('Historical window is only supported for broad Marketaux')
        if not isinstance(d['window_end'],str) or len(d['window_end'])>40:raise ValueError('Invalid historical publication bound')
        end=datetime.fromisoformat(d['window_end'])
        if end.tzinfo is None:raise ValueError('Historical publication bound requires an explicit timezone')
        d['window_end']=end.astimezone(timezone.utc).isoformat()
    if d['source'] not in {'marketaux','finnhub'}:raise ValueError('Choose an official supported news API')
    d['scope']=validate_scope(d['scope'])
    if 'acquisition_mode' in d:
        from .media_modes import scope as mode_scope
        domains=mode_scope(d['acquisition_mode'],d.get('media_choices',[]),d.get('strategy','latest'))
        if domains!=sorted(d['scope']['domains']):raise ValueError('Mode and fixed media-domain mapping differ')
        if (d['acquisition_mode']=='company')!=(mode=='company'):raise ValueError('Company and broad acquisition modes cannot be combined')
    if d.get('strategy','latest') not in ('latest','stratified'):raise ValueError('Unknown broad strategy')
    if d.get('strategy')=='stratified':
        if d['source']!='marketaux' or mode!='broad' or d['scope']['domains']:raise ValueError('Stratified collection must be unfiltered broad Marketaux')
    if d['scope']['source']!=d['source']:raise ValueError('Source and use scope differ')
    if not isinstance(d['batch_id'],str) or not re.fullmatch('[0-9a-f]{32}',d['batch_id']):raise ValueError('Save a new explicit batch confirmation')
    for key,minimum,maximum in [('max_requests',1,50),('per_request',1,300),('total_day_budget',1,10000),('days',1,30)]:
        if type(d[key]) is not int or not minimum<=d[key]<=maximum:raise ValueError('Invalid bounded '+key)
    if d.get('strategy')=='stratified' and (d['max_requests']>12 or d['days']!=1):raise ValueError('Stratified batch uses 24 hours and at most 12 total GETs')
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
        from .news_accounts import check
        check(db,d['source'],primary['slot_id'],now,needed=d['max_requests'],required='acquisition_mode' in d)
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
    broad=source=='marketaux' and d.get('mode')=='broad'
    window=None;strata=d.get('strategy')=='stratified';schedule=[];closed=set()
    if strata:
        from . import media_strata
        checkpoint=q.step(identity,'media_strata_plan_v1')
        if not checkpoint:
            value=dict(queries=media_strata.plan(worker.store,d,before),existing_ids=[n.article_id for n in worker.data.news()])
            q.save_step(identity,'media_strata_plan_v1','ok',value);checkpoint=('ok',value)
        schedule=checkpoint[1]['queries'];existing=set(checkpoint[1]['existing_ids'])
    if broad and not strata:
        from . import media_broad
        checkpoint=q.step(identity,'media_broad_plan_v1')
        if not checkpoint:
            value=dict(window=media_broad.plan(worker.store,d,before),existing_ids=[n.article_id for n in worker.data.news()])
            q.save_step(identity,'media_broad_plan_v1','ok',value);checkpoint=('ok',value)
        window=checkpoint[1]['window'];existing=set(checkpoint[1]['existing_ids'])
    if d.get('watchlist'):
        from .media_watchlist import plan,commit
        checkpoint=q.step(identity,'media_query_plan')
        if not checkpoint:
            value=dict(queries=plan(worker.store,d,before),existing_ids=[n.article_id for n in worker.data.news()])
            q.save_step(identity,'media_query_plan','ok',value);checkpoint=('ok',value)
        planned=checkpoint[1]['queries'];existing=set(checkpoint[1]['existing_ids'])
    if strata:from . import media_broad
    for page in range(min(d['max_requests'],len(schedule)) if strata else d['max_requests']):
        if strata:window=schedule[page]
        page_number=window['page'] if strata else window['page']+page if broad else page+1
        if strata and window['stratum'] in closed:continue
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
            if broad:
                (media_strata.commit(worker.store,step[1]['broad_query'],step[1]) if strata else media_broad.commit(worker.store,d,step[1]['broad_query'],step[1]))
                if step[1].get('pagination_error'):errors.append(step[1]['pagination_stop'])
                if not step[1]['more']:
                    if strata:closed.add(window['stratum'])
                    else:break
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
        if strata:media_strata.record(worker.store,window,dict(status='pending',more=False),reserve=True)
        q.save_step(identity,key,'pending',{'article_ids':[]})
        ids=[]
        try:
            amount=min(d['per_request'],c['limit']-len(set(collected)))
            if broad:amount=window['size']
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
                    if broad:kwargs.update(marketaux_page=page_number,marketaux_before=window['before'],marketaux_filters=MarketauxFilters(tuple(d['scope']['domains']),published_after=window['after']))
                symbol=query['symbols'][0] if query and source=='finnhub' else d['symbol']
                days=min(30,max(1,(service.clock()-datetime.fromisoformat(query['after'])).days+1)) if query and source=='finnhub' else d['days']
                result,rows=NewsKeyRegistry(worker.store).fetch(service,source,'technology',
                    selection=c.get('news_key_slots',{}).get(source,CURRENT),
                    rights=ContentRights(True,False,False,False,'Source-level batch access; text use basis recorded separately'),
                    remaining=d['total_day_budget']-used,days=days,symbol=symbol or None,
                    explicit=True,limit=amount,application_daily_cap=d['total_day_budget'],**kwargs)
                if result.status!='ok':raise FetchBlocked('API response failed; original receipt/hold retained; no retry')
            accepted_rows=rows[:min(amount,c['limit']-len(set(collected)))]
            prior_ids=set(collected)
            if strata:
                prior_ids=set()
                for index in range(page):
                    prior=q.step(identity,'media_request:'+str(index+1))
                    if prior and prior[1].get('broad_query',{}).get('stratum')==window['stratum']:prior_ids.update(prior[1].get('article_ids',[]))
            for raw in accepted_rows:
                check();n=apply_scope(raw,d['scope']);origin=json.loads(n.provenance)
                origin.update(capture_task_id=identity,api_page=page+1)
                if query:origin['query_cohort']={k:query[k] for k in ('group','symbols','industries','after','before','page')}
                if broad:origin.update(collection_mode='broad',api_page=page_number,query_window={k:window[k] for k in ('after','before')})
                n=replace(n,provenance=json.dumps(origin,ensure_ascii=False))
                authorize(n,('retain','local_display'));saved=persist(n)
                if saved:ids.append(saved)
            collected.extend(ids)
            receipt={'article_ids':ids,'http_status':result.http_status if result else None,
                'raw_count':result.raw_count if result else len(rows),'saved':len(ids),
                'new':task['counts'].get('new',0)-initial_new}
            current_versions={n.article_id:n.content_version for n in worker.data.news()}
            receipt.update(duplicates=len(ids)-receipt['new'],changed=sum(k in previous_versions and previous_versions[k]!=current_versions.get(k) for k in set(ids)))
            receipt['normalized_count']=result.normalized_count if result else len(rows)
            if broad:
                meta=result.pagination if result else {}
                if len(ids)!=len(accepted_rows):raise FetchBlocked('Some broad records could not be saved; no pagination advance')
                more,reason=media_broad.continuation(meta,receipt['raw_count'],page_number,amount,len(rows),len(ids),bool(ids) and set(ids)<=prior_ids)
                receipt.update(pagination=meta,broad_query={**window,'page':page_number,'operation_id':identity+':'+str(page)},more=more,pagination_stop=reason)
                previous=[]
                for index in range(page):
                    prior=q.step(identity,'media_request:'+str(index+1))
                    if prior and prior[0]=='ok' and (not strata or prior[1].get('broad_query',{}).get('stratum')==window['stratum']):previous.append((prior[1]['broad_query']['page'],prior[1]))
                receipt['pagination_diagnostics']=media_broad.diagnostics(meta,previous,ids,[n.timestamp for n in accepted_rows if n.timestamp])
                receipt['pagination_error']=reason not in ('Reported result window exhausted','More results within fixed window','Provider pagination bound reached','Record cap or persistence gap; page not fully consumed')
                if receipt['pagination_error']:errors.append(reason)  # BatchRunner counts each phase error once.
            if query:
                if len(ids)!=len(rows[:amount]):raise FetchBlocked('Some returned records could not be saved; query watermark unchanged')
                receipt.update(query=query,published=[n.timestamp for n in rows[:amount] if n.timestamp])
            q.save_step(identity,key,'ok',receipt)
            if broad:
                (media_strata.commit(worker.store,receipt['broad_query'],receipt) if strata else media_broad.commit(worker.store,d,receipt['broad_query'],receipt))
                if not more:
                    if strata:closed.add(window['stratum'])
                    else:break
            if query:commit(worker.store,d,query,published=receipt['published'],received=receipt['raw_count'],accepted=len(ids))
            if not planned and not strata and (not rows or source=='finnhub'):break
        except Cancelled:
            q.save_step(identity,key,'failed',{'article_ids':ids,'reason':'Cancelled after dispatch; no automatic repeat'})
            raise
        except Exception:
            q.save_step(identity,key,'failed',{'article_ids':ids,'reason':'API capture/persistence failed; no automatic retry'})
            collected.extend(ids);errors.append('API capture or persistence failed; committed records retained')
            break
    return [v for v in dict.fromkeys(collected) if v not in existing],errors
