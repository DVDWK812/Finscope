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
            r=monitor.evidence(source);seen=monitor.index(source)
            latest=max((n['published'] for n in seen),default='')
            age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(latest)).total_seconds()/60) if latest else None
            rows.append({'Media':FEEDS[source].name,'HTTP':r.get('http_status'),'RSS':r.get('format',''),
                'Last success UTC':monitor.success_at(source),'Latest published UTC':latest,
                'Discovered total':len(seen),'New (last check)':r.get('new',0),'Duplicates':r.get('duplicates',0),
                'Changed':r.get('changed',0),'Processable (last check)':r.get('processable',0),
                'Latency ms':r.get('latency_ms'),'Latest age min':round(age,1) if age is not None else None,
                'Failures':s['failures'],'State':s['hold'] or ('Unknown dispatch' if s['inflight'] else 'Polling' if s['enabled'] else 'Stopped')})
        from .media_reuters import report as reuters_report
        reuters=reuters_report(store)
        direct=[v for v in reuters.get('observations',[]) if v['direct_reuters_url']]
        rows.append({'Media':'Reuters via Marketaux','HTTP':reuters.get('http_status'),'Discovered total':len(direct),'New (last check)':len(direct),
            'Duplicates':0,'Processable (last check)':0,'Latest published UTC':max((v['published'] for v in direct),default='')})
        # Keep the overview narrow; the selected-source receipt exposes timing,
        # failure and policy details below without another settings page.
        for r in rows:
            if r['Media']=='Bloomberg' and not monitor.evidence('bloomberg').get('format'):r['HTTP']='200*' if r['HTTP']==200 else r['HTTP']
            if r['Media']=='Reuters via Marketaux' and r['HTTP'] is None:r['HTTP']='—'
        columns=['Media','HTTP','Discovered total','New (last check)','Duplicates','Processable (last check)','Latest published UTC']
        st.dataframe([{k:r[k] for k in columns} for r in rows],hide_index=True,width='stretch')
        if states['bloomberg']['hold']:st.caption('The original Bloomberg incomplete checkpoint is retained separately from the new diagnostic. Reuters coverage requires an actual budgeted query.')
        st.caption('Discovery counts are separate from saved news and completed NLP. Only reviewed fields enter the library. Polling runs with the local worker; no 24×7 service guarantee.')
        source=st.selectbox('Media feed',list(FEEDS),format_func=lambda k:Verbatim(FEEDS[k].name),key='media_source')
        s=states[source];feed=FEEDS[source]
        report=monitor.evidence(source);plan=monitor.capacity(source)
        st.caption(f"Last success UTC: {monitor.success_at(source) or '—'} · {plan['status']}")
        if s['hold'] or s['inflight']:st.caption('Retained prior checkpoint: '+(s['hold'] or s['inflight']))
        selected=next(r for r in rows if r['Media']==feed.name)
        age=selected.get('Latest age min')
        st.caption(f"HTTP latency: {report.get('latency_ms','—')} ms · Latest item age: {age if age is not None else '—'} min · Next due UTC: {s['next_due'] or '—'}")
        st.caption(Verbatim(feed.finding));st.markdown(f'[Feed]({feed.url}) · [Source terms]({feed.terms})')
        if report:st.json(report,expanded=False)
        st.caption(f"{plan['used_gets']} / {s['daily_cap']} GETs used · full-day demand {plan['full_day_gets']} · {plan['rounds_available_today']} rounds available today · first/last span {plan['estimated_span_minutes']} min · expires UTC {plan['budget_expires_at']}")
        if s.get('recoverable') and s['inflight'] and st.button('Recover received metadata without HTTP',key='media_recover'):
            try:monitor.recover_received(source);st.rerun()
            except ValueError as error:st.info(str(error))
        if st.button('Check selected feed once',key='media_check',disabled=bool(s['hold'] or s['inflight'])):
            try:
                result=monitor.check(source,explicit=True)
                if result:st.session_state['media_preview_'+source]=result[1]
                st.rerun()
            except ValueError as error:st.info(str(error))
        from .media_monitor import active_policy,stamp
        if not active_policy(s['policy'],stamp()):st.session_state.pop('media_preview_'+source,None)
        visible=st.session_state.get('media_preview_'+source) or monitor.preview(source) or monitor.index(source)
        if visible:
            p=s['policy']
            from .media_monitor import active_policy,stamp,publisher_covered
            allow=active_policy(p,stamp()) and 'display' in p['purposes']
            visible=[{k:v for k,v in row.items() if k not in {'title','summary'} or allow and k in p['fields'] and publisher_covered(source,row['url'],p)} for row in visible]
            # The shared evidence-table renderer uses plain cells; provide an
            # explicit original-link action instead of pretending cells link out.
            table=[]
            for row in visible:
                entry={'Feed source':row.get('feed_provider',feed.name),'Publishing domain':row.get('publishing_domain',''),'Published UTC':row['published'],'Original URL':row['url']}
                if 'title' in row:entry={'Title':row['title'],**entry}
                if 'summary' in row:entry['RSS summary']=row['summary']
                table.append(entry)
            st.dataframe(table,hide_index=True,width='stretch')
            urls=[r['url'] for r in visible]
            selected=st.selectbox('Discovered original link',urls,key='media_original_'+source)
            st.link_button('Open discovered original',selected)
        with st.expander('Source licence and polling',expanded=False):
            from .media_rights import review
            st.json(review(source,s['policy']),expanded=False)
            with st.form('media_policy_'+source):
                p=s['policy']
                statuses=['licensed','research_unverified','restricted']
                basis_status=st.selectbox('Source use basis status',statuses,index=statuses.index(p.get('basis_status','licensed')))
                basis=st.text_area('Source basis / research scope and unresolved applicability',value=p['basis'],max_chars=1500)
                exception_reference=st.text_input('Specific exception to an identified restriction',value=p.get('exception_reference',''),max_chars=1500)
                fields=st.multiselect('Covered RSS text fields',['title','summary'],default=p['fields'])
                purposes=st.multiselect('Covered operations',['display','retain','nlp','poll'],default=p['purposes'])
                retention=st.text_input('Retention basis (no_fixed_expiry only if the actual licence allows it)',value=p['retention'])
                expiry=st.text_input('Permission expiry UTC (ISO; empty only if none)',value=p['expires_at'])
                publishers=st.text_input('Additional original publisher domains covered by this licence',value=','.join(p.get('publisher_domains',[])))
                interval=int(st.number_input('Polling interval (minutes)',5,1440,s['interval']))
                cap=int(st.number_input('Per-source UTC-day GET cap',1,1000,s['daily_cap']))
                coverage=st.selectbox('Coverage mode',['bounded_window','full_day'],index=0 if s.get('coverage_mode','bounded_window')=='bounded_window' else 1)
                budget_day=st.text_input('Confirmed HTTP budget UTC date (YYYY-MM-DD)',value=s.get('budget_day',''))
                budget_reference=st.text_input('Actual HTTP budget confirmation / source allowance',value=s.get('budget_reference',''))
                enabled=st.checkbox('Enable polling for this source while the local worker runs',value=s['enabled'])
                save=st.form_submit_button('Save source scope')
            if save:
                try:
                    monitor.configure(source,enabled=enabled,interval=interval,daily_cap=cap,
                        budget_day=budget_day,budget_reference=budget_reference,coverage_mode=coverage,
                        grant=dict(basis=basis,fields=fields,purposes=purposes,retention=retention,expires_at=expiry,
                                   basis_status=basis_status,exception_reference=exception_reference,
                                   publisher_domains=[d.strip().lower() for d in publishers.split(',') if d.strip()]))
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
        st.caption(f'{len(items)} scope-covered saved originals · {current_nlp} current FinBERT results · '+(json.dumps(distribution) if distribution else 'No saved industry assignments'))
        st.caption('Reuters: actual API source/domain observations are shown below; direct Reuters/LSEG licensing and editorial originality are not established.' if reuters.get('state')=='completed' else 'Reuters: Marketaux filters are ready; actual account coverage still needs the confirmed one-request budget. No direct Reuters/LSEG licence is assumed.')
        if reuters:
            with st.expander('Reuters via Marketaux actual evidence',expanded=False):st.json(reuters,expanded=False)
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
