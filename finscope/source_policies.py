"""Versioned automatic-use policies; unknown sources receive no policy grant.

Public source terms and article-level permissions are separate requirements.
The first automatic policy covers ABS staff-authored release text only.
"""
from dataclasses import asdict,dataclass
import hashlib,json
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


ABS=SourcePolicy('abs-official-cc-by-4','2026-11-01','abs_html',
    'https://www.abs.gov.au/website-privacy-copyright-and-disclaimer',
    'https://creativecommons.org/licenses/by/4.0/','2026-11-01 Australia/Sydney',
    ('title','summary','body','source','url','timestamp','publication_date'),
    ('preview','retain','local_classification','local_sentiment','local_display'),
    'Copyright term while CC BY 4.0 conditions are satisfied; no fixed deletion date in this licence',
    'Source: Australian Bureau of Statistics, © Commonwealth of Australia',
    'Based on ABS material; FinScope preprocessing/classification/sentiment are adaptations; no ABS endorsement',
    'Third-party or separately restricted content, microdata, logos, trademarks and artwork are excluded')

POLICIES={'abs_html':ABS}


def authorize(item,purposes):
    """Return auditable evidence, never broaden an article's existing rights."""
    policy=POLICIES.get(item.provider)
    if policy is None:raise PolicyBlocked('No reviewed automatic-use policy for this source')
    if not purposes or any(p not in policy.purposes for p in purposes):
        raise PolicyBlocked('The source policy does not cover this operation')
    item.rights.require('preview')
    if any(p!='preview' for p in purposes):item.rights.require('retain')
    if any(p in {'local_classification','local_sentiment'} for p in purposes):item.rights.require('analyze')
    try:origin=json.loads(item.provenance)
    except (TypeError,ValueError):raise PolicyBlocked('Source provenance needs review') from None
    if not isinstance(origin,dict):raise PolicyBlocked('Source provenance needs review')
    url=urlsplit(item.url)
    if (item.source!='Australian Bureau of Statistics' or url.scheme!='https' or
            url.hostname!='www.abs.gov.au' or url.username or url.password or
            not url.path.startswith('/media-centre/media-releases/') or
            origin.get('source_id')!='abs_html' or origin.get('license')!='CC BY 4.0' or
            origin.get('source_license_applied') is not True):
        raise PolicyBlocked('The record is outside the reviewed ABS policy')
    if item.body and (origin.get('body_status')!='extracted' or
                      origin.get('body_byline')!='Australian Bureau of Statistics'):
        raise PolicyBlocked('The body has no reviewed official-text provenance')
    fields=[f for f in ('title','summary','body','source','url','timestamp','publication_date') if getattr(item,f,'')]
    if set(fields)-set(policy.allowed_fields):
        raise PolicyBlocked('The source policy does not cover every supplied field')
    record=asdict(policy)
    return {'policy':record,'policy_sha256':hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest(),
            'fields':fields,'purposes':list(purposes),'article_permissions_reference':item.rights.reference}
