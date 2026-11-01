"""Versioned automatic-use policies; unknown sources receive no policy grant.

Public source terms and article-level permissions are separate requirements.
Reviewed official text policies and explicit local-import evidence do not
grant rights to unreviewed news APIs or externally linked publisher content.
"""
from dataclasses import asdict,dataclass
import hashlib,json,re
from urllib.parse import urlsplit


class PolicyBlocked(ValueError):pass


@dataclass(frozen=True)
class SourcePolicy:
    policy_id: str
    version: str
    provider: str
    basis: str
    license_url: str
    reviewed_on: str
    allowed_fields: tuple[str,...]
    purposes: tuple[str,...]
    retention: str
    attribution: str
    adaptation_notice: str
    exclusions: str
    expires_at: str = ''


ABS=SourcePolicy('abs-official-cc-by-4','2026-11-01','abs_html',
    'https://www.abs.gov.au/website-privacy-copyright-and-disclaimer',
    'https://creativecommons.org/licenses/by/4.0/','2026-11-01 Australia/Sydney',
    ('title','summary','body','source','url','timestamp','publication_date'),
    ('preview','retain','local_classification','local_sentiment','local_display'),
    'Copyright term while CC BY 4.0 conditions are satisfied; no fixed deletion date in this licence',
    'Source: Australian Bureau of Statistics, © Commonwealth of Australia',
    'Based on ABS material; FinScope preprocessing/classification/sentiment are adaptations; no ABS endorsement',
    'Third-party or separately restricted content, microdata, logos, trademarks and artwork are excluded')

@dataclass(frozen=True)
class SECSourcePolicy(SourcePolicy):
    """SEC-hosted public text only; does not license material on external sites."""


FIELDS=('title','summary','body','source','url','timestamp','publication_date','source_type',
        'record_id','document_type','company','ticker','cik','disclosed_at','disclosure_precision','filed_date','issuer_industry')
PURPOSES=('preview','retain','local_classification','local_sentiment','local_display')
SEC=SECSourcePolicy('sec-public-information-text','2026-11-01','sec',
    'https://www.sec.gov/about/privacy-information#dissemination',
    'https://www.sec.gov/about/privacy-information','2026-11-01 Australia/Sydney',FIELDS,PURPOSES,
    'No fixed retention deadline for covered public information; preserve revisions and attribution',
    'Source: U.S. Securities and Exchange Commission; issuer and accession retained for filings',
    'FinScope extracts/classifies text independently; no SEC or issuer endorsement; excerpt sentiment only',
    'External links, exhibits/attachments, copyrighted or separately restricted material, images, seals, logos and trademarks excluded')
NIST=SourcePolicy('nist-unmarked-official-news','2026-11-01','nist_rss',
    'https://www.nist.gov/copyrights-disclaimers','https://www.nist.gov/copyrights-disclaimers',
    '2026-11-01 Australia/Sydney',FIELDS,PURPOSES,'No fixed retention deadline for covered public information',
    'Source: NIST, U.S. Department of Commerce; retain original byline',
    'Based on NIST information; independent FinScope analysis; no NIST endorsement',
    'Copyright-marked, separately restricted and third-party material, artwork, media, datasets and software excluded')
RBA=SourcePolicy('rba-official-release-feed','2026-11-01','rba_rss',
    'https://www.rba.gov.au/copyright/','https://creativecommons.org/licenses/by/4.0/','2026-11-01 Australia/Sydney',
    tuple(f for f in FIELDS if f!='body'),PURPOSES,'Copyright term subject to CC BY 4.0 conditions',
    'Source: Reserve Bank of Australia; original publication year retained',
    'Independent FinScope preprocessing and analysis; no RBA endorsement',
    'Third-party content, logos, banknote images, cash-rate/data series, econometric models, multimedia and separately restricted material excluded')
POLICIES={'abs_html':ABS,'abs_archive':ABS,'nist_rss':NIST,'rba_rss':RBA,'rba_html':RBA,'sec_submissions':SEC,'sec_press':SEC}


def authorize(item,purposes):
    """Return auditable evidence, never broaden an article's existing rights."""
    from .media_use import scope_of,authorize as media_authorize
    if scope_of(item):return media_authorize(item,purposes)
    policy=POLICIES.get(item.provider)
    if item.provider in {'local_import','media_rss'}:
        try:
            supplied=json.loads(item.provenance)['import_policy' if item.provider=='local_import' else 'media_policy']
            policy=SourcePolicy(**supplied)
            if policy.provider!=item.provider or not policy.basis or not policy.retention or not policy.attribution:
                raise ValueError()
        except (TypeError,KeyError,ValueError):raise PolicyBlocked('Import requires explicit field/use/retention/attribution evidence') from None
    if policy is None:raise PolicyBlocked('No reviewed automatic-use policy for this source')
    if policy.expires_at:
        from datetime import datetime,timezone
        try:deadline=datetime.fromisoformat(policy.expires_at.replace('Z','+00:00'))
        except (TypeError,ValueError):raise PolicyBlocked('Invalid policy expiry') from None
        if deadline.tzinfo is None or datetime.now(timezone.utc)>=deadline:raise PolicyBlocked('Source permission expired or has an ambiguous deadline')
    if not purposes or any(p not in policy.purposes for p in purposes):
        raise PolicyBlocked('The source policy does not cover this operation')
    item.rights.require('preview')
    if any(p!='preview' for p in purposes):item.rights.require('retain')
    if any(p in {'local_classification','local_sentiment'} for p in purposes):item.rights.require('analyze')
    try:origin=json.loads(item.provenance)
    except (TypeError,ValueError):raise PolicyBlocked('Source provenance needs review') from None
    if not isinstance(origin,dict):raise PolicyBlocked('Source provenance needs review')
    url=urlsplit(item.url)
    if item.provider=='media_rss':
        from .media_monitor import FEEDS,publisher_covered
        feed=FEEDS.get(origin.get('source_id'))
        if (feed is None or origin.get('feed_url')!=feed.url or item.source!=feed.name or item.body
                or item.source_type!='media_news' or policy.retention!='no_fixed_expiry'
                or set(policy.allowed_fields)-set(FIELDS) or 'body' in policy.allowed_fields
                or not publisher_covered(origin['source_id'],item.url,{'publisher_domains':origin.get('licensed_publisher_domains',[])})):
            raise PolicyBlocked('Outside the reviewed RSS field/use scope')
    if item.provider=='abs_html' and (item.source!='Australian Bureau of Statistics' or url.scheme!='https' or
            url.hostname!='www.abs.gov.au' or url.username or url.password or
            not url.path.startswith('/media-centre/media-releases/') or
            origin.get('source_id')!='abs_html' or origin.get('license')!='CC BY 4.0' or
            origin.get('source_license_applied') is not True):
        raise PolicyBlocked('The record is outside the reviewed ABS policy')
    if item.provider=='abs_html' and item.body and (origin.get('body_status')!='extracted' or
                      origin.get('body_byline')!='Australian Bureau of Statistics'):
        raise PolicyBlocked('The body has no reviewed official-text provenance')
    if item.provider=='nist_rss':
        if (url.scheme!='https' or url.hostname!='www.nist.gov' or not url.path.startswith('/news-events/news/')
                or item.source!='National Institute of Standards and Technology'
                or origin.get('source_id')!='nist_rss' or origin.get('source_license_applied') is not True):
            raise PolicyBlocked('Outside reviewed NIST news scope')
    if item.provider in {'rba_rss','rba_html'}:
        if (url.scheme!='https' or url.hostname!='www.rba.gov.au' or not url.path.startswith('/media-releases/')
                or item.source!='Reserve Bank of Australia' or item.body
                or origin.get('feed_source_element','') not in ('','Reserve Bank of Australia')):
            raise PolicyBlocked('Outside reviewed RBA release-index/feed scope')
    if item.provider in {'sec_submissions','sec_press'}:
        from .sec_sources import permitted_url
        if not permitted_url(item.url) or origin.get('source_id')!=item.provider or origin.get('source_license_applied') is not True:
            raise PolicyBlocked('Outside reviewed SEC public-information scope')
        if item.provider=='sec_submissions':
            if not re.fullmatch(r'\d{10}:\d{10}-\d{2}-\d{6}',item.record_id) or not item.cik or item.source_type!='regulatory_disclosure':
                raise PolicyBlocked('Missing stable SEC filing provenance')
            accession=item.record_id.split(':')[1]
            if item.source!='SEC EDGAR' or item.record_id.split(':')[0]!=item.cik or not url.path.startswith(f'/Archives/edgar/data/{int(item.cik)}/{accession.replace("-","")}/'):
                raise PolicyBlocked('SEC issuer/accession/original URL mismatch')
            if item.body and (item.document_type not in {'8-K','8-K/A','6-K','6-K/A'} or origin.get('body_status')!='event_excerpt'):
                raise PolicyBlocked('Only reviewed current-report event excerpts may be processed')
        elif (item.source_type!='government' or item.source!='U.S. Securities and Exchange Commission'
              or not url.path.startswith(('/newsroom/press-releases/','/news/press-release/'))):raise PolicyBlocked('SEC releases are official government announcements')
    if item.provider in {'nist_rss','rba_rss','rba_html','sec_submissions','sec_press'} and re.search(
            r'©|copyright|all rights reserved|reprinted (?:with|by)|third.party content|courtesy of',
            item.title+' '+item.summary+' '+item.body,re.I):
        raise PolicyBlocked('Special-rights marker requires review')
    if url.username or url.password:raise PolicyBlocked('Original URL cannot contain credentials')
    fields=[f for f in FIELDS if getattr(item,f,'')]
    if set(fields)-set(policy.allowed_fields):
        raise PolicyBlocked('The source policy does not cover every supplied field')
    record=asdict(policy)
    return {'policy':record,'policy_sha256':hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest(),
            'fields':fields,'purposes':list(purposes),'article_permissions_reference':item.rights.reference}
