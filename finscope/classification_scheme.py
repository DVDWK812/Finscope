"""Independent local topic scheme, with metadata-only permanent configuration."""
from contextlib import closing
import hashlib,json,re
from .model_assets import manifest
from .taxonomy import load_taxonomy

VERSION='semantic-topics-5'
SETTING='media_classification_scheme'


def require_private_logging():
    from pathlib import Path
    path=Path.home()/'.lmstudio/.internal/http-server-config.json'
    try:settings=json.loads(path.read_text())
    except (OSError,ValueError):raise ValueError('Verify LM Studio content logging is disabled before finite-text inference') from None
    if settings.get('logSensitiveData') is not False or settings.get('logIncomingTokens') is not False:
        raise ValueError('Disable LM Studio prompt/response and incoming-token logging before finite-text inference; operational metadata logging can remain enabled')


def validate(value):
    if not isinstance(value,dict) or set(value)!={'version','model_key','model_id','model_revision','context_length'}:
        raise ValueError('Invalid independent classifier configuration')
    c=dict(value)
    if c['version']!=VERSION:raise ValueError('Unsupported classifier version')
    for k in ('model_key','model_id'):
        if not isinstance(c[k],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/@+-]{0,199}',c[k]):raise ValueError('Select a local classifier model ID')
    if not isinstance(c['model_revision'],str) or not 1<=len(c['model_revision'])<=600:raise ValueError('Record the local model variant')
    if type(c['context_length']) is not int or not 4096<=c['context_length']<=8192:raise ValueError('Local topic classifier needs 4096–8192 context tokens')
    return c


def cache_key(options,previous_version=None):
    from .semantic_classifier import INSTRUCTIONS,PROFILES_VERSION,REVIEW_INSTRUCTIONS
    c=validate(options)
    if previous_version:
        if previous_version not in ('semantic-topics-2','semantic-topics-3'):raise ValueError('Unknown preceding generation version')
        c={**c,'version':previous_version}
    payload=[c,load_taxonomy(),manifest('minilm')['revision'],INSTRUCTIONS,PROFILES_VERSION]
    if previous_version!='semantic-topics-2':payload.append(REVIEW_INSTRUCTIONS)
    if not previous_version:
        from .topic_grounding import VERSION as grounding_version
        payload.append(grounding_version)
    return 'US-BUSINESS-1|'+c['version']+'|'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def selected(store):
    with closing(store.connect()) as db:
        r=db.execute('SELECT payload FROM product_settings WHERE name=?',(SETTING,)).fetchone()
    return validate(json.loads(r[0])) if r else None


def model_revision(model):
    from .model_providers import lmstudio_revision
    config=model['instances'][0]['config'] if model.get('instances') else {}
    return lmstudio_revision(model)+' | load_config_sha256='+hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()


def configure(store,model_key):
    require_private_logging()
    from .model_providers import LMStudioProvider
    models=LMStudioProvider().inventory();m=models.get(model_key)
    if not m or not m['callable']:raise ValueError('Load the selected installed local classifier model first')
    c=validate(dict(version=VERSION,model_key=model_key,model_id=m['model_id'],model_revision=model_revision(m),context_length=m['context_length']))
    from .news_keys import NewsKeyRegistry
    NewsKeyRegistry(store).reject_secret_text(json.dumps(c))
    with closing(store.connect()) as db:
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(SETTING,json.dumps(c)));db.commit()
    return c


def run_reclassification(worker,task):
    """ID-only source-free task; sentiment code is never entered."""
    from .semantic_classifier import SemanticIndustryClassifier
    from .source_policies import authorize
    from .task_queue import Cancelled
    q=worker.queue;identity=task['id'];c=task['snapshot'];counts=task['counts'];data=worker.data
    def check():q.check_cancel(identity)
    q.update(identity,status='running',stage='reclassification: local saved text')
    failures=0;initial_calls=counts.get('classifier_calls',0)
    classifier=None
    try:
        classifier=SemanticIndustryClassifier(worker.store,c['classifier_options'],check=check)
        for n in data.news():
            if n.article_id not in c['article_ids']:continue
            check();authorize(n,('retain','local_display','local_classification'))
            old=data.classification(n,classifier.cache_key)
            if old:
                counts['skipped']+=1;failures+=old.get('status')=='failed';continue
            result=classifier.classify(n)
            data.save_classification(n,classifier.cache_key,result)
            counts['classified']+=1
            if result['status']=='failed':counts['failed']+=1;failures+=1
            counts['classifier_calls']=initial_calls+classifier.calls
            q.update(identity,counts=counts)
        q.save_step(identity,'phase:classification','ok',dict(article_ids=c['article_ids'],cache_key=classifier.cache_key))
        q.update(identity,status='partial_failed' if failures else 'completed',stage='classification finished; sentiment unchanged',counts=counts,
                 error='Some classifier results need review; no automatic retry' if failures else '')
    except Cancelled:q.update(identity,status='cancelled',stage='classification stopped',counts=counts)
    except Exception as error:
        counts['classifier_calls']=initial_calls+(classifier.calls if classifier else 0)
        from .semantic_classifier import ClassifierPrerequisite
        reason=str(error) if isinstance(error,ClassifierPrerequisite) else 'Local classification prerequisite or expiry changed; no source/sentiment dispatch'
        q.update(identity,status='blocked',stage='classification paused; text and sentiment retained',counts=counts,error=reason)
    return True
