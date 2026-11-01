"""Unbacked-up finite text partition using existing storage/analysis table shapes.

No raw text is written to the permanent library or its task checkpoints. Reads
purge expired rows before returning any object. App shutdown cannot run cleanup;
the next process open performs it first. No claim of forensic erasure of OS,
browser, user screenshots, external backups or hardware snapshots is made.
"""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
from .media_use import utcnow, deadline, scope_of, authorize

TEXT_TABLES = ('local_news', 'local_analyses', 'product_content', 'product_classifications',
               'product_analysis_cache', 'product_current_content', 'product_record_state',
               'product_classifier_calls','product_classification_reviews','product_media_observations')


class ExpiringMediaStore:
    is_expiring_media = True

    def __init__(self, parent, *, clock=None):
        self.path = Path(str(parent.path) + '.expiring') / 'live.sqlite3'
        from . import media_use
        self.clock = clock or (lambda:media_use.utcnow())
        from .test_safety import require_test_path
        require_test_path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._open()) as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS media_lifetimes(article_id TEXT PRIMARY KEY, expires_at TEXT NOT NULL, live INTEGER NOT NULL, capture TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS media_captures(article_id TEXT,capture TEXT,epoch INTEGER NOT NULL,PRIMARY KEY(article_id,capture));
              CREATE TABLE IF NOT EXISTS local_news(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS local_analyses(id TEXT PRIMARY KEY,article_id TEXT NOT NULL,analyzed_at TEXT NOT NULL,payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS local_permission_history(article_id TEXT,changed_at TEXT,previous_rights TEXT,new_rights TEXT);
              CREATE TABLE IF NOT EXISTS product_content(article_id TEXT,version TEXT,payload TEXT,created TEXT,PRIMARY KEY(article_id,version));
              CREATE TABLE IF NOT EXISTS product_classifications(article_id TEXT,content_version TEXT,cache_key TEXT,payload TEXT,created TEXT,PRIMARY KEY(article_id,content_version,cache_key));
              CREATE TABLE IF NOT EXISTS product_analysis_cache(article_id TEXT,content_version TEXT,cache_key TEXT,analysis_id TEXT,PRIMARY KEY(article_id,content_version,cache_key));
              CREATE TABLE IF NOT EXISTS product_current_content(article_id TEXT PRIMARY KEY,version TEXT,updated TEXT);
              CREATE TABLE IF NOT EXISTS product_record_state(article_id TEXT,content_version TEXT,download TEXT,analysis TEXT,reason TEXT,updated TEXT,PRIMARY KEY(article_id,content_version));
              CREATE TABLE IF NOT EXISTS product_classifier_calls(id TEXT PRIMARY KEY,article_id TEXT,content_version TEXT,cache_key TEXT,stage TEXT,status TEXT,model_id TEXT,revision TEXT,started TEXT,finished TEXT,payload TEXT,UNIQUE(article_id,content_version,cache_key,stage));
              CREATE TABLE IF NOT EXISTS product_classification_reviews(id TEXT PRIMARY KEY,article_id TEXT,cache_key TEXT,created TEXT,payload TEXT);
              CREATE TABLE IF NOT EXISTS product_media_observations(article_id TEXT,identity TEXT,payload TEXT,PRIMARY KEY(article_id,identity));
            ''')
            self.purged_count = self._purge(db)

    @classmethod
    def exists(cls, parent):
        return (Path(str(parent.path) + '.expiring') / 'live.sqlite3').exists()

    def _open(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute('PRAGMA secure_delete=ON')
        db.execute('PRAGMA journal_mode=DELETE')
        return db

    def _purge(self, db):
        ids = [r[0] for r in db.execute('SELECT article_id FROM media_lifetimes WHERE live=1 AND expires_at<=?', (self.clock().isoformat(),))]
        for identity in ids:
            for table in TEXT_TABLES:
                db.execute('DELETE FROM ' + table + ' WHERE ' + ('id' if table == 'local_news' else 'article_id') + '=?', (identity,))
            db.execute('DELETE FROM local_permission_history WHERE article_id=?', (identity,))
            db.execute('UPDATE media_lifetimes SET live=0 WHERE article_id=?', (identity,))
        db.commit()
        return len(ids)

    def purge(self):
        with closing(self._open()) as db:
            return self._purge(db)

    def revoke(self,source):
        """Immediate user-requested deletion, including results and quote copies."""
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            for identity,payload in db.execute('SELECT id,payload FROM local_news').fetchall():
                if json.loads(payload).get('provenance') and json.loads(json.loads(payload)['provenance']).get('media_use',{}).get('source')==source:
                    db.execute('UPDATE media_lifetimes SET expires_at=? WHERE article_id=?',(self.clock().isoformat(),identity))
            db.commit()
            return self._purge(db)

    def narrow_feed_scope(self,source,policy):
        from .media_monitor import publisher_covered
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            for identity,payload in db.execute('SELECT id,payload FROM local_news').fetchall():
                item=json.loads(payload);scope=json.loads(item['provenance']).get('media_use',{})
                if scope.get('source')!='rss:'+source:continue
                end=policy.get('expires_at','')
                if (policy.get('basis_status')=='restricted' or not {'retain','display'}<=set(policy['purposes'])
                        or not set(scope['fields'])<=set(policy['fields']) or not publisher_covered(source,item['url'],policy)):
                    end=self.clock().isoformat()
                if end:
                    end=deadline(end).isoformat()
                    db.execute('UPDATE media_lifetimes SET expires_at=min(expires_at,?) WHERE article_id=?',(end,identity))
            db.commit();return self._purge(db)

    def connect(self):
        db = self._open()
        self._purge(db)
        return db

    def bind(self, db, item):
        authorize(item, ('retain', 'local_display'), now=self.clock())
        expiry = scope_of(item)['expires_at']
        origin=json.loads(item.provenance)
        capture=origin.get('capture_task_id') or origin.get('capture_request_id','')
        old = db.execute('SELECT expires_at,live,capture FROM media_lifetimes WHERE article_id=?', (item.article_id,)).fetchone()
        seen=db.execute('SELECT epoch FROM media_captures WHERE article_id=? AND capture=?',(item.article_id,capture)).fetchone()
        if old and not old[1] and (not capture or seen):
            raise ValueError('An expired capture cannot be restored from a stale object or checkpoint')
        epoch=db.execute('SELECT coalesce(max(epoch),0) FROM media_captures WHERE article_id=?',(item.article_id,)).fetchone()[0]
        if seen and seen[0]!=epoch:raise ValueError('An expired capture cannot write into a later retention period')
        if not old or not old[1]:epoch+=1
        if old and old[1]:
            expiry = min(expiry, old[0])
        if deadline(expiry)<=self.clock():raise ValueError('Media text expired during persistence')
        db.execute('INSERT OR REPLACE INTO media_lifetimes VALUES (?,?,1,?)', (item.article_id, expiry,capture))
        db.execute('INSERT OR IGNORE INTO media_captures VALUES (?,?,?)',(item.article_id,capture,epoch))

    def epoch(self,item):
        self.check(item)
        with closing(self.connect()) as db:
            return db.execute('SELECT max(epoch) FROM media_captures WHERE article_id=?',(item.article_id,)).fetchone()[0]

    def check(self, item, db=None):
        authorize(item, ('retain', 'local_display'), now=self.clock())
        if db is None:
            with closing(self.connect()) as connection:return self.check(item,connection)
        row = db.execute('SELECT expires_at,live FROM media_lifetimes WHERE article_id=?', (item.article_id,)).fetchone()
        if not row or not row[1] or deadline(row[0])<=self.clock():
            raise ValueError('Media text expired; references and cached outputs cannot be reused')
        origin=json.loads(item.provenance);capture=origin.get('capture_task_id') or origin.get('capture_request_id','')
        seen=db.execute('SELECT epoch FROM media_captures WHERE article_id=? AND capture=?',(item.article_id,capture)).fetchone()
        current=db.execute('SELECT max(epoch) FROM media_captures WHERE article_id=?',(item.article_id,)).fetchone()[0]
        if not seen or seen[0]!=current:raise ValueError('Expired capture is outside the current retention period')

    def list_news(self):
        from .product_storage import decode
        with closing(self.connect()) as db:
            return [decode(p) for p, in db.execute('SELECT payload FROM local_news')]

    def list_analyses(self):
        from .local_news import Analysis
        with closing(self.connect()) as db:
            return [Analysis(**json.loads(p)) for p, in db.execute('SELECT payload FROM local_analyses ORDER BY analyzed_at,rowid')]


def partition(parent, *, create=False):
    if getattr(parent, 'is_expiring_media', False):
        return None
    return ExpiringMediaStore(parent) if create or ExpiringMediaStore.exists(parent) else None
