"""Shared record denominators and strictly local, explicitly permitted imports."""
from dataclasses import asdict,replace
import csv,hashlib,io,json
from .local_news import NewsItem,ContentRights,utcnow
from .source_policies import SourcePolicy,FIELDS,PURPOSES,authorize
from .text_processing import prepare,canonical_url

TYPES={'media_news':'Media news','company_release':'Company press release',
       'regulatory_disclosure':'Regulatory disclosure','government':'Government / macro announcement',
       'development':'Authored development test text'}


def source_type(item):
    if item.provider=='authored_synthetic':return 'development'
    return item.source_type or ('government' if item.provider in {'abs_html','nist_rss','rba_rss','rba_html','sec_press'} else 'media_news')


def eligibility(item):
    if not item.rights.analyze:return False,'Local NLP permission is absent or revoked'
    try:authorize(item,('local_classification','local_sentiment'))
    except ValueError:return False,'No applicable current local NLP source policy'
    if item.document_type in {'10-K','10-Q','10-K/A','10-Q/A'}:return False,'Long periodic filing: no ordinary-news whole-document sentiment'
    try:origin=json.loads(item.provenance)
    except (TypeError,ValueError):origin={}
    if origin.get('sentiment_eligible') is False:return False,origin.get('ineligible_reason','No suitable sentiment text')
    if not (item.body or item.summary or item.title).strip():return False,'No permitted text'
    if item.content_version and item.language!='en':return False,'No verified language-adapted model for this text'
    return True,''


def analysis_status(item,result,states):
    if result:return 'Analyzed'
    eligible,reason=eligibility(item)
    if not eligible:return 'Permission required' if not item.rights.analyze or 'policy' in reason.lower() else 'Not applicable'
    state=states.get((item.article_id,item.content_version),{})
    return {'failed':'Failed','blocked':'Blocked','permission_required':'Permission required'}.get(state.get('analysis'),'Not analyzed')


def statistics(news,results,classes,states):
    """Each count deduplicates originals, with source types kept separate."""
    rows=[]
    for kind,label in TYPES.items():
        items={n.article_id:n for n in news if source_type(n)==kind}
        rows.append(dict(source_type=kind,label=label,records=len(items),
            analyzable=sum(eligibility(n)[0] for n in items.values()),
            analyzed=sum(k in results for k in items),
            unclassified=sum(not classes.get(k,{}).get('labels') for k in items)))
    return rows


def read_import(payload,format,policy):
    """Import asserts a user's actual licence evidence, never fetches a URL."""
    if not isinstance(payload,bytes) or len(payload)>5*1024**2:raise ValueError('Import maximum is 5 MiB')
    if not isinstance(policy,SourcePolicy) or policy.provider!='local_import':raise ValueError('Import policy is required')
    if not all(str(getattr(policy,k,'')).strip() for k in ('basis','retention','attribution','version')):raise ValueError('Record the actual import basis, retention and attribution')
    text=payload.decode('utf-8-sig')
    if format=='jsonl':rows=[json.loads(line) for line in text.splitlines() if line.strip()]
    elif format=='csv':rows=list(csv.DictReader(io.StringIO(text)))
    else:raise ValueError('Choose JSONL or CSV')
    if not 1<=len(rows)<=300:raise ValueError('Import 1–300 records per explicit action')
    allowed={'id','title','source','url','summary','body','source_type','document_type','company','ticker','cik','publication_date','timestamp'}
    items=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)-allowed or any(not isinstance(v,str) for v in row.values()):raise ValueError('Unsupported import schema')
        if any(not row.get(k,'').strip() for k in ('title','source','url')):raise ValueError('Title, source and original URL are required')
        if len(row['title'])>500 or len(row.get('body',''))>100000 or len(row.get('summary',''))>15000:raise ValueError('Import text exceeds bounds')
        kind=row.get('source_type') or 'media_news'
        if kind not in TYPES:raise ValueError('Unknown source type')
        day=row.get('publication_date','');stamp=row.get('timestamp','')
        from datetime import date,datetime
        if day:date.fromisoformat(day)
        if stamp and not datetime.fromisoformat(stamp.replace('Z','+00:00')).tzinfo:raise ValueError('Timestamp requires an explicit timezone')
        url=canonical_url(row['url'])
        reference=policy.basis
        item=NewsItem(hashlib.sha256((row['source']+'|'+url).encode()).hexdigest()[:32],'local_import',row['title'],row['source'],url,
            row.get('summary',''),stamp,'published',utcnow().isoformat(),(),ContentRights(True,True,'local_sentiment' in policy.purposes,False,reference),
            publication_date=day,company=row.get('company',''),body=row.get('body',''),source_type=kind,record_id=row.get('id',url),
            document_type=row.get('document_type',''),ticker=row.get('ticker',''),cik=row.get('cik',''),
            provenance=json.dumps(dict(source_id='local_import',origin='user-supplied local file; not an API fetch',
                import_policy=asdict(policy),attribution=policy.attribution,license_url=policy.license_url)))
        authorize(item,('retain','local_display'))
        items.append(prepare(item)[0])
    return items
