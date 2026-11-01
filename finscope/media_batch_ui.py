"""One source-level research/retention/budget form in existing batch controls."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import json
from .localized_ui import st
from .i18n import Verbatim

SETTING='media_batch_pipeline'


def saved(store):
    with closing(store.connect()) as db:
        r=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    c=json.loads(r[0]) if r else None
    if c and c.get('taxonomy')=='US-BUSINESS-1':
        from .classification_scheme import selected
        options=selected(store)
        if options:c['classifier_options']=options
    return c


def controls(q,active):
    from .media_use import record_decision,decisions,REFERENCES
    from .media_batch import preflight
    old=saved(q.store);d=(old or {}).get('media_batch',{})
    st.subheader('Media API text and local analysis')
    st.caption('One source-level scope per batch. A research confirmation records unresolved applicability; it is not publisher permission. No article pages, training, external LLM or redistribution.')
    with st.form('media_text_batch'):
        source=st.selectbox('Official media API',['marketaux','finnhub'],index=0 if d.get('source','marketaux')=='marketaux' else 1)
        status=st.selectbox('Use basis',['research_unverified','licensed','restricted'],format_func=lambda s:Verbatim({'licensed':'Existing licence evidence','research_unverified':'Personal research · applicability unverified','restricted':'Identified restriction blocks this use'}[s]))
        fields=st.selectbox('Returned text fields',['title+summary','title only'])
        reference=st.text_area('Licence evidence or research purpose and unresolved applicability',value=d.get('scope',{}).get('reference',''),max_chars=1500)
        exception=st.text_input('Specific exception evidence (only if a restriction was recorded)',max_chars=1500)
        days=int(st.number_input('Local text retention days',1,30,7))
        a,b=st.columns(2)
        with a:
            count=int(st.number_input('Maximum distinct media records',1,300,int((old or {}).get('limit',3))))
            plan=int(st.selectbox('Marketaux subscription article cap (conservative default 3)',['3','20','50','100']))
            per=int(st.number_input('Records requested / accepted per response',1,300,int(d.get('per_request',3))))
            domains=st.text_input('Marketaux publication-domain whitelist',value=','.join(d.get('scope',{}).get('domains',['reuters.com','finance.yahoo.com'])))
        with b:
            gets=int(st.number_input('Maximum new GETs in this batch',1,50,int(d.get('max_requests',1))))
            total=int(st.number_input('Confirmed total application GET budget for the UTC day',0,10000,int(d.get('total_day_budget',0))))
            day=st.text_input('Budget UTC date',value=d.get('utc_day',datetime.now(timezone.utc).date().isoformat()))
            symbol=st.text_input('Finnhub company ticker',value=d.get('symbol','NVDA'),max_chars=15)
        confirmed=st.checkbox('I choose this source-level use scope and expiry, acknowledge unresolved applicability where selected, and have verified the stated account allowance')
        save=st.form_submit_button('Save source scope and confirmed batch budget',disabled=active)
    if save:
        try:
            scope=dict(source=source,status=status,reference=reference,fields=['title','summary'] if fields=='title+summary' else ['title'],
                expires_at=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat(),confirmed=confirmed,
                exception_reference=exception,domains=[v.strip().lower() for v in domains.split(',') if v.strip()] if source=='marketaux' else [])
            if status=='restricted':
                if not reference.strip():raise ValueError('Record the concrete restricting term')
                record_decision(q.store,scope)
                st.info('Restriction recorded. No collection or analysis was started.');return
            options=dict(source=source,scope=scope,batch_id=uuid4().hex,max_requests=gets,per_request=count if source=='finnhub' else per,
                plan_limit=plan,utc_day=day,total_day_budget=total,symbol=symbol.strip().upper() if source=='finnhub' else '',days=2)
            config=dict(sources=[source],model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',classifier_llm=False,
                limit=count,budgets={},source_permissions={},media_batch=options)
            from .task_queue import validate_config
            validate_config({**config,'operation':'update'})
            from .news_keys import NewsKeyRegistry
            NewsKeyRegistry(q.store).reject_secret_text(json.dumps(config))
            # A specific licence exception may release a previously recorded hold.
            records=decisions(q.store)
            if records.get(source,{}).get('status')=='restricted':record_decision(q.store,scope)
            preflight(q.store,options,ignore_spacing=True)
            record_decision(q.store,scope)
            with closing(q.store.connect()) as db:
                db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(config)));db.commit()
            st.success('Source scope saved once. Update & Analyze uses this bounded API batch; saving made no HTTP request.')
            st.rerun()
        except ValueError as error:st.error(str(error))
    if old:
        st.caption('Saved media batch: '+d.get('source','')+' · '+str(old['limit'])+' records · '+str(d['max_requests'])+' GETs · expires '+d['scope']['expires_at'])
        left,right=st.columns(2)
        with left:
            if st.button('Save media text only',disabled=active):
                try:q.submit_batch('collect',old,confirmed=True);st.rerun()
                except ValueError as error:st.error(str(error))
        with right:
            if st.button('Analyze retained media offline',disabled=active):
                try:
                    from .product_storage import ProductStorage
                    from .media_use import scope_of
                    ids=[n.article_id for n in ProductStorage(q.store).news() if scope_of(n)]
                    q.submit_batch('analyze',old,confirmed=True,article_ids=ids);st.rerun()
                except ValueError as error:st.error(str(error))
        st.caption('Repeated use of the same saved batch reuses its collection checkpoint. Save a new explicit batch only for a new collection. Expiring media text is excluded from permanent backups and exports.')
        if st.button('Delete this source’s finite text and results',disabled=active):
            from .expiring_media import partition
            part=partition(q.store)
            if part:part.revoke(d['source'])
            with closing(q.store.connect()) as db:
                db.execute('DELETE FROM product_settings WHERE name=?',(SETTING,));db.commit()
            st.rerun()
        st.caption('If a subscription ends or the scope no longer applies, delete its finite text here immediately. Cleanup runs only while FinScope is running, and before the next startup read.')
