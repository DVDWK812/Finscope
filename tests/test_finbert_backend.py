import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from finscope.finbert_backend import (LocalFinBERTBackend, RUNTIME, TokenLimitExceeded,
                                      pinned_manifest, run, runtime_versions, verify_snapshot)


class LocalFinBERTBackendTests(unittest.TestCase):
    """Offline mocks only; actual CPU inference is a separately recorded smoke run."""

    def backend(self, lengths):
        backend = LocalFinBERTBackend()
        backend.tokenizer = MagicMock(return_value={"input_ids": [[1]*n for n in lengths]})
        backend.tokenizer.pad.return_value = {}
        backend.torch = MagicMock()
        backend.torch.inference_mode.side_effect = contextlib.nullcontext
        backend.model = MagicMock()
        backend.model.config.id2label = {0: "positive", 1: "negative", 2: "neutral"}
        backend.model.return_value.logits.softmax.return_value.cpu.return_value.tolist.return_value = [
            [0.6, 0.1, 0.3] for _ in lengths]
        backend.forward_batches = 0
        return backend

    def test_512_tokens_allowed_513_rejected_before_model_forward(self):
        good = self.backend([512])
        self.assertEqual(good.predict(["Authored synthetic text"])[0]["positive"], 0.6)
        self.assertEqual(good.forward_batches, 1)
        self.assertFalse(good.tokenizer.call_args.kwargs["truncation"])
        bad = self.backend([513])
        with self.assertRaises(TokenLimitExceeded):
            bad.predict(["Authored synthetic text"])
        bad.model.assert_not_called()
        bad.tokenizer.pad.assert_not_called()
        self.assertEqual(bad.forward_batches, 0)

    def test_batch_and_character_caps_and_empty_input(self):
        backend = self.backend([])
        for texts in (["x"]*33, ["x"*2001], [" "], "raw string"):
            with self.assertRaises(ValueError):
                backend.predict(texts)
        self.assertEqual(backend.predict([]), [])
        backend.model.assert_not_called()
        backend.tokenizer.assert_not_called()

    def test_runtime_must_match_all_pins(self):
        with patch("finscope.finbert_backend.version", side_effect=lambda name:RUNTIME[name]):
            self.assertEqual(runtime_versions(), RUNTIME)
        with patch("finscope.finbert_backend.version", return_value="different-version"):
            with self.assertRaises(RuntimeError):
                runtime_versions()

    def test_requirement_file_and_manifest_are_pinned(self):
        manifest = pinned_manifest()
        self.assertRegex(manifest["revision"], r"^[a-f0-9]{40}$")
        self.assertEqual(manifest["weight_license"], "cc-by-nc-sa-4.0")
        requirements = Path(__file__).resolve().parents[1]/"requirements-finbert.txt"
        text = requirements.read_text()
        for name, expected in RUNTIME.items():
            self.assertIn(f"{name}=={expected}", text)

    def test_missing_or_tampered_snapshot_never_loads_or_downloads(self):
        config = {"model_type":"bert", "max_position_embeddings":512,
                  "id2label":{"0":"positive","1":"negative","2":"neutral"}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {"config.json":json.dumps(config).encode(), "model.safetensors":b"synthetic fixture"}
            manifest = {"files":{name:{"size":len(data),"sha256":hashlib.sha256(data).hexdigest()}
                                 for name,data in files.items()}}
            with patch("finscope.finbert_backend.pinned_manifest", return_value=manifest):
                with self.assertRaises(ValueError):
                    verify_snapshot(root)
                for name,data in files.items():(root/name).write_bytes(data)
                self.assertEqual(verify_snapshot(root), manifest)
                (root/"adapter_config.json").write_text("{}")
                with self.assertRaises(ValueError):
                    verify_snapshot(root)
                (root/"adapter_config.json").unlink()
                (root/"model.safetensors").write_bytes(b"different fixture")
                with self.assertRaises(ValueError):
                    verify_snapshot(root)

    def test_license_acknowledgement_precedes_snapshot_or_dependency_load(self):
        with patch("finscope.finbert_backend.verify_snapshot") as verify, \
                patch("finscope.finbert_backend.runtime_versions") as runtime:
            with self.assertRaises(ValueError):
                LocalFinBERTBackend.from_snapshot(Path("unused"))
            verify.assert_not_called();runtime.assert_not_called()

    def test_real_loader_contract_forces_local_safetensors_no_remote_code_cpu_eval(self):
        torch, tokenizer_factory, model_factory = MagicMock(), MagicMock(), MagicMock()
        model = model_factory.from_pretrained.return_value
        model.to.return_value = model
        transformers = SimpleNamespace(AutoTokenizer=tokenizer_factory,
                                       AutoModelForSequenceClassification=model_factory)
        with patch("finscope.finbert_backend.verify_snapshot", return_value=pinned_manifest()), \
                patch("finscope.finbert_backend.runtime_versions", return_value=RUNTIME), \
                patch.dict("sys.modules", {"torch":torch,"transformers":transformers}), \
                patch.dict(os.environ, {}, clear=False):
            LocalFinBERTBackend.from_snapshot(Path("local_fixture"), accept_weight_license=True)
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
        model_factory.from_pretrained.assert_called_once()
        flags = model_factory.from_pretrained.call_args.kwargs
        self.assertEqual(flags, {"local_files_only":True,"trust_remote_code":False,"use_safetensors":True})
        self.assertTrue(tokenizer_factory.from_pretrained.call_args.kwargs["local_files_only"])
        model.to.assert_called_once_with("cpu")
        model.eval.assert_called_once()

    def test_default_preview_never_loads_snapshot_or_optional_runtime(self):
        with patch("finscope.finbert_backend.LocalFinBERTBackend.from_snapshot") as load, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run([]), 0)
            self.assertEqual(json.loads(output.getvalue())["inferences_executed"], 0)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
