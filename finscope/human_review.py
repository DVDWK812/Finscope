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


def validate(item, taxonomy, entries, unclassified, reason):
    catalog = load_taxonomy(taxonomy)
    nodes = {n['id']: n for n in catalog['nodes']}
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError('Enter a short review reason (1–500 characters).')
    if type(unclassified) is not bool or not isinstance(entries, list):
        raise ValueError('Invalid review selection.')
    if (unclassified and entries) or (not unclassified and not entries):
        raise ValueError('Choose supported industries or explicitly keep Unclassified.')
    text = '\n'.join((item.title, item.summary, item.body))
    labels = []
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or
                entry['id'] not in nodes or any(l['id'] == entry['id'] for l in labels)):
            raise ValueError('Select unique legal nodes from the current taxonomy.')
        quote = entry.get('quote', '')
        rationale = entry.get('reason', '')
        if not isinstance(quote, str) or not isinstance(rationale, str):
            raise ValueError('Invalid review selection.')
        quote, rationale = quote.strip(), rationale.strip()
        if (not quote or len(quote) > 2000 or quote not in text or len(quote) < 24 or
                quote.casefold() in {item.company.casefold(), item.ticker.casefold()}):
            raise ValueError('Each industry needs an exact original excerpt (24–2000 characters), not just a company name or ticker.')
        if not rationale or len(rationale) > 500:
            raise ValueError('Explain how each excerpt supports its selected industry (1–500 characters).')
        start = text.index(quote)
        labels.append(dict(id=entry['id'], parent_id=nodes[entry['id']]['parent_id'],
                           evidence=[dict(quote=quote, start=start, end=start+len(quote))],
                           reason=rationale, method=IDENTITY))
    for label in list(labels):
        parent = label['parent_id']
        if parent and not any(l['id'] == parent for l in labels):
            labels.append(dict(id=parent, parent_id=None, evidence=label['evidence'],
                               reason=label['reason'], method=IDENTITY, derived_from=label['id']))
    return dict(taxonomy=taxonomy, taxonomy_version=catalog['version'], taxonomy_digest=taxonomy_digest(catalog),
                labels=labels, status='unclassified' if unclassified else 'classified', reason=reason.strip())


class HumanReviews:
    def __init__(self, store):
        self.store = store

    def _target(self, item):
        # Enforce the live source-level decision before entering finite storage.
        other = ProductStorage(self.store)._route(item, ('retain', 'local_display', 'local_classification'))
        return other.store if other else self.store

    def save(self, item, taxonomy, entries, *, unclassified=False, reason='', confirmed=False, revoke=False):
        if confirmed is not True:
            raise ValueError('Explicit confirmation is required to save or revoke a review.')
        store = self._target(item)
        with closing(store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            item = current(store, db, item)
            if revoke:
                catalog = load_taxonomy(taxonomy)
                payload = dict(taxonomy=taxonomy, taxonomy_digest=taxonomy_digest(catalog), labels=[], status='revoked')
            else:
                payload = validate(item, taxonomy, entries, unclassified, reason)
            payload.update(id=uuid4().hex, article_id=item.article_id, content_version=item.content_version,
                           reviewer=IDENTITY, created_utc=now(),
                           evidence_basis='title + newline + summary + newline + body; character offsets',
                           evidence_attestation='User confirmed business-topic evidence, not company name or stock-price inference')
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
                # Retain history without redisplaying quotes from a superseded text.
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
            if (value['content_version'] != item.content_version or value['status'] == 'revoked' or
                    value.get('taxonomy_digest') != taxonomy_digest(load_taxonomy(taxonomy))):
                return None
            # Revalidate stored IDs, parents and exact evidence as well as permissions.
            entries = [dict(id=l['id'], quote=l['evidence'][0]['quote'], reason=l['reason'])
                       for l in value['labels'] if not l.get('derived_from')]
            checked = validate(item, taxonomy, entries, value['status'] == 'unclassified', value['reason'])
            if checked['labels'] != value['labels']:
                return None
            return value
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
                                            'classification_source': IDENTITY, 'human_review_id': value['id']}
        return display
