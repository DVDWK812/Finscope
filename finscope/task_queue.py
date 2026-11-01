"""Single-machine durable jobs. No UI, model, credential or HTTP imports."""
from contextlib import closing
from dataclasses import asdict,replace
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
        if existing.execute('PRAGMA user_version').fetchone()[0]==1:
            if all(existing.execute('SELECT 1 FROM sqlite_master WHERE name=?',(name,)).fetchone() for name in ('product_record_state','product_current_content')):return
            with ProcessLock(str(store.path)+'.schema.lock'):
                backup=store.path.parent/'backups'/(store.path.name+'.before-batch.'+uuid4().hex+'.sqlite3')
                backup.parent.mkdir(parents=True,exist_ok=True)
                with closing(sqlite3.connect(backup)) as target:existing.backup(target)
                existing.execute('CREATE TABLE IF NOT EXISTS product_record_state(article_id TEXT NOT NULL,content_version TEXT NOT NULL,download TEXT NOT NULL,analysis TEXT NOT NULL,reason TEXT NOT NULL,updated TEXT NOT NULL,PRIMARY KEY(article_id,content_version))')
                existing.execute('CREATE TABLE IF NOT EXISTS product_current_content(article_id TEXT PRIMARY KEY,version TEXT NOT NULL,updated TEXT NOT NULL)')
                existing.commit()
            return
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
            CREATE TABLE product_record_state(article_id TEXT NOT NULL,content_version TEXT NOT NULL,
                download TEXT NOT NULL,analysis TEXT NOT NULL,reason TEXT NOT NULL,updated TEXT NOT NULL,
                PRIMARY KEY(article_id,content_version));
            CREATE TABLE product_current_content(article_id TEXT PRIMARY KEY,version TEXT NOT NULL,updated TEXT NOT NULL);
            PRAGMA user_version=1; COMMIT;''')


def validate_config(config):
    """Explicit schema ensures neither credentials nor arbitrary endpoints enter jobs."""
    from .local_collectors import SOURCES
    allowed={'sources','model','model_id','taxonomy','classifier_llm','limit','source_permissions','budgets','article_ids','force_reanalysis','result_model_key','news_key_slots','operation','sec_options','media_batch','classifier_options'}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ValueError('Unsupported task configuration; credentials are separate')
    c=dict(config)
    if 'classifier_options' in c:
        from .classification_scheme import validate
        c['classifier_options']=validate(c['classifier_options'])
        if c.get('taxonomy')!='US-BUSINESS-1' or c.get('classifier_llm') or c.get('force_reanalysis'):
            raise ValueError('Independent semantic classifier supports US-BUSINESS-1 and cached classification only')
    if 'media_batch' in c:
        from .media_batch import validate
        c['media_batch']=validate(c['media_batch'])
        if c.get('model')!='Local FinBERT' or c.get('classifier_llm') or c.get('force_reanalysis'):
            raise ValueError('Finite media batches use fixed local FinBERT and cached results only')
    batch=c.get('operation') in {'collect','analyze','update','reclassify'}
    if 'operation' in c and not batch:raise ValueError('Invalid batch operation')
    if c.get('operation')=='reclassify' and (not c.get('classifier_options') or c.get('sources') or not c.get('article_ids')
            or c.get('budgets') or c.get('source_permissions') or c.get('media_batch')):
        raise ValueError('Classification-only tasks require saved IDs and an independent scheme, without source requests')
    if 'sec_options' in c:
        from .sec_sources import validate_options
        c['sec_options']=validate_options(c['sec_options'])
    if 'news_key_slots' in c:
        from .news_keys import validate_ref
        from .credential_store import NEWS_PROVIDERS
        if not isinstance(c['news_key_slots'],dict) or set(c['news_key_slots'])-set(NEWS_PROVIDERS):raise ValueError('Invalid news key selection')
        for ref in c['news_key_slots'].values():
            if ref is None:continue
            if not isinstance(ref,dict) or set(ref)!={'slot_id','credential_ref'}:raise ValueError('Invalid news key selection')
            validate_ref(ref['slot_id']);validate_ref(ref['credential_ref'])
            if (ref['slot_id']=='legacy')!=(ref['credential_ref']=='legacy'):raise ValueError('Invalid news key selection')
    if (not isinstance(c.get('sources'),list) or not (c['sources'] or c.get('article_ids')) or len(c['sources'])>10
            or any(s not in {*SOURCES,'marketaux','newsdata','finnhub','sec_submissions','sec_press'} for s in c['sources'])):
        raise ValueError('Select registered sources')
    if c.get('article_ids') and (not isinstance(c['article_ids'],list) or not 1<=len(c['article_ids'])<=(300 if batch else 20) or any(not isinstance(v,str) or len(v)!=32 or any(x not in '0123456789abcdef' for x in v) for v in c['article_ids'])):raise ValueError('Invalid original selection')
    if type(c.get('force_reanalysis',False)) is not bool:raise ValueError('Invalid reanalysis flag')
    if not isinstance(c.get('result_model_key',''),str) or len(c.get('result_model_key',''))>600:raise ValueError('Invalid selected model version')
    if c.get('model') not in {'Local FinBERT','Local LM Studio','Local Ollama'}:
        raise ValueError('Automatic tasks require an explicitly selected local model; paid external calls remain manual')
    if c.get('taxonomy') not in {'US-BUSINESS-1','CSRC-JRT0020-2024'}:
        raise ValueError('Choose a versioned taxonomy')
    if type(c.get('limit')) is not int or not 1<=c['limit']<=(300 if batch else 20):
        raise ValueError('Choose a bounded record limit (batch maximum 300)')
    if not isinstance(c.get('model_id',''),str) or len(c.get('model_id',''))>200:
        raise ValueError('Invalid local model ID')
    if c.get('classifier_llm',False) not in (True,False):
        raise ValueError('Invalid classifier setting')
    if c.get('classifier_llm') and c['model']!='Local LM Studio':
        raise ValueError('Classification enhancement must reuse the selected LM Studio model')
    for source,p in c.get('source_permissions',{}).items():
        if (source not in c['sources'] and source not in {'marketaux','newsdata','finnhub'}) or not isinstance(p,dict) or set(p)!={'preview','retain','analyze','external','reference'}:
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
        from .news_keys import NewsKeyRegistry
        if (set(c['sources'])|set(c.get('source_permissions',{})))&{'marketaux','newsdata','finnhub'}:
            NewsKeyRegistry(self.store).reject_secret_text(json.dumps(c))
        c.pop('news_key_slots',None)
        with closing(self.store.connect()) as db:
            db.execute("INSERT OR REPLACE INTO product_settings VALUES ('pipeline',?)",(json.dumps(c),))
            db.execute("DELETE FROM product_settings WHERE name='pipeline_draft'");db.commit()
    def submit(self,config=None):
        from .settings_state import guard_submit
        guard_submit(self)
        c=validate_config(config or self.config())
        return self._enqueue(c)
    def submit_ready(self,*,confirmed=False,expected_sources=None,expected_config=None):
        if confirmed is not True:raise ValueError('Confirm the ready-source scope before starting')
        from .settings_state import editable
        from .news_readiness import source_plan
        c=editable(self)
        if expected_config is not None and c!=expected_config:
            raise ValueError('Saved settings changed; review the current source scope before starting')
        if (c['model'] not in ('Local FinBERT','Local LM Studio','Local Ollama') or
                c['model']!='Local FinBERT' and not c.get('model_id')):
            raise ValueError('Complete the saved local model selection before starting')
        ready,blocked=source_plan(self.store,c)
        if expected_sources is not None and ready!=expected_sources:
            raise ValueError('Source readiness changed; review the current scope before starting')
        if not ready:raise ValueError('No selected source is ready; review News sources')
        c['sources']=ready
        c['source_permissions']={p:v for p,v in c.get('source_permissions',{}).items() if p in ready}
        c['budgets']={p:v for p,v in c.get('budgets',{}).items() if p in ready}
        return self._enqueue(validate_config(c))
    def submit_batch(self,operation,config,*,confirmed=False,article_ids=None):
        """Independent advanced actions; never inherit a draft API source list."""
        if confirmed is not True:raise ValueError('Confirm the bounded batch scope')
        c={**config,'operation':operation,'force_reanalysis':False}
        if c.get('media_batch') and c['taxonomy']=='US-BUSINESS-1' and not c.get('classifier_options'):
            from .classification_scheme import selected
            options=selected(self.store)
            if options:c['classifier_options']=options
        if operation=='analyze':
            from .product_storage import ProductStorage
            data=ProductStorage(self.store)
            ids=article_ids
            if ids is None:
                items=[n for n in data.news() if n.provider!='authored_synthetic']
                if c['model']=='Local FinBERT':
                    from .batch_config import finbert_cache_key
                    from .batch_records import eligibility
                    from .industry_classifier import IndustryClassifier
                    key=finbert_cache_key();classifier_key=IndustryClassifier(c['taxonomy']).cache_key
                    # Completed old rows cannot starve new/changed rows once a
                    # library grows beyond one 300-record offline batch.
                    items.sort(key=lambda n:bool(data.classification(n,classifier_key)) and
                        (not eligibility(n)[0] or bool(data.cached(n,key))))
                ids=[n.article_id for n in items]
            if not ids:raise ValueError('No saved originals selected')
            if c['taxonomy']=='US-BUSINESS-1' and not c.get('classifier_options'):
                from .media_use import scope_of
                if any(scope_of(n) and n.article_id in ids for n in data.news()):
                    from .classification_scheme import selected
                    options=selected(self.store)
                    if options:c['classifier_options']=options
            c.update(sources=[],article_ids=list(dict.fromkeys(ids))[:300],budgets={},source_permissions={})
        return self._enqueue(validate_config(c))
    def submit_reclassify(self,*,article_ids=None,options=None,confirmed=False):
        if confirmed is not True:raise ValueError('Confirm classification-only use of retained media')
        from .classification_scheme import selected
        from .product_storage import ProductStorage
        from .media_use import scope_of,authorize
        opts=options or selected(self.store)
        if not opts:raise ValueError('Select the independent local classifier scheme first')
        items=[n for n in ProductStorage(self.store).news() if scope_of(n) and (article_ids is None or n.article_id in article_ids)]
        if not items:raise ValueError('No current finite media selected')
        for n in items:authorize(n,('retain','local_display','local_classification'))
        c=dict(sources=[],article_ids=[n.article_id for n in items][:300],operation='reclassify',model='Local FinBERT',model_id='',
            taxonomy='US-BUSINESS-1',limit=300,classifier_llm=False,classifier_options=opts,budgets={},source_permissions={})
        return self._enqueue(validate_config(c))
    def submit_import(self,items,*,confirmed=False,taxonomy='US-BUSINESS-1'):
        if confirmed is not True:raise ValueError('Confirm the import licence scope')
        if not 1<=len(items)<=300:raise ValueError('Import 1–300 records')
        from .source_policies import authorize
        for item in items:
            evidence=authorize(item,('retain','local_display'))
            if evidence.get('policy',{}).get('expires_at'):raise ValueError('Finite imports cannot use permanent preview checkpoints; use the finite API/RSS text flow')
        c=validate_config(dict(sources=[],article_ids=[n.article_id for n in items],operation='collect',
            model='Local FinBERT',model_id='',taxonomy=taxonomy,limit=300,budgets={},source_permissions={}))
        return self._enqueue(c,preview_items=items)
    def submit_saved_local(self,article_id,*,confirmed=False,taxonomy='US-BUSINESS-1',force_reanalysis=False):
        """Analyze one retained, policy-covered original without source setup."""
        if confirmed is not True:raise ValueError('Confirm local processing of the saved original')
        from .product_storage import ProductStorage
        from .source_policies import authorize
        item=next((n for n in ProductStorage(self.store).news() if n.article_id==article_id),None)
        if item is None:raise ValueError('Saved original not found')
        from .media_use import scope_of
        if scope_of(item):
            if force_reanalysis:raise ValueError('Finite media uses cached fixed-model analysis only')
            from .media_batch_ui import saved
            config=saved(self.store)
            if not config:raise ValueError('Use the retained-media offline batch controls')
            return self.submit_batch('analyze',config,confirmed=True,article_ids=[article_id])
        evidence=authorize(item,('retain','local_classification','local_sentiment','local_display'))
        provenance=json.loads(item.provenance);provenance['automatic_use_policy']=evidence
        item=replace(item,rights=replace(item.rights,external=False),provenance=json.dumps(provenance,ensure_ascii=False))
        c=validate_config(dict(sources=[],article_ids=[article_id],model='Local FinBERT',model_id='',
            classifier_llm=False,taxonomy=taxonomy,limit=1,budgets={},source_permissions={},force_reanalysis=force_reanalysis))
        return self._enqueue(c,preview_item=item)
    def submit_preview(self,item,rights,*,scope,confirmed=False,taxonomy='US-BUSINESS-1'):
        """One selected, permitted preview; no source dispatch or draft mutation."""
        if confirmed is not True:
            raise ValueError('Confirm the selected preview and its text permissions')
        from .preview_processing import permitted_preview
        from .product_storage import ProductStorage
        item=permitted_preview(item,rights,scope)
        # An explicit restriction on an already retained original still wins.
        item=ProductStorage(self.store).apply_permissions(item)
        for action in ('preview','retain','analyze'):item.rights.require(action)
        item=replace(item,rights=replace(item.rights,external=False))
        c=validate_config(dict(sources=[],article_ids=[item.article_id],
            model='Local FinBERT',model_id='',classifier_llm=False,taxonomy=taxonomy,
            limit=1,budgets={},source_permissions={item.provider:asdict(item.rights)}))
        return self._enqueue(c,preview_item=item)
    def _enqueue(self,c,*,preview_item=None,preview_items=None):
        from .credential_store import NEWS_PROVIDERS
        from .news_keys import NewsKeyRegistry
        registry=NewsKeyRegistry(self.store) if (set(c['sources'])|set(c.get('source_permissions',{}))) & set(NEWS_PROVIDERS) else None
        if registry:registry.reject_secret_text(json.dumps(c))
        preview_payload=None
        from .media_use import scope_of
        if any(scope_of(n) for n in (preview_items or ([preview_item] if preview_item else []))):
            raise ValueError('Finite media text must use the ID-only batch queue, never a permanent preview checkpoint')
        if preview_item is not None or preview_items is not None:
            preview_payload=json.dumps([asdict(n) for n in (preview_items if preview_items is not None else [preview_item])])
            if registry:registry.reject_secret_text(preview_payload)
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            completed_collection=None
            if c.get('media_batch') and c.get('operation')!='analyze':
                nonce=c['media_batch']['batch_id']
                for old_id,snapshot in db.execute('SELECT id,snapshot FROM product_tasks ORDER BY rowid DESC'):
                    previous=json.loads(snapshot)
                    if previous.get('media_batch',{}).get('batch_id')!=nonce:continue
                    if previous.get('operation')=='analyze':continue
                    if c.get('operation')=='collect' or previous.get('operation')!='collect':return old_id,False
                    completed_collection=db.execute("SELECT status,payload FROM product_steps WHERE task_id=? AND step='phase:collection'",(old_id,)).fetchone()
                    if not completed_collection or completed_collection[0]!='ok':return old_id,False
                    break
            row=db.execute("SELECT id FROM product_tasks WHERE status IN ('queued','running')").fetchone()
            if row:return row[0],False
            if c.get('media_batch') and c.get('operation')!='analyze' and not completed_collection:
                from .media_batch import preflight
                preflight(self.store,c['media_batch'],ignore_spacing=True)
            if registry:c['news_key_slots']=registry.pin(c['sources'],db)
            identity=uuid4().hex;stamp=now()
            db.execute('INSERT INTO product_tasks(id,status,snapshot,stage,counts,created,updated) VALUES (?,?,?,?,?,?,?)',
                       (identity,'queued',json.dumps(c),'queued',json.dumps(dict(new=0,duplicates=0,classified=0,analyzed=0,failed=0,skipped=0)),stamp,stamp))
            if preview_payload is not None:
                # Atomic handoff into the worker's existing saved-originals
                # checkpoint: a crash cannot leave a job that fetches again.
                db.execute('INSERT INTO product_steps VALUES (?,?,?,?)',
                           (identity,'fetch:saved_originals','ok',preview_payload))
            if completed_collection:
                db.execute('INSERT INTO product_steps VALUES (?,?,?,?)',(identity,'phase:collection','ok',completed_collection[1]))
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
            batches=[r[0] for r in db.execute("SELECT id,snapshot,cancel FROM product_tasks WHERE status='running'")
                     if json.loads(r[1]).get('operation') and not r[2]]
            db.execute("UPDATE product_tasks SET status='interrupted',stage='interrupted',error='Worker stopped; completed stages preserved; explicit resume required',updated=? WHERE status='running'",(now(),));db.commit()
            for identity in batches:
                db.execute("UPDATE product_tasks SET status='queued',stage='recovering batch checkpoints',error='',updated=? WHERE id=?",(now(),identity))
            db.commit()
    def resume(self,identity):
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM product_tasks WHERE status IN ('queued','running')").fetchone():raise ValueError('Another task is active')
            db.execute("UPDATE product_tasks SET status='queued',cancel=0,error='',updated=? WHERE id=? AND status IN ('interrupted','blocked','cancelled','partial_failed')",(now(),identity));db.commit()


class Cancelled(Exception):pass
