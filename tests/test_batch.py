"""Authored fixtures only; real collection/model evidence is separate."""
from contextlib import closing
from dataclasses import replace,asdict
import json,os,unittest
from unittest.mock import patch
from uuid import uuid4
from finscope.local_news import LocalNewsStore,Analysis,ContentRights
from finscope.local_worker import Worker,ResourceBlocked
from finscope.task_queue import TaskQueue,Cancelled,validate_config
from finscope.product_storage import ProductStorage
from finscope.source_policies import SourcePolicy,FIELDS,PURPOSES,authorize,PolicyBlocked
from finscope.sec_sources import parse_submissions,extract_event,SECCollector,DEFAULT_OPTIONS,validate_user_agent,validate_options,permitted_url
from finscope.batch_records import read_import,eligibility,statistics,analysis_status
from finscope.text_processing import prepare
from tests.test_source_policies import item as fixture

C=dict(sources=['abs_html'],model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',limit=100)


def submissions(count=3):
    return json.dumps(dict(cik='789019',name='Fictional SEC fixture corporation',tickers=['FIX'],sic='1234',sicDescription='Fixture industry',
        filings={'recent':dict(accessionNumber=[f'0000789019-26-{i:06}' for i in range(count)],filingDate=['2026-10-30']*count,
            form=['8-K']*count,primaryDocument=[f'fixture{i}.htm' for i in range(count)],
            acceptanceDateTime=['2026-10-30T15:04:10Z']*count,items=['2.02']*count)})).encode()


def prediction(n,c):return Analysis(uuid4().hex,n.article_id,'Positive','Mock only',c['model'],'offline-fixture','2026-10-31T19:00:00+00:00')


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store);self.data=ProductStorage(self.store)
    def worker(self,fetch=None,infer=None,resources=None):
        return Worker(self.store,fetch=fetch or (lambda *a:[fixture()]),infer=infer or prediction,resources=resources or (lambda *a,**k:None))
    def test_store_only_does_not_probe_or_load_any_model(self):
        self.q.submit_batch('collect',C,confirmed=True)
        w=self.worker(infer=lambda *a:self.fail('No model'),resources=lambda *a,**k:self.fail('No model resources'))
        w.model_key=lambda *a:self.fail('No model inventory');w.run_one()
        self.assertEqual(self.q.get()['status'],'completed');self.assertEqual(len(self.data.news()),1)
        self.assertEqual(self.store.list_analyses(),[]);self.assertEqual(self.q.step(self.q.get()['id'],'phase:collection')[0],'ok')
    def test_storage_only_permission_does_not_require_nlp(self):
        n=replace(fixture(),rights=replace(fixture().rights,analyze=False))
        self.q.submit_batch('collect',C,confirmed=True);self.worker(fetch=lambda *a:[n]).run_one()
        self.assertEqual(len(self.data.news()),1);self.assertFalse(eligibility(self.data.news()[0])[0])
    def test_offline_repeated_run_uses_current_content_and_model_cache(self):
        self.q.submit_batch('collect',C,confirmed=True);self.worker().run_one();calls=[]
        w=self.worker(fetch=lambda *a:self.fail('No network'),infer=lambda *a:(calls.append(1) or prediction(*a)))
        for _ in range(2):self.q.submit_batch('analyze',C,confirmed=True);w.run_one()
        self.assertEqual(calls,[1]);self.assertEqual(len(self.store.list_analyses()),1)
        self.data.save(prepare(replace(fixture(),body=fixture().body+' The fictional company expanded food production.'))[0])
        self.q.submit_batch('analyze',C,confirmed=True);w.run_one();self.assertEqual(len(calls),2)
    def test_download_survives_model_unavailable_then_resume_without_fetch(self):
        calls=[]
        def low(*a,**k):raise ResourceBlocked('Authored low-resource condition')
        self.q.submit_batch('update',C,confirmed=True);w=self.worker(fetch=lambda *a:(calls.append(1) or [fixture()]),resources=low);w.run_one()
        self.assertEqual(len(self.data.news()),1);self.assertEqual(self.q.get()['status'],'blocked')
        self.q.resume(self.q.get()['id']);self.worker(fetch=lambda *a:self.fail('Completed download cannot replay')).run_one()
        self.assertEqual(calls,[1]);self.assertEqual(len(self.store.list_analyses()),1)
    def test_restart_completed_phases_and_inference_not_repeated(self):
        self.q.submit_batch('update',C,confirmed=True);w=self.worker();w.run_one();key=self.q.get()['id']
        self.q.update(key,status='running');self.q.interrupt_orphans();self.assertEqual(self.q.get()['status'],'queued')
        self.worker(fetch=lambda *a:self.fail('No repeated HTTP'),infer=lambda *a:self.fail('No repeated inference')).run_one()
        self.assertEqual(len(self.store.list_analyses()),1)
    def test_unreviewed_source_is_not_fetched_or_saved(self):
        self.q.submit_batch('collect',{**C,'sources':['marketaux']},confirmed=True)
        self.worker(fetch=lambda *a:self.fail('No API call')).run_one();self.assertEqual(self.data.news(),[])
    def test_revocation_blocks_previously_stored_text(self):
        n=self.data.save(prepare(fixture())[0])[0];self.store.update_rights(n.article_id,replace(n.rights,analyze=False))
        self.q.submit_batch('analyze',C,confirmed=True);self.worker(infer=lambda *a:self.fail('Revoked')).run_one()
        self.assertEqual(self.store.list_analyses(),[])
    def test_independent_publishers_not_event_merged_and_revisions_append(self):
        first=prepare(fixture())[0];self.data.save(first)
        revised=prepare(replace(first,body=first.body+' The outlook changed.'))[0];self.data.save(revised)
        self.assertEqual(len(self.data.news()),1)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_content').fetchone()[0],2)
        self.data.save(prepare(replace(first,source='Independent fixture publisher'))[0]);self.assertEqual(len(self.data.news()),2)
    def test_two_taxonomies_reuse_the_same_sentiment(self):
        self.q.submit_batch('update',C,confirmed=True);w=self.worker();w.run_one()
        self.q.submit_batch('analyze',{**C,'taxonomy':'CSRC-JRT0020-2024'},confirmed=True);w.run_one()
        self.assertEqual(len(self.store.list_analyses()),1)
        self.assertTrue(self.data.classifications('US-BUSINESS-1'));self.assertTrue(self.data.classifications('CSRC-JRT0020-2024'))
    def test_statistics_keep_disclosure_and_news_separate(self):
        n=prepare(fixture())[0];filing=prepare(parse_submissions(submissions(1),'0000789019',DEFAULT_OPTIONS)[0])[0]
        stats=statistics([n,filing],{}, {},{})
        disclosure=next(v for v in stats if v['source_type']=='regulatory_disclosure')
        self.assertEqual(disclosure['records'],1);self.assertEqual(disclosure['analyzable'],0)
        self.assertEqual(analysis_status(filing,None,{}),'Not applicable')
        stats=statistics([replace(n,provider='authored_synthetic')],{},{},{})
        self.assertEqual(next(v['records'] for v in stats if v['source_type']=='media_news'),0)
        self.assertEqual(next(v['records'] for v in stats if v['source_type']=='development'),1)
    def test_batch_limits_and_confirmation_are_bounded(self):
        for bad in ({'operation':'loop'},{'limit':301},{'sec_options':{'request_limit':100}}):
            with self.assertRaises(ValueError):validate_config({**C,'operation':'collect',**bad})
        with self.assertRaises(ValueError):self.q.submit_batch('collect',C)
    def test_failed_or_unknown_inference_not_silently_repeated_by_new_batch(self):
        self.q.submit_batch('update',C,confirmed=True)
        self.worker(infer=lambda *a:(_ for _ in ()).throw(ValueError('Authored failed model'))).run_one()
        self.q.submit_batch('analyze',C,confirmed=True)
        self.worker(infer=lambda *a:self.fail('No implicit retry')).run_one()
        self.assertEqual(self.store.list_analyses(),[]);self.assertEqual(self.q.get()['status'],'partial_failed')
    def test_index_refresh_preserves_reviewed_body_and_current_pointer_without_reinference(self):
        self.q.submit_batch('update',C,confirmed=True);self.worker().run_one()
        original=self.data.news()[0];snapshot=replace(original,body='',processed_text='',content_version='')
        self.q.submit_batch('update',C,confirmed=True)
        self.worker(fetch=lambda *a:[snapshot],infer=lambda *a:self.fail('No repeated unchanged-body inference')).run_one()
        self.assertEqual(self.data.news()[0].body,original.body);self.assertEqual(len(self.store.list_analyses()),1)
        # Selecting an already stored older/richer revision changes only the
        # pointer, never deletes or rewrites either original content revision.
        self.data.save(prepare(snapshot)[0]);self.assertFalse(self.data.news()[0].body)
        restored=prepare(self.data.merge_available_text(snapshot))[0];self.data.save(restored)
        self.assertEqual(self.data.news()[0].content_version,original.content_version)
        with closing(self.store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_content').fetchone()[0],2)
    def test_new_title_or_body_restriction_does_not_silently_reuse_old_body(self):
        original=self.data.save(prepare(fixture())[0])[0]
        changed=replace(original,title=original.title+' changed',body='')
        self.assertFalse(self.data.merge_available_text(changed).body)
        origin=json.loads(original.provenance);origin['body_reason']='Special-rights marker'
        self.assertFalse(self.data.merge_available_text(replace(original,body='',provenance=json.dumps(origin))).body)
    def test_offline_batch_prioritizes_new_content_beyond_first_300_cached_rows(self):
        items=[replace(fixture(),article_id=f'{i:032x}',content_version='version',language='en') for i in range(301)]
        with patch.object(ProductStorage,'news',return_value=items),patch.object(ProductStorage,'classification',side_effect=lambda n,k:None if n==items[-1] else {'labels':[]}),patch.object(ProductStorage,'cached',return_value='saved'):
            self.q.submit_batch('analyze',C,confirmed=True)
        ids=self.q.get()['snapshot']['article_ids'];self.assertEqual(len(ids),300)
        self.assertEqual(ids[0],items[-1].article_id)


class SECTests(unittest.TestCase):
    def setUp(self):
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store)
        self.key=self.q.submit_batch('collect',{**C,'sources':['sec_submissions']},confirmed=True)[0]
    def collector(self,get,**kwargs):
        with patch('finscope.sec_sources.user_agent',return_value='Authored offline contact identity'):
            return SECCollector(self.store,self.q,self.key,{**DEFAULT_OPTIONS,'ciks':['0000789019'],**kwargs},lambda:None,get=get,sleep=lambda _:None)
    def test_structured_identity_dates_issuer_and_metadata_eligibility(self):
        n=parse_submissions(submissions(),'0000789019',DEFAULT_OPTIONS)[0]
        self.assertEqual(n.record_id,'0000789019:0000789019-26-000000')
        self.assertEqual(n.timestamp,'');self.assertEqual(n.publication_date,'');self.assertEqual(n.filed_date,'2026-10-30')
        self.assertEqual(n.timestamp_kind,'filed');self.assertEqual(n.published_day,'2026-10-30')
        self.assertEqual(n.disclosed_at,'2026-10-30T15:04:10+00:00');self.assertFalse(eligibility(n)[0])
        authorize(n,('retain','local_classification'));self.assertEqual(n.issuer_industry['code'],'1234')
        from finscope.industry_classifier import IndustryClassifier
        result=IndustryClassifier().classify(prepare(n)[0]);self.assertEqual(result['labels'],[])
        self.assertEqual(result['issuer_reported_industry']['code'],'1234');self.assertTrue(result['entities'])
        bank=replace(n,title='Fictional Commercial Bank — 8-K',company='Fictional Commercial Bank',issuer_industry={'system':'SEC SIC','code':'6021'})
        self.assertEqual(IndustryClassifier().classify(prepare(bank)[0])['labels'],[])
    def test_accession_is_stable_when_primary_document_changes(self):
        n=parse_submissions(submissions(1),'0000789019',DEFAULT_OPTIONS)[0]
        before=prepare(n)[0];after=prepare(replace(n,url=n.url.replace('fixture0.htm','corrected.htm'),summary='Corrected factual metadata'))[0]
        self.assertEqual(before.article_id,after.article_id);self.assertNotEqual(before.content_version,after.content_version)
    def test_cik_column_mismatch_and_arbitrary_urls_rejected(self):
        with self.assertRaises(ValueError):parse_submissions(submissions(),'0000000001',DEFAULT_OPTIONS)
        for url in ('https://evil.invalid/news','https://www.sec.gov/Archives/edgar/data/1/../../x.htm','https://www.sec.gov@evil.invalid/news'):
            self.assertFalse(permitted_url(url))
    def test_large_valid_recent_history_selects_only_bounded_rows(self):
        rows=parse_submissions(submissions(10001),'0000789019',DEFAULT_OPTIONS)
        self.assertEqual(len(rows),20)
    def test_one_company_schema_failure_does_not_block_other_companies(self):
        calls=[]
        def get(url,headers):
            calls.append(url)
            if '0000019617' in url:return 200,b'{"unexpected":"authored schema fixture"}'
            return 200,submissions(1)
        collector=self.collector(get,ciks=['0000019617','0000789019'],document_limit=0)
        rows=collector.collect('sec_submissions',5)
        self.assertEqual(len(rows),1);self.assertEqual(len(calls),2);self.assertEqual(len(collector.failures),1)
    def test_contact_not_fabricated_and_conservative_limits(self):
        for value in ('','FinScope','FinScope your-email@example.com'):
            with self.assertRaises(ValueError):validate_user_agent(value)
        for options in ({'minimum_interval':.1},{'ciks':['1']},{'document_limit':100}):
            with self.assertRaises(ValueError):validate_options(options)
    def test_whole_periodic_filing_and_copyright_text_never_sentiment(self):
        for body,form in ((b'<p>authored fixture</p>','10-K'),(b'<p>Copyright all rights reserved</p>','8-K')):
            with self.assertRaises(ValueError):extract_event(body,form)
    def test_meaningful_current_report_span_has_document_coverage(self):
        text='<html><p>Cover page boilerplate.</p><p>Item 2.02 Results of Operations and Financial Condition. '+('The fictional company reported increased revenue and operating profit. '*10)+'</p><p>Item 9.01 Exhibits.</p></html>'
        body,evidence=extract_event(text.encode(),'8-K')
        self.assertTrue(body.startswith('Item 2.02'));self.assertTrue(evidence['sentiment_eligible'])
        self.assertNotIn('Cover page',body);self.assertLess(evidence['document_coverage'],1)
        procedural='<p>Item 2.02 Results of Operations and Financial Condition. '+('The registrant furnished a press release as Exhibit 99.1 which is incorporated herein by reference. '*5)+'</p><p>Item 9.01 Exhibits.</p>'
        with self.assertRaises(ValueError):extract_event(procedural.encode(),'8-K')
    def test_new_collection_reuses_existing_reviewed_filing_body(self):
        n=parse_submissions(submissions(1),'0000789019',DEFAULT_OPTIONS)[0]
        origin=json.loads(n.provenance);origin.update(body_status='event_excerpt',sentiment_eligible=True)
        n=prepare(replace(n,body='The fictional company announced a new acquisition agreement. '*10,provenance=json.dumps(origin)))[0]
        ProductStorage(self.store).save(n);calls=[]
        collector=self.collector(lambda url,headers:(calls.append(url) or (200,submissions(1))))
        rows=collector.collect('sec_submissions',1)
        self.assertEqual(len(calls),1);self.assertIn('/submissions/',calls[0]);self.assertEqual(rows[0].body,n.body)
    def test_per_url_cache_checkpoint_never_reissues_success(self):
        calls=[];collector=self.collector(lambda url,headers:(calls.append(url) or (200,submissions())))
        url='https://data.sec.gov/submissions/CIK0000789019.json'
        one=collector.request(url,lambda b:json.loads(b),'sec_submissions')
        two=collector.request(url,lambda b:self.fail('No new parsing or request'),'sec_submissions')
        self.assertEqual(one,two);self.assertEqual(len(calls),1)
    def test_403_holds_sec_but_does_not_call_other_endpoints(self):
        calls=[];collector=self.collector(lambda url,headers:(calls.append(url) or (403,b'denied')))
        for _ in range(2):
            with self.assertRaises(ValueError):collector.request('https://data.sec.gov/submissions/CIK0000789019.json',lambda b:[],'sec_submissions')
        self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):collector.request('https://data.sec.gov/submissions/CIK0000019617.json',lambda b:[],'sec_submissions')
        self.assertEqual(len(calls),1)
    def test_request_cap_checked_before_dispatch(self):
        calls=[];collector=self.collector(lambda url,headers:(calls.append(url) or (200,b'{}')),request_limit=1)
        collector.request('https://data.sec.gov/submissions/CIK0000789019.json',lambda b:{},'sec_submissions')
        with self.assertRaises(ValueError):collector.request('https://data.sec.gov/submissions/CIK0000019617.json',lambda b:{},'sec_submissions')
        self.assertEqual(len(calls),1)
    def test_unknown_http_dispatch_survives_worker_recovery_without_resend(self):
        import hashlib
        url='https://data.sec.gov/submissions/CIK0000789019.json'
        self.q.save_step(self.key,'sec_http:'+hashlib.sha256(url.encode()).hexdigest(),'pending',{})
        collector=self.collector(lambda *a:self.fail('Unknown HTTP must not repeat'))
        with self.assertRaises(ValueError):collector.request(url,lambda b:[],'sec_submissions')
    def test_unknown_transport_holds_other_urls_and_later_sec_tasks(self):
        calls=[]
        def failed(url,headers):calls.append(url);raise OSError('Authored transport outcome unknown')
        collector=self.collector(failed)
        with self.assertRaises(OSError):collector.request('https://data.sec.gov/submissions/CIK0000789019.json',lambda b:[],'sec_submissions')
        collector.task_id='another-explicit-task'
        with self.assertRaises(ValueError):collector.request('https://data.sec.gov/submissions/CIK0000019617.json',lambda b:[],'sec_submissions')
        self.assertEqual(len(calls),1)
    def test_post_response_archive_failure_is_not_treated_as_a_schema_retry(self):
        calls=[];collector=self.collector(lambda url,headers:(calls.append(url) or (200,b'{}')))
        def failed_archive(payload):raise OSError('Authored local persistence failure')
        with self.assertRaises(OSError):collector.request('https://data.sec.gov/submissions/CIK0000789019.json',failed_archive,'sec_submissions')
        with self.assertRaises(ValueError):collector.request('https://data.sec.gov/submissions/CIK0000019617.json',lambda b:[],'sec_submissions')
        self.assertEqual(len(calls),1)
    def test_archive_integrity_and_path_cannot_trigger_network_repair(self):
        collector=self.collector(lambda *a:(200,b'{}'));url='https://data.sec.gov/submissions/CIK0000789019.json'
        collector.request(url,lambda b:{},'sec_submissions')
        next(collector.archive.glob('*.json')).write_bytes(b'changed')
        with self.assertRaises(ValueError):collector.request(url,lambda b:self.fail('No repair'),'sec_submissions')


class ArchiveTests(unittest.TestCase):
    def test_only_linked_three_numbered_abs_pages_with_robots_and_no_bodies(self):
        from finscope.local_news import LocalIngestionService
        from finscope.public_sources import collect_source
        from pathlib import Path
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);root=store.path.parent
        service=LocalIngestionService(store,cooldown_path=root/'cooldowns.json',study_path=root/'study.sqlite3')
        calls=[]
        def get(url):
            calls.append(url)
            if url.endswith('robots.txt'):return b'User-agent: *\nAllow: /',200
            page=int(url.split('page=')[-1]) if 'page=' in url else 0
            text=f'<html lang="en"><div><time>30 October 2026</time><a href="/media-centre/media-releases/authored-{page}">The fictional employment release {page}</a></div><a href="?page={page+1}">Next</a><a href="https://evil.invalid/?page=2">No</a></html>'
            return text.encode(),200
        with patch('finscope.public_sources.time.sleep'):
            rows,report=collect_source(service,'abs_html',limit=100,explicit=True,get=get,archive_pages=3)
        self.assertEqual(len(rows),4);self.assertEqual(len(calls),5);self.assertEqual(report['http_request_budget'],5)
        self.assertTrue(all(not n.body for n in rows));self.assertFalse(any('page=4' in url or 'evil' in url for url in calls))
        with self.assertRaises(ValueError):collect_source(service,'abs_html',explicit=True,archive_pages=4)


class ImportTests(unittest.TestCase):
    def policy(self):return SourcePolicy('authored-fixture','1','local_import','Authored offline fixture permission','','2026-11-01',FIELDS,PURPOSES,'Indefinite for authored fixture','Authored fixture author','Independent test','No third-party text')
    def test_jsonl_csv_save_only_and_no_network_import(self):
        row=dict(title='The fictional company expands chip design',source='Authored fixture',url='https://example.invalid/fixture',summary='The company reported new revenue.')
        with patch('requests.sessions.Session.request',side_effect=AssertionError('Import cannot fetch')):
            items=read_import(json.dumps(row).encode(),'jsonl',self.policy())
            self.assertEqual(len(items),1);self.assertEqual(items[0].provider,'local_import')
            self.assertIn('not an API fetch',json.loads(items[0].provenance)['origin'])
            self.assertEqual(len(read_import(b'title,source,url\nAuthored,Fixture,https://example.invalid/csv\n','csv',self.policy())),1)
    def test_unsupported_fields_unlicensed_body_and_expiry_fail_closed(self):
        row=dict(title='Authored',source='Fixture',url='https://example.invalid/fixture',body='Not covered')
        with self.assertRaises(ValueError):read_import(json.dumps(row).encode(),'jsonl',replace(self.policy(),allowed_fields=('title','source','url')))
        with self.assertRaises(ValueError):read_import(json.dumps({**row,'api_key':'never'}).encode(),'jsonl',self.policy())
        with self.assertRaises(ValueError):read_import(json.dumps(row).encode(),'jsonl',replace(self.policy(),expires_at='2020-01-01T00:00:00Z'))
    def test_import_queue_is_durable_and_repeat_does_not_add_an_original(self):
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);q=TaskQueue(store)
        payload=b'{"title":"The authored company grows","source":"Authored fixture","url":"https://example.invalid/local","summary":"The company reported higher revenue."}'
        items=read_import(payload,'jsonl',self.policy())
        w=Worker(store,fetch=lambda *a:self.fail('Import cannot fetch'),infer=lambda *a:self.fail('Store-only cannot infer'),resources=lambda *a,**k:self.fail('No model resource probe'))
        for _ in range(2):q.submit_import(items,confirmed=True);w.run_one()
        self.assertEqual(len(store.list_news()),1);self.assertEqual(store.list_analyses(),[])


class BatchUITests(unittest.TestCase):
    def test_disclosures_use_record_kpis_and_remain_not_applicable_without_network(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);q=TaskQueue(store)
        q.configure({**C,'limit':3});store.set_setting('guide_completed',True)
        n=prepare(parse_submissions(submissions(1),'0000789019',DEFAULT_OPTIONS)[0])[0]
        ProductStorage(store).save(n)
        with patch('requests.sessions.Session.request',side_effect=AssertionError('Viewing a disclosure cannot fetch news or a model')) as http:
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'),default_timeout=20).run()
        self.assertFalse(app.exception);self.assertEqual(app.metric[0].label,'Original records')
        self.assertEqual(app.metric[0].value,'1');self.assertEqual(app.metric[1].value,'0')
        self.assertIsNone(q.get());http.assert_not_called()
    def test_mixed_library_kpis_do_not_inherit_only_the_chart_cohort_topics(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        from finscope.industry_classifier import IndustryClassifier
        store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);q=TaskQueue(store)
        q.configure({**C,'limit':3});store.set_setting('guide_completed',True)
        raw=parse_submissions(submissions(1),'0000789019',DEFAULT_OPTIONS)[0]
        origin=json.loads(raw.provenance);origin.update(body_status='event_excerpt',sentiment_eligible=True)
        filing=prepare(replace(raw,body='The fictional operator expanded oil storage and gas storage facilities.',provenance=json.dumps(origin)))[0]
        data=ProductStorage(store);classifier=IndustryClassifier()
        for n in (prepare(fixture())[0],filing):
            data.save(n);data.save_classification(n,classifier.cache_key,classifier.classify(n))
        with patch('requests.sessions.Session.request',side_effect=AssertionError('View only')):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'),default_timeout=20).run()
        self.assertFalse(app.exception);self.assertEqual(app.metric[0].value,'2')
        self.assertEqual(app.metric[2].value,'2');self.assertIsNone(q.get())


if __name__=='__main__':unittest.main()
