"""Authored fixtures/mock local transports; actual model evidence is separate."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from finscope.local_news import LocalNewsStore
from finscope.local_analytics import Filters,model_key,select_articles,result_models
from finscope.model_providers import LMStudioProvider,LMSTUDIO_ORIGIN,ModelError,model_request
from finscope.lmstudio_runtime import GIB,load_model
from test_local_news import item
import test_product_ui as product_test

KEYS=('google/authored-gemma','qwen/authored-qwen')


class LocalTransport:
    def __init__(self):
        self.calls=[];self.loaded=KEYS[0];self.response=None
    def __call__(self,method,endpoint,payload=None,headers=None,timeout=60):
        self.calls.append((method,endpoint,payload,headers))
        if endpoint.endswith('/v1/models') and '/api/' not in endpoint:
            return {'data':[{'id':k} for k in KEYS]}
        if endpoint.endswith('/api/v1/models'):
            return {'models':[{'type':'llm','key':k,'selected_variant':k+'@q4_k_m','format':'gguf',
                'size_bytes':6000000000,'architecture':'authored','quantization':{'name':'Q4_K_M'},
                'loaded_instances':[{'id':k,'config':{'context_length':2048}}] if self.loaded==k else [],
                'capabilities':{'reasoning':{'allowed_options':['off','on']}}} for k in KEYS]}
        if endpoint.endswith('/unload'):
            self.loaded=None;return {'status':'unloaded','instance_id':payload['instance_id']}
        return self.response if self.response is not None else {'id':'authored-response','model':payload['model'],
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'sentiment':'Positive','rationale':'The authored text reports rising revenue.'})}}],
            'usage':{'prompt_tokens':40,'completion_tokens':20}}


class LMStudioTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=LocalNewsStore(Path(temp.name)/'news.sqlite3');self.original=item();self.store.save_news(self.original)
        self.http=LocalTransport();self.provider=LMStudioProvider(self.http)

    def test_downloaded_loaded_and_callable_are_distinct_real_ids(self):
        models=self.provider.inventory()
        self.assertEqual(set(models),set(KEYS));self.assertTrue(models[KEYS[0]]['callable'])
        self.assertFalse(models[KEYS[1]]['loaded']);self.assertFalse(models[KEYS[1]]['callable'])
        self.assertEqual(models[KEYS[0]]['model_id'],KEYS[0])
        self.assertTrue(all(c[0]=='GET' for c in self.http.calls))

    def test_empty_lists_and_non_llm_remote_models(self):
        def empty(method,url,*args):return {'models':[]} if '/api/' in url else {'data':[]}
        self.assertEqual(LMStudioProvider(empty).inventory(),{})
        native={'models':[{'type':'embedding','key':'embedding'},{'type':'llm','key':'remote','device_identifier':'another-machine'}]}
        self.assertEqual(LMStudioProvider(lambda m,u,*a:native if '/api/' in u else {'data':[]}).inventory(),{})

    def test_wrong_port_and_remote_endpoint_are_rejected_before_transport(self):
        with patch('requests.sessions.Session.request') as request:
            for endpoint in ('http://127.0.0.1:4321/v1/models','http://192.168.1.1:1234/v1/models','https://remote.invalid/v1/chat/completions'):
                with self.assertRaises(ModelError):model_request('GET',endpoint)
            request.assert_not_called()

    def test_downloaded_but_unloaded_never_auto_loads_or_sends_text(self):
        with self.assertRaisesRegex(ModelError,'not loaded'):
            self.provider.analyze(self.original,self.store,model=KEYS[1])
        self.assertTrue(all(c[0]=='GET' and c[2] is None for c in self.http.calls))
        self.assertEqual(self.store.list_analyses(),[])

    def test_permission_and_input_bounds_fail_before_any_discovery(self):
        for original in (replace(self.original,rights=replace(self.original.rights,analyze=False)),replace(self.original,summary='x'*2001)):
            with self.assertRaises(ValueError):self.provider.analyze(original,self.store,model=KEYS[0])
        self.assertEqual(self.http.calls,[])

    def test_schema_output_provenance_actual_id_quantization_no_probabilities(self):
        result=self.provider.analyze(self.original,self.store,model=KEYS[0])
        self.assertEqual(result.family,'Local LM Studio');self.assertEqual(result.model_id,KEYS[0])
        self.assertIn('Q4_K_M',result.revision);self.assertIsNone(result.probabilities)
        self.assertEqual(result.provenance['context_length'],2048)
        post=self.http.calls[-1];payload=post[2]
        self.assertEqual(post[1],LMSTUDIO_ORIGIN+'/v1/chat/completions')
        self.assertTrue(payload['response_format']['json_schema']['strict'])
        self.assertEqual(payload['messages'][1]['content'],self.original.analysis_text)
        self.assertNotIn('tools',payload);self.assertNotIn('web_search',json.dumps(payload));self.assertIsNone(post[3])
        self.assertEqual(payload['reasoning_effort'],'none')

    def test_invalid_incomplete_refused_and_wrong_model_outputs_preserve_original_and_history(self):
        self.provider.analyze(self.original,self.store,model=KEYS[0]);before=self.store.export()
        good={'model':KEYS[0],'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
        cases=[{}, {'model':'wrong','choices':[]},{'model':KEYS[0],'choices':[None]},
            {**good,'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
            {**good,'choices':[{'finish_reason':'stop','message':{'tool_calls':[{}],'content':'{}'}}]}]
        for text in ['{}','bad json','```json\n{}\n```','{"sentiment":"Neutral","rationale":"x","confidence":1}',
                     '{"sentiment":"Positive","sentiment":"Negative","rationale":"x"}',None]:
            cases.append({**good,'choices':[{'finish_reason':'stop','message':{'content':text}}]})
        for response in cases:
            self.http.response=response
            with self.subTest(response=response),self.assertRaises(ModelError):self.provider.analyze(self.original,self.store,model=KEYS[0])
        self.assertEqual(self.store.export(),before)

    def test_two_models_keep_separate_history_and_one_original_count(self):
        one=self.provider.analyze(self.original,self.store,model=KEYS[0])
        self.http.loaded=KEYS[1];two=self.provider.analyze(self.original,self.store,model=KEYS[1])
        self.provider.analyze(self.original,self.store,model=KEYS[1])
        self.assertEqual(len(self.store.list_news()),1);self.assertEqual(len(self.store.list_analyses()),3)
        self.assertEqual(len(result_models(self.store.list_analyses())),2)
        for result in (one,two):
            news,results=select_articles(self.store.list_news(),self.store.list_analyses(),Filters(models=(model_key(result),)))
            self.assertEqual(len(news),1);self.assertEqual(len(results),1)
            self.assertEqual(results[self.original.article_id].model_id,result.model_id)

    def test_local_transport_never_uses_proxy_redirect_or_external_host(self):
        with patch('finscope.model_providers.requests.Session') as session:
            client=session.return_value.__enter__.return_value
            response=client.request.return_value;response.status_code=200;response.content=b'{}';response.json.return_value={'data':[]}
            model_request('GET',LMSTUDIO_ORIGIN+'/v1/models')
            self.assertFalse(client.trust_env);self.assertFalse(client.request.call_args.kwargs['allow_redirects'])
        self.provider.analyze(self.original,self.store,model=KEYS[0])
        self.assertTrue(all(c[1].startswith(LMSTUDIO_ORIGIN+'/') for c in self.http.calls))

    def test_non200_timeout_and_empty_loaded_registry_do_not_save(self):
        for error in (ModelError('Local timeout',kind='timeout'),ModelError('HTTP 503',kind='http_error',status=503)):
            def backend(method,url,*args):
                if url.endswith('/completions'):raise error
                return self.http(method,url,*args)
            with self.assertRaises(ModelError):LMStudioProvider(backend).analyze(self.original,self.store,model=KEYS[0])
        self.assertEqual(self.store.list_analyses(),[])

    def test_load_requires_explicit_action_and_no_other_loaded_model(self):
        with self.assertRaisesRegex(ModelError,'already loaded'):self.provider.load(KEYS[1],explicit=True)
        self.http.loaded=None
        with self.assertRaisesRegex(ModelError,'explicit'):self.provider.load(KEYS[0])
        self.assertTrue(all(c[0]=='GET' for c in self.http.calls))

    def test_resource_limit_prevents_actual_load_and_download(self):
        model=self.provider.inventory()[KEYS[1]];calls=[]
        def runner(args,timeout):
            calls.append(args);return 'Estimated GPU Memory: 9.42 GiB\nEstimated Total Memory: 18.51 GiB'
        with self.assertRaises(ModelError) as caught:
            load_model(model,explicit=True,runner=runner,resources=lambda:{'ram_available':10*GIB,'gpu_available':4*GIB})
        self.assertEqual(caught.exception.kind,'resource_limit');self.assertEqual(len(calls),1)
        self.assertIn('--estimate-only',calls[0])

    def test_safe_load_settings_use_only_selected_model_and_measured_resources(self):
        calls=[];model=self.provider.inventory()[KEYS[0]]
        def runner(args,timeout):
            calls.append(args);return 'Estimated GPU Memory: 3.25 GiB\nEstimated Total Memory: 6.18 GiB'
        report=load_model(model,explicit=True,runner=runner,resources=lambda:{'ram_available':20*GIB,'gpu_available':12*GIB})
        self.assertEqual(report['estimate']['context_length'],2048);self.assertEqual(len(calls),2)
        self.assertEqual(calls[-1][1],KEYS[0]+'@q4_k_m')
        self.assertIn('--no-engine-config-file',calls[-1]);self.assertNotIn('--estimate-only',calls[-1])
        self.assertNotIn('download',str(calls))

    def test_unload_requires_explicit_selection_and_does_not_infer(self):
        with self.assertRaises(ModelError):self.provider.unload(KEYS[0])
        self.provider.unload(KEYS[0],explicit=True)
        self.assertIsNone(self.http.loaded);self.assertFalse(any('/completions' in c[1] for c in self.http.calls))


class LMStudioUITests(unittest.TestCase):
    setUp=product_test.ProductUITests.setUp
    app=product_test.ProductUITests.app

    def test_refresh_selection_and_rerender_do_not_infer_or_auto_load(self):
        original=item();LocalNewsStore(self.db).save_news(original)
        http=LocalTransport();provider=LMStudioProvider(http)
        with patch('finscope.model_ui.LMStudioProvider',return_value=provider):
            app=self.app('Analyze');app.selectbox(key='analysis_model').set_value('Local LM Studio').run()
            self.assertFalse(http.calls)
            app.button(key='analysis_lmstudio_refresh').click().run()
            app.selectbox(key='analysis_lmstudio_model').set_value(KEYS[1]).run();app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Not loaded' in c.value for c in app.caption))
            self.assertTrue(next(b for b in app.button if b.label=='Run real AI analysis').disabled)
        self.assertTrue(all(c[0]=='GET' for c in http.calls))

    def test_single_batch_switch_and_saved_versions_reuse_the_analysis_flow(self):
        store=LocalNewsStore(self.db);one=item();two=replace(one,article_id='second-authored',title='Second authored test')
        for n in (one,two):store.save_news(n)
        http=LocalTransport();provider=LMStudioProvider(http)
        with patch('finscope.model_ui.LMStudioProvider',return_value=provider):
            app=self.app('Analyze');app.selectbox(key='analysis_model').set_value('Local LM Studio').run()
            app.button(key='analysis_lmstudio_refresh').click().run()
            app.selectbox(key='analysis_lmstudio_model').set_value(KEYS[0]).run()
            app.multiselect(key='analysis_articles').set_value([one.article_id,two.article_id]).run()
            next(b for b in app.button if b.label=='Run real AI analysis').click().run()
            self.assertEqual(len(store.list_analyses()),2)
            http.loaded=KEYS[1];app.button(key='analysis_lmstudio_refresh').click().run()
            app.selectbox(key='analysis_lmstudio_model').set_value(KEYS[1]).run()
            app.multiselect(key='analysis_articles').set_value([one.article_id]).run()
            next(b for b in app.button if b.label=='Run real AI analysis').click().run()
            self.assertFalse(app.exception)
        self.assertEqual(len(store.list_news()),2);self.assertEqual(len(store.list_analyses()),3)
        self.assertEqual(len(result_models(store.list_analyses())),2)
