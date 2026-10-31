from contextlib import closing
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import concurrent.futures
import json
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from finscope.model_providers import DeepSeekProvider,ModelError,DEEPSEEK_ORIGIN,model_request
from finscope.external_tests import DeepSeekLedger,authored_samples,run_authored_test,SCOPE
from finscope.local_news import LocalNewsStore,Analysis
from finscope.task_queue import TaskQueue
from finscope.local_analytics import result_models,model_key
from test_product_pipeline import C,fixture

KEY='DEEPSEEK-UNIT-ONLY-KEY'
MODEL='actual/model-id'
APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'


class Transport:
    def __init__(self):self.calls=[];self.reply=None
    def __call__(self,method,url,payload,headers,timeout):
        self.calls.append((method,url,deepcopy(payload),headers,timeout))
        if method=='GET':return {'data':[{'id':MODEL},{'id':'other-model'}]}
        return deepcopy(self.reply) if self.reply is not None else {'model':'actual/response-id','choices':[{'finish_reason':'stop','message':{
            'content':json.dumps({'sentiment':'Positive','rationale':'The fictional text describes its reported financial results.'})}}],
            'usage':{'prompt_tokens':72,'completion_tokens':22,'total_tokens':94,'prompt_cache_hit_tokens':0},'system_fingerprint':'provider-fingerprint'}


class DeepSeekTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'news.sqlite3');self.q=TaskQueue(self.store);self.q.configure(C)
        self.http=Transport();self.provider=DeepSeekProvider(self.http);self.item=authored_samples()[0]
        self.guard=patch('requests.sessions.Session.request',side_effect=AssertionError('Offline test attempted real HTTP'))
        self.guard.start();self.addCleanup(self.guard.stop)
        vault=patch('finscope.local_credentials.vault_key',return_value='');vault.start();self.addCleanup(vault.stop)
    def connect(self):return self.provider.models(self.store,api_key=KEY,explicit=True)
    def analyze(self,**kwargs):return self.provider.analyze(self.item,self.store,**{'api_key':KEY,'model':MODEL,'consent':True,**kwargs})
    def test_connection_is_explicit_get_only_and_cached_without_sending_text(self):
        with self.assertRaises(ModelError):self.provider.models(self.store,api_key=KEY)
        self.assertEqual(self.http.calls,[])
        self.assertEqual([m['id'] for m in self.connect()],[MODEL,'other-model']);self.connect()
        self.assertEqual(len(self.http.calls),1)
        self.assertEqual(self.http.calls[0][0:3],('GET',DEEPSEEK_ORIGIN+'/models',None))
        self.assertEqual(DeepSeekLedger(self.store).rows()[0]['status'],'ok')
    def test_json_object_payload_has_no_openai_schema_store_tools_or_reasoning_fields(self):
        self.connect();a=self.analyze();call=self.http.calls[-1];payload=call[2]
        self.assertEqual(call[1],DEEPSEEK_ORIGIN+'/chat/completions')
        self.assertEqual(set(payload),{'model','messages','thinking','response_format','max_tokens','stream'})
        self.assertEqual(payload['thinking'],{'type':'disabled'});self.assertEqual(payload['response_format'],{'type':'json_object'})
        self.assertIn('JSON',payload['messages'][0]['content']);self.assertEqual(payload['max_tokens'],512)
        self.assertEqual(a.family,'DeepSeek API');self.assertEqual(a.model_id,'actual/response-id');self.assertEqual(a.revision,'')
        self.assertEqual(a.provenance['requested_model'],MODEL);self.assertEqual(a.provenance['response_model'],'actual/response-id')
        self.assertEqual(a.provenance['usage']['total_tokens'],94);self.assertFalse(a.provenance['fixed_weight_version_verified'])
        self.assertEqual(a.provenance['text_version'],self.item.content_version);self.assertIsNone(a.probabilities)
    def test_same_article_cache_preserves_other_models_and_no_duplicate_requests(self):
        self.connect();a=self.analyze();again=self.analyze()
        other=replace(a,analysis_id='existing-finbert',family='FinBERT',model_id='pinned',revision='frozen-local',label='Neutral')
        self.store.save_analysis(other)
        self.assertEqual(a.analysis_id,again.analysis_id);self.assertEqual(len(self.http.calls),2)
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.store.list_analyses()),2)
        self.assertEqual(len(result_models(self.store.list_analyses())),2)
    def test_missing_key_consent_model_list_or_non_authored_inputs_dispatch_nothing(self):
        for options in ({'api_key':None},{'consent':False},{'budget':4},{'model':'invented'}):
            with self.assertRaises(ModelError):self.analyze(**options)
        self.assertEqual(self.http.calls,[])
        self.connect();before=len(self.http.calls)
        for bad in (fixture(),replace(self.item,summary='Changed text'),replace(self.item,provider='marketaux'),replace(self.item,url='https://example.test')):
            with self.assertRaises(ModelError):self.provider.analyze(bad,self.store,api_key=KEY,model=MODEL,consent=True)
        self.assertEqual(len(self.http.calls),before)
    def test_http_200_empty_invalid_truncated_and_extra_fields_never_save_valid_results(self):
        contents=['',None,'{}','{"sentiment":"Mixed","rationale":"x"}','{"sentiment":"Neutral","rationale":""}',
                  '{"sentiment":"Positive","rationale":"x","confidence":0.9}',
                  '{"sentiment":"Positive","sentiment":"Negative","rationale":"x"}','```json\n{}\n```']
        for index,content in enumerate(contents):
            with self.subTest(content=content):
                store=LocalNewsStore(Path(self.temp.name)/(str(index)+'.sqlite3'))
                self.provider.models(store,api_key=KEY,explicit=True)
                reply=Transport()('POST','',{}, {},45);reply['choices'][0]['message']['content']=content;self.http.reply=reply
                with self.assertRaises(ModelError):self.provider.analyze(self.item,store,api_key=KEY,model=MODEL,consent=True)
                self.assertEqual(store.list_analyses(),[]);self.assertEqual(DeepSeekLedger(store).rows()[-1]['status'],'invalid')
                self.http.reply=None
        for field,value in (('finish_reason','length'),('finish_reason','tool_calls')):
            store=LocalNewsStore(Path(self.temp.name)/(value+'.sqlite3'));self.provider.models(store,api_key=KEY,explicit=True)
            self.http.reply=Transport()('POST','',{}, {},45);self.http.reply['choices'][0][field]=value
            with self.assertRaises(ModelError):self.provider.analyze(self.item,store,api_key=KEY,model=MODEL,consent=True)
            self.assertEqual(store.list_analyses(),[])
    def test_http_errors_are_classified_stop_batch_and_preserve_independent_ledgers(self):
        for status,kind in ((401,'authentication'),(402,'insufficient_balance'),(429,'rate_limit'),(500,'provider_error'),(502,'provider_error'),(503,'provider_error'),(504,'provider_error')):
            with self.subTest(status=status):
                store=LocalNewsStore(Path(self.temp.name)/(str(status)+'.sqlite3'))
                calls=[]
                def fail(*args):calls.append(args);raise ModelError(KEY,status=status,retry_after='60' if status==429 else None,kind='http_error')
                provider=DeepSeekProvider(fail)
                with self.assertRaises(ModelError) as caught:provider.models(store,api_key=KEY,explicit=True)
                self.assertEqual(caught.exception.kind,kind);self.assertNotIn(KEY,str(caught.exception))
                with self.assertRaises(ModelError):provider.models(store,api_key=KEY,explicit=True)
                self.assertEqual(len(calls),1);row=DeepSeekLedger(store).rows()[0];self.assertEqual(row['http_status'],status)
                if status==429:self.assertTrue(row['hold_until'])
                with closing(store.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM local_model_requests').fetchone()[0],0)
    def test_timeout_unknown_and_unexpected_exceptions_block_without_echo_or_retry(self):
        for number,error in enumerate((ModelError(KEY,kind='timeout'),RuntimeError(KEY))):
            store=LocalNewsStore(Path(self.temp.name)/('unknown'+str(number)+'.sqlite3'))
            calls=[]
            def fail(*args):calls.append(args);raise error
            provider=DeepSeekProvider(fail)
            with self.assertRaises(ModelError) as caught:provider.models(store,api_key=KEY,explicit=True)
            self.assertNotIn(KEY,str(caught.exception));self.assertEqual(DeepSeekLedger(store).rows()[0]['status'],'unknown')
            with self.assertRaises(ModelError):provider.models(store,api_key=KEY,explicit=True)
            self.assertEqual(len(calls),1)
    def test_serial_three_sample_cap_and_repeated_action_are_cached(self):
        self.connect();results=run_authored_test(self.store,self.provider,api_key=KEY,model=MODEL,confirmed=True,budget=3)
        self.assertEqual(len(results),3);self.assertEqual(len(self.http.calls),4)
        run_authored_test(self.store,self.provider,api_key=KEY,model=MODEL,confirmed=True,budget=3)
        self.assertEqual(len(self.http.calls),4);self.assertTrue(all(n.provider=='authored_synthetic' for n in self.store.list_news()))
        self.assertEqual(len(DeepSeekLedger(self.store).rows()),4)
        self.assertIsNone(self.q.get());self.assertEqual(self.q.config(),C)
    def test_batch_stops_at_first_inference_failure_and_never_sends_real_news(self):
        self.store.save_news(fixture());self.connect();calls=[]
        def fail(method,url,payload,headers,timeout):calls.append(payload);raise ModelError('balance',status=402)
        self.provider.transport=fail
        with self.assertRaises(ModelError):run_authored_test(self.store,self.provider,api_key=KEY,model=MODEL,confirmed=True,budget=3)
        self.assertEqual(len(calls),1);self.assertNotIn(fixture().analysis_text,json.dumps(calls))
        self.assertEqual(self.store.list_analyses(),[])
    def test_provider_key_echo_is_rejected_before_cache_history_and_diagnostics(self):
        self.connect();self.http.reply=Transport()('POST','',{}, {},45)
        self.http.reply['choices'][0]['message']['content']=json.dumps({'sentiment':'Positive','rationale':KEY})
        with self.assertRaises(ModelError) as caught:self.analyze()
        self.assertNotIn(KEY,str(caught.exception));self.assertEqual(self.store.list_analyses(),[])
        self.assertNotIn(KEY,json.dumps(self.store.export()));self.assertNotIn(KEY,json.dumps(DeepSeekLedger(self.store).rows()))
        self.assertNotIn(KEY.encode(),self.store.path.read_bytes())
    def test_other_provider_unknown_holds_are_untouched_and_do_not_share_deepseek_namespace(self):
        with closing(self.store.connect()) as db:
            db.execute("INSERT INTO local_model_requests(id,backend,reserved_at,status) VALUES ('other','openai','2026-10-01','pending')");db.commit()
        self.connect();self.analyze()
        with closing(self.store.connect()) as db:self.assertEqual(db.execute("SELECT status FROM local_model_requests WHERE id='other'").fetchone()[0],'pending')
    def test_simultaneous_reservations_consume_one_slot(self):
        ledger=DeepSeekLedger(self.store)
        def reserve(_):
            try:return ledger.reserve('models','catalog')
            except ModelError:return None
        with concurrent.futures.ThreadPoolExecutor(4) as pool:results=list(pool.map(reserve,range(8)))
        self.assertEqual(sum(r is not None for r in results),1);self.assertEqual(len(ledger.rows()),1)
    def test_credentials_use_only_their_provider_environment_or_vault(self):
        from finscope.local_credentials import credential
        with patch('finscope.api_sources.local_credentials',return_value={'DEEPSEEK_API_KEY':'deepseek-only','OPENAI_API_KEY':'openai-only'}):
            self.assertEqual(credential('deepseek'),'deepseek-only');self.assertEqual(credential('openai'),'openai-only')
            self.assertEqual(credential('marketaux'),'')
        with self.assertRaises(ValueError):credential('unsupported')
        with patch('requests.sessions.Session.request') as request:
            for url in ('https://deepseek.invalid/chat/completions','https://api.deepseek.com/other','http://api.deepseek.com/models'):
                with self.assertRaises(ModelError):model_request('GET',url)
            request.assert_not_called()
    def test_empty_model_list_is_not_filled_with_assumed_model_ids(self):
        provider=DeepSeekProvider(lambda *a:{'data':[]})
        self.assertEqual(provider.models(self.store,api_key=KEY,explicit=True),[])
        with self.assertRaises(ModelError):provider.analyze(self.item,self.store,api_key=KEY,model=MODEL,consent=True)
        self.assertEqual(self.store.list_analyses(),[])
        self.assertEqual(len(DeepSeekLedger(self.store).rows()),1)


class DeepSeekUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/'news.sqlite3');TaskQueue(self.store).configure(C)
        self.store.set_setting('guide_completed',True);self.http=Transport();self.configured=False
        transport=self.http
        class UIProvider(DeepSeekProvider):
            def __init__(self):super().__init__(transport)
        for guard in (patch.dict('os.environ',{'FINSCOPE_LOCAL_DB':str(self.store.path)}),
                      patch('requests.sessions.Session.request',side_effect=AssertionError('No real UI HTTP')),
                      patch('finscope.local_credentials.vault_key',return_value=''),
                      patch('finscope.local_credentials.credential',side_effect=lambda p:KEY if self.configured and p=='deepseek' else ''),
                      patch('finscope.external_ui.DeepSeekProvider',UIProvider)):
            guard.start();self.addCleanup(guard.stop)
    def app(self):
        app=AppTest.from_file(str(APP),default_timeout=20);app.session_state['product_page']='Settings';app.run()
        app.selectbox(key='pipeline_model').set_value('External API').run();app.selectbox(key='external_provider').set_value('deepseek').run()
        self.assertFalse(app.exception);return app
    def test_waiting_for_key_is_explicit_and_all_external_actions_disabled(self):
        app=self.app();self.assertTrue(any('Waiting for a locally configured DeepSeek key' in i.value for i in app.info))
        self.assertTrue(app.button(key='deepseek_connect').disabled);self.assertTrue(app.button(key='deepseek_run').disabled)
        app.run();self.assertEqual(self.http.calls,[]);self.assertEqual(self.store.list_news(),[])
        self.assertEqual(TaskQueue(self.store).config(),C)
    def test_explicit_get_then_three_authored_inferences_history_and_refresh_no_replay(self):
        self.configured=True;app=self.app()
        app.button(key='deepseek_connect').click().run();self.assertEqual(len(self.http.calls),1)
        app.selectbox(key='settings_deepseek_model').set_value(MODEL).run()
        app.checkbox(key='deepseek_test_consent').check().run();app.button(key='deepseek_run').click().run()
        self.assertFalse(app.exception);self.assertEqual(len(self.http.calls),4)
        self.assertFalse(app.checkbox(key='deepseek_test_consent').value)
        self.assertEqual(len(app.selectbox(key='deepseek_history').options),3)
        app.run();self.assertEqual(len(self.http.calls),4)
        self.assertEqual(TaskQueue(self.store).config(),C);self.assertIsNone(TaskQueue(self.store).get())
        app.radio(key='product_page').set_value('Dashboard').run();self.assertEqual(app.metric[0].value,'0')
    def test_changing_model_after_confirmation_requires_new_confirmation(self):
        self.configured=True;app=self.app();app.button(key='deepseek_connect').click().run()
        app.selectbox(key='settings_deepseek_model').set_value(MODEL).run();app.checkbox(key='deepseek_test_consent').check().run()
        app.selectbox(key='settings_deepseek_model').set_value('other-model').run()
        self.assertTrue(app.button(key='deepseek_run').disabled)
        self.assertEqual(len(self.http.calls),1);self.assertEqual(self.store.list_analyses(),[])
        self.assertFalse(app.checkbox(key='deepseek_test_consent').value)
    def test_key_save_is_not_send_consent_and_clears_the_password_widget(self):
        self.configured=True;app=self.app();app.button(key='deepseek_connect').click().run()
        app.selectbox(key='settings_deepseek_model').set_value(MODEL).run();app.checkbox(key='deepseek_test_consent').check().run()
        app.button(key='settings_secret_deepseek_edit').click().run()
        app.text_input(key='settings_secret_deepseek').set_value('NEW-UNIT-ONLY-KEY').run()
        app.button(key='settings_secret_deepseek_save').click().run()
        self.assertFalse(app.exception);self.assertFalse(app.checkbox(key='deepseek_test_consent').value)
        self.assertTrue(app.button(key='deepseek_run').disabled);self.assertEqual(len(self.http.calls),1)
        self.assertNotIn('settings_secret_deepseek',app.session_state)
    def test_saving_external_configuration_is_zero_request_and_keeps_local_default(self):
        app=self.app();app.button(key='settings_save').click().run()
        self.assertFalse(app.exception);self.assertEqual(self.http.calls,[])
        with closing(self.store.connect()) as db:payload=json.loads(db.execute("SELECT payload FROM product_settings WHERE name='external_api_settings'").fetchone()[0])
        self.assertEqual(payload['provider'],'deepseek');self.assertEqual(TaskQueue(self.store).config()['model'],'Local FinBERT')
        self.assertNotIn(KEY,json.dumps(payload));self.assertIsNone(TaskQueue(self.store).get())


if __name__=='__main__':unittest.main()
