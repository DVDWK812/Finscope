"""Read-only connection gates. Never probe providers, reserve requests or expose keys."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from zoneinfo import ZoneInfo

from .api_sources import ENV_KEYS, local_credentials, project_env_path
from .local_news import LocalIngestionService, utcnow
from .rate_limits import load_cooldowns


def credential_report(provider, *, ui_key_present=False, use_env=True):
    variable = 'OPENAI_API_KEY' if provider == 'openai' else ENV_KEYS[provider]
    present = ui_key_present or bool(use_env and local_credentials().get(variable))
    return {'present': bool(present), 'variable': variable,
            'source': 'Masked UI field (session only)' if ui_key_present else
            str(project_env_path()) if present else 'Not configured in selected credential sources'}


def api_diagnostic(store, provider, *, ui_key_present=False, use_env=True, service=None):
    if provider not in {'marketaux', 'newsdata', 'finnhub', 'openai'}:
        raise ValueError('Unsupported diagnostic provider')
    service = service or LocalIngestionService(store)
    now = service.clock().astimezone(timezone.utc)
    credentials = credential_report(provider, ui_key_present=ui_key_present, use_env=use_env)
    holds = []

    def hold(kind, record, status, trigger, until=None):
        deadline = datetime.fromisoformat(until).astimezone(timezone.utc) if until else None
        holds.append({'kind': kind, 'record': record, 'status': status, 'trigger_utc': trigger,
                      'active': deadline > now if deadline else True,
                      'until_utc': deadline.isoformat() if deadline else 'Manual review; no automatic expiry',
                      'until_sydney': deadline.astimezone(ZoneInfo('Australia/Sydney')).isoformat() if deadline else 'Manual review; no automatic expiry'})

    with closing(store.connect()) as db:
        if provider == 'openai':
            rows = db.execute("SELECT id,reserved_at,completed_at,status,hold_until FROM local_model_requests WHERE backend='openai' ORDER BY reserved_at").fetchall()
        else:
            rows = db.execute('SELECT id,reserved_at,completed_at,status,hold_until FROM local_requests WHERE provider=? ORDER BY reserved_at', (provider,)).fetchall()
    for identity, reserved, completed, status, until in rows:
        end = datetime.fromisoformat(completed or reserved).astimezone(timezone.utc)
        if status == 'pending':
            hold('Unresolved local request', identity, status, reserved)
        if until:
            hold('Retry-After', identity, status, completed or reserved, until)
        if provider != 'openai':
            hold('60-second spacing', identity, status, completed or reserved, (end+timedelta(seconds=60)).isoformat())
            if status == 'failed':
                deadline = datetime.combine(end.date()+timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                hold('Failure stop for completion UTC day', identity, status, completed or reserved, deadline.isoformat())
    if provider == 'newsdata':
        hold('Code-level manual pause', 'LocalIngestionService.fetch/source_status', 'paused', '')
    if provider != 'openai':
        for name, until in load_cooldowns(service.cooldown_path).items():
            if name == provider:
                hold('Shared provider cooldown', str(service.cooldown_path), 'stored', '', until.isoformat())
        today = [r for r in rows if datetime.fromisoformat(r[1]).astimezone(timezone.utc).date() == now.date()]
        if len(today) >= 3:
            deadline = datetime.combine(now.date()+timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
            hold('Three-request UTC-day cap', 'local_requests', 'cap', '', deadline.isoformat())
    if provider == 'marketaux' and service.study_path.exists():
        with closing(sqlite3.connect(service.study_path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            study_rows = db.execute('SELECT reserved_at,completed_at,status,cooldown_until FROM attempts').fetchall()
        for reserved, completed, status, until in study_rows:
            end = datetime.fromisoformat(completed or reserved).astimezone(timezone.utc)
            if status == 'attempted_outcome_unknown':
                hold('Unresolved study request', reserved, status, reserved)
            if until:
                hold('Study cooldown', reserved, status, completed or reserved, until)
            hold('Study spacing', reserved, status, completed or reserved, (end+timedelta(seconds=60)).isoformat())
            if status in {'failed', 'review_failed'}:
                deadline = datetime.combine(end.date()+timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                hold('Study UTC-day stop', reserved, status, completed or reserved, deadline.isoformat())

    # Historical HTTP evidence is separate from current product connection status.
    historical = []
    if provider != 'openai':
        for name in ('keyed_healthcare_initial.json', 'keyed_followup_topics.json'):
            path = store.path.parent / name
            if path.is_file():
                try:
                    report = json.loads(path.read_text(encoding='utf-8'))
                    for result in report.get('results', []):
                        if result.get('provider') == provider and result.get('http_status'):
                            historical.append({'file': name, 'report_utc': report.get('generated_at_utc'),
                                               'status': result.get('status'), 'http_status': result['http_status']})
                except (OSError, ValueError, TypeError):
                    pass
    if provider == 'openai':
        state = ('Paused' if any(h['active'] for h in holds) else 'Not configured' if not credentials['present'] else
                 'Available' if rows and rows[-1][3]=='ok' else 'Failed' if rows and rows[-1][3]=='failed' else 'Untested')
    else:
        state = service.source_status(provider, configured=credentials['present']).state
    missing = []
    if not credentials['present']:
        missing.append('Configure '+credentials['variable']+' in the project .env or masked UI field')
    if provider == 'newsdata':
        missing.append('Explicit authorization and a reviewed code change are required to resume the manual pause')
        missing.extend(['Fresh confirmed available account request budget', 'Local preview permission attestation for this Fetch action'])
    elif provider == 'openai':
        missing.extend(['Recorded permission to transmit the selected text to OpenAI', 'Explicit send consent and paid account budget for this Run action'])
    else:
        missing.extend(['Fresh confirmed available account request budget', 'Local preview permission attestation for this Fetch action'])
    return {'provider': provider, 'checked_utc': now.isoformat(), 'credentials': credentials, 'state': state,
            'product_attempt_count': len(rows), 'last_product_attempt': {'id': rows[-1][0], 'reserved_utc': rows[-1][1],
                'completed_utc': rows[-1][2], 'status': rows[-1][3]} if rows else None,
            'historical_http_evidence': historical, 'holds': holds, 'required_before_request': missing,
            'downstream_nlp': 'Separate permission required; this is not an API connection failure' if provider != 'openai' else 'External transmission permission is separate from credentials'}
