import hashlib
import tempfile
import unittest
from pathlib import Path

from finscope.paired_sentiment_evaluation import compare, digest, lexicon_predict, load_lexicon, metrics, preprocess, predict_pair


class PairedEvaluationTests(unittest.TestCase):
    def test_explicit_predict_same_text_and_failure(self):
        from unittest.mock import Mock
        backend = Mock()
        backend.predict.return_value = [{'positive': .7, 'neutral': .2, 'negative': .1}]
        text = 'Our authored firm reports profit.'
        row = dict(id='DEV-ONLY', text=text, input_sha256=digest(text), language='en', local_inference_allowed=True)
        with self.assertRaises(ValueError): predict_pair([row], ({'profit'}, set()), backend)
        backend.predict.assert_not_called()
        result = predict_pair([row], ({'profit'}, set()), backend, authorized=True)
        backend.tokenize.assert_called_once_with([text])
        backend.predict.assert_called_once_with([text])
        self.assertEqual(result['finbert']['DEV-ONLY']['input_sha256'], result['lexicon']['DEV-ONLY']['input_sha256'])
        backend.predict.side_effect = RuntimeError('development failure')
        result = predict_pair([row], ({'profit'}, set()), backend, authorized=True)
        self.assertEqual(result['finbert'], {})
        self.assertEqual(len(result['failures']), 1)

    # Newly authored development inputs. Never the annotation/frozen packets.
    def test_rules_and_no_match(self):
        lex = ({'profit'}, {'loss'})
        self.assertEqual(lexicon_predict('profit profit loss', lex)['label'], 'positive')
        self.assertEqual(lexicon_predict('profit loss', lex)['label'], 'neutral')
        self.assertFalse(lexicon_predict('meeting agenda', lex)['matched'])
        self.assertEqual(lexicon_predict('not profit', lex)['label'], 'positive')

    def test_hash_schema_and_removed_flags(self):
        raw = b'Word,Positive,Negative\nPROFIT,2009,0\nLOSS,0,2009\nOLD,-2020,0\n'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'words.csv'; p.write_bytes(raw)
            self.assertEqual(load_lexicon(p, hashlib.sha256(raw).hexdigest()), ({'profit'}, {'loss'}))
            with self.assertRaises(ValueError): load_lexicon(p)

    def test_paired_failures_and_exclusions(self):
        records = [{'id': str(i), 'input_sha256': digest(str(i))} for i in range(4)]
        refs = {'0': 'positive', '1': 'negative', '2': 'neutral', '3': 'mixed-uncertain'}
        predictions = {r['id']: {'label': refs[r['id']], 'input_sha256': r['input_sha256'], 'matched': True} for r in records}
        incomplete = dict(predictions); incomplete.pop('1')
        result = compare(records, refs, incomplete, predictions)
        self.assertEqual(result['paired'], 2)
        self.assertEqual(result['coverage']['finbert'], 2/3)
        self.assertEqual(result['finbert']['accuracy'], 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(len(result['excluded']), 1)
        bad = dict(refs); bad['0'] = ''
        with self.assertRaises(ValueError): compare(records, bad, incomplete, predictions)
        with self.assertRaises(ValueError): compare(records + records[:1], refs, incomplete, predictions)

    def test_known_confusion_and_zero_denominator(self):
        result = metrics(['positive', 'neutral', 'negative'], ['positive', 'negative', 'negative'])
        self.assertEqual(result['accuracy'], 2/3)
        self.assertAlmostEqual(result['macro_f1'], (1+0+2/3)/3)
        self.assertIsNone(metrics([], [])['accuracy'])
        self.assertEqual(preprocess('  Revenue\trose ', 'Costs\n fell'), 'Revenue rose\nCosts fell')


if __name__ == '__main__': unittest.main()
