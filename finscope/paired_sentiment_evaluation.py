"""Offline, isolated paired evaluation utilities. Never reads production databases.

No command here loads models or runs the annotation packet. Prediction acquisition
requires a later, separately authorized runner after references and rules are locked.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

LABELS = ('positive', 'neutral', 'negative')
EXCLUSIONS = {'mixed-uncertain', 'not-applicable', 'non-English', 'unknown-language',
              'empty', 'unavailable-rights', 'over-512-tokens'}
VERSION = 'paired-sentiment-v1'
LEXICON_SHA256 = 'e2d1328682bab7d2187684fb9f5420bb730401c9eefc00daf835edd203f4859d'


def preprocess(title, summary=''):
    """Experimental NFC/whitespace only; no HTML parsing, truncation or generation."""
    return '\n'.join(' '.join(unicodedata.normalize('NFC', s).split())
                     for s in (title, summary) if s.strip())


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_lexicon(path, expected_sha256=LEXICON_SHA256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Lexicon hash mismatch')
    rows = csv.DictReader(raw.decode('utf-8-sig').splitlines())
    if not {'Word', 'Positive', 'Negative'} <= set(rows.fieldnames or ()):
        raise ValueError('Lexicon schema mismatch')
    positive, negative = set(), set()
    for row in rows:
        word = row['Word'].lower()
        if float(row['Positive']) > 0:
            positive.add(word)
        if float(row['Negative']) > 0:
            negative.add(word)
    return positive, negative


def lexicon_predict(text, lexicon):
    tokens = re.findall(r'[a-z]+', text.lower())
    positive, negative = lexicon
    p = sum(t in positive for t in tokens)
    n = sum(t in negative for t in tokens)
    return {'label': 'positive' if p > n else 'negative' if n > p else 'neutral',
            'positive_occurrences': p, 'negative_occurrences': n,
            'matched': bool(p + n), 'score': (p - n) / (p + n) if p + n else 0.0,
            'input_sha256': digest(text)}


def metrics(truth, predictions):
    if len(truth) != len(predictions):
        raise ValueError('Unpaired inputs')
    matrix = [[0] * 3 for _ in LABELS]
    for ref, pred in zip(truth, predictions):
        matrix[LABELS.index(ref)][LABELS.index(pred)] += 1
    f1 = []
    for i in range(3):
        tp = matrix[i][i]
        denominator = sum(matrix[i]) + sum(row[i] for row in matrix)
        f1.append(2 * tp / denominator if denominator else 0.0)
    return {'n': len(truth), 'labels': LABELS, 'rows_reference_columns_prediction': matrix,
            'accuracy': sum(matrix[i][i] for i in range(3)) / len(truth) if truth else None,
            'macro_f1': sum(f1) / 3 if truth else None, 'per_class_f1': dict(zip(LABELS, f1))}


def predict_pair(records, lexicon, backend, *, authorized=False):
    """Explicit future/development execution with an already prepared pinned backend.

    Caller owns resource checks and backend lifetime. No automatic loading,
    downloads, DB, network or retries. Formal use additionally needs the protocol
    and human reference lock; this function is not an authorization mechanism.
    """
    if not authorized:
        raise ValueError('Separate prediction authorization required')
    finbert, dictionary, excluded, failures = {}, {}, [], []
    seen = set()
    for record in records:
        rid, text = record['id'], record['text']
        if rid in seen or digest(text) != record['input_sha256']:
            raise ValueError('Duplicate ID or input hash mismatch')
        seen.add(rid)
        reason = ('unavailable-rights' if not record.get('local_inference_allowed') else
                  'unknown-language' if record.get('language') != 'en' else
                  'empty' if not text.strip() else None)
        if reason:
            excluded.append({'id': rid, 'reason': reason}); continue
        try:
            # Local pinned tokenizer, before either method; never truncate.
            backend.tokenize([text])
        except Exception as error:
            if type(error).__name__ == 'TokenLimitExceeded':
                excluded.append({'id': rid, 'reason': 'over-512-tokens'})
            else:
                failures.append({'id': rid, 'method': 'shared-input-validation', 'error_type': type(error).__name__})
            continue
        dictionary[rid] = lexicon_predict(text, lexicon)
        try:
            scores = backend.predict([text])[0]
            if set(scores) != set(LABELS) or any(not isinstance(v, (int,float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()) or abs(sum(scores.values())-1) > .001:
                raise ValueError('Invalid model scores')
            # Fixed tie order for this experiment; not a production threshold change.
            label = max(LABELS, key=lambda key: scores[key])
            finbert[rid] = {'label': label, 'input_sha256': digest(text), 'scores': scores}
        except Exception as error:
            failures.append({'id': rid, 'method': 'finbert', 'error_type': type(error).__name__})
    return {'finbert': finbert, 'lexicon': dictionary, 'excluded': excluded, 'failures': failures}


def compare(records, references, finbert, lexicon):
    """Score already acquired predictions; fail closed on missing/foreign labels.

    Per-method coverage includes failed inference in the denominator. Primary
    metrics use the same intersection for both methods, not different subsets.
    """
    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)) or set(references) != set(ids):
        raise ValueError('Duplicate IDs or incomplete/foreign reference IDs')
    if any(set(method) - set(ids) for method in (finbert, lexicon)):
        raise ValueError('Foreign prediction IDs')
    excluded, failures, paired = [], [], []
    eligible = 0
    completed = {'finbert': 0, 'lexicon': 0}
    matched = 0
    for record in records:
        rid = record['id']; reference = references[rid]
        if reference in EXCLUSIONS:
            excluded.append({'id': rid, 'reason': reference}); continue
        if reference not in LABELS:
            raise ValueError('Blank/invalid human reference; do not infer labels')
        eligible += 1
        valid = True
        for name, method in (('finbert', finbert), ('lexicon', lexicon)):
            output = method.get(rid, {})
            reason = None
            if output.get('input_sha256') != record['input_sha256']:
                reason = 'missing-or-mismatched-input'
            elif output.get('label') not in LABELS:
                reason = 'invalid-label-or-inference-failure'
            if reason:
                failures.append({'id': rid, 'method': name, 'reason': reason}); valid = False
            else:
                completed[name] += 1
                if name == 'lexicon' and output.get('matched') is True:
                    matched += 1
        if valid:
            paired.append(rid)
    result = {'version': VERSION, 'total': len(ids), 'eligible': eligible,
              'paired': len(paired), 'excluded': excluded, 'failures': failures,
              'completed': completed,
              'coverage': {k: v / eligible if eligible else None for k, v in completed.items()},
              'lexicon_match_coverage': matched / eligible if eligible else None}
    for name, method in (('finbert', finbert), ('lexicon', lexicon)):
        result[name] = metrics([references[i] for i in paired], [method[i]['label'] for i in paired])
    return result


def main():
    parser = argparse.ArgumentParser(description='Score separately authorized, precomputed paired predictions; no inference')
    parser.add_argument('locked_bundle', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle = json.loads(args.locked_bundle.read_text(encoding='utf-8'))
    lock = bundle.get('lock', {})
    if not lock.get('separate_run_authorization') or not lock.get('reference_sha256') or not lock.get('rules_sha256'):
        raise ValueError('Locked references, rules and separate run authorization required')
    if digest(json.dumps(bundle['references'], sort_keys=True, ensure_ascii=False)) != lock['reference_sha256']:
        raise ValueError('Reference hash mismatch')
    if lock['rules_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError('Scoring rules hash mismatch')
    for record in bundle['records']:
        if digest(record['text']) != record['input_sha256']:
            raise ValueError('Input hash mismatch')
    result = compare(bundle['records'], bundle['references'], bundle['finbert'], bundle['lexicon'])
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)


if __name__ == '__main__':
    main()
