import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from finscope.embedding_backend import LocalSentenceEmbedder
from finscope import model_assets


class EmbeddingAssetTests(unittest.TestCase):
    def test_embedding_256_token_boundary_no_silent_truncation_or_forward(self):
        encoder=LocalSentenceEmbedder()
        encoder.tokenizer=Mock(return_value={"input_ids":[list(range(256))]})
        encoder.model=Mock(side_effect=AssertionError("No forward for invalid input"))
        self.assertEqual(encoder.tokenize(["synthetic"])[1],[256])
        self.assertFalse(encoder.tokenizer.call_args.kwargs["truncation"])
        encoder.tokenizer.return_value={"input_ids":[list(range(257))]}
        with self.assertRaises(ValueError):encoder.encode(["synthetic"])
        encoder.model.assert_not_called()
        for value in ([" "],["x"*2001],["x"]*33):
            with self.assertRaises(ValueError):encoder.tokenize(value)

    def test_loader_requires_verified_local_safetensors_and_disables_remote_code(self):
        fake_torch=SimpleNamespace()
        tokenizer_factory=Mock();model_factory=Mock()
        fake_transformers=SimpleNamespace(AutoTokenizer=tokenizer_factory,AutoModel=model_factory)
        with patch.dict("sys.modules",{"torch":fake_torch,"transformers":fake_transformers}), \
             patch("finscope.embedding_backend.verify",return_value={"revision":"pinned","model_id":"fixture"}), \
             patch("finscope.embedding_backend.runtime_versions"):
            encoder=LocalSentenceEmbedder.load(Path("explicit-model-directory"))
        self.assertEqual(encoder.revision,"pinned")
        self.assertEqual(model_factory.from_pretrained.call_args.kwargs,
                         {"local_files_only":True,"trust_remote_code":False,"use_safetensors":True})
        self.assertTrue(tokenizer_factory.from_pretrained.call_args.kwargs["local_files_only"])

    def test_cached_preparation_makes_no_http_and_integrity_rejects_changed_or_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"weights").write_bytes(b"authored test bytes")
            spec={"model_id":"fixture","revision":"pinned","files":{"weights":{
                "size":19,"sha256":hashlib.sha256(b"authored test bytes").hexdigest()}}}
            spec["files"]["weights"]["size"]=len(b"authored test bytes")
            with patch.object(model_assets,"manifest",return_value=spec), \
                 patch.object(model_assets,"model_directory",return_value=root), \
                 patch("requests.get",side_effect=AssertionError("No HTTP when cached")):
                model_assets.prepare_models(acknowledge_licenses=True)
                (root/"extra").write_bytes(b"unexpected")
                with self.assertRaises(ValueError):model_assets.verify("fixture")
                (root/"extra").unlink();(root/"weights").write_bytes(b"changed test bytes ")
                with self.assertRaises(ValueError):model_assets.verify("fixture")

    def test_preparation_requires_explicit_acknowledgement_before_http(self):
        with patch("requests.get",side_effect=AssertionError("No HTTP before acknowledgement")):
            with self.assertRaises(ValueError):model_assets.prepare_models()
