"""UTC-day request capacity; a stopped/expired budget never silently renews."""
from datetime import timedelta,timezone
from math import ceil


def validate_schedule(interval,cap,mode):
    if type(interval) is not int or not 5<=interval<=1440:raise ValueError('Choose a 5–1440 minute interval')
    if type(cap) is not int or not 1<=cap<=1000:raise ValueError('Choose a 1–1000 HTTP request cap')
    if mode not in {'bounded_window','full_day'}:raise ValueError('Choose bounded coverage or full-day capacity')
    demand=ceil(1440/interval)
    if mode=='full_day' and cap<demand:raise ValueError(f'Full-day coverage at {interval} minutes requires at least {demand} GETs/source/day')
    return demand


def capacity(state,used,now):
    interval=state['interval'];cap=state['daily_cap'];remaining=max(0,cap-used)
    demand=ceil(1440/interval)
    day=now.astimezone(timezone.utc).date().isoformat()
    attested=state.get('budget_day')==day and bool(state.get('budget_reference','').strip())
    midnight=now.astimezone(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    rounds_today=min(remaining,ceil((midnight-now).total_seconds()/(interval*60))) if attested else 0
    status=('Budget unconfirmed/expired; stopped' if not attested else
            'Budget exhausted; stopped until explicitly renewed' if remaining==0 else
            'Stopped' if not state['enabled'] else 'Polling within confirmed budget')
    return dict(utc_day=day,used_gets=used,remaining_gets=remaining,
        full_day_gets=demand,minimum_full_day_interval=max(5,ceil(1440/cap)),
        request_slots_minutes=remaining*interval,
        first_to_last_minutes=max(0,remaining-1)*interval,
        rounds_available_today=rounds_today,estimated_span_minutes=max(0,rounds_today-1)*interval,
        budget_expires_at=midnight.isoformat(),budget_attested=attested,status=status,coverage_mode=state.get('coverage_mode','bounded_window'))
