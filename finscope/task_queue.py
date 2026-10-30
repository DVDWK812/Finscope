"""Single-machine durable jobs. No UI, model, credential or HTTP imports."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import sqlite3
from uuid import uuid4

ACTIVE = ('queued', 'running')
TERMINAL = ('completed', 'partial_failed', 'blocked', 'cancelled', 'interrupted')


def now():
    return datetime.now(timezone.utc).isoformat()


class ProcessLock:
    """OS releases the lock after a crash; never delete another process's lock."""
    def __init__(self, path):
        self.path = Path(path)
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('a+b')
        if self.file.tell() == 0:
            self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Another local worker or schema migration is active') from None
        return self
    def __exit__(self, *_):
        self.file.close()


def migrate(store):
    with closing(store.connect()) as existing:
        if existing.execute('PRAGMA user_version').fetchone()[0]==1:return
    with ProcessLock(str(store.path)+'.schema.lock'), closing(store.connect()) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise ValueError('A newer local database schema requires a newer application')
        if version == 1:
            return
        # SQLite backup includes consistent committed content, including WAL.
        backup = store.path.parent/'backups'/(store.path.name+'.before-product-v1.'+uuid4().hex+'.sqlite3')
        backup.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(backup)) as target:
            db.backup(target)
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''BEGIN IMMEDIATE;
            CREATE TABLE product_tasks(id TEXT PRIMARY KEY, status TEXT NOT NULL, snapshot TEXT NOT NULL,
                stage TEXT NOT NULL, counts TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
                cancel INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL);
            CREATE UNIQUE INDEX product_one_active ON product_tasks((1)) WHERE status IN ('queued','running');
            CREATE TABLE product_steps(task_id TEXT NOT NULL, step TEXT NOT NULL, status TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(task_id,step));
            CREATE TABLE product_content(article_id TEXT NOT NULL, version TEXT NOT NULL, payload TEXT NOT NULL,
                created TEXT NOT NULL, PRIMARY KEY(article_id,version));
            CREATE TABLE product_classifications(article_id TEXT NOT NULL, content_version TEXT NOT NULL,
                cache_key TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL,
                PRIMARY KEY(article_id,content_version,cache_key));
            CREATE TABLE product_analysis_cache(article_id TEXT NOT NULL, content_version TEXT NOT NULL,
                cache_key TEXT NOT NULL, analysis_id TEXT NOT NULL, PRIMARY KEY(article_id,content_version,cache_key));
            CREATE TABLE product_settings(name TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE product_worker(id INTEGER PRIMARY KEY CHECK(id=1), heartbeat TEXT NOT NULL, pid INTEGER NOT NULL);
            PRAGMA user_version=1; COMMIT;''')


def validate_config(config):
    """Explicit schema ensures neither credentials nor arbitrary endpoints enter jobs."""
    from .local_collectors import SOURCES
    allowed={'sources','model','model_id','taxonomy','classifier_llm','limit','source_permissions','budgets','article_ids','force_reanalysis','result_model_key'}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ValueError('Unsupported task configuration; credentials are separate')
    c=dict(config)
    if (not isinstance(c.get('sources'),list) or not (c['sources'] or c.get('article_ids')) or len(c['sources'])>8
            or any(s not in {*SOURCES,'marketaux','newsdata','finnhub'} for s in c['sources'])):
        raise ValueError('Select registered sources')
    if c.get('article_ids') and (not isinstance(c['article_ids'],list) or not 1<=len(c['article_ids'])<=20 or any(not isinstance(v,str) or len(v)!=32 or any(x not in '0123456789abcdef' for x in v) for v in c['article_ids'])):raise ValueError('Invalid original selection')
    if type(c.get('force_reanalysis',False)) is not bool:raise ValueError('Invalid reanalysis flag')
    if not isinstance(c.get('result_model_key',''),str) or len(c.get('result_model_key',''))>600:raise ValueError('Invalid selected model version')
    if c.get('model') not in {'Local FinBERT','Local LM Studio','Local Ollama'}:
        raise ValueError('Automatic tasks require an explicitly selected local model; paid external calls remain manual')
    if c.get('taxonomy') not in {'US-BUSINESS-1','CSRC-JRT0020-2024'}:
        raise ValueError('Choose a versioned taxonomy')
    if type(c.get('limit')) is not int or not 1<=c['limit']<=20:
        raise ValueError('Choose 1–20 records per source')
    if not isinstance(c.get('model_id',''),str) or len(c.get('model_id',''))>200:
        raise ValueError('Invalid local model ID')
    if c.get('classifier_llm',False) not in (True,False):
        raise ValueError('Invalid classifier setting')
    if c.get('classifier_llm') and c['model']!='Local LM Studio':
        raise ValueError('Classification enhancement must reuse the selected LM Studio model')
    for source,p in c.get('source_permissions',{}).items():
        if source not in c['sources'] or not isinstance(p,dict) or set(p)!={'preview','retain','analyze','external','reference'}:
            raise ValueError('Invalid source permission')
        if any(type(p[x]) is not bool for x in ('preview','retain','analyze','external')) or not isinstance(p['reference'],str) or len(p['reference'])>500:
            raise ValueError('Invalid source permission')
    for source,b in c.get('budgets',{}).items():
        if (source not in {'marketaux','newsdata','finnhub'} or not isinstance(b,dict) or set(b)!={'utc_day','remaining','topic','symbol'}
                or type(b['remaining']) is not int or not 0<=b['remaining']<=10000
                or b['topic'] not in {'technology','healthcare','materials'} or not isinstance(b['symbol'],str)
                or len(b['symbol'])>15):
            raise ValueError('Invalid daily source budget')
        datetime.strptime(b['utc_day'],'%Y-%m-%d')
    # Also reject an accidentally pasted known local key in any free text field.
    from .api_sources import local_credentials
    serialized=json.dumps(c,sort_keys=True)
    from .local_credentials import vault_key,PROVIDERS
    secrets=[*local_credentials().values(),*(vault_key(p) for p in PROVIDERS)]
    if any(value and len(value)>5 and value in serialized for value in secrets):
        raise ValueError('Credential text cannot be stored in task configuration')
    return c


class TaskQueue:
    def __init__(self,store):
        self.store=store
        migrate(store)
    def config(self):
        with closing(self.store.connect()) as db:
            row=db.execute("SELECT payload FROM product_settings WHERE name='pipeline'").fetchone()
        return json.loads(row[0]) if row else None
    def configure(self,config):
        c=validate_config(config)
        with closing(self.store.connect()) as db:
            db.execute("INSERT OR REPLACE INTO product_settings VALUES ('pipeline',?)",(json.dumps(c),));db.commit()
    def submit(self,config=None):
        c=validate_config(config or self.config())
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id FROM product_tasks WHERE status IN ('queued','running')").fetchone()
            if row:return row[0],False
            identity=uuid4().hex;stamp=now()
            db.execute('INSERT INTO product_tasks(id,status,snapshot,stage,counts,created,updated) VALUES (?,?,?,?,?,?,?)',
                       (identity,'queued',json.dumps(c),'queued',json.dumps(dict(new=0,duplicates=0,classified=0,analyzed=0,failed=0,skipped=0)),stamp,stamp))
            db.commit();return identity,True
    def get(self,identity=None):
        with closing(self.store.connect()) as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM product_tasks '+('WHERE id=?' if identity else 'ORDER BY rowid DESC LIMIT 1'),(identity,) if identity else ()).fetchone()
        if not row:return None
        result=dict(row)
        for key in ('snapshot','counts'):result[key]=json.loads(result[key])
        return result
    def update(self,identity,*,status=None,stage=None,counts=None,error=None):
        values={'status':status,'stage':stage,'counts':json.dumps(counts) if counts is not None else None,'error':error}
        values={k:v for k,v in values.items() if v is not None}
        if 'status' in values and values['status'] not in (*ACTIVE,*TERMINAL):raise ValueError('Invalid task state')
        values['updated']=now()
        with closing(self.store.connect()) as db:
            db.execute('UPDATE product_tasks SET '+','.join(k+'=?' for k in values)+' WHERE id=?',(*values.values(),identity));db.commit()
    def cancel(self,identity):
        with closing(self.store.connect()) as db:
            db.execute("UPDATE product_tasks SET cancel=1 WHERE id=? AND status IN ('queued','running')",(identity,));db.commit()
    def check_cancel(self,identity):
        if self.get(identity)['cancel']:raise Cancelled()
    def step(self,identity,key):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT status,payload FROM product_steps WHERE task_id=? AND step=?',(identity,key)).fetchone()
        return (row[0],json.loads(row[1])) if row else None
    def save_step(self,identity,key,status,payload):
        with closing(self.store.connect()) as db:
            db.execute('INSERT OR REPLACE INTO product_steps VALUES (?,?,?,?)',(identity,key,status,json.dumps(payload)));db.commit()
    def heartbeat(self):
        with closing(self.store.connect()) as db:
            db.execute('INSERT OR REPLACE INTO product_worker VALUES (1,?,?)',(now(),os.getpid()));db.commit()
    def worker_alive(self):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT heartbeat FROM product_worker WHERE id=1').fetchone()
        return bool(row and (datetime.now(timezone.utc)-datetime.fromisoformat(row[0])).total_seconds()<15)
    def interrupt_orphans(self):
        # Called only while holding the exclusive worker lock after process startup.
        with closing(self.store.connect()) as db:
            db.execute("UPDATE product_tasks SET status='interrupted',stage='interrupted',error='Worker stopped; completed stages preserved; explicit resume required',updated=? WHERE status='running'",(now(),));db.commit()
    def resume(self,identity):
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM product_tasks WHERE status IN ('queued','running')").fetchone():raise ValueError('Another task is active')
            db.execute("UPDATE product_tasks SET status='queued',cancel=0,error='',updated=? WHERE id=? AND status IN ('interrupted','blocked','cancelled','partial_failed')",(now(),identity));db.commit()


class Cancelled(Exception):pass
