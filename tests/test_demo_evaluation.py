import unittest
from finscope.demo_evaluation import binary_metrics, sentiment_metrics


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
