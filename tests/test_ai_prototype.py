from dataclasses import asdict
import json
import math
import unittest
from unittest.mock import Mock, patch

from finscope.ai_prototype import EvaluationText, EmbeddingSimilarity, FinBERTInterface
from finscope.api_sources import Article


def synthetic(text="Invented company reports a synthetic profit increase."):
    return EvaluationText(text, "synthetic")


class AIPrototypeTests(unittest.TestCase):
    def sentiment(self, rows):
        backend = Mock()
        backend.predict.return_value = rows
        return FinBERTInterface(backend, model_id="synthetic-sentiment-fixture", revision="fixture-v1"), backend

    def embedding(self, vectors):
        backend = Mock()
        backend.encode.return_value = vectors
        return EmbeddingSimilarity(backend, model_id="synthetic-vector-fixture", revision="fixture-v1"), backend

    def test_no_default_backend_download_network_or_heuristic_prediction(self):
        with patch("requests.get", side_effect=AssertionError("network forbidden")) as network:
            with self.assertRaises(RuntimeError):
                FinBERTInterface().predict([synthetic()])
            with self.assertRaises(RuntimeError):
                EmbeddingSimilarity().compare([synthetic(), synthetic()])
            network.assert_not_called()

    def test_provenance_rejects_api_records_raw_strings_and_unlicensed_text(self):
        inference, backend = self.sentiment([])
        api_record = Article("marketaux", "Synthetic API fixture", "https://example.org", "example.org",
                             "Synthetic description", "", "published")
        for record in (api_record, "untagged text"):
            with self.subTest(record=type(record)), self.assertRaises(ValueError):
                inference.predict([record])
        with self.assertRaises(ValueError):
            EvaluationText("Invented text", "news_api")
        with self.assertRaises(ValueError):
            EvaluationText("Invented text", "licensed")
        licensed = EvaluationText("Team-authored invented example.", "licensed",
                                  "Self-authored test fixture; permitted for this test")
        self.assertNotIn(licensed.text, repr(licensed))
        self.assertNotIn(licensed.license_reference, repr(licensed))
        backend.predict.assert_not_called()

    def test_batch_and_text_limits_reject_before_backend_without_truncation(self):
        inference, backend = self.sentiment([])
        for text in ("", "  ", "x" * 2001):
            with self.assertRaises(ValueError):
                synthetic(text)
        with self.assertRaises(ValueError):
            inference.predict([synthetic()] * 33)
        backend.predict.assert_not_called()

    def test_complete_label_probabilities_provenance_and_no_input_text_in_result(self):
        inference, backend = self.sentiment([{"negative": 0.1, "neutral": 0.2, "positive": 0.7}])
        record = synthetic()
        output = inference.predict([record])[0]
        self.assertEqual(output.label, "positive")
        self.assertEqual(output.positive, 0.7)
        self.assertEqual(output.model_id, "synthetic-sentiment-fixture")
        self.assertEqual(output.revision, "fixture-v1")
        self.assertEqual(output.origin, "synthetic")
        backend.predict.assert_called_once_with((record.text,))
        self.assertNotIn(record.text, json.dumps(asdict(output)))

    def test_invalid_probabilities_missing_unknown_labels_and_wrong_counts(self):
        cases = [[], [{"positive": 1.0}], [{"LABEL_0": 0.7, "negative": 0.1, "neutral": 0.2}],
                 [{"positive": math.nan, "negative": 0.1, "neutral": 0.2}],
                 [{"positive": math.inf, "negative": 0.1, "neutral": 0.2}],
                 [{"positive": 1.1, "negative": -0.2, "neutral": 0.1}],
                 [{"positive": 0.7, "negative": 0.7, "neutral": 0.7}],
                 [{"positive": True, "negative": 0.0, "neutral": 0.0}]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.sentiment(rows)[0].predict([synthetic()])

    def test_equal_scores_use_documented_neutral_tie_convention(self):
        inference, _ = self.sentiment([dict.fromkeys(("positive", "negative", "neutral"), 1/3)])
        self.assertEqual(inference.predict([synthetic()])[0].label, "neutral")

    def test_empty_batch_never_invokes_either_backend(self):
        sentiment, predict = self.sentiment([])
        embedding, encode = self.embedding([])
        self.assertEqual(sentiment.predict([]), ())
        self.assertEqual(embedding.compare([]), ())
        predict.predict.assert_not_called()
        encode.encode.assert_not_called()

    def test_synthetic_vectors_verify_cosine_not_semantic_accuracy(self):
        similarity, backend = self.embedding([[1, 0], [2, 0], [0, 1], [-1, 0]])
        inputs = [synthetic(f"Invented fixture {i}.") for i in range(4)]
        pairs = similarity.compare(inputs)
        scores = {(p.left_index, p.right_index): p.cosine_similarity for p in pairs}
        self.assertEqual(len(pairs), 6)
        self.assertAlmostEqual(scores[0, 1], 1)
        self.assertAlmostEqual(scores[0, 2], 0)
        self.assertAlmostEqual(scores[0, 3], -1)
        backend.encode.assert_called_once()
        self.assertNotIn(inputs[0].text, repr(pairs))

    def test_vectors_reject_zero_nan_infinity_wrong_dimensions_or_count(self):
        for vectors in ([], [[0, 0], [1, 0]], [[1], [1, 0]], [[math.nan], [1]],
                        [[math.inf], [1]], [[True], [1]], [[], []],
                        [[1] * 4097, [1] * 4097], [[1.7e308, 1.7e308], [1, 0]]):
            with self.subTest(kind=str(type(vectors))), self.assertRaises(ValueError):
                self.embedding(vectors)[0].compare([synthetic(), synthetic()])

    def test_numerically_stable_cosine_for_large_finite_vectors(self):
        similarity, _ = self.embedding([[1e200, 1e200], [1e200, 1e200]])
        self.assertAlmostEqual(similarity.compare([synthetic(), synthetic()])[0].cosine_similarity, 1)

    def test_backend_errors_never_echo_text_and_do_not_retry(self):
        sentiment, predict = self.sentiment([])
        embedding, encode = self.embedding([])
        predict.predict.side_effect = RuntimeError("PRIVATE_EVALUATION_TEXT")
        encode.encode.side_effect = RuntimeError("PRIVATE_EVALUATION_TEXT")
        for action in (sentiment.predict, embedding.compare):
            with self.assertRaises(RuntimeError) as caught:
                action([synthetic()])
            self.assertNotIn("PRIVATE_EVALUATION_TEXT", str(caught.exception))
        predict.predict.assert_called_once()
        encode.encode.assert_called_once()

    def test_configured_backends_require_model_identity_and_revision(self):
        for factory in (FinBERTInterface, EmbeddingSimilarity):
            with self.assertRaises(ValueError):
                factory(Mock())
            with self.assertRaises(ValueError):
                factory(Mock(), model_id="synthetic-fixture", revision=" ")
            with self.assertRaises(ValueError):
                factory(Mock(), model_id="synthetic-fixture", revision="main")


if __name__ == "__main__":
    unittest.main()
