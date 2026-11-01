"""Offline link-domain evidence, never a claim of editorial originality."""
import json
from urllib.parse import urlsplit

PUBLISHERS={'reuters.com':'Reuters','bloomberg.com':'Bloomberg','cnbc.com':'CNBC',
 'wsj.com':'WSJ','ft.com':'Financial Times','finance.yahoo.com':'Yahoo Finance'}
INTERMEDIARIES=('finnhub.io','news.google.com','news.yahoo.com','feeds.finance.yahoo.com')


def link_key(url):
    from .text_processing import canonical_url
    from urllib.parse import parse_qsl,urlunsplit,urlencode
    p=urlsplit(canonical_url(url));pairs=parse_qsl(p.query,keep_blank_values=True)
    if len({k for k,_ in pairs})==len(pairs):pairs.sort()
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(pairs),''))


def attribution(item):
    try:p=json.loads(item.provenance)
    except (ValueError,TypeError):p={}
    host=(urlsplit(item.url).hostname or '').lower()
    intermediary=any(host==d or host.endswith('.'+d) for d in INTERMEDIARIES)
    direct=next((d for d in PUBLISHERS if host==d or host.endswith('.'+d)),None) if not intermediary else None
    meta=p.get('api_record',{})
    return dict(collection_service=item.provider if item.provider!='media_rss' else 'RSS / '+p.get('source_id','unknown'),
        supplier_reported_source=p.get('returned_source',item.source),link_domain=host,
        linked_publisher=PUBLISHERS[direct] if direct else 'Unverified',publisher_domain=direct or '',
        verification='Direct supplied URL matches reviewed publisher domain; page not requested' if direct else 'Intermediary or unreviewed domain; no publisher attribution inferred',
        editorial_originality='Unverified; a publisher-domain URL does not establish original authorship',
        original_link=item.url,provider_record_id=meta.get('record_id',''),explicit_wire_credit=p.get('wire_credit',''))


def observed(item):
    try:p=json.loads(item.provenance)
    except (TypeError,ValueError):p={}
    return dict(attribution=attribution(item),api_record=p.get('api_record',{}),query=p.get('query_cohort',{}),
        published_at=item.timestamp,timestamp_kind=item.timestamp_kind,
        captured_at=item.fetched_at,capture_task_id=p.get('capture_task_id') or p.get('capture_request_id',''))
