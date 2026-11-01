"""Nonsecret key evidence and shared source preflight; inspection never reads keys."""
from contextlib import closing
from datetime import datetime,timezone
from .news_keys import NewsKeyRegistry,NewsKeyError,LEGACY
from .credential_store import NEWS_PROVIDERS,validate_secret
from .local_news import LocalIngestionService,ContentRights,FetchBlocked

LABELS={'marketaux':'Marketaux','newsdata':'NewsData.io','finnhub':'Finnhub'}
LOCAL={'saved':'Saved; local read verified','unchecked':'Not checked locally','missing':'Missing locally','read_failed':'Local read failed'}
API={'verified':'Verified','untested':'Not tested','authentication':'Authentication failed','restricted':'Restricted','failed':'Verification failed','pending':'Outcome unknown'}
CONDITIONS={'primary':'Enabled primary key','local':'Local key check','preview':'Preview permission',
    'processing':'Storage and NLP permission','quota':'Verified UTC-day allowance','ticker':'Finnhub ticker',
    'hold':'Provider safeguards clear','enabled':'Source enabled','sec_identity':'Real SEC User-Agent/contact configured'}


def storage_label(row):
    if row['local_state']=='saved' and row['check_basis']=='save_readback':return 'Saved; verified when saved'
    return LOCAL[row['local_state']]


def key_metadata(store,provider):
    """Only SQLite metadata, including exact credential version request evidence.

    A managed version's creation records a successful write/readback. It is dated
    evidence, not a fresh system-vault probe. Legacy existence stays unknown until
    the user explicitly checks it; no .env or credential API is accessed here.
    """
    NewsKeyRegistry.provider(provider)
    with closing(store.connect()) as db:
        db.row_factory=__import__('sqlite3').Row
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        policy=db.execute('SELECT primary_slot,legacy_enabled FROM news_key_policies WHERE provider=?',(provider,)).fetchone() if 'news_key_policies' in tables else None
        selected=policy[0] if policy else LEGACY
        rows=[dict(r) for r in db.execute('SELECT * FROM news_key_slots WHERE provider=? AND deleted_at IS NULL ORDER BY created_at,slot_id',(provider,))] if 'news_key_slots' in tables else []
        checks=[dict(r) for r in db.execute('SELECT * FROM news_key_checks WHERE provider=?',(provider,))] if 'news_key_checks' in tables else []
        if selected==LEGACY or any(r['slot_id']==LEGACY for r in checks):
            rows.insert(0,dict(provider=provider,slot_id=LEGACY,name='Existing credential / project .env',credential_ref=LEGACY,
                enabled=bool(policy[1]) if policy else True,created_at='',last_used_at=None,last_status='untested',last_error=None,deletion_pending=0))
        for row in rows:
            ref=row['credential_ref'];slot=row['slot_id']
            version=db.execute('SELECT created_at FROM news_key_versions WHERE provider=? AND slot_id=? AND credential_ref=?',(provider,slot,ref)).fetchone() if 'news_key_versions' in tables else None
            check=next((c for c in checks if c['slot_id']==slot and c['credential_ref']==ref),None)
            row['local_state']=check['state'] if check else 'saved' if version else 'unchecked'
            row['checked_at']=check['checked_at'] if check else version[0] if version else ''
            row['check_basis']='explicit_read' if check else 'save_readback' if version else 'none'
            request=db.execute('SELECT k.status,k.error,k.reserved_at FROM news_request_keys k WHERE k.provider=? AND k.slot_id=? AND k.credential_ref=? ORDER BY k.rowid DESC LIMIT 1',(provider,slot,ref)).fetchone() if 'news_request_keys' in tables else None
            if request:
                row['last_used_at']=request[2];row['last_status']=request[0];row['last_error']=request[1]
            row['api_state']=('verified' if request[0]=='ok' else 'authentication' if request[0]=='invalid' else
                'restricted' if request[1] in ('permission_or_subscription','rate_limit') else 'pending' if request[0]=='pending' else 'failed') if request else 'authentication' if row['last_status']=='invalid' else 'untested'
            row['api_checked_at']=request[2] if request else ''
            row['is_primary']=slot==selected
            row['role']='Disabled' if not row['enabled'] or row['deletion_pending'] else 'Primary key' if row['is_primary'] else 'Backup key'
    primary=next((r for r in rows if r['is_primary']),None)
    return {'rows':rows,'primary':primary,'backups':sum(r['role']=='Backup key' for r in rows)}


def check_local(store,provider,slot,*,secrets=None):
    """Explicit user action; returns fixed status only, never the credential."""
    registry=NewsKeyRegistry(store,secrets=secrets)
    rows=key_metadata(store,provider)['rows'];row=next((r for r in rows if r['slot_id']==slot),None)
    if row is None and slot==LEGACY:
        row={'slot_id':LEGACY,'credential_ref':LEGACY}
    if row is None:raise NewsKeyError('News key slot no longer exists')
    ref=row['credential_ref']
    try:
        value=registry.legacy_key(provider) if slot==LEGACY else registry.secrets.read_slot(provider,ref)
        state='missing' if not value else 'saved'
        if value:validate_secret(value)
    except (ValueError,OSError):state='read_failed'
    finally:value=None
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        if slot!=LEGACY and registry._row(db,provider,slot)[0]!=ref:
            raise NewsKeyError('The task key is disabled or changed; start a new task after reviewing settings')
        db.execute('CREATE TABLE IF NOT EXISTS news_key_checks(provider TEXT NOT NULL,slot_id TEXT NOT NULL,credential_ref TEXT NOT NULL,state TEXT NOT NULL,checked_at TEXT NOT NULL,PRIMARY KEY(provider,slot_id,credential_ref))')
        db.execute('INSERT OR REPLACE INTO news_key_checks VALUES (?,?,?,?,?)',(provider,slot,ref,state,datetime.now(timezone.utc).isoformat()));db.commit()
    return state


def source_readiness(store,provider,config,*,target='pipeline',service=None):
    if target not in ('pipeline','preview'):raise ValueError('Invalid source operation')
    service=service or LocalIngestionService(store);now=service.clock().astimezone(timezone.utc)
    info=key_metadata(store,provider);key=info['primary']
    rights=config.get('source_permissions',{}).get(provider,{})
    budget=config.get('budgets',{}).get(provider,{})
    with closing(store.connect()) as db:
        used=db.execute('SELECT count(*) FROM local_requests WHERE provider=? AND substr(reserved_at,1,10)=?',(provider,now.date().isoformat())).fetchone()[0]
    quota=(budget.get('utc_day')==now.date().isoformat() and type(budget.get('remaining')) is int and budget['remaining']>used)
    status=service.source_status(provider,configured=True)
    checks={'primary':bool(key and key['enabled'] and not key['deletion_pending'] and key['api_state']!='authentication'),
            'local':bool(key and key['local_state']=='saved'),'preview':bool(rights.get('preview') and rights.get('reference')),
            'quota':quota,'hold':not status.blocked}
    if target=='pipeline':
        checks['processing']=bool(rights.get('retain') and rights.get('analyze') and rights.get('reference'))
        checks['enabled']=provider in config.get('sources',[])
    if provider=='finnhub':checks['ticker']=bool(budget.get('symbol','').strip())
    return {'ready':all(checks.values()),'complete':[k for k,v in checks.items() if v],
            'missing':[k for k,v in checks.items() if not v],'hold_reason':status.reason if status.blocked else '',
            'keys':info,'remaining':max(0,budget.get('remaining',0)-used) if quota else 0,
            'quota_exhausted':bool(budget.get('utc_day')==now.date().isoformat() and type(budget.get('remaining')) is int and 0<budget['remaining']<=used)}


def source_plan(store,config,*,service=None):
    from .local_collectors import SOURCES
    ready=[];blocked={}
    for provider in config.get('sources',[]):
        if provider in {'sec_submissions','sec_press'}:
            from .sec_sources import user_agent,access_problem
            try:user_agent(store);problem=access_problem(store)
            except ValueError:problem='Configure an actual SEC User-Agent/contact before requesting'
            if problem:
                blocked[provider]={'missing':['sec_identity'],'complete':[],'hold_reason':problem};continue
            ready.append(provider);continue
        if provider in NEWS_PROVIDERS:
            state=source_readiness(store,provider,config,service=service)
            if not state['ready']:blocked[provider]=state;continue
        else:
            bucket=SOURCES.get(provider,{}).get('bucket','rba' if provider.startswith('rba_') else provider)
            status=(service or LocalIngestionService(store)).source_status(bucket,configured=True)
            if status.blocked:
                blocked[provider]={'missing':['hold'],'complete':[],'hold_reason':status.reason};continue
        ready.append(provider)
    return ready,blocked


def verify_api(store,provider,config,*,confirmed=False,service=None,expected_selection=None,details=False):
    """One explicitly confirmed preview, using unchanged provider reservations."""
    if confirmed is not True:raise FetchBlocked('Confirm one quota-consuming API preview before checking')
    service=service or LocalIngestionService(store)
    state=source_readiness(store,provider,config,target='preview',service=service)
    if not state['ready']:raise FetchBlocked('API preview is not ready; complete the listed conditions')
    selection=state['keys']['primary']
    ref={k:selection[k] for k in ('slot_id','credential_ref')}
    if expected_selection is not None and ref!=expected_selection:
        raise FetchBlocked('Primary key changed; confirm the selected version again before checking')
    permission=config['source_permissions'][provider]
    rights=ContentRights(preview=True,reference=permission['reference'])
    result,items=NewsKeyRegistry(store).fetch(service,provider,config['budgets'][provider]['topic'],selection=ref,
        rights=rights,remaining=state['remaining'],symbol=config['budgets'][provider].get('symbol') or None,explicit=True)
    with closing(store.connect()) as db:
        row=db.execute('SELECT k.request_id,r.reserved_at,r.completed_at FROM news_request_keys k JOIN local_requests r ON r.id=k.request_id WHERE k.provider=? AND k.slot_id=? AND k.credential_ref=? ORDER BY k.rowid DESC LIMIT 1',(provider,ref['slot_id'],ref['credential_ref'])).fetchone()
        db.execute('CREATE TABLE IF NOT EXISTS news_api_receipts(request_id TEXT PRIMARY KEY,raw_count INTEGER,preview_count INTEGER)')
        if row:db.execute('INSERT OR IGNORE INTO news_api_receipts VALUES (?,?,?)',(row[0],result.raw_count,len(items)))
        db.commit()
    if details:
        return {'status':result.status,'http_status':result.http_status,'returned':result.raw_count,'previewed':len(items),
                'requested_utc':row[1] if row else '', 'completed_utc':row[2] if row else '', 'items':items}
    return result.status,len(items)


def latest_receipt(store,provider):
    info=key_metadata(store,provider);primary=info['primary']
    if not primary:return None
    with closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='news_api_receipts'").fetchone():return None
        row=db.execute('SELECT r.status,r.http_status,x.raw_count,x.preview_count,r.reserved_at,r.completed_at FROM news_api_receipts x JOIN local_requests r ON r.id=x.request_id JOIN news_request_keys k ON k.request_id=r.id WHERE k.provider=? AND k.slot_id=? AND k.credential_ref=? ORDER BY r.rowid DESC LIMIT 1',(provider,primary['slot_id'],primary['credential_ref'])).fetchone()
    return dict(zip(('status','http_status','returned','previewed','requested_utc','completed_utc'),row)) if row else None
