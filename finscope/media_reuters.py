"""One expressly budgeted Marketaux Reuters probe, never an original-page fetch."""
from contextlib import closing
from datetime import datetime,timezone
import json
from .api_sources import MarketauxFilters,HTTPResponse,_http_get_json,_published_datetime
from .local_news import LocalIngestionService,ContentRights
from .media_monitor import safe_url

SETTING='p3b1_reuters_probe'


def report(store):
    with closing(store.connect()) as db:r=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    return json.loads(r[0]) if r else {}


def probe(store,*,confirmed=False,total_day_budget=0,reference='',fetch=None):
    if confirmed is not True or type(total_day_budget) is not int or total_day_budget<1 or not isinstance(reference,str) or not reference.strip():raise ValueError('Confirm an actual current UTC-day account budget and this one request')
    now=datetime.now(timezone.utc);day=now.date().isoformat()
    from .news_keys import NewsKeyRegistry,CURRENT
    registry=NewsKeyRegistry(store);registry.reject_secret_text(reference)
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
        if old:
            value=json.loads(old[0])
            if value['state']=='completed':return value
            if value['state']!='preflight_blocked':raise ValueError('Previous Reuters probe outcome is pending/unknown; not repeated')
        used=db.execute('SELECT count(*) FROM local_requests WHERE provider=? AND substr(reserved_at,1,10)=?',('marketaux',day)).fetchone()[0]
        if used>=total_day_budget:raise ValueError('Confirmed current UTC-day total budget exhausted')
        pending=dict(state='pending',utc_day=day,approved_total_day_budget=total_day_budget,reference=reference,
            domains=['reuters.com'],limit=3,max_requests=1,started=now.isoformat())
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(pending)));db.commit()
    observations=[]
    def transport(url,params,headers,timeout):
        response=_http_get_json(url,params,headers,timeout)
        data=response.payload if isinstance(response,HTTPResponse) else response
        token=params.get('api_token','')
        rows=data.get('data',[]) if isinstance(data,dict) else []
        for row in rows[:3] if isinstance(rows,list) else []:
            if not isinstance(row,dict):continue
            original=row.get('url','');claimed=row.get('source','')
            if not isinstance(original,str) or not safe_url(original) or not isinstance(claimed,str):continue
            from urllib.parse import urlsplit
            host=urlsplit(original).hostname
            metadata=dict(url=original,api_source=claimed[:200],publishing_domain=host,
                published=_published_datetime(row.get('published_at')),
                direct_reuters_url=host=='reuters.com' or host.endswith('.reuters.com'))
            if token and any(token in str(v) for v in metadata.values()):continue
            observations.append(metadata)
        return response
    service=LocalIngestionService(store,transport=transport)
    rights=ContentRights(True,False,False,False,'https://www.marketaux.com/tos ; personal API preview only; no publisher archive or NLP grant')
    call=fetch or (lambda **kw:registry.fetch(service,'marketaux','technology',selection=CURRENT,**kw))
    try:result,items=call(rights=rights,remaining=total_day_budget-used,explicit=True,days=2,marketaux_filters=MarketauxFilters(('reuters.com',)))
    except Exception:
        with closing(store.connect()) as db:
            after=db.execute('SELECT count(*) FROM local_requests WHERE provider=? AND substr(reserved_at,1,10)=?',('marketaux',day)).fetchone()[0]
            value={**pending,'state':'preflight_blocked' if after==used else 'pending_unknown','reason':'Source preflight blocked; no reservation/HTTP' if after==used else 'A reservation exists; inspect the existing ledger; no retry'}
            db.execute('UPDATE product_settings SET payload=? WHERE name=?',(json.dumps(value),SETTING));db.commit()
        raise ValueError(value['reason']) from None
    if fetch is not None:
        # Authored tests may inject already normalized previews, never real I/O.
        from urllib.parse import urlsplit
        observations=[dict(url=n.url,api_source=n.source,publishing_domain=urlsplit(n.url).hostname,published=n.timestamp,
            direct_reuters_url=(urlsplit(n.url).hostname=='reuters.com' or (urlsplit(n.url).hostname or '').endswith('.reuters.com'))) for n in items]
    value={**pending,'state':'completed','finished':datetime.now(timezone.utc).isoformat(),
        'http_status':result.http_status,'outcome':result.outcome,'status':result.status,'raw_count':result.raw_count,
        'matched_preview_count':len(items),'observations':observations,
        'direct_reuters_links':sum(x['direct_reuters_url'] for x in observations),
        'outside_reuters_domain':sum(not x['direct_reuters_url'] for x in observations),
        'publisher_pages_fetched':0,'saved_articles':0,'nlp_completed':0,
        'scope':'API-reported source and publication URL only; editorial originality and direct Reuters/LSEG licensing not established'}
    with closing(store.connect()) as db:
        db.execute('UPDATE product_settings SET payload=? WHERE name=?',(json.dumps(value),SETTING));db.commit()
    return value
