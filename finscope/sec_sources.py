"""Bounded official SEC feeds/submissions, with durable per-URL receipts.

No request on import. No URL traversal, pagination, exhibit or external-site fetch.
"""
from contextlib import closing
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib,json,os,re,time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET

from .local_news import NewsItem,ContentRights,FetchBlocked,utcnow

PRESS_URL='https://www.sec.gov/news/pressreleases.rss'
DEFAULT_OPTIONS=dict(ciks=['0000789019','0000019617','0000018230','0000200406','0000034088','0001018724'],
    forms=['8-K','6-K','10-K','10-Q'],per_company=20,document_limit=12,request_limit=20,minimum_interval=1.5)
WATCHLIST_LABELS={'0000789019':'Microsoft','0000019617':'JPMorgan Chase','0000018230':'Caterpillar',
                 '0000200406':'Johnson & Johnson','0000034088':'Exxon Mobil','0001018724':'Amazon'}
ITEMS={'1.01':'Entry into a Material Definitive Agreement','2.01':'Completion of Acquisition or Disposition of Assets',
       '2.02':'Results of Operations and Financial Condition','2.03':'Creation of a Direct Financial Obligation',
       '5.02':'Departure or Appointment of Directors or Officers','7.01':'Regulation FD Disclosure','8.01':'Other Events'}


def validate_options(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULT_OPTIONS):raise ValueError('Unsupported SEC batch option')
    c={**DEFAULT_OPTIONS,**value}
    if (not isinstance(c['ciks'],list) or not 1<=len(c['ciks'])<=20 or len(set(c['ciks']))!=len(c['ciks'])
            or any(not isinstance(v,str) or not re.fullmatch(r'\d{10}',v) for v in c['ciks'])):raise ValueError('Choose 1–20 distinct ten-digit CIKs')
    if (not isinstance(c['forms'],list) or not c['forms'] or len(c['forms'])>8
            or set(c['forms'])-{'8-K','8-K/A','6-K','6-K/A','10-K','10-K/A','10-Q','10-Q/A'}):raise ValueError('Unsupported SEC form')
    for key,maximum in [('per_company',50),('document_limit',20),('request_limit',40)]:
        if type(c[key]) is not int or not (0 if key=='document_limit' else 1)<=c[key]<=maximum:raise ValueError('SEC bounded limit invalid: '+key)
    if type(c['minimum_interval']) not in (int,float) or not 1<=c['minimum_interval']<=60:raise ValueError('SEC interval must be at least one second')
    return c


def validate_user_agent(value):
    if (not isinstance(value,str) or not 12<=len(value)<=250 or any(ord(c)<32 or ord(c)>126 for c in value)
            or not re.search(r'\b[^\s<>@]+@[^\s<>@]+\.[A-Za-z]{2,}\b',value)
            or re.search(r'example\.(?:com|org|net)|example\.invalid|your.?email|sample.?company|placeholder',value,re.I)):
        raise ValueError('Configure a truthful SEC User-Agent with an actual contact email; placeholders are refused')
    return value


def user_agent(store):
    value=os.getenv('FINSCOPE_SEC_USER_AGENT','')
    if not value:
        from dotenv import dotenv_values
        from .local_credentials import project_env_path
        value=dotenv_values(project_env_path()).get('FINSCOPE_SEC_USER_AGENT','')
    if not value:
        with closing(store.connect()) as db:
            row=db.execute("SELECT payload FROM product_settings WHERE name='sec_user_agent'").fetchone()
        value=json.loads(row[0]) if row else ''
    return validate_user_agent(value)


def permitted_url(value):
    try:
        p=urlsplit(value)
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.query or p.fragment:return False
        if p.hostname=='data.sec.gov':return bool(re.fullmatch(r'/submissions/CIK\d{10}\.json',p.path))
        return p.hostname=='www.sec.gov' and bool(p.path=='/news/pressreleases.rss'
            or re.fullmatch(r'/Archives/edgar/data/\d{1,10}/\d{18}/[A-Za-z0-9_.-]+\.html?',p.path)
            or re.fullmatch(r'/(?:newsroom/press-releases|news/press-release)/[A-Za-z0-9_-]+',p.path))
    except (TypeError,ValueError):return False


def rights():
    from .source_policies import SEC
    return ContentRights(True,True,True,False,SEC.basis+' ; covered SEC-hosted public factual text only; exclusions apply')


def parse_submissions(payload,cik,options):
    data=json.loads(payload)
    if str(data.get('cik','')).zfill(10)!=cik:raise ValueError('SEC CIK mismatch')
    name=data.get('name','');tickers=data.get('tickers',[])
    if not isinstance(name,str) or not name or len(name)>300:raise ValueError('Missing issuer identity')
    recent=data.get('filings',{}).get('recent',{})
    required=('accessionNumber','filingDate','form','primaryDocument')
    if any(not isinstance(recent.get(k),list) for k in required):raise ValueError('SEC submissions schema mismatch')
    count=len(recent['accessionNumber'])
    if count>100000:raise ValueError('SEC submissions column row bound exceeded')
    if any(len(recent[k])!=count for k in required):raise ValueError('SEC columns are inconsistent')
    result=[]
    for index in range(count):
        def cell(key):
            values=recent.get(key,[])
            return str(values[index]) if isinstance(values,list) and len(values)>index and values[index] is not None else ''
        form=cell('form')
        if form not in options['forms']:continue
        accession=cell('accessionNumber');document=cell('primaryDocument');day=cell('filingDate')
        if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):continue
        try:datetime.strptime(day,'%Y-%m-%d')
        except ValueError:continue
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.html?',document):continue
        url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}'
        if not permitted_url(url):continue
        acceptance=cell('acceptanceDateTime');precision='unknown'
        try:
            parsed=datetime.fromisoformat(acceptance.replace('Z','+00:00'))
            if parsed.tzinfo:acceptance=parsed.astimezone(timezone.utc).isoformat();precision='timestamp'
            else:acceptance=''  # Never invent a timezone for an ambiguous value.
        except ValueError:acceptance=''
        provenance={'source_id':'sec_submissions','source_license_applied':True,'entry_url':f'https://data.sec.gov/submissions/CIK{cik}.json',
            'accession':accession,'primary_document':document,'filing_date':day,'acceptance_time_original':cell('acceptanceDateTime'),
            'report_date':cell('reportDate'),'form':form,'items_original':cell('items'),'document_description':cell('primaryDocDescription'),
            'attribution':'SEC EDGAR; issuer: '+name+'; accession: '+accession,'license':'SEC public-information dissemination policy',
            'license_url':'https://www.sec.gov/about/privacy-information','title_basis':'Generated display label from SEC issuer/form/filing date; not a news headline',
            'body_status':'metadata_only','sentiment_eligible':False,'ineligible_reason':'Filing metadata alone is not meaningful sentiment text',
            'timestamp_precision':'date_only','disclosure_precision':precision,'text_basis':'filing_metadata'}
        identity=cik+':'+accession
        result.append(NewsItem(hashlib.sha256(identity.encode()).hexdigest()[:32],'sec_submissions',f'{name} — {form} — {day}',
            'SEC EDGAR',url,'','','filed',utcnow().isoformat(),(),rights(),filed_date=day,company=name,
            provenance=json.dumps(provenance),language='en',source_type='regulatory_disclosure',record_id=identity,document_type=form,
            ticker=','.join(t for t in tickers if isinstance(t,str))[:100],cik=cik,disclosed_at=acceptance,disclosure_precision=precision,
            issuer_industry={'system':'SEC SIC','code':str(data.get('sic','')),'description':str(data.get('sicDescription','')),
                             'basis':f'https://data.sec.gov/submissions/CIK{cik}.json','use':'issuer industry only; not news-topic evidence'}))
        if len(result)>=options['per_company']:break
    return result


def extract_event(payload,form):
    """Only narrative current-report sections; never whole 10-K/Q sentiment."""
    from .public_sources import plain_text,Tree
    if form not in {'8-K','8-K/A','6-K','6-K/A'}:raise ValueError('Long periodic filings are metadata only')
    html=payload.decode('utf-8-sig');text=plain_text(html)
    if re.search(r'©|copyright|all rights reserved|third.party content|courtesy of',text,re.I):raise ValueError('Special-rights marker; metadata retained')
    spans=[]
    if form.startswith('8-K'):
        matches=list(re.finditer(r'\bItem\s+([1-9]\.\d{2})\s*[.:]?\s*',text,re.I))
        for i,match in enumerate(matches):
            if match.group(1) not in ITEMS:continue
            end=matches[i+1].start() if i+1<len(matches) else len(text)
            section=re.split(r'\bSIGNATURES?\b',text[match.start():end],maxsplit=1,flags=re.I)[0].strip()
            substantive=re.sub(r'[^a-z ]',' ',section.lower())
            # A heading or a pointer to an earnings exhibit is not an operating
            # narrative. Remove the heading before testing substantive content.
            narrative=re.sub(re.escape(ITEMS[match.group(1)]),' ',substantive,flags=re.I)
            if len(section)>=180 and re.search(r'revenue|income|profit|loss|agreement|acquisit|sale|segment|cash|debt|dividend|appoint|resign',narrative):
                spans.append((match.start(),match.start()+min(len(section),6000),match.group(1)))
    else:
        tree=Tree();tree.feed(html)
        for node in tree.root.walk():
            if node.tag!='p':continue
            paragraph=' '.join(node.text().split())
            if 180<=len(paragraph)<=6000 and re.search(r'revenue|net income|operating profit|financial results|acquisition',paragraph,re.I) and not re.search(r'forward.looking|incorporated by reference|exhibit\s*99',paragraph,re.I):
                start=text.find(paragraph)
                if start>=0:spans.append((start,start+len(paragraph),'6-K narrative'))
    if not spans:raise ValueError('No meaningful operating-event excerpt; metadata retained')
    start,end,section=spans[0]
    return text[start:end],dict(body_status='event_excerpt',sentiment_eligible=True,ineligible_reason='',
        input_text_type='current-report operating-event excerpt',extraction_version='sec-event-span-1',
        document_characters=len(text),document_span_start=start,document_span_end=end,document_coverage=(end-start)/max(1,len(text)),event_section=section)


def parse_press(payload,limit):
    from .public_sources import plain_text
    from .rss_collector import _publication
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',payload,re.I) or b'\x00' in payload:raise ValueError('Unsafe feed XML')
    root=ET.fromstring(payload);result=[];seen=set()
    for row in root.findall('./channel/item'):
        url=row.findtext('link','').strip();title=plain_text(row.findtext('title',''));summary=plain_text(row.findtext('description',''))
        if not permitted_url(url) or url in seen or not title or len(title)>500 or len(summary)>15000:continue
        if re.search(r'©|copyright|all rights reserved|courtesy of',title+' '+summary,re.I):continue
        seen.add(url);stamp=_publication(row.findtext('pubDate',''))
        origin=dict(source_id='sec_press',source_license_applied=True,entry_url=PRESS_URL,
            license='SEC public-information dissemination policy',license_url='https://www.sec.gov/about/privacy-information',
            attribution='Source: U.S. Securities and Exchange Commission',text_basis='official RSS title and description',
            publication_time_original=row.findtext('pubDate',''),timestamp_precision='timestamp' if stamp else 'unknown')
        result.append(NewsItem(hashlib.sha256(url.encode()).hexdigest()[:32],'sec_press',title,'U.S. Securities and Exchange Commission',
            url,summary,stamp,'published',utcnow().isoformat(),(),rights(),provenance=json.dumps(origin),language='en',
            source_type='government',record_id=row.findtext('guid',url),document_type='SEC press release'))
        if len(result)>=limit:break
    if not result:raise ValueError('No supported SEC press release entries')
    return result


def access_problem(store):
    """A failed/unknown SEC request is never silently retried by a later batch."""
    with closing(store.connect()) as db:
        row=db.execute("SELECT status,http_status FROM local_collector_http WHERE source_id LIKE 'sec_%' AND (status IN ('pending','unknown') OR (status='failed' AND http_status IS NULL) OR http_status IN (401,403,429)) ORDER BY rowid DESC LIMIT 1").fetchone()
    return 'SEC access requires review: unknown request or HTTP '+str(row[1]) if row else ''


class SECCollector:
    def __init__(self,store,queue,task_id,options,check,*,get=None,sleep=time.sleep):
        self.store=store;self.queue=queue;self.task_id=task_id;self.options=validate_options(options);self.check=check
        self.get=get;self.sleep=sleep;self.archive=store.path.parent/'batch_archive'
        self.failures=[]
        try:self.ua=user_agent(store)
        except ValueError as error:raise FetchBlocked(str(error)) from None
    def request(self,url,transform,source):
        if not permitted_url(url):raise FetchBlocked('Unregistered SEC URL')
        key='sec_http:'+hashlib.sha256(url.encode()).hexdigest();step=self.queue.step(self.task_id,key)
        if step:
            if step[0]!='ok':raise FetchBlocked('Earlier SEC request failed/unknown; no resend')
            path=self.archive/step[1]['archive']
            if path.parent.resolve()!=self.archive.resolve() or path.is_symlink():raise FetchBlocked('Invalid local archive path')
            payload=path.read_bytes()
            if hashlib.sha256(payload).hexdigest()!=step[1]['sha256']:raise FetchBlocked('Local archive integrity mismatch; no network repair')
            return json.loads(payload)
        problem=access_problem(self.store)
        if problem:raise FetchBlocked(problem)
        with closing(self.store.connect()) as db:
            used=db.execute("SELECT count(*) FROM local_collector_http WHERE action_id=? AND source_id LIKE 'sec_%'",(self.task_id,)).fetchone()[0]
            last=db.execute("SELECT started_at FROM local_collector_http WHERE source_id LIKE 'sec_%' ORDER BY rowid DESC LIMIT 1").fetchone()
        if used>=self.options['request_limit']:raise FetchBlocked('SEC batch HTTP request limit reached')
        if last:
            delay=self.options['minimum_interval']-(utcnow()-datetime.fromisoformat(last[0])).total_seconds()
            while delay>0:
                self.check();wait=min(delay,.5);self.sleep(wait);delay-=wait
        self.check();identity=uuid4().hex;start=utcnow().isoformat()
        self.queue.save_step(self.task_id,key,'pending',{'reason':'SEC dispatch outcome unknown; never resend automatically'})
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO local_collector_http VALUES (?,?,?,?,?,?,?,?,?)',
                (identity,self.task_id,source,url,start,None,'pending',None,None));db.commit()
        status=None;payload=b''
        try:
            if self.get:status,payload=self.get(url,{'User-Agent':self.ua,'Accept-Encoding':'gzip, deflate'})
            else:
                import requests
                with requests.get(url,headers={'User-Agent':self.ua,'Accept-Encoding':'gzip, deflate'},timeout=(5,20),allow_redirects=False,stream=True) as response:
                    status=response.status_code
                    chunks=[];size=0
                    for chunk in response.iter_content(65536):
                        size+=len(chunk)
                        if size>8*1024**2:raise ValueError('SEC response exceeded 8 MiB bound')
                        chunks.append(chunk)
                    payload=b''.join(chunks)
            if status!=200:raise FetchBlocked('SEC HTTP '+str(status)+'; no retry or alternate route')
            value=transform(payload)
            encoded=json.dumps(value,ensure_ascii=False).encode();digest=hashlib.sha256(encoded).hexdigest()
            self.archive.mkdir(parents=True,exist_ok=True);path=self.archive/(digest+'.json')
            if not path.exists():path.write_bytes(encoded)
            self.queue.save_step(self.task_id,key,'ok',{'archive':path.name,'sha256':digest,'response_sha256':hashlib.sha256(payload).hexdigest()})
            state='ok'
        except Exception as error:
            state='failed' if isinstance(error,(ValueError,FetchBlocked)) else 'unknown'
            reason=(str(error) if isinstance(error,ValueError) and str(error).startswith(('SEC ','No meaningful','Special-rights','Long periodic','Missing issuer'))
                    else 'SEC request/transform failed: '+type(error).__name__)
            evidence={'reason':reason,'response_sha256':hashlib.sha256(payload).hexdigest()}
            if '/submissions/' in url and status==200:
                try:evidence['response_recent_rows']=len(json.loads(payload)['filings']['recent']['accessionNumber'])
                except (KeyError,TypeError,ValueError):pass
            self.queue.save_step(self.task_id,key,'failed',evidence)
            raise
        finally:
            with closing(self.store.connect()) as db:
                db.execute('UPDATE local_collector_http SET completed_at=?,status=?,http_status=?,response_bytes=? WHERE id=?',
                    (utcnow().isoformat(),locals().get('state','pending'),status,len(payload),identity));db.commit()
        return value
    def collect(self,source,limit,*,on_items=lambda rows:None):
        from .product_storage import decode,ProductStorage
        storage=ProductStorage(self.store)
        if source=='sec_press':
            rows=[decode(json.dumps(row)) for row in self.request(PRESS_URL,lambda b:[asdict(n) for n in parse_press(b,limit)],source)]
            on_items(rows);return rows
        items=[];docs=0
        for cik in self.options['ciks']:
            self.check()
            try:rows=self.request(f'https://data.sec.gov/submissions/CIK{cik}.json',lambda b:[asdict(n) for n in parse_submissions(b,cik,self.options)],source)
            except (ValueError,FetchBlocked) as error:
                reason='CIK '+cik+': '+(str(error) if isinstance(error,FetchBlocked) else 'SEC metadata schema validation failed')
                self.failures.append(reason);self.queue.save_step(self.task_id,'sec_company:'+cik,'failed',{'reason':reason})
                continue
            company_items=[decode(json.dumps(row)) for row in rows][:max(0,limit-len(items))]
            company_docs=0
            for index,n in enumerate(company_items):
                previous=storage.merge_available_text(n)
                if previous.body:
                    company_items[index]=previous;continue
                share=max(1,(self.options['document_limit']+len(self.options['ciks'])-1)//len(self.options['ciks']))
                if docs>=self.options['document_limit'] or company_docs>=share or n.document_type not in {'8-K','8-K/A','6-K','6-K/A'}:continue
                company_docs+=1
                docs+=1
                try:
                    body,evidence=self.request(n.url,lambda b:extract_event(b,n.document_type),source)
                    origin=json.loads(n.provenance);origin.update(evidence)
                    company_items[index]=replace(n,body=body,provenance=json.dumps(origin))
                except (ValueError,FetchBlocked) as error:
                    # The factual filing metadata is still useful and permitted.
                    origin=json.loads(n.provenance);origin['body_reason']=str(error)[:250]
                    company_items[index]=replace(n,provenance=json.dumps(origin))
            on_items(company_items);items.extend(company_items)
            # Each completed company survives interruption before the next one.
            self.queue.save_step(self.task_id,'sec_company:'+cik,'ok',[asdict(n) for n in company_items])
            if len(items)>=limit:break
        return items
