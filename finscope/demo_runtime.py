"""Lazy actual-model bundle. Reused by Streamlit, smoke tests and evaluation."""
from .ai_prototype import FinBERTInterface
from .demo_pipeline import DemoPipeline
from .embedding_backend import LocalSentenceEmbedder
from .finbert_backend import LocalFinBERTBackend
from .model_assets import model_directory


def load_pipeline():
    sentiment=LocalFinBERTBackend.from_snapshot(model_directory("finbert"),accept_weight_license=True)
    embeddings=LocalSentenceEmbedder.load()
    interface=FinBERTInterface(sentiment,model_id=sentiment.manifest["model_id"],revision=sentiment.manifest["revision"])
    return DemoPipeline(interface,embeddings,sentiment_backend=sentiment)
