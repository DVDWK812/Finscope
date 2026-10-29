from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from finscope.local_news import ContentRights,LocalNewsStore,analyze_finbert
from finscope.model_providers import (ExternalLLMProvider,FinBERTProvider,ModelError,OllamaProvider,
    OPENAI_MODELS,OLLAMA_ORIGIN,model_request,structured_sentiment)
from test_local_news import item,pipeline


class ModelProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalNewsStore(Path(self.temp.name)/"local.sqlite3")
        self.item=item(rights=ContentRights(True,True,True,True,"Authored fixture with explicit external rights"))
        self.store.save_news(self.item)
        self.calls=[]

    def openai(self,method,endpoint,payload,headers,timeout):
        self.calls.append((method,endpoint,payload,headers))
        return {"model":OPENAI_MODELS[0],"status":"completed","output":[{"type":"message","content":[{
            "type":"output_text","text":json.dumps({"sentiment":"Positive","rationale":"Authored text reports higher profits."})}]}]}

    def test_finbert_default_interface_uses_real_backend_boundary_not_a_fake_fallback(self):
        result=FinBERTProvider(pipeline).analyze(self.item,self.store)
        self.assertEqual(result.family,"FinBERT")
        self.assertEqual(sum(result.probabilities.values()),1.)

    def test_external_consent_rights_key_and_model_fail_before_dispatch(self):
        provider=ExternalLLMProvider(self.openai)
        cases=[{"consent":False},{"api_key":None},{"model":"arbitrary-model"}]
        for case in cases:
            kwargs={"consent":True,"api_key":"UNIT-SECRET-KEY"};kwargs.update(case)
            with self.subTest(case=case),self.assertRaises(ValueError):
                provider.analyze(self.item,self.store,**kwargs)
        with self.assertRaises(ValueError):
            provider.analyze(replace(self.item,rights=replace(self.item.rights,external=False)),self.store,
                             consent=True,api_key="UNIT-SECRET-KEY")
        self.assertEqual(self.calls,[])

    def test_structured_external_output_provenance_and_no_fabricated_probabilities(self):
        result=ExternalLLMProvider(self.openai).analyze(self.item,self.store,api_key="UNIT-SECRET-KEY",consent=True)
        self.assertEqual(result.family,"External LLM")
        self.assertEqual(result.revision,OPENAI_MODELS[0])
        self.assertIsNone(result.probabilities)
        self.assertEqual(result.candidate_id,"")
        self.assertIn("Authored",result.rationale)
        request=self.calls[0]
        self.assertEqual(request[1],"https://api.openai.com/v1/responses")
        self.assertFalse(request[2]["store"])
        self.assertEqual(request[2]["input"][0]["content"],self.item.analysis_text)
        self.assertNotIn(self.item.rights.reference,json.dumps(request[2]))
        self.assertNotIn("UNIT-SECRET-KEY",json.dumps(self.store.export()))
        self.assertNotIn(b"UNIT-SECRET-KEY",self.store.path.read_bytes())

    def test_llm_validation_rejects_confidence_fields_fences_duplicates_and_refusal(self):
        for text in ['```json\n{}\n```','{"sentiment":"Positive","rationale":"x","confidence":0.99}',
                     '{"sentiment":"Positive","sentiment":"Negative","rationale":"x"}',
                     '{"sentiment":"Mixed","rationale":"x"}','{"sentiment":"Neutral","rationale":""}']:
            with self.subTest(text=text),self.assertRaises(ModelError):
                structured_sentiment(text)

    def test_incomplete_model_mismatch_refusal_and_secret_echo_save_nothing(self):
        responses=[{"status":"incomplete"},{"status":"completed","model":"unexpected"},
            {"status":"completed","model":OPENAI_MODELS[0],"output":[{"type":"message","content":[{"type":"refusal"}]}]},
            {"status":"completed","model":OPENAI_MODELS[0],"output":[{"type":"message","content":[{
                "type":"output_text","text":"UNIT-SECRET-KEY"}]}]}]
        for response in responses:
            with self.subTest(response=response),self.assertRaises(ModelError):
                ExternalLLMProvider(lambda *a:response).analyze(self.item,self.store,api_key="UNIT-SECRET-KEY",consent=True)
        self.assertEqual(self.store.list_analyses(),[])

    def test_external_429_hold_is_durable_and_never_retried(self):
        calls=[]
        def fail(*args):
            calls.append(args)
            raise ModelError("Model rate limited",status=429,retry_after="120")
        provider=ExternalLLMProvider(fail)
        with self.assertRaises(ModelError):
            provider.analyze(self.item,self.store,api_key="UNIT-SECRET-KEY",consent=True)
        with self.assertRaisesRegex(ModelError,"Retry-After"):
            provider.analyze(self.item,LocalNewsStore(self.store.path),api_key="UNIT-SECRET-KEY",consent=True)
        self.assertEqual(len(calls),1)

    def test_unknown_external_outcome_blocks_duplicates_and_does_not_echo_exception(self):
        def fail(*args): raise RuntimeError("UNIT-SECRET-KEY")
        with self.assertRaisesRegex(ModelError,"outcome needs review") as caught:
            ExternalLLMProvider(fail).analyze(self.item,self.store,api_key="UNIT-SECRET-KEY",consent=True)
        self.assertNotIn("UNIT-SECRET-KEY",str(caught.exception))
        with self.assertRaisesRegex(ModelError,"unknown outcome"):
            ExternalLLMProvider(self.openai).analyze(self.item,self.store,api_key="UNIT-SECRET-KEY",consent=True)
        self.assertEqual(self.calls,[])

    def ollama(self,method,endpoint,payload,headers,timeout):
        self.calls.append((method,endpoint,payload,headers))
        if endpoint.endswith("/tags"):
            return {"models":[{"name":"unit-local:latest","digest":"a"*64,"size":12345,"details":{"format":"gguf"}},
                              {"name":"remote:cloud","digest":"b"*64,"size":1,"details":{"format":"gguf"}}]}
        if endpoint.endswith("/show"):
            return {"details":{"format":"gguf"},"model_info":{"general.architecture":"unit-model"},"capabilities":["completion"]}
        return {"model":"unit-local:latest","done":True,"done_reason":"stop",
                "message":{"content":json.dumps({"sentiment":"Neutral","rationale":"Authored local test."})}}

    def test_ollama_fixed_loopback_installed_digest_and_structured_output(self):
        provider=OllamaProvider(self.ollama)
        self.assertEqual(provider.installed_models(),{"unit-local:latest":"a"*64})
        result=provider.analyze(self.item,self.store,model="unit-local:latest")
        self.assertEqual(result.family,"Local Ollama")
        self.assertEqual(result.revision,"a"*64)
        self.assertIsNone(result.probabilities)
        self.assertTrue(all(call[1].startswith(OLLAMA_ORIGIN+"/") for call in self.calls))
        self.assertTrue(all(call[3] is None for call in self.calls))
        self.assertFalse(any("pull" in call[1] for call in self.calls))

    def test_ollama_remote_and_uninstalled_models_never_receive_article_text(self):
        provider=OllamaProvider(self.ollama)
        for name in ("remote:cloud","arbitrary-model","https://attacker.invalid/proxy"):
            with self.subTest(name=name),self.assertRaises(ModelError):
                provider.analyze(self.item,self.store,model=name)
        self.assertTrue(all(call[1].endswith("/tags") for call in self.calls))

    def test_ollama_cloud_alias_metadata_is_rejected_before_chat(self):
        def backend(*args):
            result=self.ollama(*args)
            if args[1].endswith("/show"):
                result["remote_host"]="https://remote.invalid"
            return result
        with self.assertRaisesRegex(ModelError,"Local completion"):
            OllamaProvider(backend).analyze(self.item,self.store,model="unit-local:latest")
        self.assertFalse(any(call[1].endswith("/chat") for call in self.calls))

    def test_model_transport_disallows_arbitrary_endpoints_and_redacts_errors(self):
        with self.assertRaisesRegex(ModelError,"Unsupported model endpoint"):
            model_request("POST","http://attacker.invalid/api/chat")
        import requests
        with patch("finscope.model_providers.requests.Session") as session:
            connection=session.return_value.__enter__.return_value
            connection.request.side_effect=requests.ConnectionError("UNIT-SECRET-KEY")
            with self.assertRaises(ModelError) as caught:
                model_request("GET",OLLAMA_ORIGIN+"/api/tags")
            self.assertNotIn("UNIT-SECRET-KEY",str(caught.exception))
            self.assertFalse(connection.trust_env)
            self.assertFalse(connection.request.call_args.kwargs["allow_redirects"])

    def test_permission_update_is_local_audited_and_preserves_original(self):
        previous=self.store.list_news()[0]
        rights=replace(previous.rights,external=False,reference="Revised fixture permission")
        self.store.update_rights(previous.article_id,rights)
        current=self.store.list_news()[0]
        self.assertEqual(replace(current,rights=previous.rights),previous)
        self.assertFalse(current.rights.external)
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM local_permission_history").fetchone()[0],1)

