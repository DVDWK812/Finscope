"""Append-only content, classification and model cache versions over the legacy store."""
from contextlib import closing
from dataclasses import asdict
import json
from .local_news import ContentRights,NewsItem
from .task_queue import now


def decode(payload):
    data=json.loads(payload);data['rights']=ContentRights(**data['rights']);data['sectors']=tuple(data['sectors'])
    return NewsItem(**data)


class ProductStorage:
    def __init__(self,store):self.store=store
    def _partition(self,create=False):
        from .expiring_media import partition
        value=partition(self.store,create=create)
        return ProductStorage(value) if value else None
    def _route(self,item,purposes=()):
        from .media_use import scope_of,enforce_decision
        if scope_of(item) and not getattr(self.store,'is_expiring_media',False):enforce_decision(self.store,scope_of(item),purposes)
        return self._partition(True) if scope_of(item) else None
    def expire(self):
        other=self._partition()
        return other.store.purged_count+other.store.purge() if other else 0
    def analyses(self):
        rows=self.store.list_analyses()
        other=self._partition()
        if other:
            ids={n.article_id for n in self.news()}
            rows += [a for a in other.analyses() if a.article_id in ids]
        return sorted(rows,key=lambda a:(a.analyzed_at,a.analysis_id))
    def visible_analyses(self,news=None,analyses=None):
        """Revalidate on every view; never cache permission/expiry decisions."""
        from .source_policies import authorize
        current={}
        for item in self.news() if news is None else news:
            try:
                for right in ('preview','retain','analyze'):item.rights.require(right)
                try:origin=json.loads(item.provenance)
                except (ValueError,TypeError):origin={}
                if isinstance(origin,dict) and any(k in origin for k in ('media_use','import_policy','media_policy','automatic_use_policy')):
                    authorize(item,('retain','local_display','local_sentiment'))
            except ValueError:continue
            current[item.article_id]=item
        return [a for a in (self.analyses() if analyses is None else analyses) if a.article_id in current and
                (not current[a.article_id].content_version or a.provenance.get('content_sha256')==current[a.article_id].content_version)]
    def view_revision(self):
        """Exact relevant-row fingerprint, excluding heartbeats and UI preferences.

        No cached SQL connection, mtime assumption or max-timestamp heuristic:
        in-place permission/content edits and deletions invalidate the snapshot too.
        Only a digest escapes this method, never a persistent copy of article text.
        """
        import hashlib,sqlite3
        from pathlib import Path
        tables=('local_news','local_analyses','local_permission_history','product_content',
                'product_current_content','product_classifications','product_analysis_cache',
                'product_record_state','media_lifetimes','media_captures','product_settings')
        digest=hashlib.sha256()
        for path in (self.store.path,Path(str(self.store.path)+'.expiring')/'live.sqlite3'):
            if not Path(path).exists():continue
            with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
                db.execute('BEGIN')
                existing={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in tables:
                    if table not in existing:continue
                    where=" WHERE name NOT IN ('view_preferences','ui_theme','ui_language')" if table=='product_settings' else ''
                    digest.update(table.encode())
                    for row in db.execute('SELECT * FROM '+table+where+' ORDER BY rowid'):
                        digest.update(repr(row).encode());digest.update(b'\n')
        from .batch_config import finbert_cache_key
        digest.update(finbert_cache_key().encode())
        return digest.hexdigest()
    def view_snapshot(self,state,taxonomy):
        """Session-only reuse with a live revision and time/permission gate per read."""
        from .source_policies import authorize
        revision=self.view_revision();saved=state.get('_library_snapshot')
        if not saved or saved['revision']!=revision:
            saved={'revision':revision,'news':self.news(),'analyses':self.analyses(),
                   'states':self.states(),'classes':{},'computed':{}}
            state['_library_snapshot']=saved
        permitted=[]
        for item in saved['news']:
            try:
                item.rights.require('preview');item.rights.require('retain')
                # Legacy manual records have no source-policy wrapper; their own
                # explicit article permission remains authoritative.
                try:origin=json.loads(item.provenance) if item.provenance else {}
                except (ValueError,TypeError):origin={}
                if isinstance(origin,dict) and any(k in origin for k in ('media_use','import_policy','media_policy','automatic_use_policy')):
                    authorize(item,('retain','local_display'))
            except (ValueError,TypeError):continue
            permitted.append(item)
        if len(permitted)!=len(saved['news']):
            # Expiry can change with no database write. Drop all derived content.
            saved['news']=permitted;saved['computed'].clear();saved['classes'].clear()
            ids={n.article_id for n in permitted}
            saved['analyses']=[a for a in saved['analyses'] if a.article_id in ids]
        if taxonomy not in saved['classes']:saved['classes'][taxonomy]=self.classifications(taxonomy)
        return saved
    def task_results(self,queue,task):
        """Only exact still-valid result receipts from this task, including reuse."""
        news={n.article_id:n for n in self.news()}
        analyses={a.analysis_id:a for a in self.visible_analyses(list(news.values()))}
        results={}
        for identity,receipt in queue.outcomes(task['id']).items():
            item=news.get(identity);result=analyses.get(receipt.get('analysis_id'))
            key=receipt.get('cache_key','')
            if not item or not result or item.content_version!=receipt.get('content_version'):continue
            if key.startswith('Local FinBERT|') and '|mock-test|' not in key:
                from .batch_config import finbert_cache_key
                if key!=finbert_cache_key():continue
            try:
                if self.cached(item,key)==result.analysis_id:results[identity]=result
            except ValueError:continue
        return results
    def apply_permissions(self,item):
        """Explicit article-level edits outrank subsequent source-level grants."""
        from dataclasses import replace
        from .text_processing import canonical_url
        with closing(self.store.connect()) as db:
            edited={r[0] for r in db.execute('SELECT DISTINCT article_id FROM local_permission_history')}
            originals=db.execute('SELECT id,payload FROM local_news').fetchall()
        url=canonical_url(item.url)
        for identity,payload in originals:
            old=json.loads(payload)
            if identity==item.article_id or url and old['source']==item.source and canonical_url(old['url'])==url:
                if identity in edited:return replace(item,article_id=identity,rights=ContentRights(**old['rights']))
                break
        return item
    def merge_available_text(self,item):
        """An unchanged index entry is not a source deletion of a retained body.

        Only reviewed official sources, identical title/date and an already
        licensed body qualify. A new body restriction or failed body fetch wins.
        No network operation and no grant for a narrower local-file import.
        """
        if item.provider not in {'abs_html','nist_rss','sec_submissions'} or item.body:return item
        try:origin=json.loads(item.provenance)
        except (TypeError,ValueError):return item
        if origin.get('body_reason'):return item
        from .text_processing import canonical_url
        with closing(self.store.connect()) as db:
            rows=db.execute('SELECT payload FROM product_content ORDER BY created DESC,rowid DESC').fetchall()
        for (payload,) in rows:
            old=decode(payload)
            if (old.provider!=item.provider or old.source!=item.source or not old.body or old.title!=item.title
                    or old.timestamp!=item.timestamp or old.publication_date!=item.publication_date
                    or old.filed_date!=item.filed_date
                    or canonical_url(old.url)!=canonical_url(item.url)):continue
            from .source_policies import authorize
            try:authorize(old,('retain','local_display'))
            except ValueError:continue
            previous=json.loads(old.provenance);combined={**previous,**origin}
            for key in ('body_status','body_byline','body_sha256','body_extraction_version','sentiment_eligible','ineligible_reason',
                        'input_text_type','extraction_version','document_characters','document_span_start','document_span_end','document_coverage','event_section'):
                if key in previous:combined[key]=previous[key]
            combined.update(retained_body_version=old.content_version,body_original_fetched_at=old.fetched_at,
                            body_refresh='Not re-downloaded; existing reviewed body retained for unchanged title/publication metadata')
            from dataclasses import replace
            return replace(item,body=old.body,summary=item.summary or old.summary,provenance=json.dumps(combined,ensure_ascii=False))
        return item
    def save(self,item,*,require_analysis=True):
        other=self._route(item,('local_classification','local_sentiment') if require_analysis else ())
        if other:return other.save(item,require_analysis=require_analysis)
        if not getattr(self.store,'is_expiring_media',False):
            try:origin=json.loads(item.provenance)
            except (TypeError,ValueError):origin={}
            if any(origin.get(k,{}).get('expires_at') for k in ('import_policy','media_policy')):
                raise ValueError('Finite text cannot enter the permanent library; use a supported finite media scope')
        item=self.apply_permissions(item)
        item.rights.require('retain');item.rights.require('preview')
        if require_analysis:item.rights.require('analyze')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            # Find a legacy original with the same publisher and normalized URL.
            from .text_processing import canonical_url
            for key,payload in db.execute('SELECT id,payload FROM local_news'):
                old=json.loads(payload)
                finite=getattr(self.store,'is_expiring_media',False)
                from .publisher_attribution import link_key
                same_url=False
                if item.url and (finite or old['source']==item.source):
                    same_url=(link_key(old['url'])==link_key(item.url)) if finite else canonical_url(old['url'])==canonical_url(item.url)
                if same_url:
                    from dataclasses import replace
                    item=replace(item,article_id=key);break
            if getattr(self.store,'is_expiring_media',False):
                from .publisher_attribution import observed
                import hashlib
                observation=observed(item)
                identity=hashlib.sha256(json.dumps(observation,sort_keys=True).encode()).hexdigest()
                previous=db.execute('SELECT c.payload FROM product_current_content p JOIN product_content c ON c.article_id=p.article_id AND c.version=p.version WHERE p.article_id=?',(item.article_id,)).fetchone()
                if previous:
                    old_item=decode(previous[0]);self.store.check(old_item,db)
                    origin=json.loads(item.provenance);capture=origin.get('capture_task_id') or origin.get('capture_request_id','')
                    epoch=db.execute('SELECT max(epoch) FROM media_captures WHERE article_id=?',(item.article_id,)).fetchone()[0]
                    seen=db.execute('SELECT epoch FROM media_captures WHERE article_id=? AND capture=?',(item.article_id,capture)).fetchone()
                    if seen and seen[0]!=epoch:raise ValueError('Expired capture cannot write into a later retention period')
                    db.execute('INSERT OR IGNORE INTO media_captures VALUES (?,?,?)',(item.article_id,capture,epoch))
                    expiry=db.execute('SELECT expires_at FROM media_lifetimes WHERE article_id=?',(item.article_id,)).fetchone()[0]
                    from .media_use import scope_of
                    expiry=min(expiry,scope_of(item)['expires_at'])
                    db.execute('UPDATE media_lifetimes SET expires_at=? WHERE article_id=? AND expires_at>?',(expiry,item.article_id,expiry))
                    if item.content_version==old_item.content_version:
                        db.execute('INSERT OR IGNORE INTO product_media_observations VALUES (?,?,?)',(item.article_id,identity,json.dumps(observation)))
                        db.commit();return old_item,False,False
                    origin['media_use']['expires_at']=expiry
                    from dataclasses import replace
                    item=replace(item,provenance=json.dumps(origin,ensure_ascii=False))
                db.execute('INSERT OR IGNORE INTO product_media_observations VALUES (?,?,?)',(item.article_id,identity,json.dumps(observation)))
            if getattr(self.store,'is_expiring_media',False):self.store.bind(db,item)
            fresh=not db.execute('SELECT 1 FROM local_news WHERE id=?',(item.article_id,)).fetchone()
            db.execute('INSERT OR IGNORE INTO local_news VALUES (?,?)',(item.article_id,json.dumps(asdict(item))))
            changed=db.execute('INSERT OR IGNORE INTO product_content VALUES (?,?,?,?)',
                (item.article_id,item.content_version,json.dumps(asdict(item)),now())).rowcount
            db.execute('INSERT OR REPLACE INTO product_current_content VALUES (?,?,?)',(item.article_id,item.content_version,now()))
            db.commit()
        return item,fresh,bool(changed)
    def state(self,item,status,reason='',*,download='saved'):
        other=self._route(item)
        if other:return other.state(item,status,reason,download=download)
        if getattr(self.store,'is_expiring_media',False):self.store.check(item)
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if getattr(self.store,'is_expiring_media',False):self.store.check(item,db)
            db.execute('INSERT OR REPLACE INTO product_record_state VALUES (?,?,?,?,?,?)',
                (item.article_id,item.content_version,download,status,reason,now()));db.commit()
    def states(self):
        with closing(self.store.connect()) as db:
            result={(r[0],r[1]):dict(download=r[2],analysis=r[3],reason=r[4],updated=r[5])
                    for r in db.execute('SELECT * FROM product_record_state')}
        other=self._partition()
        if other:result.update(other.states())
        return result
    def news(self):
        originals={n.article_id:n for n in self.store.list_news()}
        with closing(self.store.connect()) as db:
            edited={r[0] for r in db.execute('SELECT DISTINCT article_id FROM local_permission_history')}
            for (payload,) in db.execute('SELECT payload FROM product_content ORDER BY created,rowid'):
                item=decode(payload)
                # Permission history remains authoritative for already saved originals.
                from dataclasses import replace
                if item.article_id in edited and item.article_id in originals:item=replace(item,rights=originals[item.article_id].rights)
                originals[item.article_id]=item
            for (payload,) in db.execute('SELECT c.payload FROM product_current_content p JOIN product_content c ON c.article_id=p.article_id AND c.version=p.version'):
                item=decode(payload)
                if item.article_id in edited and item.article_id in originals:item=replace(item,rights=originals[item.article_id].rights)
                originals[item.article_id]=item
        other=self._partition()
        if other:
            from .media_use import enforce_decision,scope_of
            for item in other.news():
                try:
                    enforce_decision(self.store,scope_of(item))
                    try:enforce_decision(self.store,scope_of(item),('local_classification','local_sentiment'))
                    except ValueError:
                        from dataclasses import replace
                        item=replace(item,rights=replace(item.rights,analyze=False))
                    originals[item.article_id]=item
                except ValueError:pass
        if getattr(self.store,'is_expiring_media',False):
            from .media_use import authorize
            valid={}
            for key,item in originals.items():
                try:authorize(item,('retain','local_display'));valid[key]=item
                except ValueError:pass
            originals=valid
        return list(originals.values())
    def classification(self,item,key):
        other=self._route(item)
        if other:return other.classification(item,key)
        if getattr(self.store,'is_expiring_media',False):self.store.check(item)
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT payload FROM product_classifications WHERE article_id=? AND content_version=? AND cache_key=?',
                (item.article_id,item.content_version,key)).fetchone()
        return json.loads(row[0]) if row else None
    def save_classification(self,item,key,result):
        other=self._route(item,('local_classification',))
        if other:return other.save_classification(item,key,result)
        if getattr(self.store,'is_expiring_media',False):self.store.check(item)
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if getattr(self.store,'is_expiring_media',False):self.store.check(item,db)
            db.execute('INSERT OR IGNORE INTO product_classifications VALUES (?,?,?,?,?)',(item.article_id,item.content_version,key,json.dumps(result),now()));db.commit()
    def classifications(self,taxonomy,cache_key=None):
        result={}
        current={n.article_id:n.content_version for n in self.news()}
        with closing(self.store.connect()) as db:
            for article,version,payload,key in db.execute('SELECT article_id,content_version,payload,cache_key FROM product_classifications ORDER BY created,rowid'):
                data=json.loads(payload)
                if data['taxonomy']==taxonomy and current.get(article)==version and (cache_key is None or key==cache_key):result[article]=data
        other=self._partition()
        if other:
            key=cache_key
            if key is None and taxonomy=='US-BUSINESS-1':
                from .classification_scheme import selected,cache_key as scheme_key
                scheme=selected(self.store)
                if scheme:key=scheme_key(scheme)
            result.update({k:v for k,v in other.classifications(taxonomy,key).items() if k in current})
        return result
    def repair_classification(self,item,key,result,task_id):
        """Replace only a failed result; retain its complete finite history."""
        from .source_policies import authorize
        from uuid import uuid4
        authorize(item,('retain','local_display','local_classification'))
        other=self._route(item,('local_classification',))
        if other:return other.repair_classification(item,key,result,task_id)
        if not getattr(self.store,'is_expiring_media',False):raise ValueError('Classifier repairs require finite storage')
        if result.get('cache_key')!=key or result.get('content_version')!=item.content_version:
            raise ValueError('Classifier repair version mismatch')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE');self.store.check(item,db)
            row=db.execute('SELECT payload,created FROM product_classifications WHERE article_id=? AND content_version=? AND cache_key=?',
                           (item.article_id,item.content_version,key)).fetchone()
            if not row or json.loads(row[0]).get('status')!='failed':raise ValueError('Only a current failed classification can be repaired')
            previous=json.loads(row[0]);stamp=now()
            history=dict(content_version=item.content_version,classification=previous,created_utc=row[1],task_id=task_id,superseded=True)
            db.execute('INSERT INTO product_classification_reviews VALUES (?,?,?,?,?)',(uuid4().hex,item.article_id,key,stamp,json.dumps(history)))
            repaired={**result,'output_repair':dict(task_id=task_id,protocol='output-contract-1',previous_status='failed')}
            db.execute('UPDATE product_classifications SET payload=?,created=? WHERE article_id=? AND content_version=? AND cache_key=?',
                       (json.dumps(repaired),stamp,item.article_id,item.content_version,key));db.commit()
    def classification_history(self,article_id,taxonomy):
        with closing(self.store.connect()) as db:
            rows=db.execute('SELECT content_version,cache_key,created,payload FROM product_classifications WHERE article_id=? ORDER BY created,rowid',(article_id,)).fetchall()
        result=[{'content_version':v,'classifier_cache_key':k,'created_utc':t,'classification':json.loads(p)} for v,k,t,p in rows if json.loads(p)['taxonomy']==taxonomy]
        if getattr(self.store,'is_expiring_media',False):
            with closing(self.store.connect()) as db:
                for key,payload in db.execute('SELECT cache_key,payload FROM product_classification_reviews WHERE article_id=? ORDER BY created',(article_id,)):
                    review=json.loads(payload)
                    if review.get('classification',{}).get('taxonomy')==taxonomy:result.append({**review,'classifier_cache_key':key})
            result.sort(key=lambda r:r['created_utc'])
        other=self._partition()
        if other and article_id in {n.article_id for n in self.news()}:result+=other.classification_history(article_id,taxonomy)
        return result
    def cached(self,item,key):
        other=self._route(item)
        if other:return other.cached(item,key)
        if getattr(self.store,'is_expiring_media',False):self.store.check(item)
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT analysis_id FROM product_analysis_cache WHERE article_id=? AND content_version=? AND cache_key=?',
                (item.article_id,item.content_version,key)).fetchone()
        return row[0] if row else None
    def analysis(self,item,key,result):
        other=self._route(item,('local_sentiment',))
        if other:return other.analysis(item,key,result)
        if getattr(self.store,'is_expiring_media',False):self.store.check(item)
        # Commit the version and cache marker together: a restart cannot repeat a
        # successfully persisted inference after a separate cache-write crash.
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if getattr(self.store,'is_expiring_media',False):self.store.check(item,db)
            db.execute('INSERT INTO local_analyses VALUES (?,?,?,?)',(result.analysis_id,result.article_id,result.analyzed_at,json.dumps(asdict(result))))
            db.execute('INSERT OR REPLACE INTO product_analysis_cache VALUES (?,?,?,?)',(item.article_id,item.content_version,key,result.analysis_id));db.commit()
