"""Pinned MiniLM sentence embeddings; official attention-mask mean pooling."""
from .finbert_backend import runtime_versions
from .model_assets import model_directory, verify


class LocalSentenceEmbedder:
    @classmethod
    def load(cls, directory=None):
        import os
        root=directory or model_directory("minilm")
        spec=verify("minilm",root)
        runtime_versions()
        os.environ["HF_HUB_OFFLINE"]="1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
        import torch
        from transformers import AutoModel,AutoTokenizer
        instance=cls()
        instance.torch=torch
        instance.tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        instance.model=AutoModel.from_pretrained(str(root),local_files_only=True,trust_remote_code=False,use_safetensors=True)
        instance.model.to("cpu").eval()
        instance.revision=spec["revision"]
        instance.model_id=spec["model_id"]
        return instance

    def tokenize(self,texts):
        if (not isinstance(texts,(list,tuple)) or len(texts)>32
                or any(not isinstance(t,str) or not t.strip() or len(t)>2000 for t in texts)):
            raise ValueError("Embedding text exceeds the demo batch/character limits")
        if not texts:return {},[]
        encoded=self.tokenizer(list(texts),padding=False,truncation=False,verbose=False)
        counts=[len(ids) for ids in encoded["input_ids"]]
        if len(counts)!=len(texts) or any(count>256 for count in counts):
            raise ValueError("MiniLM supports at most 256 tokens including special tokens; shorten the input")
        return encoded,counts

    def encode(self,texts):
        encoded,_=self.tokenize(texts)
        if not texts:return []
        batch=self.tokenizer.pad(encoded,padding=True,return_tensors="pt")
        with self.torch.inference_mode():
            tokens=self.model(**batch).last_hidden_state
            mask=batch["attention_mask"].unsqueeze(-1).expand(tokens.size()).float()
            pooled=(tokens*mask).sum(1)/mask.sum(1).clamp(min=1e-9)
            vectors=self.torch.nn.functional.normalize(pooled,p=2,dim=1)
        return vectors.cpu().tolist()
