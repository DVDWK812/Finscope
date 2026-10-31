"""One bounded DeepSeek interface rehearsal. Never includes the real-news library."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import sqlite3
from uuid import uuid4
from .local_news import NewsItem,ContentRights,utcnow
from .rate_limits import retry_deadline

SCOPE='deepseek-authored-financial-smoke-v1'
NAMESPACE=SCOPE+':sentiment-v1'
SAMPLES=(
    ('positive','Fictional Northstar Components reported quarterly revenue of $120 million, up 18 percent, and operating profit rose from $9 million to $14 million as customer orders grew.'),
    ('negative','Fictional Harbour Retail reported quarterly sales fell 12 percent and recorded an operating loss of $8 million. Management announced store closures after weaker customer demand.'),
    ('neutral','Fictional Summit Infrastructure announced that its scheduled investor briefing will take place on 15 November. The notice contains no earnings update or revised forecast.'),
)


def authored_samples():
    result=[]
    for number,(kind,text) in enumerate(SAMPLES,1):
        title='Authored DeepSeek interface test '+str(number)
        version=hashlib.sha256((title+'\n'+text).encode()).hexdigest()
        identity=hashlib.sha256((SCOPE+version).encode()).hexdigest()[:32]
        result.append(NewsItem(identity,'authored_synthetic',title,'FinScope authored interface tests','',text,
            '', 'submitted',utcnow().isoformat(),(),ContentRights(True,True,True,True,'FinScope-authored fictional interface test; sending requires this-run confirmation'),
            content_version=version,language='en',text_basis='authored_test'))
    return result


class DeepSeekLedger:
    def __init__(self,store):
        self.store=store
        with closing(store.connect()) as db:
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='deepseek_requests'").fetchone()
        if exists:return
        from .task_queue import ProcessLock
        with ProcessLock(str(store.path)+'.deepseek-schema.lock'),closing(store.connect()) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='deepseek_requests'").fetchone():return
            backup=store.path.parent/'backups'/(store.path.name+'.before-deepseek-v1.'+uuid4().hex+'.sqlite3')
            backup.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(backup)) as target:db.backup(target)
            db.executescript('''BEGIN IMMEDIATE;
                CREATE TABLE deepseek_requests(id TEXT PRIMARY KEY,scope TEXT NOT NULL,kind TEXT NOT NULL,
                    sample_id TEXT NOT NULL,status TEXT NOT NULL,reserved_at TEXT NOT NULL,completed_at TEXT,
                    hold_until TEXT,http_status INTEGER,error_kind TEXT,request_model TEXT NOT NULL,
                    analysis_id TEXT,consent_at TEXT,UNIQUE(scope,kind,sample_id));
                CREATE TABLE deepseek_model_cache(namespace TEXT PRIMARY KEY,payload TEXT NOT NULL,checked_at TEXT NOT NULL);
                CREATE TABLE deepseek_analysis_cache(namespace TEXT NOT NULL,article_id TEXT NOT NULL,
                    content_version TEXT NOT NULL,request_model TEXT NOT NULL,analysis_id TEXT NOT NULL,
                    PRIMARY KEY(namespace,article_id,content_version,request_model)); COMMIT;''')
    def rows(self):
        with closing(self.store.connect()) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute('SELECT * FROM deepseek_requests ORDER BY reserved_at,rowid')]
    def guard(self,db):
        from .model_providers import ModelError
        rows=db.execute('SELECT status,hold_until FROM deepseek_requests WHERE scope=?',(SCOPE,)).fetchall()
        if any(status in ('pending','unknown') for status,_ in rows):
            raise ModelError('DeepSeek has an unresolved request; review its ledger before any further request.',kind='unknown_outcome')
        if any(hold and datetime.fromisoformat(hold)>utcnow() for _,hold in rows):
            raise ModelError('DeepSeek Retry-After hold is active; no request was made.',kind='rate_limit')
        if any(status in ('failed','invalid') for status,_ in rows):
            raise ModelError('DeepSeek test stopped after an error; no automatic retry or further samples.',kind='test_stopped')
    def cached_models(self):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT payload FROM deepseek_model_cache WHERE namespace=?',(SCOPE,)).fetchone()
        return json.loads(row[0]) if row else None
    def checked_models(self):
        with closing(self.store.connect()) as db:self.guard(db)
        return self.cached_models()
    def reserve(self,kind,sample_id,model='',*,budget=3,consent=False):
        from .model_providers import ModelError
        if kind not in ('models','inference'):raise ModelError('Unsupported DeepSeek operation')
        if kind=='inference' and (consent is not True or type(budget) is not int or not 1<=budget<=3):
            raise ModelError('Confirm this test action and a budget of at most three inferences.',kind='consent_required')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');self.guard(db)
            if db.execute('SELECT 1 FROM deepseek_requests WHERE scope=? AND kind=? AND sample_id=?',(SCOPE,kind,sample_id)).fetchone():
                raise ModelError('This DeepSeek request was already reserved; it will not be repeated.',kind='duplicate_request')
            if kind=='inference' and db.execute("SELECT count(*) FROM deepseek_requests WHERE scope=? AND kind='inference'",(SCOPE,)).fetchone()[0]>=min(3,budget):
                raise ModelError('DeepSeek test inference budget is exhausted; no request was made.',kind='budget_exhausted')
            identity=uuid4().hex;stamp=utcnow().isoformat()
            db.execute('INSERT INTO deepseek_requests(id,scope,kind,sample_id,status,reserved_at,request_model,consent_at) VALUES (?,?,?,?,?,?,?,?)',
                (identity,SCOPE,kind,sample_id,'pending',stamp,model,stamp if consent else None));db.commit()
        return identity
    def failure(self,identity,error,*,unknown=False):
        stamp=utcnow();hold=retry_deadline(error.retry_after,stamp) if error.retry_after or error.status==429 else None
        status='unknown' if unknown else 'failed' if error.status else 'invalid'
        with closing(self.store.connect()) as db:
            db.execute('UPDATE deepseek_requests SET completed_at=?,status=?,hold_until=?,http_status=?,error_kind=? WHERE id=?',
                (stamp.isoformat(),status,hold.isoformat() if hold else None,error.status,error.kind,identity));db.commit()
    def save_models(self,identity,models):
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR REPLACE INTO deepseek_model_cache VALUES (?,?,?)',(SCOPE,json.dumps(models),utcnow().isoformat()))
            db.execute("UPDATE deepseek_requests SET status='ok',http_status=200,completed_at=? WHERE id=?",(utcnow().isoformat(),identity));db.commit()
    def cached_analysis(self,item,model):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT analysis_id FROM deepseek_analysis_cache WHERE namespace=? AND article_id=? AND content_version=? AND request_model=?',
                (NAMESPACE,item.article_id,item.content_version,model)).fetchone()
        if not row:return None
        result=next((a for a in self.store.list_analyses() if a.analysis_id==row[0]),None)
        if result is None:
            from .model_providers import ModelError
            raise ModelError('DeepSeek cached history needs review; no repeat request was made.',kind='cache_error')
        return result
    def success(self,identity,item,model,analysis):
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            self.store.save_analysis(analysis,transaction=db)
            db.execute('INSERT INTO deepseek_analysis_cache VALUES (?,?,?,?,?)',(NAMESPACE,item.article_id,item.content_version,model,analysis.analysis_id))
            db.execute("UPDATE deepseek_requests SET status='ok',http_status=200,analysis_id=?,completed_at=? WHERE id=?",(analysis.analysis_id,utcnow().isoformat(),identity));db.commit()


def run_authored_test(store,provider,*,api_key,model,confirmed=False,budget=3):
    from .model_providers import ModelError
    if confirmed is not True or type(budget) is not int or not 1<=budget<=3:
        raise ModelError('Confirm this test action and a budget of at most three inferences.',kind='consent_required')
    results=[]
    for item in authored_samples()[:budget]:
        # Serial, no catch/retry: the first failed/unknown result stops the batch.
        results.append(provider.analyze(item,store,api_key=api_key,model=model,consent=True,budget=budget))
    return results
