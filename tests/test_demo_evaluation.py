import unittest
from finscope.demo_evaluation import binary_metrics, sentiment_metrics, challenge_metrics


class EvaluationMetricTests(unittest.TestCase):
    def test_known_confusion_counts(self):
        result=sentiment_metrics(["positive","negative","neutral"],["positive","positive","neutral"])
        self.assertAlmostEqual(result["accuracy"],2/3)
        self.assertEqual(result["confusion_actual_rows"]["negative"]["positive"],1)
        self.assertAlmostEqual(result["macro_f1"],(2/3+0+1)/3)

    def test_binary_zero_denominators_and_false_pairs(self):
        self.assertEqual(binary_metrics([])["f1"],0)
        result=binary_metrics([(True,True),(True,False),(False,True),(False,False)])
        self.assertEqual([result[key] for key in ("tp","fp","fn","tn")],[1,1,1,1])
        self.assertEqual(result["f1"],.5)

    def test_invalid_or_unpaired_labels_rejected(self):
        for actual,predicted in (([],[]),(["positive"],[]),(["market-up"],["positive"])):
            with self.assertRaises(ValueError):sentiment_metrics(actual,predicted)


class ChallengeMetricTests(unittest.TestCase):
    """Invented IDs/labels only; no blind-case inference or expected answers."""

    def setUp(self):
        self.reference = {"records": [{"id":"X1", "label":"positive"},
                                      {"id":"X2", "label":"negative"},
                                      {"id":"X3", "label":"mixed/uncertain"}],
                          "pairs": [{"id":"Q1", "event_label":"same-event"},
                                    {"id":"Q2", "event_label":"different-event"},
                                    {"id":"Q3", "event_label":"uncertain"}]}
        self.outputs = [{"id":"X1", "predicted":"positive"},
                        {"id":"X2", "predicted":"neutral"},
                        {"id":"X3", "predicted":"positive"}]
        self.pairs = [{"id":"Q1", "similarity_candidate":True, "same_pipeline_group":True},
                      {"id":"Q2", "similarity_candidate":False, "same_pipeline_group":True},
                      {"id":"Q3", "similarity_candidate":True, "same_pipeline_group":True}]

    def test_uncertainty_coverage_and_selected_pairs_only(self):
        result = challenge_metrics(self.reference, self.outputs, self.pairs)
        self.assertEqual(result["sentiment"]["excluded_mixed_or_uncertain"], ["X3"])
        self.assertEqual(result["sentiment"]["scored_cases"], 2)
        self.assertAlmostEqual(result["sentiment"]["scored_fraction_of_all"], 2/3)
        self.assertEqual(result["sentiment"]["metrics"]["accuracy"], .5)
        self.assertEqual(result["excluded_uncertain_event_pairs"], ["Q3"])
        self.assertEqual(result["similarity_candidate"]["metrics"]["fp"], 0)
        self.assertEqual(result["same_pipeline_group"]["metrics"]["fp"], 1)
        self.assertEqual(result["same_pipeline_group"]["scored_pairs"], 2)

    def test_missing_duplicate_and_extra_ids_rejected(self):
        for outputs, pairs in ((self.outputs[:-1], self.pairs),
                               (self.outputs+[self.outputs[0]], self.pairs),
                               (self.outputs, self.pairs+[{"id":"unannotated"}])):
            with self.assertRaises(ValueError):
                challenge_metrics(self.reference, outputs, pairs)

    def test_errors_stay_visible_and_pair_metrics_can_be_unobserved(self):
        self.outputs[0] = {"id":"X1", "error":"inference_failed"}
        self.pairs[0].update(similarity_candidate=None, same_pipeline_group=None)
        result = challenge_metrics(self.reference, self.outputs, self.pairs)
        self.assertEqual(result["sentiment"]["failed_cases"], ["X1"])
        self.assertEqual(result["sentiment"]["scored_cases"], 1)
        self.assertEqual(result["similarity_candidate"]["unobserved_pairs"], ["Q1"])
        self.assertEqual(result["similarity_candidate"]["scored_pairs"], 1)

    def test_all_uncertain_has_no_score_instead_of_perfect_or_zero_accuracy(self):
        for row in self.reference["records"]:
            row["label"] = "mixed/uncertain"
        for row in self.reference["pairs"]:
            row["event_label"] = "uncertain"
        result = challenge_metrics(self.reference, self.outputs, self.pairs)
        self.assertIsNone(result["sentiment"]["metrics"])
        self.assertIsNone(result["same_pipeline_group"]["metrics"])

    def test_invalid_reference_or_ambiguous_output_rejected(self):
        self.outputs[0]["error"] = "failed_but_also_predicted"
        with self.assertRaises(ValueError):
            challenge_metrics(self.reference, self.outputs, self.pairs)
        self.outputs[0]["predicted"] = "invalid_but_also_error"
        with self.assertRaises(ValueError):
            challenge_metrics(self.reference, self.outputs, self.pairs)
        self.outputs[0]["predicted"] = "positive"
        del self.outputs[0]["error"]
        self.reference["records"][0]["label"] = "unresolved"
        with self.assertRaises(ValueError):
            challenge_metrics(self.reference, self.outputs, self.pairs)

    def test_pair_truthiness_is_not_silently_accepted(self):
        self.pairs[0]["same_pipeline_group"] = "False"
        with self.assertRaises(ValueError):
            challenge_metrics(self.reference, self.outputs, self.pairs)
