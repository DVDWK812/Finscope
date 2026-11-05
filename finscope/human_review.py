"""Explicit local-user annotations, separate from every automatic model cache.

Only display projections consume these append-only events. Finite evidence lives
in the existing expiring partition and is purged with its original article.
"""
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from uuid import uuid4

from .product_storage import ProductStorage, decode
from .source_policies import authorize
from .task_queue import now
from .taxonomy import load_taxonomy

TABLE = 'product_human_reviews'
IDENTITY = 'Local user review'
METHOD = 'Manual selection'
SOURCE = IDENTITY + ' / ' + METHOD
FORMAT_VERSION = 2


def taxonomy_digest(catalog):
    return hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest()


def exists(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone())


def permitted(item):
    # No inference is performed, but classification-use permission still applies.
    authorize(item, ('retain', 'local_display', 'local_classification'))


def current(store, db, expected):
    row = db.execute('SELECT c.payload FROM product_current_content p JOIN product_content c '
                     'ON c.article_id=p.article_id AND c.version=p.version WHERE p.article_id=?',
                     (expected.article_id,)).fetchone()
    if row is None:
        row = db.execute('SELECT payload FROM local_news WHERE id=?', (expected.article_id,)).fetchone()
    if row is None:
        raise ValueError('Review unavailable: the original record is no longer available.')
    item = decode(row[0])
    original = db.execute('SELECT payload FROM local_news WHERE id=?', (item.article_id,)).fetchone()
    if original and db.execute('SELECT 1 FROM local_permission_history WHERE article_id=?', (item.article_id,)).fetchone():
        item = replace(item, rights=decode(original[0]).rights)
    if (not item.content_version or item.content_version != expected.content_version or
            (item.title, item.summary, item.body) != (expected.title, expected.summary, expected.body)):
        raise ValueError('Review unavailable: the text version changed. Reopen the record.')
    permitted(item)
    if getattr(store, 'is_expiring_media', False):
        store.check(item, db)
    return item


def selection_labels(catalog, ids, status):
    nodes = {n['id']: n for n in catalog['nodes']}
    if not isinstance(ids, list) or any(not isinstance(k, str) or k not in nodes for k in ids):
        raise ValueError('Select unique legal nodes from the current taxonomy.')
    if len(ids) != len(set(ids)):
        raise ValueError('Select unique legal nodes from the current taxonomy.')
    if status not in ('classified', 'unclassified') or bool(ids) != (status == 'classified'):
        raise ValueError('Choose industries or Unclassified.')
    labels = {k: dict(id=k, parent_id=nodes[k]['parent_id'], method=SOURCE) for k in ids}
    for k in ids:
        parent = nodes[k]['parent_id']
        if parent and parent not in labels:
            labels[parent] = dict(id=parent, parent_id=None, method=SOURCE, derived_from=k)
    return list(labels.values())


def validate_note(note):
    if not isinstance(note, str) or len(note) > 500:
        raise ValueError('Note must be at most 500 characters.')
    return note.strip()


def selection_view(value, catalog):
    """Resolve old evidence-bearing events and new manual choices without rewriting history."""
    if value.get('reviewer') != IDENTITY or value.get('taxonomy') != catalog['id']:
        return None
    status = value['status']
    if value.get('format_version') == FORMAT_VERSION:
        if value.get('method') != METHOD:
            return None
        ids = value['industry_ids']
        return {**value, 'labels': selection_labels(catalog, ids, status), 'note': validate_note(value.get('note', ''))}
    if 'format_version' in value:
        return None
    legacy = value['labels']
    if not isinstance(legacy, list) or any(not isinstance(label, dict) for label in legacy):
        return None
    ids = [label['id'] for label in legacy if not label.get('derived_from')]
    expected = selection_labels(catalog, ids, status)
    # Legacy excerpts and reasons are archival data, not an eligibility condition.
    if [(l['id'], l['parent_id'], l.get('derived_from')) for l in legacy] != [
            (l['id'], l['parent_id'], l.get('derived_from')) for l in expected]:
        return None
    return {**value, 'industry_ids': ids}


class HumanReviews:
    def __init__(self, store):
        self.store = store

    def _target(self, item):
        # Enforce the live source-level decision before entering finite storage.
        other = ProductStorage(self.store)._route(item, ('retain', 'local_display', 'local_classification'))
        return other.store if other else self.store

    def save(self, item, taxonomy, industry_ids, *, unclassified=False, note='', revoke=False):
        catalog = load_taxonomy(taxonomy)
        if type(unclassified) is not bool or type(revoke) is not bool:
            raise ValueError('Invalid review selection.')
        status = 'revoked' if revoke else 'unclassified' if unclassified else 'classified'
        if revoke:
            if industry_ids != [] or unclassified or note:
                raise ValueError('Invalid review selection.')
        else:
            selection_labels(catalog, industry_ids, status)
        note = validate_note(note)
        store = self._target(item)
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            item = current(store, db, item)
            payload = dict(id=uuid4().hex, article_id=item.article_id, content_version=item.content_version,
                           taxonomy=taxonomy, taxonomy_version=catalog['version'], taxonomy_digest=taxonomy_digest(catalog),
                           format_version=FORMAT_VERSION, industry_ids=list(industry_ids), note=note,
                           reviewer=IDENTITY, method=METHOD, status=status, created_utc=now())
            # Lazily created only by an explicit save; browsing does not migrate a library.
            db.execute('CREATE TABLE IF NOT EXISTS '+TABLE+' (id TEXT PRIMARY KEY, article_id TEXT NOT NULL, '
                       'content_version TEXT NOT NULL, taxonomy TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)')
            db.execute('INSERT INTO '+TABLE+' VALUES (?,?,?,?,?,?)',
                       (payload['id'], item.article_id, item.content_version, taxonomy, payload['created_utc'], json.dumps(payload)))
            db.commit()
        return payload

    def history(self, item, taxonomy):
        store = self._target(item)
        with closing(store.connect()) as db:
            db.execute('BEGIN')
            current(store, db, item)
            if not exists(db):
                return []
            rows = db.execute('SELECT payload FROM '+TABLE+' WHERE article_id=? AND taxonomy=? ORDER BY rowid',
                              (item.article_id, taxonomy)).fetchall()
        result = []
        for row in rows:
            value = json.loads(row[0])
            if value['content_version'] != item.content_version:
                # Retain history without redisplaying text from a superseded version.
                value = {k: value[k] for k in ('id', 'article_id', 'content_version', 'taxonomy', 'reviewer', 'created_utc', 'status')}
                value['inactive_reason'] = 'Text version changed; old evidence is hidden'
            result.append(value)
        return result

    def active(self, item, taxonomy):
        try:
            rows = self.history(item, taxonomy)
            if not rows:
                return None
            value = rows[-1]
            catalog = load_taxonomy(taxonomy)
            if (value['content_version'] != item.content_version or value['status'] == 'revoked' or
                    value.get('taxonomy_digest') != taxonomy_digest(catalog)):
                return None
            return selection_view(value, catalog)
        except (ValueError, KeyError, TypeError, IndexError):
            return None

    def overlay(self, news, taxonomy, automated):
        display = dict(automated)
        candidates = set()
        other = ProductStorage(self.store)._partition()
        for store in (self.store, other.store if other else None):
            if store is None:
                continue
            with closing(store.connect()) as db:
                if exists(db):
                    candidates.update(r[0] for r in db.execute('SELECT DISTINCT article_id FROM '+TABLE+' WHERE taxonomy=?', (taxonomy,)))
        for item in news:
            if item.article_id not in candidates:
                continue
            value = self.active(item, taxonomy)
            if value:
                display[item.article_id] = {**automated.get(item.article_id, {}), **value,
                                            'classification_source': SOURCE, 'human_review_id': value['id']}
        return display
