"""Bounded public-feed discovery, independent of news/API/model permissions.

Only fixed feed URLs are requested. No redirects, article pages, remote images,
keys or model calls. The default durable discovery index contains factual URLs,
dates, fingerprints and receipts, not publisher titles/descriptions.
"""
from contextlib import closing
from dataclasses import asdict,dataclass
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
import hashlib,json,re,time
from urllib.parse import urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET

import requests

from .task_queue import ProcessLock

VERSION='media-rss-1'
MAX_BYTES=2_000_000
MAX_ITEMS=100

@dataclass(frozen=True)
class Feed:
    name:str
    url:str
    terms:str
    finding:str

FEEDS={
 'bloomberg':Feed('Bloomberg','https://www.bloomberg.com/feeds/markets/news.rss',
   'https://www.bloomberg.com/notices/tos/','No automatic storage/NLP grant verified; licensed distribution is separate'),
 'cnbc':Feed('CNBC','https://www.cnbc.com/id/100003114/device/rss/rss.html',
   'https://www.cnbc.com/rss-feeds/','RSS terms page unavailable to research browser; storage/NLP unverified'),
 'wsj':Feed('WSJ','https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
   'https://www.wsj.com/policy/subscriber-agreement','Personal reader access does not establish archiving/NLP rights'),
 'ft':Feed('Financial Times','https://www.ft.com/rss/home',
   'https://help.ft.com/legal-privacy/terms-and-conditions/','Terms access blocked; no archiving/NLP grant verified'),
 'yahoo':Feed('Yahoo Finance','https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA,MSFT,AAPL&region=US&lang=en-US',
   'https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html','RSS clause permits unmodified attributed display with links; local archiving/NLP not established'),
}

FIRST_PARTY={'bloomberg':'bloomberg.com','cnbc':'cnbc.com','wsj':'wsj.com','ft':'ft.com','yahoo':'finance.yahoo.com'}

def publisher_covered(source,url,p):
    host=(urlsplit(url).hostname or '').lower()
    domains=[FIRST_PARTY[source],*p.get('publisher_domains',[])]
    return any(host==d or host.endswith('.'+d) for d in domains)

def stamp():return datetime.now(timezone.utc)
def iso(d):return d.astimezone(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def date(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,TypeError):
        try:d=parsedate_to_datetime(value)
        except (ValueError,TypeError,OverflowError):return ''
    return iso(d) if d.tzinfo else ''

def safe_url(value):
    try:
        u=urlsplit(value)
        return bool(u.scheme in {'http','https'} and u.hostname and '.' in u.hostname
                    and not u.username and not u.password and len(value)<=2000
                    and not re.search(r'[\x00-\x20]',value)
                    and not re.fullmatch(r'[\d.:]+',u.hostname)
                    and not u.hostname.endswith(('.local','.localhost')))
    except ValueError:return False

def parse_feed(body,source):
    """Parse RSS/Atom within bounds. Body/content:encoded/media are ignored."""
    if source not in FEEDS:raise ValueError('Unknown feed')
    if len(body)>MAX_BYTES or re.search(br'<!\s*(?:DOCTYPE|ENTITY)',body,re.I):raise ValueError('XML bounds/DTD rejected')
    try:root=ET.fromstring(body)
    except ET.ParseError:raise ValueError('Not valid XML') from None
    local=lambda tag:tag.rsplit('}',1)[-1]
    fmt=local(root.tag)
    if fmt not in {'rss','RDF','feed'}:raise ValueError('Not RSS/Atom')
    nodes=[n for n in root.iter() if local(n.tag) in {'item','entry'}]
    if len(nodes)>MAX_ITEMS:raise ValueError('Feed item cap exceeded')
    rows=[];fields=set();rejected=0
    for n in nodes:
        values={}
        for c in n:
            key=local(c.tag);fields.add(key)
            if key=='link' and c.get('href') and c.get('rel','alternate')=='alternate':values['link']=c.get('href')
            elif key in {'title','link','guid','id','pubDate','published','updated','description','summary','creator','author','source','category'}:
                values.setdefault(key,''.join(c.itertext()).strip())
        title=values.get('title','');url=values.get('link','');summary=values.get('description',values.get('summary',''))
        if not title or len(title)>4000 or not safe_url(url) or len(summary)>40000:rejected+=1;continue
        # Canonical URL is preferred to unstable feed GUIDs; publisher feeds are
        # independent identities even when they syndicate the same wire story.
        from .text_processing import canonical_url
        key=digest(source+'|'+canonical_url(url))
        published=date(values.get('pubDate') or values.get('published') or values.get('updated',''))
        credit=' '.join(values.get(k,'') for k in ('creator','author','source'))
        wire='Reuters (explicit feed credit; syndicated, not direct Reuters access)' if re.search(r'\bReuters\b',credit,re.I) else ''
        rows.append(dict(identity=key,title=title,summary=summary,url=url,published=published,
                         publisher=FEEDS[source].name,wire_credit=wire,feed_credit=credit[:500],
                         fingerprint=digest(json.dumps([title,summary,published,credit],ensure_ascii=False))))
    return rows,dict(format=fmt,raw_items=len(nodes),valid_items=len(rows),rejected_items=rejected,
                     fields=sorted(fields),latest_published=max((r['published'] for r in rows),default=''))

def policy(value=None):
    """User-supplied actual source licence only. Defaults never grant NLP."""
    p=value or dict(basis='',fields=[],purposes=[],retention='',expires_at='')
    required={'basis','fields','purposes','retention','expires_at'}
    if not required<=set(p) or set(p)-required-{'publisher_domains'}:raise ValueError('Invalid media policy')
    p={**p,'publisher_domains':p.get('publisher_domains',[])}
    domains=p['publisher_domains']
    if not isinstance(domains,list) or len(domains)>20 or any(not isinstance(d,str) or not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}',d) for d in domains):raise ValueError('Invalid covered publisher domains')
    if domains and not p['basis'].strip():raise ValueError('Actual licence evidence must cover the named original publishers')
    if any(not isinstance(p[k],str) or len(p[k])>1500 for k in ('basis','retention','expires_at')):raise ValueError('Invalid media evidence')
    if (not isinstance(p['fields'],list) or set(p['fields'])-{'title','summary'} or
        not isinstance(p['purposes'],list) or set(p['purposes'])-{'display','retain','nlp','poll'}):raise ValueError('Invalid field/use scope')
    if (p['fields'] or p['purposes']) and not p['basis'].strip():raise ValueError('Actual licence/legal evidence required')
    if 'retain' in p['purposes'] and (not p['retention'].strip() or 'title' not in p['fields']):raise ValueError('Storage needs title scope and retention evidence')
    if 'retain' in p['purposes'] and p['retention']!='no_fixed_expiry' and not p['expires_at']:raise ValueError('Finite retention needs an enforceable expiry timestamp')
    if 'nlp' in p['purposes'] and not {'retain','display'}<=set(p['purposes']):raise ValueError('NLP needs covered storage/display')
    if p['expires_at'] and not date(p['expires_at']):raise ValueError('Invalid policy expiry')
    return p

def active_policy(p,now):return not p['expires_at'] or date(p['expires_at'])>iso(now)

def get_feed(url,headers):
    """One bounded streamed GET, no retry/redirect/session cookies."""
    with requests.get(url,headers=headers,timeout=(5,15),stream=True,allow_redirects=False) as r:
        body=bytearray();started=time.monotonic()
        if r.status_code==200:
            for chunk in r.iter_content(32768):
                body.extend(chunk)
                if len(body)>MAX_BYTES or time.monotonic()-started>25:raise ValueError('Response byte/time bound exceeded')
        return r.status_code,dict(r.headers),bytes(body)

class MediaMonitor:
    def __init__(self,store,*,get=get_feed,clock=stamp):
        self.store=store;self.get=get;self.clock=clock;self.migrate()
    def migrate(self):
        with closing(self.store.connect()) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='media_seen'").fetchone():return
        with ProcessLock(str(self.store.path)+'.schema.lock'),closing(self.store.connect()) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='media_seen'").fetchone():return
            import sqlite3
            path=self.store.path.parent/'backups'/('before-media-'+uuid4().hex+'.sqlite3');path.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(path)) as target:db.backup(target)
            db.executescript('''BEGIN IMMEDIATE;
              CREATE TABLE media_sources(source TEXT PRIMARY KEY,payload TEXT NOT NULL);
              CREATE TABLE media_requests(id TEXT PRIMARY KEY,source TEXT NOT NULL,started TEXT NOT NULL,
                finished TEXT,status TEXT NOT NULL,http_status INTEGER,report TEXT NOT NULL);
              CREATE TABLE media_seen(source TEXT NOT NULL,identity TEXT NOT NULL,url TEXT NOT NULL,
                published TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,
                fingerprint TEXT NOT NULL,payload TEXT NOT NULL,policy TEXT NOT NULL,PRIMARY KEY(source,identity));
              CREATE TABLE media_versions(source TEXT NOT NULL,identity TEXT NOT NULL,fingerprint TEXT NOT NULL,
                observed TEXT NOT NULL,PRIMARY KEY(source,identity,fingerprint));COMMIT;''')
    def states(self):
        with closing(self.store.connect()) as db:rows=dict(db.execute('SELECT source,payload FROM media_sources'))
        return {k:json.loads(rows[k]) if k in rows else dict(enabled=False,interval=15,daily_cap=12,
            etag='',modified='',watermark='',last_success='',last_check='',next_due='',hold='',failures=0,
            inflight='',policy=policy(),last_report={}) for k in FEEDS}
    def configure(self,source,*,enabled=False,interval=15,daily_cap=12,grant=None,
                  budget_day=None,budget_reference=None,coverage_mode='bounded_window'):
        from .media_schedule import validate_schedule
        if source not in FEEDS or type(enabled) is not bool:raise ValueError('Invalid bounded monitor scope')
        validate_schedule(interval,daily_cap,coverage_mode)
        p=policy(grant)
        from .news_keys import NewsKeyRegistry
        NewsKeyRegistry(self.store).reject_secret_text(json.dumps(p))
        if enabled and ('poll' not in p['purposes'] or not active_policy(p,self.clock())):raise ValueError('Scheduling requires applicable feed polling evidence')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            s=self._state(db,source)
            day=s.get('budget_day','') if budget_day is None else budget_day
            reference=s.get('budget_reference','') if budget_reference is None else budget_reference
            if not isinstance(day,str) or not isinstance(reference,str) or len(reference)>500:raise ValueError('Invalid budget attestation')
            if day:
                try:datetime.strptime(day,'%Y-%m-%d')
                except ValueError:raise ValueError('Budget day must be a UTC calendar date') from None
            if enabled and (day!=iso(self.clock())[:10] or not reference.strip()):raise ValueError('Confirm the current UTC-day HTTP budget and its basis before polling')
            NewsKeyRegistry(self.store).reject_secret_text(reference)
            # A successful new diagnostic plus an explicitly enabled, licensed
            # budget may resolve only the known old client/redirect guard.
            # The original unknown metrics and receipt remain in history.
            probe=s.get('probe_report',{});prior=s.get('last_report',{})
            if enabled and (s['hold'] or s['inflight']) and probe.get('diagnostic_state')=='completed' and probe.get('http_status')==200:
                known=(source=='ft' and prior.get('http_status')==301 or source=='bloomberg' and prior.get('outcome')=='persistence_failed')
                if s['inflight']:
                    row=db.execute('SELECT status,http_status FROM media_requests WHERE id=?',(s['inflight'],)).fetchone()
                    known=known and row==('persistence_failed',200)
                if not known:raise ValueError('An unknown/provider hold cannot be resolved by this source configuration')
                s.setdefault('retained_prior_checkpoints',[]).append(dict(inflight=s['inflight'],hold=s['hold'],report=prior))
                s.update(inflight='',hold='')
            s.update(enabled=enabled,interval=interval,daily_cap=daily_cap,policy=p,
                     budget_day=day,budget_reference=reference,coverage_mode=coverage_mode)
            for identity,payload in db.execute('SELECT identity,payload FROM media_seen WHERE source=?',(source,)).fetchall():
                saved=json.loads(payload)
                url=db.execute('SELECT url FROM media_seen WHERE source=? AND identity=?',(source,identity)).fetchone()[0]
                kept={k:v for k,v in saved.items() if k=='wire_credit' or 'retain' in p['purposes'] and k in p['fields'] and active_policy(p,self.clock()) and publisher_covered(source,url,p)}
                db.execute('UPDATE media_seen SET payload=?,policy=? WHERE source=? AND identity=?',(json.dumps(kept),json.dumps(p),source,identity))
            self._put(db,source,s);db.commit()
        from .media_preview import publish
        publish(self.store,source,[],iso(self.clock()))
        # Revocation/narrowing wins over previously promoted article grants.
        from .product_storage import ProductStorage
        from dataclasses import replace
        for item in ProductStorage(self.store).news():
            if item.provider!='media_rss' or item.source!=FEEDS[source].name:continue
            if ('nlp' not in p['purposes'] or not active_policy(p,self.clock()) or
                'title' not in p['fields'] or item.summary and 'summary' not in p['fields'] or not publisher_covered(source,item.url,p)):
                self.store.update_rights(item.article_id,replace(item.rights,analyze=False,external=False))
    def _state(self,db,source):
        row=db.execute('SELECT payload FROM media_sources WHERE source=?',(source,)).fetchone()
        return json.loads(row[0]) if row else self.states()[source]
    def _put(self,db,source,state):db.execute('INSERT OR REPLACE INTO media_sources VALUES (?,?)',(source,json.dumps(state)))
    def capacity(self,source):
        from .media_schedule import capacity
        now=self.clock()
        with closing(self.store.connect()) as db:
            used=db.execute('SELECT count(*) FROM media_requests WHERE source=? AND substr(started,1,10)=?',(source,iso(now)[:10])).fetchone()[0]
        return capacity(self.states()[source],used,now)
    def evidence(self,source):
        s=self.states()[source];reports=[s.get('last_report',{}),s.get('probe_report',{})]
        return max(reports,key=lambda r:r.get('checked_at',''))
    def success_at(self,source):
        with closing(self.store.connect()) as db:
            row=db.execute("SELECT MAX(started) FROM media_requests WHERE source=? AND status IN ('ok','metadata_recovered') AND http_status IN (200,304)",(source,)).fetchone()
        return row[0] or ''
    def check(self,source,*,explicit=False):
        if source not in FEEDS:raise ValueError('Unknown feed')
        now=self.clock();rid=uuid4().hex
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');s=self._state(db,source)
            if s['inflight'] or s['hold']:raise ValueError(s['hold'] or 'Previous dispatch outcome unknown; review required')
            if not explicit and (not s['enabled'] or 'poll' not in s['policy']['purposes'] or not active_policy(s['policy'],now)):return None
            if s.get('budget_day')!=iso(now)[:10] or not s.get('budget_reference','').strip():raise ValueError('Current UTC-day HTTP budget is unconfirmed or expired; no request')
            if s['next_due'] and s['next_due']>iso(now):raise ValueError('Source interval/backoff has not elapsed')
            used=db.execute('SELECT count(*) FROM media_requests WHERE source=? AND substr(started,1,10)=?',(source,iso(now)[:10])).fetchone()[0]
            if used>=s['daily_cap']:raise ValueError('Source UTC-day request cap reached')
            s.update(inflight=rid,last_check=iso(now));self._put(db,source,s)
            db.execute('INSERT INTO media_requests VALUES (?,?,?,NULL,?,NULL,?)',(rid,source,iso(now),'pending','{}'));db.commit()
        headers={'User-Agent':'FinScope-local-feed-reader/1.0','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'}
        for k,v in [('If-None-Match',s['etag']),('If-Modified-Since',s['modified'])]:
            if v:headers[k]=v
        request_url=FEEDS[source].url
        if source=='ft' and s.get('resolved_url'):
            from .media_probe import reviewed_ft_url
            request_url=reviewed_ft_url(s['resolved_url'],request_url)
        validator_url=s.get('validator_url',FEEDS[source].url)
        if validator_url!=request_url:
            headers.pop('If-None-Match',None);headers.pop('If-Modified-Since',None)
        # A new display grant/full restart cannot reconstruct titles from a304.
        # If only metadata survived, initialize the permitted representation
        # with this same one approved GET, rather than spending another request.
        representation=True
        p=s['policy']
        if 'display' in p['purposes'] and p['fields']:
            from .media_preview import read
            candidates=read(self.store,source,iso(now),allow_expired=True) or self.index(source)
            representation=any(any(k in r for k in p['fields']) for r in candidates)
            if not representation:
                headers.pop('If-None-Match',None);headers.pop('If-Modified-Since',None)
        started=time.perf_counter();status=None;meta={};rows=[];response_headers={};size=0;body=b''
        try:
            status,response_headers,body=self.get(request_url,headers);size=len(body)
            if status==200:rows,meta=parse_feed(body,source)
            elif status==304:
                if not s['last_success'] or not any(k in headers for k in ('If-None-Match','If-Modified-Since')):raise ValueError('Unexpected 304 without an earlier valid feed and conditional headers')
                meta={'format':s['last_report'].get('format',''),'valid_items':0,'latest_published':s['watermark']}
            else:meta={'reason':'HTTP '+str(status)+'; no redirect or alternative URL attempted'}
        except requests.RequestException:meta={'reason':'Transport outcome unknown; no automatic retry'}
        except ValueError as e:meta={'reason':str(e)}
        except Exception:meta={'reason':'Unexpected dispatch outcome; review required'}
        report={**meta,'request_id':rid,'source':source,'http_status':status,'checked_at':iso(now),
                'latency_ms':round((time.perf_counter()-started)*1000,2),'response_bytes':size,
                'new':0,'duplicates':0,'changed':0,'processable':0,'stored':0,'nlp_completed':0}
        from .media_probe import response_headers as safe_headers
        report.update(request_url=request_url,request_validators={k:v for k,v in headers.items() if k in {'If-None-Match','If-Modified-Since'}},
                      response_headers=safe_headers(response_headers),response_sha256=hashlib.sha256(body).hexdigest() if body else '',reusable_display_representation=representation)
        if rows:report['explicit_reuters_credits']=sum(bool(r['wire_credit']) for r in rows)
        checkpoint=[{k:r[k] for k in ('identity','url','published','fingerprint','publisher','wire_credit')} for r in rows]
        ok=status in {200,304} and 'reason' not in meta
        # Commit the received HTTP/schema evidence BEFORE indexing. A later disk
        # or schema error must not erase a known response or encourage a retry.
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');current=self._state(db,source);current['last_report']=report;current['recoverable']=bool(checkpoint) and ok
            self._put(db,source,current)
            db.execute('UPDATE media_requests SET status=?,http_status=?,report=? WHERE id=?',
                       ('received',status,json.dumps({**report,'metadata_checkpoint':checkpoint}),rid));db.commit()
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');current=self._state(db,source)
            if ok:
                counts=self._ingest(db,source,rows,now,current['policy']);report.update(counts)
                s['watermark']=max(s['watermark'],meta.get('latest_published',''));s['last_success']=iso(now);s['failures']=0
                for key,header in [('etag','ETag'),('modified','Last-Modified')]:
                    value=next((v for k,v in response_headers.items() if k.lower()==header.lower()),'')
                    if value and len(value)<=500 and not re.search(r'[\r\n]',value):s[key]=value
                s['validator_url']=request_url
                s['next_due']=iso(now+timedelta(minutes=s['interval']))
            else:
                s['failures']+=1
                if status==429:
                    from .rate_limits import retry_deadline
                    value=next((v for k,v in response_headers.items() if k.lower()=='retry-after'),None)
                    wait=min(1440,s['interval']*2**min(s['failures'],6))
                    s['next_due']=iso(max(now+timedelta(minutes=wait),retry_deadline(value,now)))
                else:s['hold']=meta.get('reason','Review required')
            # A concurrent stop/policy edit must not be overwritten by this response.
            s.update(enabled=current['enabled'],interval=current['interval'],daily_cap=current['daily_cap'],policy=current['policy'],inflight='',last_report=report)
            for key in ('budget_day','budget_reference','coverage_mode'):s[key]=current.get(key,'')
            if ok:s['next_due']=iso(now+timedelta(minutes=current['interval']))
            self._put(db,source,s)
            db.execute('UPDATE media_requests SET finished=?,status=?,http_status=?,report=? WHERE id=?',
                       (iso(self.clock()),'ok' if ok else 'failed',status,json.dumps(report),rid));db.commit()
        visible=[]
        p=s['policy'];allow=active_policy(p,now) and 'display' in p['purposes']
        for row in rows:
            covered=allow and publisher_covered(source,row['url'],p)
            entry={k:v for k,v in row.items() if k in {'url','published','wire_credit'} or covered and k in p['fields']}
            entry.update(feed_provider=FEEDS[source].name,publishing_domain=urlsplit(row['url']).hostname)
            visible.append(entry)
        from .media_preview import publish,read
        if status==304 and ok:
            candidates=read(self.store,source,iso(now),allow_expired=True)
            visible=[{k:v for k,v in row.items() if k not in {'title','summary'} or allow and k in p['fields'] and publisher_covered(source,row['url'],p)} for row in candidates]
        publish(self.store,source,visible,iso(now+timedelta(minutes=min(s['interval'],15))))
        return report,visible
    def _ingest(self,db,source,rows,now,p):
        counts=dict(new=0,duplicates=0,changed=0,processable=0,stored=0)
        for r in rows:
            old=db.execute('SELECT fingerprint FROM media_seen WHERE source=? AND identity=?',(source,r['identity'])).fetchone()
            counts['new' if not old else 'duplicates' if old[0]==r['fingerprint'] else 'changed']+=1
            keep=active_policy(p,now) and 'retain' in p['purposes'] and publisher_covered(source,r['url'],p)
            keep=keep and 'title' in r
            payload={k:r[k] for k in p['fields'] if k in r} if keep else {}
            payload['wire_credit']=r['wire_credit']  # Factual explicit credit, never an inferred licence.
            if keep:counts['stored']+=1
            if keep and 'nlp' in p['purposes']:counts['processable']+=1
            db.execute('''INSERT INTO media_seen VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(source,identity)
                DO UPDATE SET url=excluded.url,published=excluded.published,last_seen=excluded.last_seen,
                fingerprint=excluded.fingerprint,payload=excluded.payload,policy=excluded.policy''',
                (source,r['identity'],r['url'],r['published'],iso(now),iso(now),r['fingerprint'],json.dumps(payload),json.dumps(p)))
            db.execute('INSERT OR IGNORE INTO media_versions VALUES (?,?,?,?)',(source,r['identity'],r['fingerprint'],iso(now)))
        return counts
    def recover_received(self,source):
        """Finish only a known received metadata checkpoint, never redo HTTP.

        Unretained titles/descriptions cannot be reconstructed from a receipt.
        Old unknown/failed dispatches and missing checkpoints stay blocked.
        """
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');s=self._state(db,source)
            r=db.execute('SELECT status,http_status,report FROM media_requests WHERE id=? AND source=?',(s['inflight'],source)).fetchone()
            if not r or r[0]!='received' or r[1]!=200:raise ValueError('No recoverable received HTTP checkpoint')
            report=json.loads(r[2]);rows=report.pop('metadata_checkpoint',None)
            if rows is None:raise ValueError('Response metadata was not retained; no reconstruction or HTTP retry')
            report.update(self._ingest(db,source,rows,self.clock(),policy()))
            report['recovery']='Received metadata only; unretained publisher text unavailable'
            s.update(inflight='',recoverable=False,last_report=report,last_success=report['checked_at'],next_due=iso(self.clock()+timedelta(minutes=s['interval'])))
            s['watermark']=max(s['watermark'],report.get('latest_published',''))
            self._put(db,source,s)
            db.execute('UPDATE media_requests SET finished=?,status=?,report=? WHERE id=?',(iso(self.clock()),'metadata_recovered',json.dumps(report),report['request_id']));db.commit()
        return report
    def replay(self,source,rows):
        """Offline de-duplication check of an already obtained response; no HTTP."""
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');result=self._ingest(db,source,rows,self.clock(),self._state(db,source)['policy']);db.commit()
        return result
    def promote(self,source):
        """Copy only licensed text into the existing source-free analysis queue.

        The legacy append-only library has no deletion scheduler: finite-term
        grants remain in the discovery index, not in permanent news/history.
        """
        from .source_policies import SourcePolicy,FIELDS
        from .local_news import NewsItem,ContentRights
        from .product_storage import ProductStorage
        from .text_processing import prepare
        p=self.states()[source]['policy']
        if not active_policy(p,self.clock()) or not {'retain','display','nlp'}<=set(p['purposes']):raise ValueError('No applicable storage/display/local NLP grant')
        if p['expires_at'] or p['retention']!='no_fixed_expiry':raise ValueError('Finite-term grants cannot enter the permanent append-only library')
        scoped=SourcePolicy('user-reviewed-media-'+source,VERSION,'media_rss',p['basis'],FEEDS[source].terms,
            iso(self.clock()),tuple([f for f in FIELDS if f not in {'title','summary','body'}]+p['fields']),
            ('preview','retain','local_display','local_classification','local_sentiment'),p['retention'],FEEDS[source].name,
            'Independent local analysis; no publisher endorsement','RSS title/summary only; no linked pages, media or content:encoded')
        result={'new':0,'duplicates':0,'changed':0};data=ProductStorage(self.store)
        for row in self.index(source):
            if not row.get('title') or not publisher_covered(source,row['url'],p):continue
            # Recheck the current grant and the stored field scope.
            n=NewsItem(digest(source+'|'+row['url'])[:32],'media_rss',row['title'],FEEDS[source].name,row['url'],
                row.get('summary',''),row['published'],'published',row['first_seen'],(),
                ContentRights(True,True,True,False,p['basis']),source_type='media_news',
                provenance=json.dumps(dict(source_id=source,feed_url=FEEDS[source].url,
                    publishing_domain=urlsplit(row['url']).hostname,feed_provider=FEEDS[source].name,
                    wire_credit=row.get('wire_credit',''),licensed_publisher_domains=p.get('publisher_domains',[]),media_policy=asdict(scoped))))
            n=prepare(n)[0]
            from .source_policies import authorize
            authorize(n,('retain','local_classification','local_sentiment','local_display'))
            n,fresh,changed=data.save(n)
            result['new' if fresh else 'changed' if changed else 'duplicates']+=1
        return result
    def tick(self):
        """At most one due source per worker tick. No work while disabled."""
        self.expire()
        now=iso(self.clock())
        for source,s in self.states().items():
            if not s['enabled'] or s['hold'] or s['inflight'] or s['next_due'] and s['next_due']>now:continue
            cap=self.capacity(source)
            if not cap['budget_attested'] or not cap['remaining_gets']:continue
            try:
                result=self.check(source)
                grant=self.states()[source]['policy']
                if result and result[0]['http_status'] in {200,304} and {'retain','display','nlp'}<=set(grant['purposes']) and grant['retention']=='no_fixed_expiry' and not grant['expires_at']:
                    self.promote(source)
                    from .task_queue import TaskQueue,ACTIVE
                    from .product_storage import ProductStorage
                    from .batch_config import DEFAULT,finbert_cache_key
                    queue=TaskQueue(self.store);task=queue.get()
                    if not task or task['status'] not in ACTIVE:
                        data=ProductStorage(self.store)
                        ids=[n.article_id for n in data.news() if n.provider=='media_rss' and n.source==FEEDS[source].name and not data.cached(n,finbert_cache_key())]
                        if ids:queue.submit_batch('analyze',DEFAULT,confirmed=True,article_ids=ids)
                return result
            except ValueError:continue
        return None
    def expire(self):
        """Finite RSS caches only; no legacy originals/history are deleted."""
        with closing(self.store.connect()) as db:
            rows=db.execute('SELECT source,identity,payload,policy FROM media_seen WHERE payload!=?',('{}',)).fetchall()
            for source,identity,payload,p in rows:
                if not active_policy(json.loads(p),self.clock()):
                    data=json.loads(payload);kept={k:v for k,v in data.items() if k=='wire_credit'}
                    if kept!=data:db.execute('UPDATE media_seen SET payload=? WHERE source=? AND identity=?',(json.dumps(kept),source,identity))
            db.commit()
    def index(self,source):
        self.expire()
        with closing(self.store.connect()) as db:
            rows=db.execute('SELECT url,published,first_seen,last_seen,payload,policy FROM media_seen WHERE source=? ORDER BY published DESC',(source,)).fetchall()
        result=[]
        for url,published,first,last,payload,p in rows:
            grant=json.loads(p);current=self.states()[source]['policy']
            # Archived grants do not outrank present revocation/expiry.
            text=json.loads(payload) if active_policy(grant,self.clock()) and active_policy(current,self.clock()) and 'display' in current['purposes'] and publisher_covered(source,url,current) else {}
            text={k:v for k,v in text.items() if k in current['fields']}
            credit=json.loads(payload).get('wire_credit','Not captured in initial receipt')
            result.append(dict(feed_provider=FEEDS[source].name,publishing_domain=urlsplit(url).hostname,url=url,published=published,first_seen=first,last_seen=last,wire_credit=credit,**text))
        return result
    def preview(self,source):
        from .media_preview import read
        rows=read(self.store,source,iso(self.clock()));p=self.states()[source]['policy']
        allow=active_policy(p,self.clock()) and 'display' in p['purposes']
        return [{k:v for k,v in row.items() if k not in {'title','summary'} or allow and k in p['fields'] and publisher_covered(source,row['url'],p)} for row in rows]
