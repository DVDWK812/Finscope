"""Isolated SEntFiN benchmark. No production DB, news provider or model downloads."""
import argparse
import ast
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time
import unicodedata

from .paired_sentiment_evaluation import preprocess, digest, load_lexicon, lexicon_predict, compare, LABELS

DATA_SHA = '570af7ba58f724f3fcc414dd5ba80da5b1a3b342134d76c6ebdf53a32c54a92f'
DATA_COMMIT = 'eba43610fe3cb57a3e5773cd6c037da1f8992ad5'
SEED = 20261105


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def select(rows, count=300):
    """Dataset is documented English; screen unsupported scripts, not financial tone.

    NFC/whitespace/casefold duplicates; remove *all* conflicting-label groups.
    Stable source order, earliest ID for concordant duplicates, fixed seeded sample.
    """
    groups = defaultdict(list); exclusions = []
    for row in rows:
        rid = row['S No.']
        try:
            labels = ast.literal_eval(row['Decisions'])
            if not isinstance(labels, dict): raise ValueError()
        except (ValueError, SyntaxError):
            exclusions.append({'id': rid, 'reason': 'invalid-annotation'}); continue
        if len(labels) != 1:
            exclusions.append({'id': rid, 'reason': 'not-single-entity'}); continue
        entity, label = next(iter(labels.items()))
        if label not in LABELS:
            exclusions.append({'id': rid, 'reason': 'invalid-label'}); continue
        text = preprocess(row['Title'])
        letters = [c for c in text if c.isalpha()]
        if not letters or any('LATIN' not in unicodedata.name(c, '') for c in letters):
            exclusions.append({'id': rid, 'reason': 'empty-or-non-Latin-script'}); continue
        groups[text.casefold()].append(dict(id=rid, text=text, original_title=row['Title'],
            entity=entity, original_label=label, input_sha256=digest(text), language='en',
            language_basis='English corpus provenance plus Latin script screen; not independent human language adjudication'))
    eligible = []
    for group in groups.values():
        if len({r['original_label'] for r in group}) > 1:
            exclusions.extend({'id': r['id'], 'reason': 'conflicting-duplicate-label'} for r in group)
        else:
            eligible.append(group[0])
            exclusions.extend({'id': r['id'], 'reason': 'concordant-duplicate'} for r in group[1:])
    selected = random.Random(SEED).sample(eligible, min(count, len(eligible)))
    return selected, {'input_rows': len(rows), 'eligible_unique': len(eligible),
        'excluded_rows': len(exclusions), 'exclusion_counts': dict(Counter(x['reason'] for x in exclusions)),
        'not_sampled': len(eligible)-len(selected), 'sample_count': len(selected),
        'class_distribution': dict(Counter(x['original_label'] for x in selected))}, exclusions


def prepare(directory):
    from .model_assets import manifest, verify
    p = Path(directory)
    if (p/'protocol.json').exists():
        raise ValueError('Packet already fixed; do not resample or overwrite')
    if sha(p/'SEntFiN.csv') != DATA_SHA: raise ValueError('Dataset hash mismatch')
    with (p/'SEntFiN.csv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    records, audit, exclusions = select(rows)
    verify('finbert')
    write(p/'sample.json', records); write(p/'selection_exclusions.json', exclusions)
    import finscope.paired_sentiment_evaluation as paired
    protocol = dict(fixed_at=stamp(), seed=SEED, dataset_commit=DATA_COMMIT,
        dataset_sha256=DATA_SHA, sample_sha256=sha(p/'sample.json'), selection=audit,
        preprocessing='NFC and whitespace only; title-only, no generated text or truncation',
        duplicate_rule='casefold of normalized title; all conflicting groups excluded',
        lexicon_rule='active flags >0, alphabetic lowercase occurrences; P>N positive, N>P negative, otherwise neutral; no negation',
        finbert_tie_order=list(LABELS), finbert_manifest=manifest('finbert'),
        code_sha256={Path(__file__).name:sha(__file__),Path(paired.__file__).name:sha(paired.__file__)},
        base_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        authorization='User explicitly authorized SEntFiN isolated real evaluation, 5 November 2026 Sydney')
    write(p/'protocol.json', protocol)
    print(json.dumps(audit), flush=True)


def run(directory, lexicon_path):
    import psutil
    from .finbert_process import ProcessFinBERT
    from .local_worker import resource_check
    from .model_assets import model_directory, verify
    p = Path(directory); protocol = json.loads((p/'protocol.json').read_text(encoding='utf-8'))
    import finscope.paired_sentiment_evaluation as paired
    for name, path in ((Path(__file__).name,__file__),(Path(paired.__file__).name,paired.__file__)):
        if sha(path) != protocol['code_sha256'][name]: raise ValueError('Frozen runner/rules changed')
    if sha(p/'sample.json') != protocol['sample_sha256'] or sha(p/'SEntFiN.csv') != DATA_SHA:
        raise ValueError('Frozen input changed')
    records = json.loads((p/'sample.json').read_text(encoding='utf-8'))
    lex = load_lexicon(lexicon_path); verify('finbert')
    log_path = p/'run.jsonl'
    def log(event, **fields):
        with log_path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(dict(at=stamp(),event=event,**fields))+'\n')
    resource_check('Local FinBERT',loading=True)
    # Metadata/tokenizer only in coordinator; actual weights owned by bounded child.
    import os
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(model_directory('finbert')),local_files_only=True,trust_remote_code=False)
    last_check=[0.0]
    def check():
        if time.monotonic()-last_check[0]>=5:
            resource_check('Local FinBERT');last_check[0]=time.monotonic()
    def observe(edge):
        mem=psutil.virtual_memory(); child=None
        if model.pid:
            try:child=psutil.Process(model.pid).memory_info()._asdict()
            except psutil.NoSuchProcess:pass
        log('resource',edge=edge,available_ram=mem.available,coordinator_rss=psutil.Process().memory_info().rss,child_pid=model.pid,child_memory=child)
    model=ProcessFinBERT(check=check,observe=observe)
    completed={}
    if (p/'outcomes.jsonl').exists():
        for line in (p/'outcomes.jsonl').read_text(encoding='utf-8').splitlines():
            row=json.loads(line);completed[row['id']]=row
    started=time.monotonic();log('start',already_recorded=len(completed));observe('before-stage')
    try:
        for record in records:
            rid=record['id']
            if rid in completed: continue
            check(); text=record['text']
            tokens=len(tokenizer(text,add_special_tokens=True,truncation=False)['input_ids'])
            row={'id':rid,'input_sha256':digest(text),'tokens':tokens}
            if tokens>512 or len(text)>2000:
                row['exclusion']='over-input-limit'
            else:
                row['lexicon']=lexicon_predict(text,lex)
                try:
                    scores=model.predict([text])[0]
                    row['finbert']={'label':max(LABELS,key=lambda k:scores[k]),'scores':scores,'input_sha256':digest(text)}
                except Exception as error:
                    row['failure']=type(error).__name__
            with (p/'outcomes.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
            completed[rid]=row
            if len(completed)%25==0: print(json.dumps({'completed':len(completed),'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
            if row.get('failure'):
                log('stopped-on-failure',id=rid,error_type=row['failure']);break
    finally:
        model.close();observe('after-stage')
        log('end',calls=model.calls,exit_verified=model.exit_verified,elapsed_seconds=time.monotonic()-started)
    summarize(p)


def summarize(directory):
    p=Path(directory);records=json.loads((p/'sample.json').read_text(encoding='utf-8'))
    outcomes={r['id']:r for r in map(json.loads,(p/'outcomes.jsonl').read_text(encoding='utf-8').splitlines())}
    refs={r['id']:r['original_label'] for r in records}
    for rid,o in outcomes.items():
        if o.get('exclusion'):refs[rid]='over-512-tokens'
    result=compare(records,refs,{k:v['finbert'] for k,v in outcomes.items() if 'finbert'in v},
                   {k:v['lexicon'] for k,v in outcomes.items() if 'lexicon'in v})
    result['selection']=json.loads((p/'protocol.json').read_text(encoding='utf-8'))['selection']
    result['dataset']='SEntFiN single-entity English headline sample';result['seed']=SEED
    result['recorded_outcomes']=len(outcomes)
    for method in ('finbert','lexicon'):
        m=result[method]['rows_reference_columns_prediction']; per_class={}
        for i,label in enumerate(LABELS):
            tp=m[i][i];support=sum(m[i]);predicted=sum(row[i] for row in m)
            per_class[label]={'support':support,'precision':tp/predicted if predicted else 0,
                'recall':tp/support if support else 0,'f1':result[method]['per_class_f1'][label]}
        result[method]['per_class']=per_class
    write(p/'metrics.json',result)
    with (p/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        columns=['id','entity','text','input_sha256','reference','finbert','lexicon','lexicon_matched','tokens','failure','exclusion']
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in records:
            o=outcomes.get(r['id'],{})
            writer.writerow(dict(id=r['id'],entity=r['entity'],text=r['text'],input_sha256=r['input_sha256'],reference=r['original_label'],
                finbert=o.get('finbert',{}).get('label',''),lexicon=o.get('lexicon',{}).get('label',''),lexicon_matched=o.get('lexicon',{}).get('matched',''),
                tokens=o.get('tokens',''),failure=o.get('failure','' if o else 'not-run'),exclusion=o.get('exclusion','')))
    print(json.dumps({k:result[k] for k in ('total','paired','coverage','failures','finbert','lexicon')}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run','summarize'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--lexicon',type=Path)
    parser.add_argument('--authorized-real-run',action='store_true')
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.directory)
    elif args.action=='summarize':summarize(args.directory)
    else:
        if not args.authorized_real_run or not args.lexicon:parser.error('Explicit real-run flag and existing lexicon required')
        run(args.directory,args.lexicon)


if __name__=='__main__':main()
