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
    def save(self,item):
        item=self.apply_permissions(item)
        item.rights.require('retain');item.rights.require('analyze');item.rights.require('preview')
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            # Find a legacy original with the same publisher and normalized URL.
            from .text_processing import canonical_url
            for key,payload in db.execute('SELECT id,payload FROM local_news'):
                old=json.loads(payload)
                if item.url and old['source']==item.source and canonical_url(old['url'])==canonical_url(item.url):
                    from dataclasses import replace
                    item=replace(item,article_id=key);break
            fresh=not db.execute('SELECT 1 FROM local_news WHERE id=?',(item.article_id,)).fetchone()
            db.execute('INSERT OR IGNORE INTO local_news VALUES (?,?)',(item.article_id,json.dumps(asdict(item))))
            changed=db.execute('INSERT OR IGNORE INTO product_content VALUES (?,?,?,?)',
                (item.article_id,item.content_version,json.dumps(asdict(item)),now())).rowcount
            db.commit()
        return item,fresh,bool(changed)
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
        return list(originals.values())
    def classification(self,item,key):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT payload FROM product_classifications WHERE article_id=? AND content_version=? AND cache_key=?',
                (item.article_id,item.content_version,key)).fetchone()
        return json.loads(row[0]) if row else None
    def save_classification(self,item,key,result):
        with closing(self.store.connect()) as db:
            db.execute('INSERT OR IGNORE INTO product_classifications VALUES (?,?,?,?,?)',(item.article_id,item.content_version,key,json.dumps(result),now()));db.commit()
    def classifications(self,taxonomy):
        result={}
        current={n.article_id:n.content_version for n in self.news()}
        with closing(self.store.connect()) as db:
            for article,version,payload in db.execute('SELECT article_id,content_version,payload FROM product_classifications ORDER BY created,rowid'):
                data=json.loads(payload)
                if data['taxonomy']==taxonomy and current.get(article)==version:result[article]=data
        return result
    def classification_history(self,article_id,taxonomy):
        with closing(self.store.connect()) as db:
            rows=db.execute('SELECT content_version,cache_key,created,payload FROM product_classifications WHERE article_id=? ORDER BY created,rowid',(article_id,)).fetchall()
        return [{'content_version':v,'classifier_cache_key':k,'created_utc':t,'classification':json.loads(p)} for v,k,t,p in rows if json.loads(p)['taxonomy']==taxonomy]
    def cached(self,item,key):
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT analysis_id FROM product_analysis_cache WHERE article_id=? AND content_version=? AND cache_key=?',
                (item.article_id,item.content_version,key)).fetchone()
        return row[0] if row else None
    def analysis(self,item,key,result):
        # Commit the version and cache marker together: a restart cannot repeat a
        # successfully persisted inference after a separate cache-write crash.
        with closing(self.store.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO local_analyses VALUES (?,?,?,?)',(result.analysis_id,result.article_id,result.analyzed_at,json.dumps(asdict(result))))
            db.execute('INSERT OR REPLACE INTO product_analysis_cache VALUES (?,?,?,?)',(item.article_id,item.content_version,key,result.analysis_id));db.commit()
