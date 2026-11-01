"""Dated source review findings, separate from an applicable active grant."""

REVIEWED_ON='2026-11-02 Australia/Sydney'
YAHOO_TERMS='https://legal.yahoo.com/ca/en/yahoo/terms/otos/'

def review(source,grant):
    from .media_monitor import FEEDS
    candidate=('Official RSS clause describes unmodified attributed supplied-feed display with original links; product/region and extra restrictions must apply'
               if source=='yahoo' else 'No applicable source/account display grant established in reviewed evidence')
    active=bool(grant['basis'])
    basis=('User research scope; applicability unverified, not publisher permission' if grant.get('basis_status')=='research_unverified' else 'Recorded licence evidence')
    return dict(reviewed_on=REVIEWED_ON,basis_status=grant.get('basis_status','licensed') if active else 'unrecorded',
        qualification='A user research decision is not publisher permission; specific restrictions cannot be waived by it',
        primary_reference=YAHOO_TERMS if source=='yahoo' else FEEDS[source].terms,
        title_display=(basis if active and 'display' in grant['purposes'] and 'title' in grant['fields'] else candidate),
        summary_display=(basis if active and 'display' in grant['purposes'] and 'summary' in grant['fields'] else candidate),
        short_term_disk_cache=(basis+'; finite expiry applies' if active and 'retain' in grant['purposes'] and grant['expires_at'] else 'Not established; no disk text cache grant inferred'),
        persistent_text=('Recorded source grant' if active and 'retain' in grant['purposes'] and grant['retention']=='no_fixed_expiry' and not grant['expires_at'] else 'Not established'),
        local_nlp=(basis+'; field/publisher restrictions still apply' if active and 'nlp' in grant['purposes'] else 'Not established; zero media NLP'),
        runtime_display='Approved display fields can use the worker RAM buffer; no disk archive or model input is created')
