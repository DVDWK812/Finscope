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


def main():
    try:
        data=json.loads(sys.stdin.read(70000))
        if set(data)!={'texts'}:raise ValueError()
        from .embedding_backend import LocalSentenceEmbedder
        encoder=LocalSentenceEmbedder.load();vectors=encoder.encode(data['texts'])
        print(json.dumps(dict(model_id=encoder.model_id,revision=encoder.revision,vectors=vectors)))
        return 0
    except Exception:
        print('Pinned local embedding process failed; no text logged',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
