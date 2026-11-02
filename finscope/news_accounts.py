"""Nonsecret account attestations and immutable request attribution.

Unmapped keys share an unknown pool; keys never create additional quota.
Provider-wide budget/cooldown/unknown-request guards remain independently active.
"""
from contextlib import closing
from datetime import datetime,timezone
import json,re
from uuid import uuid4

SHARED='shared-unverified'

def ensure(store):
    with closing(store.connect()) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS news_accounts(provider TEXT,account_id TEXT,payload TEXT,PRIMARY KEY(provider,account_id));
        CREATE TABLE IF NOT EXISTS news_account_history(id TEXT PRIMARY KEY,provider TEXT,account_id TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS news_key_accounts(provider TEXT,slot_id TEXT,account_id TEXT,PRIMARY KEY(provider,slot_id));
        CREATE TABLE IF NOT EXISTS news_request_accounts(request_id TEXT PRIMARY KEY,provider TEXT,account_id TEXT,attestation_id TEXT);
        CREATE TABLE IF NOT EXISTS news_usage_receipts(request_id TEXT PRIMARY KEY,provider TEXT,observed_at TEXT,http_status INTEGER,headers TEXT);
        ''')

def exists(db,table):
    return bool(db.execute('SELECT 1 FROM sqlite_master WHERE name=?',(table,)).fetchone())

def account_id(db,provider,slot):
    row=db.execute('SELECT account_id FROM news_key_accounts WHERE provider=? AND slot_id=?',(provider,slot)).fetchone() if exists(db,'news_key_accounts') else None
    return row[0] if row else SHARED

def view(db,provider,slot,now):
    identity=account_id(db,provider,slot)
    row=db.execute('SELECT payload FROM news_accounts WHERE provider=? AND account_id=?',(provider,identity)).fetchone() if exists(db,'news_accounts') else None
    data=json.loads(row[0]) if row else None
    all_rows=db.execute('SELECT id,reserved_at,http_status FROM local_requests WHERE provider=?',(provider,)).fetchall()
    attributed=dict(db.execute('SELECT request_id,account_id FROM news_request_accounts WHERE provider=?',(provider,))) if exists(db,'news_request_accounts') else {}
    key_requests=dict(db.execute('SELECT request_id,slot_id FROM news_request_keys WHERE provider=?',(provider,))) if exists(db,'news_request_keys') else {}
    # Older unassigned receipts count conservatively against every account's
    # application-day cap, never disappear through a key/account switch.
    relevant=[r for r in all_rows if identity==SHARED or r[0] not in attributed or attributed[r[0]] in (identity,SHARED)
              or r[0] in key_requests and account_id(db,provider,key_requests[r[0]])==identity]
    day=now.astimezone(timezone.utc).date().isoformat()
    used=sum(r[1][:10]==day for r in relevant)
    current=bool(data and data['utc_day']==day)
    spent=sum(r[1]>=data['observed_at'] for r in relevant) if current else 0
    balance=max(0,data['remaining']-spent) if current and data['remaining'] is not None else None
    limited=any(r[2]==402 and (not data or r[1]>=data['observed_at']) for r in relevant)
    if exists(db,'news_usage_receipts'):
        ids={r[0] for r in relevant}
        limited=limited or any(identity in ids and (not data or observed>=data['observed_at']) and json.loads(headers).get('X-UsageLimit-Remaining')=='0'
            for identity,observed,headers in db.execute('SELECT request_id,observed_at,headers FROM news_usage_receipts WHERE provider=?',(provider,)))
    return dict(account_id=identity,attestation=data,current=current,used=used,
        remaining_after_local_requests=balance,usage_limit_unresolved=limited,
        provider_used=sum(r[1][:10]==day for r in all_rows))

def check(db,provider,slot,now,needed=1,required=False):
    info=view(db,provider,slot,now);data=info['attestation']
    if info['usage_limit_unresolved']:raise ValueError('HTTP 402 account usage limit requires new verified balance evidence; no key fallback')
    if not data:
        known_accounts=exists(db,'news_accounts') and db.execute('SELECT 1 FROM news_accounts WHERE provider=?',(provider,)).fetchone()
        if required or known_accounts:raise ValueError('Account balance unknown: record current account allowance before a new batch')
        return info
    if not info['current']:raise ValueError('Account allowance attestation expired for this UTC day')
    if data['remaining'] is None:raise ValueError('Account balance unknown; no allowance inferred from keys')
    if info['account_id']!=SHARED and not data['independent_confirmed']:raise ValueError('Independent account terms/allowance not confirmed')
    if info['remaining_after_local_requests']<needed:raise ValueError('Insufficient attested account allowance')
    if info['used']+needed>data['day_budget']:raise ValueError('Account application-day budget exhausted; explicitly revise total without resetting history')
    return info

def attest(store,provider,slot,identity,*,remaining,day_budget,reference,independent_confirmed=False,confirmed=False,now=None):
    from .news_keys import NewsKeyRegistry
    NewsKeyRegistry.provider(provider)
    from .news_readiness import key_metadata
    if slot not in {r['slot_id'] for r in key_metadata(store,provider)['rows']}:raise ValueError('Select a saved credential by name')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',identity) or len(identity)>23:raise ValueError('Use a short local account alias, not an account credential')
    if confirmed is not True:raise ValueError('Confirm the account budget explicitly')
    if identity!=SHARED and independent_confirmed is not True:raise ValueError('Confirm lawful independent account allowance and applicable terms')
    if remaining is not None and (type(remaining) is not int or not 0<=remaining<=10000000):raise ValueError('Invalid account remaining allowance')
    if type(day_budget) is not int or not 1<=day_budget<=10000:raise ValueError('Invalid account application-day total')
    if not isinstance(reference,str) or not 8<=len(reference)<=800 or re.search(r'api[_-]?key|api_token|Bearer|sk-|[A-Za-z0-9_-]{32,}',reference,re.I):raise ValueError('Use nonsecret account/terms evidence, never credentials')
    now=now or datetime.now(timezone.utc);now=now.astimezone(timezone.utc);ensure(store)
    value=dict(id=uuid4().hex,utc_day=now.date().isoformat(),observed_at=now.isoformat(),remaining=remaining,
        day_budget=day_budget,reference=reference,independent_confirmed=independent_confirmed,basis='user_attestation_not_supplier_probe')
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM local_requests WHERE provider=? AND status='pending'",(provider,)).fetchone():raise ValueError('Resolve unknown request before changing account allowance')
        old=db.execute('SELECT account_id FROM news_key_accounts WHERE provider=? AND slot_id=?',(provider,slot)).fetchone()
        if old and old[0]!=identity:raise ValueError('Existing key account attribution cannot be silently reassigned')
        db.execute('INSERT OR REPLACE INTO news_key_accounts VALUES (?,?,?)',(provider,slot,identity))
        db.execute('INSERT OR REPLACE INTO news_accounts VALUES (?,?,?)',(provider,identity,json.dumps(value)))
        db.execute('INSERT INTO news_account_history VALUES (?,?,?,?)',(value['id'],provider,identity,json.dumps(value)));db.commit()
    return value
