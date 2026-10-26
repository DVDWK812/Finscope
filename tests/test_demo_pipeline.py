from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from uuid import uuid4

from finscope.demo_pipeline import (ApprovedDemoRepository, ApprovedSubmission, DemoPipeline,
                                   classify_sectors, cosine)


class DemoPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=ApprovedDemoRepository(Path(self.temp.name)/"demo.sqlite3")
        self.sid=uuid4().hex
        self.now=datetime.now(timezone.utc)-timedelta(minutes=1)
        self.submission=ApprovedSubmission("Invented bank expands cloud software investment.","Synthetic bank update",
            "Authored fixture",self.now,"published","synthetic","Self-authored test fixture",True)
        class Encoder:
            revision="fixture-embedding-v1"
            def tokenize(self,texts):return {},[10 for _ in texts]
            def encode(self,texts):return [[1.,0.] for _ in texts]
        class Sentiment:
            def predict(self,records):return [SimpleNamespace(label="positive",positive=.8,negative=.1,neutral=.1,revision="fixture-finbert-v1")]
        self.pipeline=DemoPipeline(Sentiment(),Encoder())

    def test_multilabel_rules_evidence_boundaries_and_fallback(self):
        self.assertEqual(set(classify_sectors(self.submission.text)),{"Financials","Technology"})
        self.assertEqual(classify_sectors("A meeting occurred."),{"Unclassified":[]})
        self.assertEqual(classify_sectors("The discussion was about Vegas."),{"Unclassified":[]})
        self.assertIn("Technology",classify_sectors("A chipmaker grew profits."))

    def test_approval_metadata_limits_and_realistic_timestamp_semantics(self):
        from dataclasses import replace
        for record in (replace(self.submission,rights_confirmed=False),replace(self.submission,origin="marketaux"),
                       replace(self.submission,text=""),replace(self.submission,text="x"*2001),
                       replace(self.submission,timestamp=self.now.replace(tzinfo=None)),
                       replace(self.submission,timestamp=self.now+timedelta(days=1)),
                       replace(self.submission,url="javascript:bad")):
            with self.subTest(kind=record.origin),self.assertRaises(ValueError):record.validate()

    def test_pipeline_persists_actual_returned_scores_and_isolated_session(self):
        record=self.pipeline.submit(self.submission,self.repo,self.sid)
        self.assertEqual(record.article.sectors,("Technology","Financials"))
        self.assertEqual(record.article.sentiment,"Positive")
        self.assertEqual(record.scores["positive"],.8)
        self.assertIsNone(record.similarity)
        restarted=ApprovedDemoRepository(self.repo.path)
        self.assertEqual(restarted.list_records(self.sid)[0].article,record.article)
        self.assertEqual(restarted.list_records(uuid4().hex),[])
        with self.assertRaises(ValueError):restarted.list_records("bad workspace")

    def test_candidate_group_preserves_raw_records_without_asserting_identity(self):
        first=self.pipeline.submit(self.submission,self.repo,self.sid)
        second=self.pipeline.submit(self.submission,self.repo,self.sid)
        self.assertNotEqual(first.article.article_id,second.article.article_id)
        self.assertEqual(first.article.event_id,second.article.event_id)
        self.assertEqual(second.similarity,1.)
        self.assertEqual(len(self.repo.list_records(self.sid)),2)

    def test_time_window_and_model_revision_do_not_merge_incompatible_records(self):
        from dataclasses import replace
        first=self.pipeline.submit(self.submission,self.repo,self.sid)
        older=self.pipeline.submit(replace(self.submission,timestamp=self.now-timedelta(days=4)),self.repo,self.sid)
        self.assertNotEqual(first.article.event_id,older.article.event_id)
        self.pipeline.embedder.revision="new-fixture-revision"
        changed=self.pipeline.submit(self.submission,self.repo,self.sid)
        self.assertNotEqual(first.article.event_id,changed.article.event_id)

    def test_cosine_math_not_duplicate_ground_truth(self):
        self.assertAlmostEqual(cosine([1,0],[2,0]),1.)
        self.assertAlmostEqual(cosine([1,0],[0,1]),0.)
        with self.assertRaises(ValueError):cosine([0,0],[1,0])
        with self.assertRaises(ValueError):cosine([1,0],[1])


if __name__=="__main__":unittest.main()
