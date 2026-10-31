"""News-only key slots. SQLite contains IDs/statuses, never credential blobs."""
from contextlib import closing
from datetime import datetime,timezone
import json
import re
import sqlite3
from uuid import uuid4
from .credential_store import NEWS_PROVIDERS,validate_slot,validate_secret

LEGACY='legacy'
CURRENT=object()


class NewsKeyError(ValueError):pass


def stamp():return datetime.now(timezone.utc).isoformat()


def validate_ref(value):
    if value==LEGACY:return
    validate_slot('marketaux',value)


class NewsKeyRegistry:
    def __init__(self,store,*,secrets=None):
        from .local_credentials import credential_store
        self.store=store;self.secrets=secrets if secrets is not None else credential_store()
        with closing(store.connect()) as db:
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='news_key_slots'").fetchone()
        if exists:return
        from .task_queue import ProcessLock
        with ProcessLock(str(store.path)+'.news-keys-schema.lock'),closing(store.connect()) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='news_key_slots'").fetchone():return
            backup=store.path.parent/'backups'/(store.path.name+'.before-news-keys-v1.'+uuid4().hex+'.sqlite3')
            backup.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(backup)) as target:db.backup(target)
            db.executescript('''BEGIN IMMEDIATE;
              CREATE TABLE news_key_slots(provider TEXT NOT NULL CHECK(provider IN ('marketaux','finnhub','newsdata')),
                slot_id TEXT NOT NULL,name TEXT NOT NULL,credential_ref TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
                created_at TEXT NOT NULL,last_used_at TEXT,last_status TEXT NOT NULL DEFAULT 'untested',last_error TEXT,
                deletion_pending INTEGER NOT NULL DEFAULT 0,deleted_at TEXT,PRIMARY KEY(provider,slot_id));
              CREATE TABLE news_key_policies(provider TEXT PRIMARY KEY CHECK(provider IN ('marketaux','finnhub','newsdata')),
                primary_slot TEXT,legacy_enabled INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
              CREATE TABLE news_key_versions(provider TEXT NOT NULL,slot_id TEXT NOT NULL,credential_ref TEXT NOT NULL,
                created_at TEXT NOT NULL,PRIMARY KEY(provider,credential_ref));
              CREATE TABLE news_request_keys(request_id TEXT PRIMARY KEY,provider TEXT NOT NULL,slot_id TEXT NOT NULL,
                credential_ref TEXT NOT NULL,reserved_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',error TEXT);
              COMMIT;''')

    @staticmethod
    def provider(provider):
        if provider not in NEWS_PROVIDERS:raise NewsKeyError('Choose a news API source')

    def legacy_key(self,provider):
        self.provider(provider)
        from .api_sources import local_credentials
        from .local_credentials import ENV_KEYS
        try:return self.secrets.read(provider) or local_credentials().get(ENV_KEYS[provider],'')
        except (ValueError,OSError):raise NewsKeyError('News credential could not be read; no request was made') from None

    def _selection(self,db,provider):
        self.provider(provider)
        policy=db.execute('SELECT primary_slot,legacy_enabled FROM news_key_policies WHERE provider=?',(provider,)).fetchone()
        selected=policy[0] if policy else LEGACY
        if not selected:return None
        if selected==LEGACY:return {'slot_id':LEGACY,'credential_ref':LEGACY} if not policy or policy[1] else None
        row=db.execute('SELECT credential_ref,enabled,last_status,deletion_pending,deleted_at FROM news_key_slots WHERE provider=? AND slot_id=?',(provider,selected)).fetchone()
        if not row or not row[1] or row[2]=='invalid' or row[3] or row[4]:return None
        return {'slot_id':selected,'credential_ref':row[0]}

    def selection(self,provider):
        with closing(self.store.connect()) as db:return self._selection(db,provider)

    def pin(self,sources,db):
        return {p:self._selection(db,p) for p in sources if p in NEWS_PROVIDERS}

    def rows(self,provider,*,inspect_legacy=True):
        self.provider(provider)
        with closing(self.store.connect()) as db:
            db.row_factory=sqlite3.Row
            policy=db.execute('SELECT primary_slot,legacy_enabled FROM news_key_policies WHERE provider=?',(provider,)).fetchone()
            primary=policy[0] if policy else LEGACY
            last=db.execute("SELECT reserved_at,status,error FROM news_request_keys WHERE provider=? AND slot_id='legacy' ORDER BY reserved_at DESC LIMIT 1",(provider,)).fetchone()
            rows=[dict(r) for r in db.execute('SELECT * FROM news_key_slots WHERE provider=? AND deleted_at IS NULL ORDER BY created_at,slot_id',(provider,))]
        if inspect_legacy and self.legacy_key(provider):
            rows.insert(0,dict(provider=provider,slot_id=LEGACY,name='Existing credential / project .env',credential_ref=LEGACY,
                enabled=bool(policy[1]) if policy else True,created_at='',last_used_at=last[0] if last else '',
                last_status=last[1] if last else 'untested',last_error=last[2] if last else None,deletion_pending=False,deleted_at=None))
        for row in rows:row['is_primary']=row['slot_id']==primary
        return rows

    def _row(self,db,provider,slot):
        self.provider(provider)
        if slot!=LEGACY:validate_slot(provider,slot)
        row=db.execute('SELECT credential_ref,enabled,last_status,deletion_pending,deleted_at FROM news_key_slots WHERE provider=? AND slot_id=?',(provider,slot)).fetchone()
        if not row or row[4]:raise NewsKeyError('News key slot no longer exists')
        return row

    @staticmethod
    def _busy(db,provider,slot):
        if db.execute("SELECT 1 FROM news_request_keys k JOIN local_requests r ON r.id=k.request_id WHERE k.provider=? AND k.slot_id=? AND r.status='pending'",(provider,slot)).fetchone():
            raise NewsKeyError('A request is using this key or has an unknown outcome; key changes are paused')

    def _ensure_policy(self,db,provider):
        db.execute('INSERT OR IGNORE INTO news_key_policies(provider,primary_slot,updated_at) VALUES (?,?,?)',(provider,LEGACY if self.legacy_key(provider) else None,stamp()))

    def _write_verified(self,provider,value):
        validate_secret(value);reference=uuid4().hex
        try:
            if self.secrets.read_slot(provider,reference):raise ValueError
            self.secrets.write_slot(provider,reference,value)
            if self.secrets.read_slot(provider,reference)!=value:raise ValueError
        except (ValueError,OSError):
            raise NewsKeyError('News key save failed; previous keys are unchanged') from None
        return reference

    def add(self,provider,name,value,*,primary=False):
        self.provider(provider);validate_secret(value)
        if (not isinstance(name,str) or not name.strip() or len(name)>40 or value in name
                or re.search(r'[A-Za-z0-9_-]{24,}|sk-|Bearer|api[_-]?key\s*[=:]',name,re.I)
                or any(ord(c)<32 for c in name)):
            raise NewsKeyError('Use a short display name, not credential text')
        self.reject_secret_text(name)
        reference=self._write_verified(provider,value);slot=uuid4().hex
        try:
            with closing(self.store.connect()) as db:
                db.execute('BEGIN IMMEDIATE');self._ensure_policy(db,provider)
                db.execute('INSERT INTO news_key_slots(provider,slot_id,name,credential_ref,enabled,created_at) VALUES (?,?,?,?,1,?)',(provider,slot,name.strip(),reference,stamp()))
                db.execute('INSERT INTO news_key_versions VALUES (?,?,?,?)',(provider,slot,reference,stamp()))
                if primary:db.execute('UPDATE news_key_policies SET primary_slot=?,updated_at=? WHERE provider=?',(slot,stamp(),provider))
                db.commit()
        except sqlite3.Error:
            raise NewsKeyError('News key configuration save failed; previous keys are unchanged') from None
        return slot

    def replace(self,provider,slot,value):
        self.provider(provider)
        if slot==LEGACY:raise NewsKeyError('Add a managed key to replace the legacy selection; the original is preserved')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');row=self._row(db,provider,slot);self._busy(db,provider,slot)
            if row[3]:raise NewsKeyError('News key deletion is pending; resolve it before editing')
            reference=self._write_verified(provider,value)
            db.execute('INSERT INTO news_key_versions VALUES (?,?,?,?)',(provider,slot,reference,stamp()))
            db.execute("UPDATE news_key_slots SET credential_ref=?,last_status='untested',last_error=NULL WHERE provider=? AND slot_id=?",(reference,provider,slot));db.commit()
        # Old immutable credential versions remain protected, so failed/unknown
        # cross-store commits cannot destroy the previous credential.

    def promote(self,provider,slot):
        self.provider(provider)
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if slot==LEGACY:
                if not self.legacy_key(provider):raise NewsKeyError('Existing credential is not configured')
            else:
                row=self._row(db,provider,slot)
                if not row[1] or row[2]=='invalid' or row[3]:raise NewsKeyError('Enable a valid key before making it primary')
            self._ensure_policy(db,provider)
            if slot==LEGACY:db.execute('UPDATE news_key_policies SET legacy_enabled=1 WHERE provider=?',(provider,))
            db.execute('UPDATE news_key_policies SET primary_slot=?,updated_at=? WHERE provider=?',(slot,stamp(),provider));db.commit()

    def enable(self,provider,slot,enabled):
        self.provider(provider)
        if type(enabled) is not bool:raise NewsKeyError('Invalid news key state')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');self._busy(db,provider,slot)
            if slot==LEGACY:
                self._ensure_policy(db,provider)
                db.execute('UPDATE news_key_policies SET legacy_enabled=? WHERE provider=?',(int(enabled),provider))
            else:
                row=self._row(db,provider,slot)
                if row[3]:raise NewsKeyError('News key deletion is pending; resolve it before editing')
                db.execute('UPDATE news_key_slots SET enabled=? WHERE provider=? AND slot_id=?',(int(enabled),provider,slot))
            if not enabled:db.execute('UPDATE news_key_policies SET primary_slot=NULL,updated_at=? WHERE provider=? AND primary_slot=?',(stamp(),provider,slot))
            db.commit()

    def delete(self,provider,slot,*,confirmed=False):
        self.provider(provider)
        if confirmed is not True:raise NewsKeyError('Confirm deletion of this news key')
        if slot==LEGACY:raise NewsKeyError('Existing credentials are preserved; disable their selection instead')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');self._row(db,provider,slot);self._busy(db,provider,slot)
            db.execute('UPDATE news_key_slots SET enabled=0,deletion_pending=1 WHERE provider=? AND slot_id=?',(provider,slot))
            db.execute('UPDATE news_key_policies SET primary_slot=NULL,updated_at=? WHERE provider=? AND primary_slot=?',(stamp(),provider,slot));db.commit()
        # Delete all owned immutable versions for this logical slot. References
        # used by old requests are retained as nonsensitive history only.
        with closing(self.store.connect()) as db:
            refs={self._row(db,provider,slot)[0],*[r[0] for r in db.execute('SELECT credential_ref FROM news_key_versions WHERE provider=? AND slot_id=?',(provider,slot))]}
        try:
            for reference in refs:self.secrets.delete_slot(provider,reference,confirmed=True)
        except (ValueError,OSError):raise NewsKeyError('News key deletion failed; configuration remains disabled for review') from None
        with closing(self.store.connect()) as db:
            db.execute('UPDATE news_key_slots SET deletion_pending=0,deleted_at=? WHERE provider=? AND slot_id=?',(stamp(),provider,slot));db.commit()

    def resolve(self,provider,*,selection=CURRENT,transaction=None,request_id=None):
        self.provider(provider)
        if transaction is None:
            with closing(self.store.connect()) as db:return self.resolve(provider,selection=selection,transaction=db)
        db=transaction;ref=self._selection(db,provider) if selection is CURRENT else selection
        if not ref:raise NewsKeyError('No enabled primary news key; this source was skipped')
        slot=ref['slot_id'];validate_ref(slot);validate_ref(ref['credential_ref'])
        if (slot==LEGACY)!=(ref['credential_ref']==LEGACY):raise NewsKeyError('Invalid news key selection')
        if slot==LEGACY:
            policy=db.execute('SELECT legacy_enabled FROM news_key_policies WHERE provider=?',(provider,)).fetchone()
            if policy and not policy[0]:raise NewsKeyError('The task key is disabled or changed; start a new task after reviewing settings')
            key=self.legacy_key(provider)
        else:
            row=self._row(db,provider,slot)
            if not row[1] or row[2]=='invalid' or row[3] or row[0]!=ref['credential_ref']:
                raise NewsKeyError('The task key is disabled or changed; start a new task after reviewing settings')
            try:key=self.secrets.read_slot(provider,row[0])
            except (ValueError,OSError):raise NewsKeyError('News credential could not be read; no request was made') from None
        if not key:raise NewsKeyError('Primary news credential is missing; this source was skipped')
        validate_secret(key)
        if request_id:
            db.execute('INSERT INTO news_request_keys(request_id,provider,slot_id,credential_ref,reserved_at) VALUES (?,?,?,?,?)',(request_id,provider,slot,ref['credential_ref'],stamp()))
            if slot!=LEGACY:db.execute("UPDATE news_key_slots SET last_used_at=?,last_status='pending',last_error=NULL WHERE provider=? AND slot_id=?",(stamp(),provider,slot))
        return key

    def configured(self,provider):
        try:return bool(self.resolve(provider))
        except NewsKeyError:return False

    def fetch(self,service,provider,topic,*,selection=CURRENT,**kwargs):
        identities=[]
        def resolve(db,identity):
            key=self.resolve(provider,selection=selection,transaction=db,request_id=identity)
            identities.append(identity)
            return key
        result,items=service.fetch(provider,topic,credential_resolver=resolve,**kwargs)
        if identities:self.finish(identities[0],result)
        return result,items

    def reject_secret_text(self,text):
        with closing(self.store.connect()) as db:
            refs=db.execute('SELECT provider,credential_ref FROM news_key_versions').fetchall()
        for provider,reference in refs:
            try:value=self.secrets.read_slot(provider,reference)
            except (ValueError,OSError):raise NewsKeyError('News credential could not be read; no request was made') from None
            if value and len(value)>5 and value in text:raise NewsKeyError('Credential text cannot be stored in task configuration')

    def finish(self,request_id,result):
        error=(None if result.status=='ok' else 'authentication' if result.http_status==401 else
            'permission_or_subscription' if result.http_status==403 else 'rate_limit' if result.http_status==429 else
            'provider_error' if result.http_status and result.http_status>=500 else 'transport_or_response_error')
        status='ok' if result.status=='ok' else 'invalid' if result.http_status==401 else 'failed'
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT provider,slot_id,credential_ref FROM news_request_keys WHERE request_id=?',(request_id,)).fetchone()
            if not row:return
            db.execute('UPDATE news_request_keys SET status=?,error=? WHERE request_id=?',(status,error,request_id))
            db.execute('UPDATE news_key_slots SET last_status=?,last_error=? WHERE provider=? AND slot_id=? AND credential_ref=?',(status,error,*row));db.commit()
