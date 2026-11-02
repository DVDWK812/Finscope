"""Six fixed UTC strata; metadata-only durable request fences, no I/O to sources."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import hashlib,json

SETTING='media_strata_progress_v1'

def read(store):
    with closing(store.connect()) as db:
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    return json.loads(row[0]) if row else {}

def window_id(query):
    return hashlib.sha256(json.dumps([query['logical_after'],query['logical_before'],query['size']]).encode()).hexdigest()

def plan(store,options,created):
    end=datetime.fromisoformat(options['window_end']) if options.get('window_end') else created-timedelta(hours=1)
    end=end.astimezone(timezone.utc).replace(microsecond=0)
    if end>created:raise ValueError('Stratified window cannot end in the future')
    windows=[];state=read(store)
    for index in range(6):
        upper=end-timedelta(hours=4*index);lower=upper-timedelta(hours=4)
        # Intentional one-second guard on BOTH sides: don't assume the supplier
        # treats exact timestamp boundaries as inclusive. Keep received boundary
        # records and deduplicate globally; this is not exhaustive coverage.
        query=dict(logical_after=lower.isoformat(),logical_before=upper.isoformat(),
            after=(lower-timedelta(seconds=1)).isoformat(),before=(upper+timedelta(seconds=1)).isoformat(),
            size=options['per_request'],stratum=index+1)
        key=window_id(query);old=state.get(key,{})
        closed=any(v.get('status')!='ok' or not v.get('more',False) for v in old.values())
        if not closed:windows.append((query,old))
    # Cover all six strata before taking second pages; skipped slots never
    # redistribute their allowance into a third request for another stratum.
    return [{**query,'page':page} for page in (1,2) for query,old in windows if str(page) not in old]

def record(store,query,value,*,reserve=False):
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
        state=json.loads(row[0]) if row else {};window=state.setdefault(window_id(query),{})
        page=str(query['page'])
        if reserve and page in window:raise ValueError('Stratum page already dispatched or unknown; no retry')
        window[page]=value
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(state)));db.commit()

def commit(store,query,receipt):
    record(store,query,dict(status='ok',more=receipt['more'] and query['page']<2,
        reason=receipt['pagination_stop'],operation_id=query['operation_id']))
