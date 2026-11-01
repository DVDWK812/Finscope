"""Explicit, single-run RSS diagnostics. Never edits earlier request receipts."""
from contextlib import closing
from datetime import timedelta
import hashlib,json,time
from urllib.parse import urljoin,urlsplit
from uuid import uuid4
import requests

from .media_monitor import FEEDS,MediaMonitor,get_feed,parse_feed,iso,stamp
from .task_queue import ProcessLock

REDIRECTS={301,302,303,307,308}
FT_HOSTS={'www.ft.com','ft.com'}
FT_PATHS={'/rss/home','/rss/home/international'}


def reviewed_ft_url(location,base):
    if not isinstance(location,str) or len(location)>2000 or any(ord(c)<33 for c in location):raise ValueError('Invalid FT Location')
    value=urljoin(base,location);u=urlsplit(value)
    if (u.scheme!='https' or u.hostname not in FT_HOSTS or u.port not in {None,443}
        or u.username or u.password or u.path not in FT_PATHS or u.query or u.fragment):
        raise ValueError('FT redirect is outside reviewed HTTPS official RSS paths; not followed')
    return value


def response_headers(headers):
    result={}
    for name in ('Location','ETag','Last-Modified','Content-Type','Cache-Control','Vary','Retry-After'):
        value=next((v for k,v in headers.items() if k.lower()==name.lower()),'')
        if isinstance(value,str) and value and len(value)<=2000 and '\r' not in value and '\n' not in value:result[name]=value
    return result


class MediaProbe:
    def __init__(self,store,*,get=get_feed,clock=stamp,minimum_interval=1.5):
        self.store=store;self.monitor=MediaMonitor(store,clock=clock);self.get=get;self.clock=clock
        self.minimum_interval=max(1.5,minimum_interval)
        with closing(store.connect()) as db:
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='media_probe_runs'").fetchone()
        if not exists:
            with ProcessLock(str(store.path)+'.schema.lock'),closing(store.connect()) as db:
                import sqlite3
                path=store.path.parent/'backups'/('before-media-probes-'+uuid4().hex+'.sqlite3');path.parent.mkdir(parents=True,exist_ok=True)
                with closing(sqlite3.connect(path)) as target:db.backup(target)
                db.execute('CREATE TABLE IF NOT EXISTS media_probe_runs(id TEXT PRIMARY KEY,source TEXT NOT NULL,payload TEXT NOT NULL)');db.commit()
    def begin(self,source,*,max_gets,reference,confirmed=False):
        if confirmed is not True or source not in {'bloomberg','ft'}:raise ValueError('Explicit source-specific RSS diagnostic authorization required')
        if type(max_gets) is not int or not 1<=max_gets<=(1 if source=='bloomberg' else 3):raise ValueError('Diagnostic HTTP cap exceeded')
        if not isinstance(reference,str) or not reference.strip() or len(reference)>500:raise ValueError('Record the actual authorization')
        from .news_keys import NewsKeyRegistry
        NewsKeyRegistry(self.store).reject_secret_text(reference)
        rid=uuid4().hex;now=self.clock()
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            # A new explicit budget does not resolve an unknown HTTP outcome.
            if db.execute("SELECT 1 FROM media_requests WHERE source=? AND status IN ('pending','received') LIMIT 1",(source,)).fetchone():raise ValueError('An HTTP/index checkpoint needs review before a new diagnostic')
            if db.execute("SELECT 1 FROM media_requests WHERE source=? AND status='failed' AND http_status IS NULL LIMIT 1",(source,)).fetchone():raise ValueError('An earlier transport outcome remains unknown; no new diagnostic')
            for (payload,) in db.execute('SELECT payload FROM media_probe_runs WHERE source=?',(source,)):
                old=json.loads(payload)
                if old['reference']==reference and old['utc_day']==iso(now)[:10]:return old['id']
                if old['state'] in {'ready','in_flight'}:raise ValueError('An earlier diagnostic is still active/unknown')
            current=self.monitor._state(db,source)
            last=current.get('probe_report') or current.get('last_report',{})
            if last.get('http_status')==429:
                from .rate_limits import retry_deadline
                until=retry_deadline(last.get('response_headers',{}).get('Retry-After'),__import__('datetime').datetime.fromisoformat(last['checked_at']))
                if iso(until)>iso(now):raise ValueError('Provider Retry-After remains active; no diagnostic')
            p=dict(id=rid,source=source,utc_day=iso(now)[:10],expires_at=iso(now+timedelta(hours=1)),
                max_gets=max_gets,used=0,state='ready',next_url=FEEDS[source].url,reference=reference,
                chain=[],prior_source_state=self.monitor._state(db,source))
            db.execute('INSERT INTO media_probe_runs VALUES (?,?,?)',(rid,source,json.dumps(p)));db.commit()
        return rid
    def get_run(self,identity):
        with closing(self.store.connect()) as db:r=db.execute('SELECT payload FROM media_probe_runs WHERE id=?',(identity,)).fetchone()
        if not r:raise ValueError('Diagnostic authorization not found')
        return json.loads(r[0])
    def step(self,identity):
        now=self.clock();request_id=uuid4().hex
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT source,payload FROM media_probe_runs WHERE id=?',(identity,)).fetchone()
            if not r:raise ValueError('Diagnostic not found')
            source,payload=r;p=json.loads(payload)
            if p['state']!='ready' or p['used']>=p['max_gets']:raise ValueError('Diagnostic is stopped, spent or has an unknown dispatch')
            if p['utc_day']!=iso(now)[:10] or p['expires_at']<=iso(now):raise ValueError('Diagnostic budget expired')
            url=p['next_url']
            if source=='ft':reviewed_ft_url(url,FEEDS[source].url)
            elif url!=FEEDS[source].url:raise ValueError('Only the fixed Bloomberg feed is approved')
            p.update(state='in_flight',used=p['used']+1,next_url='')
            db.execute('UPDATE media_probe_runs SET payload=? WHERE id=?',(json.dumps(p),identity))
            db.execute('INSERT INTO media_requests VALUES (?,?,?,NULL,?,NULL,?)',(request_id,source,iso(now),'pending',json.dumps({'diagnostic_id':identity,'url':url,'hop':p['used']-1})));db.commit()
        started=time.perf_counter();status=None;headers={};body=b'';reason=''
        try:status,headers,body=self.get(url,{'User-Agent':'FinScope-local-feed-reader/1.0','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
        except requests.RequestException:reason='Transport outcome unknown; no retry'
        except Exception:reason='Bounded dispatch failed; no retry'
        report=dict(source=source,request_id=request_id,diagnostic_id=identity,request_url=url,checked_at=iso(now),
            http_status=status,latency_ms=round((time.perf_counter()-started)*1000,2),response_bytes=len(body),
            response_sha256=hashlib.sha256(body).hexdigest() if body else '',response_headers=response_headers(headers),
            hop=p['used']-1,new=0,duplicates=0,changed=0,processable=0,stored=0,nlp_completed=0)
        # Persist the literal status and safe headers before parsing/indexing.
        with closing(self.store.connect()) as db:
            db.execute('UPDATE media_requests SET finished=?,status=?,http_status=?,report=? WHERE id=?',
                (iso(self.clock()),'received',status,json.dumps(report),request_id));db.commit()
        rows=[];next_url='';ok=False
        if not reason and status==200:
            try:rows,meta=parse_feed(body,source);report.update(meta);ok=True
            except ValueError as error:reason=str(error)
        elif not reason and source=='ft' and status in REDIRECTS:
            try:
                target=reviewed_ft_url(report['response_headers'].get('Location',''),url)
                if not report['response_headers'].get('Location'):raise ValueError('FT redirect has no Location')
                if target==url or target in [c['request_url'] for c in p['chain']]:raise ValueError('FT redirect cycle; not followed')
                if p['used']>=p['max_gets'] or p['used']>=3:raise ValueError('FT redirect hop/request budget reached')
                next_url=target
            except ValueError as error:reason=str(error)
        elif not reason:reason='HTTP '+str(status)+'; diagnostic stopped without retry'
        if reason:report['reason']=reason
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            state=self.monitor._state(db,source)
            if ok:
                report.update(self.monitor._ingest(db,source,rows,now,state['policy']))
                if source=='ft':state['resolved_url']=url
            p['chain'].append(report);p['state']='ready' if next_url else 'completed' if ok else 'blocked';p['next_url']=next_url
            state['probe_report']={**report,'diagnostic_state':p['state'],'total_gets':p['used']}
            # Keep hold/inflight and all old request rows exactly as observed.
            self.monitor._put(db,source,state)
            db.execute('UPDATE media_probe_runs SET payload=? WHERE id=?',(json.dumps(p),identity))
            db.execute('UPDATE media_requests SET status=?,report=? WHERE id=?',
                ('ok' if ok else 'redirect' if next_url else 'failed',json.dumps(report),request_id));db.commit()
        return report
    def run(self,identity):
        while self.get_run(identity)['state']=='ready':
            p=self.get_run(identity)
            if p['used']:time.sleep(self.minimum_interval)
            self.step(identity)
        return self.get_run(identity)
