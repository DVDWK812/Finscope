"""Recorded use basis, not a publisher licence manufactured from a checkbox."""
from datetime import datetime, timezone
from dataclasses import replace
import json
from urllib.parse import urlsplit

PURPOSES = ('retain', 'local_display', 'local_classification', 'local_sentiment')
STATUSES = ('licensed', 'research_unverified', 'restricted')
REFERENCES = {
    'marketaux': 'https://www.marketaux.com/tos',
    'finnhub': 'https://finnhub.io/terms-of-service',
    'cnbc': 'https://www.nbcuniversal.com/terms/prohibited-actions',
    'bloomberg': 'https://www.bloomberg.com/notices/tos/',
}
# A research acknowledgement cannot waive this identified direct-feed restriction.
# An actual source-specific exception must be recorded separately as licence evidence.
RESTRICTIONS = {'rss:cnbc': REFERENCES['cnbc'],'rss:bloomberg':REFERENCES['bloomberg']}


def utcnow():
    return datetime.now(timezone.utc)


def deadline(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Use an explicit timezone-aware text expiry') from None


def validate(scope, *, now=None, active=True):
    allowed = {'source', 'status', 'reference', 'fields', 'expires_at', 'confirmed',
               'exception_reference', 'domains'}
    if not isinstance(scope, dict) or set(scope) - allowed:
        raise ValueError('Invalid source use scope')
    s = dict(scope)
    if s.get('source') not in {'marketaux', 'finnhub', 'rss:bloomberg', 'rss:cnbc', 'rss:wsj', 'rss:ft', 'rss:yahoo'}:
        raise ValueError('Select a supported media source')
    if s.get('status') not in STATUSES:
        raise ValueError('Record licensed, research_unverified or restricted separately')
    if s['status'] == 'restricted':
        raise ValueError('An identified restriction blocks this operation')
    if s.get('confirmed') is not True:
        raise ValueError('Confirm the source-level fields, purpose, expiry and unresolved applicability')
    if not isinstance(s.get('reference'), str) or not s['reference'].strip() or len(s['reference']) > 1500:
        raise ValueError('Record the actual licence evidence or the unverified research scope')
    if not isinstance(s.get('fields'), list) or not all(isinstance(f,str) for f in s['fields']) or 'title' not in s['fields'] or set(s['fields']) - {'title', 'summary'}:
        raise ValueError('This flow accepts actual titles and optionally returned summaries only')
    end = deadline(s.get('expires_at'))
    if active and end <= (now or utcnow()):
        raise ValueError('Media text use expired')
    s['expires_at'] = end.isoformat()
    exception = s.get('exception_reference', '')
    if not isinstance(exception, str) or len(exception) > 1500:
        raise ValueError('Invalid specific exception evidence')
    if s['source'] in RESTRICTIONS and (s['status'] != 'licensed' or not exception.strip()):
        raise ValueError('Direct-feed restriction requires a specific applicable exception: ' + RESTRICTIONS[s['source']])
    domains = s.get('domains', [])
    if not isinstance(domains, list) or len(domains) > 20:
        raise ValueError('Invalid publication-domain scope')
    if s['source']=='marketaux' and not domains:raise ValueError('Select an explicit Marketaux publication-domain whitelist')
    from .api_sources import MarketauxFilters
    if domains:
        MarketauxFilters(tuple(domains)).parameters()
    s.update(exception_reference=exception, domains=domains)
    return s


def scope_of(item):
    try:
        return json.loads(item.provenance).get('media_use')
    except (ValueError, TypeError, AttributeError):
        return None


def authorize(item, purposes, *, now=None):
    s = validate(scope_of(item), now=now)
    source = 'rss:' + json.loads(item.provenance).get('source_id', '') if item.provider == 'media_rss' else item.provider
    if s['source'] != source or item.body or item.rights.external or item.source_type != 'media_news':
        raise ValueError('Outside the confirmed API/feed headline-summary scope')
    if item.summary and 'summary' not in s['fields']:
        raise ValueError('Summary is outside the confirmed fields')
    if not item.title.strip() or not purposes or set(purposes) - set(PURPOSES) - {'preview'}:
        raise ValueError('Only private local display, storage, classification and fixed sentiment inference')
    host = (urlsplit(item.url).hostname or '').lower()
    if not host or urlsplit(item.url).username or urlsplit(item.url).password:
        raise ValueError('Invalid original publication link')
    if s['domains'] and not any(host == d or host.endswith('.' + d) for d in s['domains']):
        raise ValueError('Publication domain outside confirmed source scope')
    item.rights.require('preview')
    item.rights.require('retain')
    if set(purposes) & {'local_classification', 'local_sentiment'}:
        item.rights.require('analyze')
    return {'basis_status': s['status'], 'licence_evidence_recorded': s['status'] == 'licensed',
            'publisher_permission_independently_verified': False,
            'reference': s['reference'], 'fields': s['fields'], 'expires_at': s['expires_at'],
            'purposes': list(purposes), 'training': False, 'external_transmission': False,
            'redistribution': False, 'scope': s}


def apply(item, scope):
    s = validate(scope)
    from .local_news import ContentRights
    try:
        origin = json.loads(item.provenance)
    except (ValueError, TypeError):
        origin = {}
    origin.update(media_use=s, input_origin='official API response' if item.provider != 'media_rss' else 'official RSS supplied fields',
                  returned_source=item.source, publishing_domain=urlsplit(item.url).hostname,
                  source_qualification='Supplier-reported source and original-link domain; no claim of editorial originality or direct publisher licence',
                  attribution='Source: ' + item.source + '; original publication link retained')
    label = 'Recorded licence evidence' if s['status'] == 'licensed' else 'User research confirmation; applicability unverified; not publisher permission'
    result = replace(item, summary=item.summary if 'summary' in s['fields'] else '', body='', processed_text='',
                     content_version='', source_type='media_news',
                     rights=ContentRights(True, True, True, False, label + ': ' + s['reference']),
                     provenance=json.dumps(origin, ensure_ascii=False))
    authorize(result, PURPOSES)
    return result


def decisions(store):
    from contextlib import closing
    with closing(store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='media_use_decisions'").fetchone()
    return json.loads(row[0]) if row else {}


def enforce_decision(store,scope,purposes=()):
    record=decisions(store).get(scope['source'],{})
    if record.get('status')=='restricted':
        raise ValueError('Recorded source restriction remains active: '+record.get('reference',''))
    if scope['source'].startswith('rss:'):
        from contextlib import closing
        with closing(store.connect()) as db:
            row=db.execute('SELECT payload FROM media_sources WHERE source=?',(scope['source'][4:],)).fetchone()
        if not row:raise ValueError('Current feed use scope unavailable')
        p=json.loads(row[0])['policy']
        if (p.get('basis_status')=='restricted' or not {'retain','display'}<=set(p['purposes'])
                or not set(scope['fields'])<=set(p['fields']) or p['expires_at'] and deadline(p['expires_at'])<=utcnow()):
            raise ValueError('Current source scope no longer covers retained text')
        if set(purposes)&{'local_classification','local_sentiment'} and 'nlp' not in p['purposes']:
            raise ValueError('Current source scope no longer covers NLP')


def record_decision(store,scope):
    from contextlib import closing
    if not isinstance(scope,dict) or scope.get('status') not in STATUSES or not isinstance(scope.get('reference'),str) or not scope['reference'].strip() or len(scope['reference'])>1500:
        raise ValueError('Record the source and concrete use basis or restricting term')
    if scope.get('source') not in {'marketaux','finnhub',*RESTRICTIONS,'rss:yahoo','rss:ft','rss:wsj','rss:bloomberg'}:raise ValueError('Unknown source')
    from .news_keys import NewsKeyRegistry
    NewsKeyRegistry(store).reject_secret_text(json.dumps(scope))
    records=decisions(store);old=records.get(scope['source'],{})
    if old.get('status')=='restricted' and (scope['status']!='licensed' or not scope.get('exception_reference','').strip()):
        raise ValueError('A research confirmation cannot waive the recorded restriction; supply specific applicable exception evidence')
    if scope['status']!='restricted':scope=validate(scope)
    records[scope['source']]=scope
    with closing(store.connect()) as db:
        db.execute("INSERT OR REPLACE INTO product_settings VALUES ('media_use_decisions',?)",(json.dumps(records),));db.commit()
    if scope['status']=='restricted':
        from .expiring_media import partition
        finite=partition(store)
        if finite:finite.revoke(scope['source'])
