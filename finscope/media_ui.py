"""Compact source monitor in the existing workspace; no work on render."""
from contextlib import closing
from dataclasses import asdict
from datetime import datetime,timezone
import json
from .localized_ui import st
from .i18n import Verbatim
from .media_monitor import FEEDS,MediaMonitor,policy

def controls(store):
    with st.expander('Global media monitor',expanded=False):
        monitor=MediaMonitor(store);states=monitor.states();rows=[]
        for source,s in states.items():
            r=s['last_report'];seen=monitor.index(source)
            latest=max((n['published'] for n in seen),default='')
            age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(latest)).total_seconds()/60) if latest else None
            rows.append({'Media':FEEDS[source].name,'HTTP':r.get('http_status'),'RSS':r.get('format',''),
                'Last success UTC':s['last_success'],'Latest published UTC':latest,
                'Discovered total':len(seen),'New (last check)':r.get('new',0),'Duplicates':r.get('duplicates',0),
                'Changed':r.get('changed',0),'Processable (last check)':r.get('processable',0),
                'Latency ms':r.get('latency_ms'),'Latest age min':round(age,1) if age is not None else None,
                'Failures':s['failures'],'State':s['hold'] or ('Unknown dispatch' if s['inflight'] else 'Polling' if s['enabled'] else 'Stopped')})
        rows.append({'Media':'Reuters via Marketaux','HTTP':None,'Discovered total':0,'New (last check)':0,
            'Duplicates':0,'Processable (last check)':0,'Latest published UTC':''})
        # Keep the overview narrow; the selected-source receipt exposes timing,
        # failure and policy details below without another settings page.
        for r in rows:
            if r['Media']=='Bloomberg' and states['bloomberg']['hold']:r['HTTP']='200*' if r['HTTP']==200 else r['HTTP']
            if r['Media']=='Reuters via Marketaux':r['HTTP']='—'
        columns=['Media','HTTP','Discovered total','New (last check)','Duplicates','Processable (last check)','Latest published UTC']
        st.dataframe([{k:r[k] for k in columns} for r in rows],hide_index=True,width='stretch')
        if states['bloomberg']['hold']:st.caption('Bloomberg *: incomplete indexing checkpoint. Reuters: no request; account coverage untested.')
        st.caption('Discovery counts are separate from saved news and completed NLP. Only reviewed fields enter the library. Polling runs with the local worker; no 24×7 service guarantee.')
        source=st.selectbox('Media feed',list(FEEDS),format_func=lambda k:Verbatim(FEEDS[k].name),key='media_source')
        s=states[source];feed=FEEDS[source]
        st.caption(Verbatim(f"Last success UTC: {s['last_success'] or '—'} · Failures: {s['failures']} · {s['hold'] or ('Incomplete checkpoint' if s['inflight'] else 'Polling' if s['enabled'] else 'Stopped')}"))
        selected=next(r for r in rows if r['Media']==feed.name)
        age=selected.get('Latest age min')
        st.caption(Verbatim(f"HTTP latency: {s['last_report'].get('latency_ms','—')} ms · Latest item age: {age if age is not None else '—'} min · Next due UTC: {s['next_due'] or '—'}"))
        st.caption(Verbatim(feed.finding));st.markdown(f'[Feed]({feed.url}) · [Source terms]({feed.terms})')
        if s['last_report']:st.json(s['last_report'],expanded=False)
        if s.get('recoverable') and s['inflight'] and st.button('Recover received metadata without HTTP',key='media_recover'):
            try:monitor.recover_received(source);st.rerun()
            except ValueError as error:st.info(str(error))
        if st.button('Check selected feed once',key='media_check',disabled=bool(s['hold'] or s['inflight'])):
            try:
                result=monitor.check(source,explicit=True)
                if result:st.session_state['media_preview_'+source]=result[1]
                st.rerun()
            except ValueError as error:st.info(str(error))
        visible=st.session_state.get('media_preview_'+source) or monitor.index(source)
        if visible:
            p=s['policy']
            from .media_monitor import active_policy,stamp
            allow=active_policy(p,stamp()) and 'display' in p['purposes']
            visible=[{k:v for k,v in row.items() if k not in {'title','summary'} or allow and k in p['fields']} for row in visible]
            st.dataframe(visible,hide_index=True,width='stretch',column_config={'url':st.column_config.LinkColumn('Original link')})
        with st.expander('Source licence and polling',expanded=False):
            with st.form('media_policy_'+source):
                p=s['policy']
                basis=st.text_area('Actual source licence / legal basis',value=p['basis'],max_chars=1500)
                fields=st.multiselect('Covered RSS text fields',['title','summary'],default=p['fields'])
                purposes=st.multiselect('Covered operations',['display','retain','nlp','poll'],default=p['purposes'])
                retention=st.text_input('Retention basis (no_fixed_expiry only if the actual licence allows it)',value=p['retention'])
                expiry=st.text_input('Permission expiry UTC (ISO; empty only if none)',value=p['expires_at'])
                interval=st.slider('Polling interval (minutes)',5,15,s['interval'])
                cap=st.number_input('Per-source UTC-day GET cap',1,288,s['daily_cap'])
                enabled=st.checkbox('Enable polling for this source while the local worker runs',value=s['enabled'])
                save=st.form_submit_button('Save source scope')
            if save:
                try:
                    monitor.configure(source,enabled=enabled,interval=interval,daily_cap=cap,
                        grant=dict(basis=basis,fields=fields,purposes=purposes,retention=retention,expires_at=expiry))
                    st.session_state.pop('media_preview_'+source,None);st.rerun()
                except ValueError as error:st.error(str(error))
            if st.button('Save covered discoveries and queue local analysis',key='media_promote'):
                try:
                    result=monitor.promote(source);st.write(result)
                    from .product_storage import ProductStorage
                    from .task_queue import TaskQueue
                    from .batch_config import DEFAULT
                    ids=[n.article_id for n in ProductStorage(store).news() if n.provider=='media_rss' and n.source==feed.name]
                    if ids:TaskQueue(store).submit_batch('analyze',DEFAULT,confirmed=True,article_ids=ids)
                except ValueError as error:st.info(str(error))
        # Industry counts use only licensed originals and saved classifications.
        from .product_storage import ProductStorage
        data=ProductStorage(store);items=[n for n in data.news() if n.provider=='media_rss' and n.source==feed.name]
        classes=data.classifications('US-BUSINESS-1');distribution={}
        for n in items:
            labels=classes.get(n.article_id,{}).get('labels',[])
            for label in labels:distribution[label['id']]=distribution.get(label['id'],0)+1
        from .batch_config import finbert_cache_key
        current_nlp=sum(bool(data.cached(n,finbert_cache_key())) and n.rights.analyze for n in items)
        st.caption(f'{len(items)} licensed saved originals · {current_nlp} current FinBERT results · '+(json.dumps(distribution) if distribution else 'No saved industry assignments'))
        st.caption('Reuters: Marketaux domain filters are supported; current account coverage is untested. Explicit wire credits remain separate from the publishing website. Direct Reuters/LSEG requires the applicable subscription.')
        marketaux_scope(store)

def marketaux_scope(store):
    from .api_sources import MarketauxFilters,build_request
    saved=store.setting('marketaux_media_filters') or {}
    with st.expander('Marketaux media whitelist (offline configuration)',expanded=False):
        with st.form('media_marketaux_filters'):
            choices=['reuters.com','bloomberg.com','cnbc.com','wsj.com','finance.yahoo.com','ft.com']
            domains=st.multiselect('Marketaux media domains',choices,default=saved.get('domains',['reuters.com']))
            symbols=st.text_input('Marketaux symbols (comma separated)',value=','.join(saved.get('symbols',[])))
            industries=st.text_input('Marketaux entity industries (official names, comma separated)',value=','.join(saved.get('industries',[])))
            after=st.text_input('Marketaux published_after (timezone-aware ISO; blank uses current lookback)',value=saved.get('published_after',''))
            save=st.form_submit_button('Validate and save Marketaux filters')
        if save:
            try:
                f=MarketauxFilters(tuple(domains),tuple(v.strip() for v in symbols.split(',') if v.strip()),
                    tuple(v.strip() for v in industries.split(',') if v.strip()),after.strip())
                f.parameters();store.set_setting('marketaux_media_filters',asdict(f))
                _,params,_,mode,_=build_request('marketaux','technology',datetime.now(timezone.utc),2,3,None,marketaux_filters=f)
                params.pop('api_token',None);st.json({'mode':mode,'parameters':params});st.success('Filters saved offline. No API request was made; existing budget, permission and cooldown checks still apply.')
            except ValueError as error:st.error(str(error))
