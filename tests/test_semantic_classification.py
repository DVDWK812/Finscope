"""Authored fixtures only, not the diagnostic news or frozen challenge packet."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json,os,unittest
from unittest.mock import patch
from finscope.local_news import LocalNewsStore,NewsItem,ContentRights,Analysis
from finscope.task_queue import TaskQueue
from finscope.product_storage import ProductStorage
from finscope.media_use import apply
from finscope.text_processing import prepare
from finscope.semantic_classifier import SemanticIndustryClassifier
from finscope.classification_scheme import VERSION,cache_key,run_reclassification
from finscope.expiring_media import partition,TEXT_TABLES
from finscope.local_worker import Worker

OPTIONS=dict(version=VERSION,model_key='fixture/local',model_id='fixture/local',model_revision='authored-local-variant',context_length=4096)


class Encoder:
    model_id='authored-embedding';revision='fixture-revision'
    def encode(self,texts):return [[1.,0.] if 'Cybersecurity' in t or 'defend' in t else [0.,1.] for t in texts]


class SemanticTests(unittest.TestCase):
    def test_cold_embedding_guard_and_worker_backend_release(self):
        from finscope.local_worker import resource_check,ResourceBlocked
        from finscope.semantic_classifier import ClassifierPrerequisite
        c=self.classifier();c.resources=None
        resources=dict(ram_available=3*1024**3,gpu_available=4*1024**3)
        with patch('finscope.lmstudio_runtime.system_resources',return_value=resources):
            self.assertEqual(c.resource_check('LM Studio'),resources)
            with self.assertRaisesRegex(ClassifierPrerequisite,'3.00 GiB available / 5.00 GiB required'):
                c.resource_check('MiniLM')
        w=Worker(self.store);w.backend=object()
        with patch('gc.collect') as collect:
            w.release_sentiment_backend();self.assertIsNone(w.backend);collect.assert_called_once()
            w.release_sentiment_backend();collect.assert_called_once()
    def test_resource_metadata_is_bounded_and_failed_preflight_never_dispatches(self):
        from finscope.semantic_classifier import ClassifierPrerequisite
        n=self.item();c=self.classifier();c.resources=lambda kind:dict(ram_available=9*1024**3,private='must not persist')
        c.call(n,'test-resource','fixture','revision','authored input',lambda:'ok')
        with closing(partition(self.store).connect()) as db:
            payload=json.loads(db.execute("SELECT payload FROM product_classifier_calls WHERE stage='test-resource'").fetchone()[0])
        self.assertEqual(payload['resources_before'],{'ram_available':9*1024**3})
        c.resources=lambda kind:(_ for _ in ()).throw(ClassifierPrerequisite('low RAM'))
        with self.assertRaises(ClassifierPrerequisite):c.call(n,'never-dispatched','fixture','revision','authored input',lambda:self.fail('dispatched'))
        with closing(partition(self.store).connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM product_classifier_calls WHERE stage='never-dispatched'").fetchone()[0],0)
    def test_resource_pause_count_survives_task_resume_without_text(self):
        from finscope.local_worker import record_resource_pause,ResourceBlocked
        n=self.item();identity,_=self.q.submit_reclassify(article_ids=[n.article_id],options=OPTIONS,confirmed=True)
        counts=self.q.get(identity)['counts'];error=ResourceBlocked('low RAM',resources={'ram_available':123,'gpu_available':456,'secret':'excluded'})
        record_resource_pause(self.q,identity,counts,error)
        self.q.update(identity,status='blocked',counts=counts)
        self.q.resume(identity);counts=self.q.get(identity)['counts']
        record_resource_pause(self.q,identity,counts,error)
        self.assertEqual(counts['resource_pauses'],2)
        self.assertEqual(self.q.step(identity,'resource_pause:1')[1],{'ram_available':123,'gpu_available':456})
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        p=patch('finscope.media_use.utcnow',side_effect=lambda:self.now);p.start();self.addCleanup(p.stop)
        self.store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);self.q=TaskQueue(self.store);self.data=ProductStorage(self.store);self.posts=[]
    def item(self,text='Providers defend corporate networks against intrusions and protect business customers.'):
        raw=NewsItem('0'*32,'finnhub','Authored fixture','Authored publisher','https://example.com/fixture',text,
            self.now.isoformat(),'published',self.now.isoformat(),(),ContentRights(),company='QUERY')
        n=apply(raw,dict(source='finnhub',status='research_unverified',reference='Authored offline fixture',fields=['title','summary'],
            expires_at=(self.now+timedelta(days=7)).isoformat(),confirmed=True,domains=[]))
        origin=json.loads(n.provenance);origin['capture_task_id']='fixture-capture'
        return self.data.save(prepare(replace(n,provenance=json.dumps(origin)))[0])[0]
    def classifier(self,output=None):
        def transport(method,url,payload,*args):
            self.posts.append(payload)
            result=output or dict(labels=[dict(id='technology.cybersecurity',quote='defend corporate networks against intrusions',reason='Defending enterprise networks is a cybersecurity service activity, rather than device manufacturing.')],unclassified_reason='')
            return dict(model='fixture/local',choices=[dict(finish_reason='stop',message=dict(content=json.dumps(result)))])
        return SemanticIndustryClassifier(self.store,OPTIONS,embedder=Encoder(),transport=transport,
            model=dict(model_id='fixture/local',reasoning={}),resources=lambda *args:None)
    def test_zero_literal_candidate_can_receive_semantic_child_and_parent(self):
        n=self.item();c=self.classifier();self.assertFalse(c.rules.classify(n)['labels'])
        r=c.classify(n);self.assertEqual({v['id'] for v in r['labels']},{'technology','technology.cybersecurity'})
        self.assertEqual(r['query_ticker'],'QUERY');self.assertEqual(r['company_business'],[])
        self.assertEqual(len(self.posts),2);self.assertNotIn('probability',r['labels'][0])
        self.assertEqual(r['labels'][0]['evidence'][0]['quote'],'defend corporate networks against intrusions')
    def test_parent_only_and_macro_reasons_are_legal(self):
        n=self.item()
        output=dict(labels=[dict(id='technology',quote='defend corporate networks against intrusions',reason='The described business activity supports technology but a specific subindustry is uncertain.')],unclassified_reason='')
        self.assertEqual(len(self.classifier(output).classify(n)['labels']),1)
        # New scheme key for a separate authored response, never retry a failed real input.
        with closing(partition(self.store).connect()) as db:db.execute('DELETE FROM product_classifier_calls');db.commit()
        out=dict(labels=[],unclassified_reason='macro_non_industry')
        self.assertEqual(self.classifier(out).classify(n)['unclassified_reason'],'macro_non_industry')
    def test_forged_quote_fails_closed_and_raw_output_stays_in_finite_store(self):
        n=self.item();out=dict(labels=[dict(id='technology',quote='INVENTED QUOTE NEVER PRESENT',reason='An authored rejected output with no supporting original evidence.')],unclassified_reason='')
        r=self.classifier(out).classify(n);self.assertEqual(r['status'],'failed');self.assertFalse(r['labels'])
        with closing(self.store.connect()) as db:self.assertNotIn('INVENTED QUOTE','\n'.join(db.iterdump()))
        with closing(partition(self.store).connect()) as db:self.assertIn('INVENTED QUOTE','\n'.join(db.iterdump()))
    def test_invalid_taxonomy_id_cannot_be_saved_as_label(self):
        r=self.classifier(dict(labels=[dict(id='invented',quote='defend corporate networks',reason='Authored rejected category')],unclassified_reason='')).classify(self.item())
        self.assertEqual(r['unclassified_reason'],'classifier_failed')
    def test_quote_existence_does_not_override_semantic_insufficiency(self):
        n=self.item();out=dict(labels=[dict(id='technology',quote='defend corporate networks against intrusions',reason='This is an authored contradictory proposal without sufficient industry support.')],unclassified_reason='no_sector_evidence')
        r=self.classifier(out).classify(n)
        self.assertFalse(r['labels']);self.assertEqual(r['status'],'unclassified');self.assertTrue(r['semantic_consistency_note'])
    def test_literal_rules_remain_high_precision_and_do_not_invoke_llm(self):
        r=self.classifier().classify(self.item('The business sells cybersecurity services to enterprise customers.'))
        self.assertTrue(r['labels']);self.assertFalse(self.posts)
    def test_cache_history_selected_version_and_sentiment_are_independent(self):
        n=self.item();legacy=self.classifier().rules;self.data.save_classification(n,legacy.cache_key,legacy.classify(n))
        c=self.classifier();result=c.classify(n);self.data.save_classification(n,c.cache_key,result)
        with closing(self.store.connect()) as db:
            db.execute('INSERT INTO product_settings VALUES (?,?)',('media_classification_scheme',json.dumps(OPTIONS)));db.commit()
        self.assertEqual(self.data.classifications('US-BUSINESS-1')[n.article_id]['cache_key'],c.cache_key)
        self.assertEqual(len(self.data.classification_history(n.article_id,'US-BUSINESS-1')),2)
        task,_=self.q.submit_reclassify(confirmed=True)
        w=Worker(self.store,fetch=lambda *a:self.fail('No news'),infer=lambda *a:self.fail('No sentiment'))
        with patch('finscope.semantic_classifier.SemanticIndustryClassifier',side_effect=lambda *a,**kw:self.classifier()):w.run_one()
        self.assertEqual(self.q.get(task)['counts']['classified'],0);self.assertEqual(len(self.posts),2)
        with closing(self.store.connect()) as db:self.assertNotIn(n.summary,'\n'.join(db.iterdump()))
    def test_classification_only_task_never_enters_fetch_or_finbert(self):
        n=self.item();task,_=self.q.submit_reclassify(options=OPTIONS,confirmed=True)
        w=Worker(self.store,fetch=lambda *a:self.fail('No news'),infer=lambda *a:self.fail('No sentiment'))
        with patch('finscope.semantic_classifier.SemanticIndustryClassifier',side_effect=lambda *a,**kw:self.classifier()):w.run_one()
        self.assertEqual(self.q.get(task)['status'],'completed');self.assertEqual(self.q.get(task)['counts']['analyzed'],0)
        self.assertFalse(self.data.analyses());self.assertEqual(len(self.data.news()),1)
    def test_classification_only_schema_rejects_source_dispatch_and_requires_scheme(self):
        from finscope.task_queue import validate_config
        base=dict(sources=[],article_ids=['0'*32],operation='reclassify',model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',classifier_options=OPTIONS)
        for change in (dict(sources=['finnhub']),dict(classifier_options=None),dict(article_ids=[]),dict(budgets={'finnhub':1})):
            with self.assertRaises(ValueError):validate_config({**base,**change})
    def test_unknown_local_dispatch_is_not_automatically_repeated(self):
        n=self.item();c=self.classifier();part=partition(self.store)
        with closing(part.connect()) as db:
            db.execute('INSERT INTO product_classifier_calls VALUES (?,?,?,?,?,?,?,?,?,?,?)',('pending',n.article_id,n.content_version,c.cache_key,'document_embedding','pending','fixture','fixture',self.now.isoformat(),None,'{}'));db.commit()
        self.assertEqual(c.classify(n)['status'],'failed');self.assertFalse(self.posts)
    def test_expiry_removes_classifier_outputs_embeddings_quotes_and_reviews(self):
        n=self.item();c=self.classifier();self.data.save_classification(n,c.cache_key,c.classify(n));part=partition(self.store)
        with closing(part.connect()) as db:
            db.execute('INSERT INTO product_classification_reviews VALUES (?,?,?,?,?)',('r',n.article_id,c.cache_key,self.now.isoformat(),json.dumps({'note':n.summary})));db.commit()
        self.now+=timedelta(days=8);self.assertFalse(self.data.news())
        with closing(part.connect()) as db:
            for t in TEXT_TABLES:self.assertEqual(db.execute('SELECT count(*) FROM '+t).fetchone()[0],0,t)
    def test_cache_key_binds_classifier_model_separately_from_finbert(self):
        other={**OPTIONS,'model_revision':'different-authored-local-variant'}
        self.assertNotEqual(cache_key(OPTIONS),cache_key(other))
    def test_company_performance_and_customer_relationship_do_not_support_sectors(self):
        from finscope.topic_grounding import guard
        for quote in ('Arcvale', 'deal with the Ministry', 'stock price growth'):
            label=dict(id='industrials.aerospace',evidence=[dict(quote=quote)])
            accepted,rejected=guard([label],quote)
            self.assertFalse(accepted);self.assertEqual(len(rejected),1)
    def test_one_invalid_label_does_not_discard_an_independently_supported_child(self):
        output=dict(labels=[dict(id='technology',quote='',reason='An invalid parent without an original quotation.'),
            dict(id='technology.cybersecurity',quote='defend corporate networks against intrusions',reason='Defending business networks is a security service rather than manufacturing.')],unclassified_reason='')
        r=self.classifier(output).classify(self.item())
        self.assertEqual({v['id'] for v in r['labels']},{'technology','technology.cybersecurity'})
        self.assertTrue(r['output_validation_notes'])
    def test_preceding_generation_reused_without_new_model_dispatch(self):
        from finscope.semantic_classifier import text_of
        import hashlib
        n=self.item();c=self.classifier();text=text_of(n)
        response=dict(model='fixture/local',choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(labels=[],unclassified_reason='macro_non_industry'))))])
        with closing(partition(self.store).connect()) as db:
            db.execute('INSERT INTO product_classifier_calls VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                ('previous',n.article_id,n.content_version,cache_key(OPTIONS,previous_version='semantic-topics-3'),'semantic_decision','ok','fixture/local',OPTIONS['model_revision'],self.now.isoformat(),self.now.isoformat(),json.dumps(dict(input_sha256=hashlib.sha256(text.encode()).hexdigest(),output=response))))
            db.commit()
        r=c.classify(n)
        self.assertEqual(r['unclassified_reason'],'macro_non_industry');self.assertFalse(self.posts);self.assertTrue(r['preceding_generation_reused'])
    def test_embedding_process_uses_stdin_not_command_arguments(self):
        from finscope.embedding_process import ProcessSentenceEmbedder
        from types import SimpleNamespace
        encoder=ProcessSentenceEmbedder();v=[1.]+[0.]*383
        response=SimpleNamespace(returncode=0,stdout=json.dumps(dict(model_id=encoder.model_id,revision=encoder.revision,vectors=[v])))
        with patch('finscope.embedding_process.subprocess.run',return_value=response) as run:
            self.assertEqual(encoder.encode(['Authored pipe-only input']),[v])
        args,kw=run.call_args
        self.assertNotIn('Authored pipe-only input',' '.join(args[0]));self.assertIn('Authored pipe-only input',kw['input'])
        self.assertEqual(kw['timeout'],120)


if __name__=='__main__':unittest.main()
