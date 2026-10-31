"""Allowlisted editable settings; incomplete drafts can never become worker jobs."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime,timezone
import json

DEFAULT={'sources':['nist_rss','abs_html'],'model':'Local FinBERT','model_id':'',
         'taxonomy':'US-BUSINESS-1','limit':6,'budgets':{},'source_permissions':{},'classifier_llm':False}


def saved(queue):
    with closing(queue.store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='pipeline_draft'").fetchone()
    return json.loads(row[0]) if row else None


def editable(queue):
    return deepcopy({**DEFAULT,**(saved(queue) or queue.config() or {})})


def issues(config):
    from .local_credentials import credential
    result=[]
    if not config['sources']:result.append('Select at least one news source.')
    if config['model']=='OpenAI API':result.append('External API is manual only; automatic updates require a local model.')
    elif config['model'] in ('Local LM Studio','Local Ollama') and not config.get('model_id'):
        result.append('Choose a local model ID before running.')
    today=datetime.now(timezone.utc).date().isoformat()
    for source in config['sources']:
        if source not in ('marketaux','newsdata','finnhub'):continue
        if not credential(source):result.append('Configure credentials for {source}.'.format(source=source))
        p=config.get('source_permissions',{}).get(source,{})
        if not all(p.get(k) for k in ('preview','retain','analyze','reference')):
            result.append('Confirm preview, storage and NLP permission for {source}.'.format(source=source))
        b=config.get('budgets',{}).get(source,{})
        if b.get('utc_day')!=today or not b.get('remaining'):
            result.append('Verify the current UTC-day request allowance for {source}.'.format(source=source))
        if source=='finnhub' and not b.get('symbol'):result.append('Choose the Finnhub ticker.')
    return result


def save(queue,config):
    from .task_queue import validate_config
    c=deepcopy(config)
    if not isinstance(c.get('sources'),list):raise ValueError('Select registered sources')
    if c.get('model') not in ('Local FinBERT','Local LM Studio','Local Ollama','OpenAI API'):
        raise ValueError('Unsupported settings model')
    # Validate the identical credential-free schema even for incomplete drafts.
    candidate={**c,'sources':c.get('sources') or ['abs_html'],'model':'Local FinBERT' if c['model']=='OpenAI API' else c['model']}
    validate_config(candidate)
    pending=issues(c)
    with closing(queue.store.connect()) as db:
        if pending:
            db.execute("INSERT OR REPLACE INTO product_settings VALUES ('pipeline_draft',?)",(json.dumps(c),))
        else:
            db.execute("INSERT OR REPLACE INTO product_settings VALUES ('pipeline',?)",(json.dumps(c),))
            db.execute("DELETE FROM product_settings WHERE name='pipeline_draft'")
        db.commit()
    return pending


def guard_submit(queue):
    draft=saved(queue)
    if draft is not None:raise ValueError('Saved settings are a draft. Complete and save them in Settings before starting a task.')
