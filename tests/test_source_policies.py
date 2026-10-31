"""Authored policy-boundary tests; no real provider or model calls."""
from contextlib import closing
from dataclasses import replace
import json,os,unittest
from uuid import uuid4
from unittest.mock import patch

from finscope.local_news import ContentRights,NewsItem,LocalNewsStore,Analysis
from finscope.local_worker import Worker
from finscope.task_queue import TaskQueue
from finscope.source_policies import authorize,PolicyBlocked
from finscope.settings_state import save,saved


def item():
    origin={'source_id':'abs_html','license':'CC BY 4.0','source_license_applied':True,
            'body_status':'extracted','body_byline':'Australian Bureau of Statistics'}
    return NewsItem('a'*32,'abs_html','The fictional food and beverages update','Australian Bureau of Statistics',
        'https://www.abs.gov.au/media-centre/media-releases/authored-fixture','',
        '', 'published','2026-10-31T00:00:00+00:00',(),ContentRights(True,True,True,False,'Authored licence fixture'),
        publication_date='2026-10-30',body='The fictional food and beverages industry reported a new result.',
        provenance=json.dumps(origin))


class SourcePolicyTests(unittest.TestCase):
    def test_abs_records_fields_purposes_retention_attribution_and_version(self):
        evidence=authorize(item(),('retain','local_classification','local_sentiment','local_display'))
        self.assertIn('body',evidence['fields']);self.assertEqual(evidence['policy']['version'],'2026-11-01')
        self.assertTrue(evidence['policy']['retention']);self.assertTrue(evidence['policy']['attribution'])
        self.assertTrue(evidence['policy']['adaptation_notice']);self.assertEqual(len(evidence['policy_sha256']),64)
    def test_unknown_source_and_external_processing_receive_no_policy_grant(self):
        for n,purposes in ((replace(item(),provider='marketaux'),('retain',)),(item(),('external_llm',))):
            with self.assertRaises(PolicyBlocked):authorize(n,purposes)
    def test_record_exclusions_origin_and_body_review_are_required(self):
        cases=[replace(item(),url='https://example.invalid/news'),replace(item(),provenance='[]'),
               replace(item(),provenance=json.dumps({'source_id':'abs_html','license':'CC BY 4.0','source_license_applied':False})),
               replace(item(),provenance=json.dumps({'source_id':'abs_html','license':'CC BY 4.0','source_license_applied':True}))]
        for n in cases:
            with self.subTest(n=n.article_id),self.assertRaises(PolicyBlocked):authorize(n,('local_sentiment',))
    def test_article_restrictions_outrank_source_policy(self):
        with self.assertRaises(ValueError):authorize(replace(item(),rights=replace(item().rights,analyze=False)),('local_sentiment',))
    def test_narrow_field_policy_cannot_silently_allow_body_processing(self):
        from finscope.source_policies import POLICIES,ABS
        with patch.dict(POLICIES,{'abs_html':replace(ABS,allowed_fields=('title','source','url','publication_date'))}):
            with self.assertRaises(PolicyBlocked):authorize(item(),('local_sentiment',))
    def test_saved_processing_does_not_change_api_draft_or_fetch_and_keeps_policy_evidence(self):
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);q=TaskQueue(store);store.save_news(item())
        draft=dict(sources=['marketaux'],model='Local LM Studio',model_id='',taxonomy='US-BUSINESS-1',limit=3,budgets={},source_permissions={})
        save(q,draft);before=saved(q)
        identity,created=q.submit_saved_local(item().article_id,confirmed=True)
        self.assertTrue(created);self.assertEqual(saved(q),before)
        self.assertEqual(q.get(identity)['snapshot']['sources'],[])
        checkpoint=q.step(identity,'fetch:saved_originals')[1][0]
        self.assertIn('automatic_use_policy',json.loads(checkpoint['provenance']))
        def no_fetch(*a):self.fail('A saved-original job must not collect news')
        def prediction(n,c):return Analysis(uuid4().hex,n.article_id,'Neutral','Mock only','test','mock','2026-10-31T01:00:00+00:00')
        Worker(store,fetch=no_fetch,infer=prediction,resources=lambda *a,**k:None).run_one()
        self.assertEqual(q.get(identity)['status'],'completed')
        self.assertIn('source_policy',store.list_analyses()[0].provenance)
        with closing(store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
    def test_confirmation_and_current_saved_permissions_are_checked_before_queueing(self):
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);q=TaskQueue(store);store.save_news(item())
        with self.assertRaises(ValueError):q.submit_saved_local(item().article_id)
        store.update_rights(item().article_id,replace(item().rights,analyze=False))
        with self.assertRaises(ValueError):q.submit_saved_local(item().article_id,confirmed=True)
        self.assertIsNone(q.get())
