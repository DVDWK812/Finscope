"""Metadata-only broad-feed cursor, independent of company tracking state."""
from contextlib import closing
from datetime import timedelta,datetime
import hashlib,json

SETTING='media_broad_progress_v1'

def key(options):
    identity=['broad-v1','en',options['scope']['domains'],options['per_request']]
    # An explicitly reviewed historical window has its own cursor. Never clear
    # the blocked live-window cursor or silently reinterpret its old receipts.
    if options.get('window_end'):identity+=['historical',options['window_end'],options['days']]
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()

def plan(store,options,before):
    if options.get('window_end'):
        end=datetime.fromisoformat(options['window_end'])
        if end>before:raise ValueError('Historical publication window cannot end in the future')
        before=end
    with closing(store.connect()) as db:
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    old=json.loads(row[0]).get(key(options),{}) if row else {}
    if old.get('blocked'):raise ValueError('Previous broad pagination needs review; no automatic repeat')
    if old.get('more'):
        return {k:old[k] for k in ('after','before','page','size')}
    after=before-timedelta(days=options['days'])
    if old.get('before'):after=max(after,datetime.fromisoformat(old['before'])-timedelta(minutes=5))
    return dict(after=after.isoformat(),before=before.isoformat(),page=1,size=options['per_request'])


def diagnostics(meta,previous,ids,timestamps):
    """IDs/counts/times only; no news, credentials or asserted root cause."""
    exact=[page for page,receipt in previous if ids and ids==receipt.get('article_ids')]
    earlier=[r.get('pagination',{}).get('found') for _,r in previous]
    baseline=next((v for v in earlier if type(v) is int),None)
    found=meta.get('found')
    return dict(exact_repeat_pages=exact,
        found_delta_from_first=found-baseline if type(found) is int and baseline is not None else 0,
        result_set_changed=baseline is not None and found!=baseline,
        publication_min=min(timestamps,default=''),publication_max=max(timestamps,default=''))

def continuation(meta,raw,page,size,normalized,saved,duplicate_page=False):
    if any(k not in meta for k in ('found','returned','limit','page')):return False,'Pagination metadata missing; no inferred extra request'
    if meta['page']!=page or meta['limit']!=size or meta['returned']!=raw or raw>size:
        return False,'Pagination metadata inconsistent; stopped for review'
    if saved<normalized:return False,'Record cap or persistence gap; page not fully consumed'
    if duplicate_page:return False,'Repeated page identities; stopped without retry'
    if raw==0 or raw<size or page*size>=meta['found']:return False,'Reported result window exhausted'
    if (page+1)*size>20000:return False,'Provider pagination bound reached'
    return True,'More results within fixed window'

def commit(store,options,query,receipt):
    # Unsafe/partial pages retain their position for explicit future review;
    # this task still never dispatches the same page a second time.
    partial=receipt['pagination_stop'] not in ('Reported result window exhausted','More results within fixed window','Provider pagination bound reached')
    value={**query,'page':query['page']+(not partial),'more':receipt['more'] or partial,
           'blocked':partial and receipt['pagination_stop']!='Record cap or persistence gap; page not fully consumed'}
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
        state=json.loads(row[0]) if row else {}
        applied=state.setdefault('applied_steps',[])
        operation=query.get('operation_id')
        if operation and operation in applied:return
        if operation:applied.append(operation)
        state[key(options)]=value
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(state)));db.commit()
