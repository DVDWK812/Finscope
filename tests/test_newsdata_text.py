"""Authored adapter fixtures only; NewsData remains manually paused."""
from contextlib import closing
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib,json,os
import unittest
from unittest.mock import Mock

from finscope.api_sources import NewsDataTextAccess,normalize,build_request,fetch_provider,HTTPResponse
from finscope.local_news import LocalIngestionService,LocalNewsStore,ContentRights,NewsItem,FetchBlocked
from finscope.text_processing import prepare


NOW=datetime(2026,10,31,tzinfo=timezone.utc)
PAID=NewsDataTextAccess('paid',True,'Authored fixture subscription evidence','Authored fixture body permission')
RIGHTS=ContentRights(True,True,True,False,'Authored fixture local preview/storage/NLP')


def payload(content='The fictional company reported a new semiconductor chip design and higher revenue.'):
    return {'status':'success','results':[{'title':'The fictional semiconductor company grows',
        'description':'An authored short summary.', 'content':content,'link':'https://example.invalid/story',
        'source_name':'Fixture wire','pubDate':'2026-10-31 01:00:00'}]}


class NewsDataTextTests(unittest.TestCase):
    def test_unknown_free_and_paid_without_optin_keep_headline_summary_only(self):
        for access in (None,NewsDataTextAccess('free'),NewsDataTextAccess('paid')):
            item=normalize('newsdata',payload(),newsdata_text_access=access)[0][0]
            self.assertEqual(item.description,'An authored short summary.')
            self.assertEqual(item.body,'');self.assertEqual(item.body_permission_reference,'')
            params=build_request('newsdata','technology',NOW,2,3,'FAKE',newsdata_text_access=access)[1]
            self.assertNotIn('full_content',params)
    def test_paid_content_stays_separate_from_summary_with_evidence(self):
        item=normalize('newsdata',payload(),newsdata_text_access=PAID)[0][0]
        self.assertEqual(item.description,'An authored short summary.')
        self.assertEqual(item.body,payload()['results'][0]['content'])
        self.assertIn(PAID.plan_reference,item.body_permission_reference)
        self.assertIn(PAID.body_permission_reference,item.body_permission_reference)
        prepared,evidence=prepare(NewsItem.from_article(item,RIGHTS,now=NOW))
        self.assertEqual(evidence['analysis_basis'],'body');self.assertEqual(prepared.text_basis,'body')
        self.assertIn(PAID.body_permission_reference,prepared.provenance)
        self.assertFalse(prepared.rights.external)
    def test_optin_is_one_api_call_with_documented_availability_filter_no_page_fetch(self):
        transport=Mock(return_value=HTTPResponse(payload(),200,{}))
        result=fetch_provider('newsdata','technology',now=NOW,api_key='FAKE',
                              transport=transport,newsdata_text_access=PAID)
        self.assertEqual(result.status,'ok');transport.assert_called_once()
        url,params,_,_=transport.call_args.args
        self.assertEqual(url,'https://newsdata.io/api/1/latest');self.assertEqual(params['full_content'],1)
        self.assertNotIn(PAID.plan_reference,str(params));self.assertNotIn(PAID.body_permission_reference,str(params))
    def test_invalid_or_unverified_access_refused_before_transport(self):
        bad=[NewsDataTextAccess('free',True,'plan','permission'),NewsDataTextAccess('paid',True),
             replace(PAID,plan_reference=' '),replace(PAID,body_permission_reference=''),
             replace(PAID,include_body=1),{'plan':'paid'}]
        for access in bad:
            transport=Mock()
            with self.subTest(access=access),self.assertRaises(ValueError):
                fetch_provider('newsdata','technology',api_key='FAKE',transport=transport,newsdata_text_access=access)
            transport.assert_not_called()
        with self.assertRaises(ValueError):build_request('marketaux','technology',NOW,2,3,'FAKE',newsdata_text_access=PAID)
    def test_upgrade_placeholder_missing_or_malformed_content_is_never_body(self):
        for value in ('ONLY AVAILABLE IN PAID PLANS','only available in paid plans.',None,{},['bad'],'  '):
            item=normalize('newsdata',payload(value),newsdata_text_access=PAID)[0][0]
            self.assertEqual(item.body,'');self.assertEqual(item.body_permission_reference,'')
            self.assertEqual(prepare(NewsItem.from_article(item,RIGHTS))[1]['analysis_basis'],'summary')
    def test_newsdata_manual_pause_precedes_reservation_and_secret_resolution(self):
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);transport=Mock();resolve=Mock()
        service=LocalIngestionService(store,transport=transport)
        with self.assertRaises(FetchBlocked):service.fetch('newsdata','technology',credential_resolver=resolve,
            rights=RIGHTS,remaining=1,explicit=True,newsdata_text_access=PAID)
        transport.assert_not_called();resolve.assert_not_called()
        with closing(store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],0)
    def test_summary_record_identity_remains_compatible_with_existing_articles(self):
        article=normalize('newsdata',payload())[0][0]
        old=asdict(article);old.pop('body');old.pop('body_permission_reference')
        expected=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()[:32]
        self.assertEqual(NewsItem.from_article(article,RIGHTS).article_id,expected)
        with self.assertRaises(ValueError):NewsItem.from_article(replace(article,body='Unapproved body'),RIGHTS)
