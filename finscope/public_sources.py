"""Bounded official-source collection. Two GETs/action, up to 50 records/response.

Source-level CC BY applies to staff-authored text only. No article-page traversal,
pagination, retry, media, arbitrary endpoints, API keys or implicit model calls.
"""
from contextlib import closing
from dataclasses import dataclass,field,replace
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser
from uuid import uuid4
import xml.etree.ElementTree as ET

import requests

from .api_sources import Article
from .local_news import ContentRights,FetchBlocked,NewsItem,utcnow
from .local_collectors import SOURCES
from .rate_limits import retry_deadline,safe_retry_after
from .rss_collector import _publication,CollectionError

USER_AGENT='FinScope-LocalNews/1.0'
MAX_BYTES=1_000_000
MAX_RECORDS=50
HTTP_BUDGET=2


class SourceError(CollectionError):
    def __init__(self,reason,*,status=None,retry_after=None):
        super().__init__(reason);self.status=status;self.retry_after=retry_after


@dataclass
class Node:
    tag:str
    attrs:dict=field(default_factory=dict)
    children:list=field(default_factory=list)
    parent:object=None

    def text(self):
        if self.tag in {'script','style','noscript','svg','iframe'}:
            return ''
        return ' '.join(c.text() if isinstance(c,Node) else c for c in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child,Node):
                yield from child.walk()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.root=Node('root');self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        if len(self.stack)>100:
            raise SourceError('HTML nesting exceeds limit')
        node=Node(tag,dict(attrs),parent=self.stack[-1]);self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack=self.stack[:i];break
    def handle_data(self,data):
        self.stack[-1].children.append(data)


def plain_text(html):
    tree=Tree();tree.feed(html)
    return ' '.join(tree.root.text().split())


def original_url(source_id,value):
    if not isinstance(value,str) or any(c.isspace() or ord(c)<32 for c in value):
        return ''
    config=SOURCES[source_id]
    url=urljoin(config['url'],value)
    try:
        parsed=urlsplit(url)
        prefix=('/news-events/news/' if source_id=='nist_rss' else '/media-centre/media-releases/' if source_id=='abs_html' else '/media-release/')
        if (parsed.scheme!='https' or parsed.netloc!=urlsplit(config['url']).netloc or parsed.username or parsed.password
                or parsed.query or parsed.fragment or not parsed.path.startswith(prefix) or len(parsed.path)<=len(prefix)):
            return ''
        return url
    except ValueError:
        return ''


def date_only(value):
    value=' '.join(value.split())
    for fmt in ('%Y-%m-%d','%d %B %Y','%d %b %Y'):
        try:return datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    return ''


def licensed_item(source_id,title,url,summary,raw_date,*,date_precision=False,source_element=''):
    config=SOURCES[source_id]
    if not original_url(source_id,url) or not title.strip() or len(title)>300 or len(summary)>10000:
        return None
    stamp='' if date_precision else _publication(raw_date)
    day=date_only(raw_date) if not stamp else ''
    # Excluded material is visible as restricted preview, never automatically saved/analyzed.
    excluded=bool(source_element and source_element.casefold() not in {config['publisher'].casefold(),'accc','abs'}) or bool(
        re.search(r'©(?!\s*Commonwealth)|copyright\s+(?:\d{4}|reserved|belongs)|all rights reserved|supplied by|courtesy of|third.party (?:content|copyright)',title+' '+summary,re.I))
    reference=f"{config['license']}; {config['terms_url']}; {config['scope']}; staff-authored text only; exclusions apply"
    rights=ContentRights(True,not excluded,not excluded,False,reference if not excluded else 'Third-party/special-rights marker; downstream use needs review')
    original=Article(source_id,title.strip(),url,config['publisher'],summary,stamp,'published')
    item=NewsItem.from_article(original,rights,publication_date=day)
    provenance={'source_id':source_id,'publisher_id':config['bucket'],'entry_url':config['url'],
        'attribution':config['attribution'],'derivative_attribution':config['derivative_attribution'],
        'license':config['license'],'license_url':config['license_url'],'terms_url':config['terms_url'],
        'license_checked_on':config['verified_on'],'rights_scope':config['scope'],'exclusions':config['exclusions'],
        'source_license_applied':not excluded,'publication_time_original':raw_date,
        'timestamp_precision':'timestamp' if stamp else 'date_only' if day else 'unknown',
        'text_basis':'headline_and_feed_description' if summary else 'headline_only_index' if source_id=='abs_html' else 'headline_only_feed',
        'source_element':source_element}
    return replace(item,provenance=json.dumps(provenance,ensure_ascii=False))


def parse_abs(payload,limit=50):
    tree=Tree();tree.feed(payload.decode('utf-8-sig'))
    items=[];seen=set()
    for anchor in tree.root.walk():
        if anchor.tag!='a':continue
        url=original_url('abs_html',anchor.attrs.get('href',''))
        title=' '.join(anchor.text().split())
        if not url or not title or url in seen:continue
        seen.add(url);row=anchor.parent;raw_date=''
        while row and row.tag!='root':
            links={original_url('abs_html',n.attrs.get('href','')) for n in row.walk() if n.tag=='a'}-{''}
            if len(links)>1:break
            match=re.search(r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',row.text())
            if match:raw_date=match.group();break
            times=[n for n in row.walk() if n.tag=='time']
            if times:
                value=times[0].attrs.get('datetime','')
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raw_date=value;break
            row=row.parent
        item=licensed_item('abs_html',title,url,'',raw_date,date_precision=True)
        if item:items.append(item)
        if len(items)>=limit:break
    if not items:
        raise SourceError('ABS index schema returned no supported release records')
    return items


def parse_accc(payload,limit=50):
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',payload,re.I) or b'\x00' in payload:
        raise SourceError('Unsafe RSS XML')
    try:root=ET.fromstring(payload)
    except ET.ParseError:raise SourceError('Invalid ACCC RSS XML') from None
    if root.tag!='rss' or root.find('channel') is None:
        raise SourceError('Unexpected ACCC feed schema')
    items=[];seen=set()
    for row in root.findall('./channel/item'):
        url=original_url('accc_rss',row.findtext('link','').strip())
        if not url or url in seen:continue
        seen.add(url)
        item=licensed_item('accc_rss',plain_text(row.findtext('title','')),url,
            plain_text(row.findtext('description','')),row.findtext('pubDate','').strip(),
            source_element=row.findtext('source','').strip())
        if item:items.append(item)
        if len(items)>=limit:break
    if not items:raise SourceError('ACCC feed returned no supported release records')
    return items


def parse_source(source_id,payload,limit):
    if type(limit) is not int or not 1<=limit<=MAX_RECORDS or len(payload)>MAX_BYTES:
        raise SourceError('Choose 1–50 records within a 1 MB response')
    if source_id=='abs_html':return parse_abs(payload,limit)
    if source_id=='accc_rss':return parse_accc(payload,limit)
    if source_id=='nist_rss':return parse_nist(payload,limit)
    raise SourceError('Choose a registered licensed source')


def http_get(url):
    allowed={c[k] for c in SOURCES.values() for k in ('url','robots') if k in c and 'license' in c}
    if url not in allowed and original_url('nist_rss',url)!=url:raise SourceError('Endpoint is not allowlisted')
    start=time.monotonic()
    try:
        with requests.get(url,headers={'User-Agent':USER_AGENT},timeout=(5,15),allow_redirects=False,stream=True) as response:
            retry=safe_retry_after(response.headers.get('Retry-After',''))
            if response.status_code!=200 or retry:
                raise SourceError('Source stopped: HTTP '+str(response.status_code),status=response.status_code,retry_after=retry)
            result=bytearray()
            for chunk in response.iter_content(8192):
                result.extend(chunk)
                if len(result)>MAX_BYTES or time.monotonic()-start>25:
                    raise SourceError('Source response exceeded the byte/time bound',status=response.status_code)
            return bytes(result),response.status_code
    except requests.RequestException:
        raise SourceError('Source transport failed; no retry',status=None) from None


def collect_source(service,source_id,*,limit=50,explicit=False,get=None,evidence_root=None,check_cancel=lambda:None):
    if explicit is not True or source_id not in {'abs_html','accc_rss','nist_rss'} or type(limit) is not int or not 1<=limit<=MAX_RECORDS:
        raise FetchBlocked('Explicit collection from a registered source with 1–50 parsed records is required')
    config=SOURCES[source_id]
    if not config.get('enabled'):
        raise FetchBlocked('Source access is not verified: '+config['access_status'])
    check_cancel()
    request_id,started=service._reserve(config['bucket'],1)
    directory=Path(evidence_root or service.store.path.parent/'public_sources')/request_id
    directory.mkdir(parents=True,exist_ok=False)
    log=[];transport=get or http_get
    allowed_urls={config['robots'],config['url']}
    request_budget=config.get('http_budget',HTTP_BUDGET)
    def request(url,filename):
        check_cancel()
        if len(log)>=request_budget or url not in allowed_urls or any(r['url']==url for r in log):
            raise SourceError('HTTP budget/endpoint bound exceeded')
        if source_id=='nist_rss' and log:
            # Cancellation remains responsive during source spacing.
            for _ in range(10):
                check_cancel();time.sleep(.1)
        record={'id':uuid4().hex,'url':url,'started_at':utcnow().isoformat(),'status':'pending','http_status':None,'response_bytes':None}
        log.append(record)
        with closing(service.store.connect()) as db:
            db.execute('INSERT INTO local_collector_http(id,action_id,source_id,url,started_at,status) VALUES (?,?,?,?,?,?)',
                (record['id'],request_id,source_id,url,record['started_at'],'pending'));db.commit()
        try:
            payload,status=transport(url)
            if status!=200:raise SourceError('Source stopped: HTTP '+str(status),status=status)
            if not isinstance(payload,bytes) or len(payload)>MAX_BYTES:raise SourceError('Response exceeds byte bound')
            # Keep hashes/status, not a bulk raw feed containing potentially
            # excluded third-party material outside the selected record limit.
            if filename=='robots.txt':(directory/filename).write_bytes(payload)
            record.update(status='ok',http_status=status,response_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
            return payload
        except SourceError as error:
            record.update(status='failed',http_status=error.status);raise
        finally:
            if record['status']!='pending':
                record['completed_at']=utcnow().isoformat()
                with closing(service.store.connect()) as db:
                    db.execute('UPDATE local_collector_http SET completed_at=?,status=?,http_status=?,response_bytes=? WHERE id=?',
                        (record['completed_at'],record['status'],record['http_status'],record['response_bytes'],record['id']));db.commit()
    report={'action_id':request_id,'source_id':source_id,'query_utc':started.isoformat(),'entry_url':config['url'],
            'http_request_budget':request_budget,'parse_record_limit':limit,'license':config['license'],'terms_url':config['terms_url'],'requests':log}
    try:
        robots=request(config['robots'],'robots.txt')
        policy=RobotFileParser();policy.parse(robots.decode('utf-8-sig').splitlines())
        if not policy.can_fetch(USER_AGENT,config['url']):raise SourceError('Robots disallows this fixed entry')
        payload=request(config['url'],'response.html' if source_id=='abs_html' else 'response.xml')
        items=parse_source(source_id,payload,limit)
        body_errors=[];body_hold=None
        if source_id=='nist_rss':
            for index,item in enumerate(items[:config['body_limit']]):
                if not item.rights.analyze or not policy.can_fetch(USER_AGENT,item.url):continue
                allowed_urls.add(item.url)
                try:
                    page=request(item.url,'body.html')
                    body,byline=extract_nist_body(page)
                    evidence=json.loads(item.provenance);evidence.update(body_status='extracted',body_byline=byline,body_sha256=hashlib.sha256(body.encode()).hexdigest())
                    items[index]=replace(item,body=body,provenance=json.dumps(evidence,ensure_ascii=False))
                except SourceError as error:
                    evidence=json.loads(item.provenance);evidence.update(body_status='fallback_to_permitted_feed_text',body_reason=str(error))
                    items[index]=replace(item,provenance=json.dumps(evidence,ensure_ascii=False))
                    body_errors.append(str(error))
                    if error.status in {401,403,429} or error.status is None or error.retry_after:
                        body_hold=retry_deadline(error.retry_after,utcnow()) if error.retry_after or error.status==429 else None
                        break
        report['body_errors']=body_errors
        report.update(status='ok',records=len(items),restricted_records=sum(not n.rights.retain for n in items))
        for i,item in enumerate(items):
            provenance=json.loads(item.provenance);provenance.update(action_id=request_id,fetched_at_utc=started.isoformat(),response_sha256=log[1].get('sha256',''))
            items[i]=replace(item,provenance=json.dumps(provenance,ensure_ascii=False),fetched_at=started.isoformat())
        status='failed' if body_errors else 'ok';hold=body_hold
    except (SourceError,UnicodeError) as error:
        report.update(status='failed',reason=str(error) if isinstance(error,SourceError) else 'Invalid source encoding',records=0)
        status='failed';items=[]
        hold=retry_deadline(getattr(error,'retry_after',None),utcnow()) if getattr(error,'retry_after',None) or getattr(error,'status',None)==429 else None
    except __import__('finscope.task_queue',fromlist=['Cancelled']).Cancelled:
        report.update(status='cancelled',reason='Explicit cancellation; completed HTTP stages preserved',records=0)
        with closing(service.store.connect()) as db:
            db.execute("UPDATE local_requests SET completed_at=?,status='cancelled',outcome='cancelled' WHERE id=?",(utcnow().isoformat(),request_id));db.commit()
        raise
    except Exception:
        report.update(status='pending',reason='Outcome needs review; durable reservation preserved',records=0)
        raise FetchBlocked(report['reason']) from None
    finally:
        report['completed_utc']=utcnow().isoformat()
        (directory/'collection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with closing(service.store.connect()) as db:
        db.execute('UPDATE local_requests SET completed_at=?,status=?,http_status=?,hold_until=?,outcome=? WHERE id=?',
            (report['completed_utc'],status,log[-1]['http_status'] if log else None,hold.isoformat() if hold else None,'records' if status=='ok' else 'collector_error',request_id));db.commit()
    if status!='ok' and not items:raise FetchBlocked(report['reason'])
    return items,report


def parse_nist(payload,limit):
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',payload,re.I) or b'\x00' in payload:raise SourceError('Unsafe RSS XML')
    try:root=ET.fromstring(payload)
    except ET.ParseError:raise SourceError('Invalid NIST RSS') from None
    items=[];seen=set()
    for row in root.findall('./channel/item'):
        url=original_url('nist_rss',row.findtext('link','').strip())
        if not url or url in seen:continue
        seen.add(url)
        item=licensed_item('nist_rss',plain_text(row.findtext('title','')),url,plain_text(row.findtext('description','')),
                           row.findtext('pubDate','').strip())
        if item:items.append(item)
        if len(items)>=limit:break
    if not items:raise SourceError('NIST RSS contained no supported official news')
    return items


def extract_nist_body(payload):
    tree=Tree();tree.feed(payload.decode('utf-8-sig'))
    # Drupal's article-body field, never the whole page/main/navigation.
    candidates=[n for n in tree.root.walk() if 'field--name-body' in n.attrs.get('class','').split()]
    if len(candidates)!=1:raise SourceError('Body selector unavailable; using feed text')
    node=candidates[0]
    for child in list(node.walk()):
        if child.tag in {'script','style','nav','footer','figure','aside','iframe','noscript'}:
            child.children=[]
    body=clean_body=node.text()
    body=' '.join(body.split())
    if not 120<=len(body)<=100000:raise SourceError('Body length invalid; using feed text')
    if re.search(r'copyright|all rights reserved|©|reprinted (?:with|by)|third.party content|courtesy of',clean_body,re.I):
        raise SourceError('Body has a special-rights marker; using permitted feed text')
    bylines=[n.text() for n in tree.root.walk() if 'field--name-field-author' in n.attrs.get('class','')]
    return body,' '.join(' '.join(bylines).split())[:500]
