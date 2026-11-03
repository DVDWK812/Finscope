"""Bounded short-lived CPU MiniLM execution; inputs travel only over stdin.

The durable worker does not retain Torch's process-wide allocation beside an
independent GPU classifier. No temporary text files, downloads or article URLs.
"""
import json,math,os,subprocess,sys
from .model_assets import manifest


class ProcessSentenceEmbedder:
    def __init__(self):
        spec=manifest('minilm');self.model_id=spec['model_id'];self.revision=spec['revision']
    def encode(self,texts):
        if not isinstance(texts,(tuple,list)) or not 1<=len(texts)<=32 or any(not isinstance(t,str) or not t.strip() or len(t)>2000 for t in texts):
            raise ValueError('Bounded local embedding input required')
        result=subprocess.run([sys.executable,'-m','finscope.embedding_process'],input=json.dumps({'texts':list(texts)}),
            capture_output=True,text=True,encoding='utf-8',timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode or len(result.stdout)>1024*1024:raise ValueError('Local embedding process unavailable; no input diagnostic emitted')
        data=json.loads(result.stdout)
        if data.get('model_id')!=self.model_id or data.get('revision')!=self.revision:raise ValueError('Pinned embedding model changed')
        vectors=data['vectors']
        if len(vectors)!=len(texts) or any(len(v)!=384 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) for v in vectors):raise ValueError('Invalid local embedding vectors')
        return vectors


from .finbert_process import ProcessFinBERT


class PersistentSentenceEmbedder(ProcessFinBERT):
    """One owned encoder for the candidate stage; fingerprints still cache each call."""
    module='finscope.embedding_process'
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        spec=manifest('minilm');self.model_id=spec['model_id'];self.revision=spec['revision']
    def encode(self,texts):
        try:return self._encode(texts)
        except BaseException:
            self.close();raise

    def _encode(self,texts):
        if not isinstance(texts,(tuple,list)) or not 1<=len(texts)<=32 or any(not isinstance(t,str) or not t.strip() or len(t)>2000 for t in texts):raise ValueError('Bounded embedding input required')
        data=self.exchange(list(texts))
        if data.get('model_id')!=self.model_id or data.get('revision')!=self.revision:raise ValueError('Pinned embedding model changed')
        vectors=data['vectors']
        if len(vectors)!=len(texts) or any(len(v)!=384 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) for v in vectors):raise ValueError('Invalid local embedding vectors')
        return vectors


def main():
    try:
        encoder=None;persistent='--persistent' in sys.argv
        for _ in range(600 if persistent else 1):
            line=sys.stdin.readline(400000) if persistent else sys.stdin.read(400000)
            if not line:return 0
            data=json.loads(line)
            if set(data)!={'texts'}:raise ValueError()
            texts=data['texts']
            if not isinstance(texts,list) or not 1<=len(texts)<=32 or any(not isinstance(t,str) or not 0<len(t)<=2000 for t in texts):raise ValueError()
            if encoder is None:
                from .embedding_backend import LocalSentenceEmbedder
                encoder=LocalSentenceEmbedder.load()
            vectors=encoder.encode(texts)
            print(json.dumps(dict(model_id=encoder.model_id,revision=encoder.revision,vectors=vectors)),flush=True)
        return 0
    except Exception:return 2


if __name__=='__main__':raise SystemExit(main())
