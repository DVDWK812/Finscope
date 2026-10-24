"""Offline AI contracts for synthetic or explicitly licensed evaluation text.

No API, Streamlit, model SDK, weights, downloads, cache or fallback classifier.
Backends must be supplied explicitly and run locally. Fixture outputs test the
contracts/math only; they do not measure sentiment or event-matching accuracy.
"""

from dataclasses import dataclass, field
from itertools import combinations
import math
from numbers import Real
from typing import Mapping, Protocol, Sequence


MAX_BATCH = 32
MAX_TEXT_CHARS = 2000
MAX_DIMENSIONS = 4096
LABELS = ("positive", "negative", "neutral")


@dataclass(frozen=True)
class EvaluationText:
    """Caller attests provenance; this is not an automated licence verifier.

    Never relabel an API article as synthetic/licensed to bypass source gates.
    Text and permission references are omitted from repr and inference results.
    """
    text: str = field(repr=False)
    origin: str
    license_reference: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if (not isinstance(self.text, str) or not self.text.strip()
                or len(self.text) > MAX_TEXT_CHARS):
            raise ValueError("Evaluation text must be nonempty and within the character cap")
        if self.origin not in {"synthetic", "licensed"}:
            raise ValueError("Only synthetic or explicitly licensed evaluation text is accepted")
        if self.origin == "licensed" and (not isinstance(self.license_reference, str)
                                          or not self.license_reference.strip()):
            raise ValueError("Licensed text requires a permission reference")


class SentimentBackend(Protocol):
    def predict(self, texts: Sequence[str]) -> Sequence[Mapping[str, float]]:
        """Return all positive/negative/neutral probabilities for each input.

        A future local FinBERT adapter maps labels from its pinned model config,
        explicitly handles token limits and returns all labels, not top-1 only.
        """
        ...


class EmbeddingBackend(Protocol):
    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one finite, nonzero vector of equal dimension per input."""
        ...


@dataclass(frozen=True)
class SentimentPrediction:
    label: str
    positive: float
    negative: float
    neutral: float
    model_id: str
    revision: str
    origin: str


@dataclass(frozen=True)
class SimilarityPair:
    left_index: int
    right_index: int
    cosine_similarity: float
    model_id: str
    revision: str


def _inputs(records: Sequence[EvaluationText]) -> tuple[EvaluationText, ...]:
    if not isinstance(records, (list, tuple)) or len(records) > MAX_BATCH:
        raise ValueError("Evaluation batch must be a bounded list or tuple")
    if any(not isinstance(record, EvaluationText) for record in records):
        raise ValueError("Explicit evaluation-text provenance is required")
    return tuple(records)


def _identity(model_id: str, revision: str) -> None:
    if not all(isinstance(value, str) and value.strip() for value in (model_id, revision)):
        raise ValueError("An explicit model ID and pinned revision are required")
    if revision.strip().casefold() in {"main", "master", "latest", "head"}:
        raise ValueError("A mutable model revision is not accepted")


def _finite_number(value) -> float:
    try:
        valid = not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(value)
        number = float(value) if valid else math.nan
    except (ValueError, OverflowError):
        number = math.nan
    if not math.isfinite(number):
        raise ValueError("Backend must return finite numeric values")
    return number


class FinBERTInterface:
    """Validated sentiment seam, deliberately unconfigured by default.

    No presumed label-index mapping, top-1 expansion, score normalization or
    heuristic fallback. A backend's probabilities are not calibrated accuracy.
    """

    def __init__(self, backend: SentimentBackend | None = None, *,
                 model_id: str = "unconfigured", revision: str = "unconfigured"):
        _identity(model_id, revision)
        if backend is not None and (model_id == "unconfigured" or revision == "unconfigured"):
            raise ValueError("A configured backend requires explicit model provenance")
        self.backend, self.model_id, self.revision = backend, model_id, revision

    def predict(self, records: Sequence[EvaluationText]) -> tuple[SentimentPrediction, ...]:
        records = _inputs(records)
        if not records:
            return ()
        if self.backend is None:
            raise RuntimeError("No local FinBERT backend configured; no inference performed")
        try:
            rows = self.backend.predict(tuple(record.text for record in records))
        except Exception:
            raise RuntimeError("Local sentiment backend failed; input/errors not retained") from None
        if not isinstance(rows, (list, tuple)) or len(rows) != len(records):
            raise ValueError("Sentiment backend result count mismatch")
        predictions = []
        for record, row in zip(records, rows):
            if not isinstance(row, Mapping) or set(row) != set(LABELS):
                raise ValueError("Sentiment backend must return exactly three named labels")
            scores = {label: _finite_number(row[label]) for label in LABELS}
            if (any(not 0 <= score <= 1 for score in scores.values())
                    or not math.isclose(sum(scores.values()), 1.0, abs_tol=1e-6)):
                raise ValueError("Sentiment probabilities must lie in [0,1] and sum to one")
            # Deterministic tie convention; not evidence of a neutral conclusion.
            label = max(("neutral", "positive", "negative"), key=scores.__getitem__)
            predictions.append(SentimentPrediction(label, **scores, model_id=self.model_id,
                                                    revision=self.revision, origin=record.origin))
        return tuple(predictions)


class EmbeddingSimilarity:
    """Pairwise cosine seam. Scores do not assert duplicate events or thresholds."""

    def __init__(self, backend: EmbeddingBackend | None = None, *,
                 model_id: str = "unconfigured", revision: str = "unconfigured"):
        _identity(model_id, revision)
        if backend is not None and (model_id == "unconfigured" or revision == "unconfigured"):
            raise ValueError("A configured backend requires explicit model provenance")
        self.backend, self.model_id, self.revision = backend, model_id, revision

    def compare(self, records: Sequence[EvaluationText]) -> tuple[SimilarityPair, ...]:
        records = _inputs(records)
        if not records:
            return ()
        if self.backend is None:
            raise RuntimeError("No local embedding backend configured; no inference performed")
        try:
            vectors = self.backend.encode(tuple(record.text for record in records))
        except Exception:
            raise RuntimeError("Local embedding backend failed; input/errors not retained") from None
        if not isinstance(vectors, (list, tuple)) or len(vectors) != len(records):
            raise ValueError("Embedding backend result count mismatch")
        unit_vectors, dimension = [], None
        for vector in vectors:
            if not isinstance(vector, (list, tuple)) or not 1 <= len(vector) <= MAX_DIMENSIONS:
                raise ValueError("Embedding dimension is invalid")
            if dimension is not None and len(vector) != dimension:
                raise ValueError("Embedding dimensions must agree")
            dimension = len(vector)
            numbers = [_finite_number(value) for value in vector]
            norm = math.hypot(*numbers)
            if not math.isfinite(norm) or norm == 0:
                raise ValueError("Embedding vectors require finite nonzero norm")
            unit_vectors.append([value / norm for value in numbers])
        pairs = []
        for left, right in combinations(range(len(records)), 2):
            cosine = math.fsum(a * b for a, b in zip(unit_vectors[left], unit_vectors[right]))
            pairs.append(SimilarityPair(left, right, max(-1.0, min(1.0, cosine)),
                                        self.model_id, self.revision))
        return tuple(pairs)


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Offline AI interface preview only")
    parser.add_argument("--dry-run", required=True, action="store_true")
    parser.parse_args()
    print(json.dumps({"backend_configured": False, "model_downloads": 0,
                      "inferences_executed": 0, "real_news_connected": False,
                      "accepted_origins": ["synthetic", "licensed"],
                      "max_batch": MAX_BATCH, "model_accuracy": "not_evaluated"}, indent=2))
