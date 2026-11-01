"""Bounded query planning; company cohorts are not news topic classifications."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import hashlib,json,re

SETTING='media_watchlist_progress'
DEFAULT=[dict(group=g,symbols=s,industries=[]) for g,s in (
 ('Technology',['MSFT','AAPL']),('Financials',['JPM','BAC']),
 ('Energy',['XOM','CVX']),('Healthcare',['JNJ','PFE']),
 ('Industrials',['CAT','GE']),('Consumer',['AMZN','WMT']))]


def validate(value):
    if not isinstance(value,list) or not 1<=len(value)<=12:raise ValueError('Use 1–12 company watchlist groups')
    result=[];names=set();symbols=set()
    for row in value:
        if not isinstance(row,dict) or set(row)!={'group','symbols','industries'}:raise ValueError('Watchlist needs group, symbols and optional official entity industries')
        if not isinstance(row['group'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9 &/-]{0,59}',row['group']) or row['group'] in names:raise ValueError('Use distinct short watchlist group names')
        names.add(row['group'])
        if not isinstance(row['symbols'],list) or not 1<=len(row['symbols'])<=4 or any(not isinstance(s,str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',s) for s in row['symbols']):raise ValueError('Each group needs 1–4 ticker symbols')
        if len(set(row['symbols']))!=len(row['symbols']) or symbols&set(row['symbols']):raise ValueError('A watchlist ticker can occur in only one group')
        symbols.update(row['symbols'])
        if not isinstance(row['industries'],list) or len(row['industries'])>4 or any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z][A-Za-z &-]{0,59}',v) for v in row['industries']):raise ValueError('Use actual Marketaux entity-industry names, or leave empty')
        result.append({k:list(v) if isinstance(v,list) else v for k,v in row.items()})
    return result


def parse(text):
    """One editable group|ticker,ticker|optional industry,industry per line."""
    rows=[]
    for line in text.splitlines():
        if not line.strip():continue
        parts=line.split('|')
        if len(parts) not in (2,3):raise ValueError('Use group | ticker,ticker | optional official industries')
        rows.append(dict(group=parts[0].strip(),symbols=[s.strip().upper() for s in parts[1].split(',') if s.strip()],
            industries=[s.strip() for s in parts[2].split(',') if s.strip()] if len(parts)==3 else []))
    return validate(rows)


def format_rows(rows):return '\n'.join(r['group']+' | '+','.join(r['symbols'])+' | '+','.join(r['industries']) for r in validate(rows))
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)


def units(options):
    groups=validate(options['watchlist'])
    if options['source']=='marketaux':return groups
    return [dict(group=r['group'],symbols=[s],industries=[]) for r in groups for s in r['symbols']]


def read(store):
    with closing(store.connect()) as db:
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    return json.loads(row[0]) if row else {}


def plan(store,options,before):
    rows=units(options);state=read(store);source=options['source'];domains=options['scope']['domains']
    list_key=digest([source,rows,domains]);cursor=state.get(list_key,{}).get('next_index',0)%len(rows);queries=[]
    for offset in range(min(options['max_requests'],len(rows))):
        index=(cursor+offset)%len(rows);r=rows[index];key=digest([source,r['symbols'],r['industries'],domains]);old=state.get(key,{})
        after=before-timedelta(days=options['days'])
        if old.get('watermark'):after=max(after,stamp(old['watermark'])-timedelta(minutes=5))
        end=before;page=1
        if source=='marketaux' and old.get('more_possible'):
            after=stamp(old['after']);end=stamp(old['before']);page=old['next_page']
        if page>6666:raise ValueError('Bounded provider result window needs review; no pagination reset')
        queries.append(dict(**r,key=key,list_key=list_key,next_index=(index+1)%len(rows),
            after=after.isoformat(),before=end.isoformat(),page=page))
    return queries


def commit(store,options,query,*,published,received,accepted):
    """Only called after all permitted response records are transactionally saved."""
    with closing(store.connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone();state=json.loads(row[0]) if row else {}
        applied=state.setdefault('applied_steps',[])
        if query['operation_id'] in applied:return
        old=state.get(query['key'],{});watermark=max([old.get('watermark',''),*[p for p in published if p]])
        more=options['source']=='marketaux' and received>=query['requested']
        state[query['key']]=dict(source=options['source'],symbols=query['symbols'],group=query['group'],watermark=watermark,
            after=query['after'],before=query['before'],next_page=query['page']+1 if more else 1,more_possible=more,
            received=received,accepted=accepted,coverage='bounded window; completeness not established' if more or options['source']=='finnhub' else 'returned page shorter than requested cap')
        state[query['list_key']]=dict(next_index=query['next_index'])
        applied.append(query['operation_id'])
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(state)));db.commit()


def snapshot(store,options):
    now=datetime.now(timezone.utc)
    return [dict(group=q['group'],symbols=','.join(q['symbols']),industries=','.join(q['industries']),
        published_after=q['after'],published_before=q['before'],page=q['page'],max_records=options['per_request']) for q in plan(store,options,now)]
