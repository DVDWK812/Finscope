"""Authored process protocols and resource boundaries; no model/news I/O."""
import io,json,unittest
from unittest.mock import Mock,patch
from finscope.finbert_process import ProcessFinBERT
from finscope.embedding_process import PersistentSentenceEmbedder
from finscope.local_worker import ResourceBlocked
from finscope.stage_resources import StageResources
from finscope.task_queue import Cancelled


class LifecycleTests(unittest.TestCase):
    def process(self,lines):
        p=Mock(pid=987654321,stdin=io.StringIO(),stdout=io.StringIO(''.join(json.dumps(x)+'\n' for x in lines)))
        p.poll.return_value=None;p.wait.side_effect=lambda **k:setattr(p,'returncode',0)
        return p
    def test_embedding_reuses_one_process_and_close_verifies_exit(self):
        b=PersistentSentenceEmbedder();out=dict(model_id=b.model_id,revision=b.revision,vectors=[[1.]+[0.]*383])
        p=self.process([out,out]);p.poll.side_effect=lambda:getattr(p,'returncode',None) if type(getattr(p,'returncode',None)) is int else None
        with patch('finscope.finbert_process.subprocess.Popen',return_value=p) as spawn,patch('psutil.Process') as proc:
            proc.return_value.children.return_value=[]
            self.assertEqual(b.encode(['Authored input']),out['vectors']);b.encode(['Another authored input'])
            spawn.assert_called_once();self.assertNotIn('Authored',str(spawn.call_args))
            b.close();self.assertTrue(b.exit_verified);self.assertTrue(b.closed)
            with self.assertRaises(ValueError):b.encode(['Closed process'])
    def test_cancelled_inflight_process_is_closed(self):
        b=ProcessFinBERT();p=self.process([]);p.poll.return_value=0;b.process=p
        checks=iter([None,Cancelled()])
        def check():
            result=next(checks)
            if result:raise result
        b.check=check
        with patch('psutil.Process') as proc:
            proc.return_value.children.return_value=[]
            with self.assertRaises(Cancelled):b.predict(['Authored input'])
        self.assertTrue(b.closed);self.assertTrue(b.exit_verified)
    def test_resource_recovery_remeasures_once_and_keeps_cold_threshold(self):
        w=Mock(backend=object());w.resources.side_effect=[ResourceBlocked('low'),ResourceBlocked('still low')]
        r=StageResources(w,'fixture');r.observe=Mock()
        with self.assertRaises(ResourceBlocked):r.check_resources('Local FinBERT')
        w.release_sentiment_backend.assert_called_once()
        self.assertEqual(w.resources.call_count,2)
        self.assertTrue(w.resources.call_args.kwargs['loading'])
        with self.assertRaises(ResourceBlocked):
            w.resources.side_effect=ResourceBlocked('low');r.check_resources('Local FinBERT')
        w.release_sentiment_backend.assert_called_once()
    def test_observation_failure_still_releases_owned_children(self):
        w=Mock();r=StageResources(w,'fixture');r.active='stage';r.encoder=Mock(pid=123,exit_verified=True)
        encoder=r.encoder;r.observe=Mock(side_effect=RuntimeError('database unavailable'))
        with self.assertRaises(RuntimeError):r.end()
        encoder.close.assert_called_once()
        # Cleanup must not depend on a diagnostic database write succeeding.
        w.release_sentiment_backend.assert_called_once()

    def test_timeout_terminates_only_owned_descendants(self):
        import subprocess
        b=ProcessFinBERT(timeout=0);p=self.process([]);child=Mock()
        p.poll.side_effect=lambda:None if not b.closed else 0
        # Closing sees the tracked process alive; wait then proves it exited.
        def wait(**kwargs):p.poll.side_effect=None;p.poll.return_value=0;return 0
        p.wait.side_effect=wait
        with patch('finscope.finbert_process.subprocess.Popen',return_value=p),patch('psutil.Process') as proc,patch('psutil.wait_procs',side_effect=[([], [child]),([], [child]),([child],[]) ]):
            proc.return_value.children.return_value=[child]
            with self.assertRaises(TimeoutError):b.predict(['Authored timeout input'])
        child.terminate.assert_called_once();child.kill.assert_called_once()
        self.assertTrue(b.exit_verified)
