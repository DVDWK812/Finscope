"""Optional CPU FinBERT backend: pinned, hash-verified local files only.

No downloads, news readers, training, UI imports, or implicit runtime setup.
The CLI uses authored synthetic fixtures, not API data or an accuracy dataset.
"""

import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import time

from .ai_prototype import EvaluationText, FinBERTInterface, MAX_BATCH, MAX_TEXT_CHARS


MANIFEST_PATH = Path(__file__).with_name("finbert_manifest.json")
RUNTIME = {"torch": "2.14.1+cpu", "transformers": "5.20.2", "huggingface-hub": "2.3.0",
           "safetensors": "0.8.0", "tokenizers": "0.23.3"}
SYNTHETIC_FIXTURES = (
    ("synthetic_growth", "Invented company Solara reported higher revenue and a strong increase in profit."),
    ("synthetic_loss", "Invented company Solara reported a large loss after revenue declined sharply."),
    ("synthetic_notice", "Invented company Solara scheduled its annual shareholder meeting for Tuesday."),
)


def pinned_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify_snapshot(directory: Path) -> dict:
    manifest = pinned_manifest()
    root = Path(directory).resolve()
    if not root.is_dir() or {path.name for path in root.iterdir()} != set(manifest["files"]):
        raise ValueError("Use only the pinned snapshot files; no unverified local configuration")
    for name, expected in manifest["files"].items():
        path = root / name
        if (not path.is_file() or path.is_symlink() or path.resolve().parent != root
                or path.stat().st_size != expected["size"]):
            raise ValueError("Pinned FinBERT file missing or invalid; no download attempted")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected["sha256"]:
            raise ValueError("Pinned FinBERT integrity check failed; no model loaded")
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    if (config.get("model_type") != "bert" or config.get("max_position_embeddings") != 512
            or config.get("id2label") != {"0": "positive", "1": "negative", "2": "neutral"}):
        raise ValueError("Pinned FinBERT configuration mismatch")
    return manifest


def runtime_versions() -> dict:
    try:
        actual = {name: version(name) for name in RUNTIME}
    except PackageNotFoundError:
        raise RuntimeError("Optional pinned CPU runtime missing; install requirements-finbert.txt separately") from None
    if actual != RUNTIME:
        raise RuntimeError("Optional CPU runtime version mismatch; use the pinned environment")
    return actual


class TokenLimitExceeded(ValueError):
    def __init__(self):
        super().__init__("FinBERT input exceeds 512 tokens including special tokens; no truncation/inference")


class LocalFinBERTBackend:
    """Use through FinBERTInterface with explicit EvaluationText provenance."""

    @classmethod
    def from_snapshot(cls, directory: Path, *, accept_weight_license: bool = False):
        if accept_weight_license is not True:
            raise ValueError("Explicit acknowledgement of the pinned noncommercial weight licence required")
        manifest = verify_snapshot(directory)
        packages = runtime_versions()
        # Enforce local/offline behavior even if the caller configured hub access.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            root = str(Path(directory).resolve())
            tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True,
                                                       trust_remote_code=False, use_fast=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                root, local_files_only=True, trust_remote_code=False, use_safetensors=True)
            torch.set_num_threads(1)
            model.to("cpu").eval()
        except Exception:
            raise RuntimeError("Local FinBERT loading failed; no fallback or download attempted") from None
        backend = cls()
        backend.torch, backend.tokenizer, backend.model = torch, tokenizer, model
        backend.manifest, backend.packages = manifest, packages
        backend.forward_batches = 0
        return backend

    def tokenize(self, texts):
        if (not isinstance(texts, (tuple, list)) or len(texts) > MAX_BATCH
                or any(not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS
                       for text in texts)):
            raise ValueError("FinBERT requires a bounded nonempty-text batch")
        if not texts:
            return {}, []
        encoded = self.tokenizer(list(texts), add_special_tokens=True, padding=False,
                                 truncation=False, verbose=False)
        lengths = [len(ids) for ids in encoded["input_ids"]]
        if len(lengths) != len(texts) or any(length > 512 for length in lengths):
            raise TokenLimitExceeded()
        return encoded, lengths

    def predict(self, texts):
        encoded, _ = self.tokenize(texts)
        if not texts:
            return []
        inputs = self.tokenizer.pad(encoded, padding=True, return_tensors="pt")
        with self.torch.inference_mode():
            self.forward_batches += 1
            probabilities = self.model(**inputs).logits.softmax(dim=-1).cpu().tolist()
        labels = self.model.config.id2label
        if set(labels.values()) != {"positive", "negative", "neutral"}:
            raise ValueError("Local model label mapping is invalid")
        return [{labels[index]: score for index, score in enumerate(row)} for row in probabilities]


def synthetic_demo(directory: Path, *, accept_weight_license: bool) -> dict:
    started = time.perf_counter()
    backend = LocalFinBERTBackend.from_snapshot(directory, accept_weight_license=accept_weight_license)
    load_ms = (time.perf_counter() - started) * 1000
    records = [EvaluationText(text, "synthetic") for _, text in SYNTHETIC_FIXTURES]
    _, lengths = backend.tokenize(tuple(record.text for record in records))
    interface = FinBERTInterface(backend, model_id=backend.manifest["model_id"],
                                revision=backend.manifest["revision"])
    started = time.perf_counter()
    predictions = interface.predict(records)
    inference_ms = (time.perf_counter() - started) * 1000
    over_limit_blocked = False
    try:
        backend.tokenize(["q " * 700])
    except TokenLimitExceeded:
        over_limit_blocked = True
    return {"execution_kind": "real_local_cpu_inference", "model_id": backend.manifest["model_id"],
            "revision": backend.manifest["revision"], "weight_license": backend.manifest["weight_license"],
            "snapshot_hashes_verified": True, "runtime": backend.packages, "load_ms": round(load_ms, 2),
            "inference_ms": round(inference_ms, 2), "forward_batches": backend.forward_batches,
            "over_limit_blocked_before_forward": over_limit_blocked, "accuracy": "not_evaluated",
            "predictions": [{"fixture_id": fixture[0], "tokens_including_special": count, **asdict(prediction)}
                            for fixture, count, prediction in zip(SYNTHETIC_FIXTURES, lengths, predictions)]}


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local-only FinBERT; preview by default, never downloads")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--synthetic-demo", action="store_true")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--accept-weight-license", action="store_true")
    args = parser.parse_args(argv)
    if not args.synthetic_demo:
        print(json.dumps({"mode": "offline_preview", "model_id": pinned_manifest()["model_id"],
                          "revision": pinned_manifest()["revision"], "network_downloads": 0,
                          "inferences_executed": 0}, indent=2))
        return 0
    if args.model_dir is None:
        parser.error("An existing pinned local --model-dir is required")
    try:
        print(json.dumps(synthetic_demo(args.model_dir, accept_weight_license=args.accept_weight_license), indent=2))
        return 0
    except (ValueError, RuntimeError):
        print(json.dumps({"status": "blocked_or_failed", "model_inference_result": "unobserved",
                          "reason": "Check pinned files, runtime, licence acknowledgement and token limits"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
