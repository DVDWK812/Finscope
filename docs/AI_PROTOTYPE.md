# Independent AI interface prototype — 25 October 2026 Sydney

**Latest status (26 October): a pinned local CPU backend has run three authored synthetic fixtures in two smoke runs. Actual outputs are below, separately from the mock contract tests. No API data or Streamlit connection; accuracy remains unmeasured.** The original 25 October interface-only checkpoint is retained below as historical design context. This is the user's separately authorized prototype work; it does not close the Phase 1.5 source gates or approve Phase 2 production integration.

## Module boundaries

`finscope.ai_prototype` imports only the standard library. Its inputs are deliberately different from API `Article` objects and UI records. There is no adapter from real news, and raw strings/API records are rejected by the public inference methods. Model backends must be explicitly injected; an unconfigured interface raises an error rather than returning heuristic or fabricated predictions.

| Contract | Input | Output / behavior |
|---|---|---|
| `EvaluationText` | Nonempty text, origin `synthetic` or `licensed`; licensed requires a permission reference | Frozen input with text/reference omitted from repr; caller attests provenance, not an automated rights check |
| `SentimentBackend.predict` | Sequence of permitted text strings, transiently passed by the interface | One mapping of all three named probabilities per input |
| `FinBERTInterface.predict` | List/tuple of `EvaluationText`, explicit backend identity/revision | Positive/negative/neutral probabilities, selected label, model/revision and input origin; no input text |
| `EmbeddingBackend.encode` | Sequence of permitted text strings | One equal-dimensional finite, nonzero vector per input |
| `EmbeddingSimilarity.compare` | List/tuple of `EvaluationText`, explicit backend identity/revision | One cosine score per unordered pair, input indices and model/revision; no text, duplicate classification or automatic clustering |

Both interfaces cap a batch at 32 texts and each text at 2,000 characters. Embeddings must have 1–4,096 dimensions. Zero vectors, NaN/infinite/boolean values, mismatched counts/dimensions, malformed labels and invalid probabilities are rejected. Sentiment requires all three labels and probabilities in [0,1] summing to one (absolute tolerance 1e-6); it does not invent missing classes or renormalize broken output. Exact ties use neutral first as a deterministic convention, not evidence of neutrality. Cosine uses normalized vectors for numerical stability and clamps floating-point roundoff to [-1,1]. A high cosine score is not proof of a shared financial event.

Backend errors are replaced by fixed messages without input/error-body echo or retries. Outputs are returned in memory; this module has no writer/cache. A supplied backend itself must obey local-only/no-logging policy. The interface cannot audit arbitrary injected code, verify a caller's licence attestation or prevent deliberate relabelling of news. Do not mark provider content synthetic/licensed to bypass the source gates.

Explicit model IDs and revision identifiers are required when injecting a backend; common mutable names such as `main`/`latest` are rejected. Identity strings are provenance claims, not downloaded artifact verification. A future genuine model loader must verify a fixed artifact revision, tokenizer, label mapping, weight licence and offline load policy separately. Character bounds are **not tokenizer limits**: the future local adapter must measure tokens and reject/report over-limit inputs rather than silently truncate. No such loader, tokenizer or heavy dependency is introduced here.

## FinBERT mapping and model permissions

The official [ProsusAI/finbert model card](https://huggingface.co/ProsusAI/finbert), checked on 25 October Sydney, describes three labels and all-class scores. A future local adapter can map all-class outputs to the interface's named fields; it must use that specific pinned model's configuration rather than assume another model's `LABEL_0` order. No Transformers/PyTorch backend is installed or called by this prototype.

The current model card lists the weights under **CC BY-NC-SA 4.0**, with third-party training-data rights and use-case responsibilities separate. The repository software's MIT licence does not license those weights, publisher inputs or every derived use. Confirm the intended noncommercial use, attribution/share-alike obligations and deployment scope before loading or distributing a model. No weight-licence clearance is claimed. No embedding model has been selected or downloaded; its model/data/output terms require a separate review.

Marketaux display, metadata/description retention, team review, inference and derived-output permissions remain unresolved. None of its nine prior samples is an AI prototype input. NewsData remains manually paused; GDELT's one-shot completed with transport failure on 25 October and its task was deleted. Do not recreate or retry it. Synthetic Streamlit data remains on its existing separate repository path.

## What the tests establish

All new AI tests use invented texts and mock probability/vector backends. A licence-reference validation test also uses invented, team-authored text, not an external licensed corpus. Fixture names/model IDs make this distinction explicit.

- Provenance/size gates reject raw API records, untagged strings, absent permission references and oversized batches/text before backend invocation.
- Known fixture probabilities verify mapping, count/label/score checks, model provenance and tie handling.
- Hand-assigned vectors verify identical, orthogonal and opposite-vector cosine, dimension/norm checks and large-finite-value stability. These vectors are not produced by a trained embedding model.
- Default interfaces make no network call; exceptions are sanitized and not retried. Empty batches do not invoke backends.
- No sentiment accuracy, calibration, semantic-similarity accuracy, event precision/recall, real model runtime or source fitness is measured.

Preview without models, data or writes:

```powershell
.venv/Scripts/python.exe -m finscope.ai_prototype --dry-run
```

Before any accuracy claim, use a permitted, independently labelled evaluation corpus with an agreed task, fixed model/tokenizer versions, split/leakage policy, metrics and failure analysis. Relevance/description annotation is a different task from sentiment classification; synthetic contract tests cannot establish either model's accuracy. Real-news/model/UI integration remains **NO-GO** pending all source, model, input/output-rights and evaluation gates.


## Local FinBERT backend — 26 October 2026 Sydney

`finscope.finbert_backend.LocalFinBERTBackend` implements the sentiment protocol using optional Transformers/PyTorch CPU dependencies in a separate ignored `.venv-ai`. The API/UI requirements and environment are unchanged. Optional direct runtime pins are in `requirements-finbert.txt`: torch 2.14.1+cpu, transformers 5.20.2, huggingface-hub 2.3.0, safetensors 0.8.0, tokenizers 0.23.3. Dependency installation was explicit setup, not an import/startup side effect.

**Model pin:** ProsusAI/finbert, revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`. The official [model metadata](https://huggingface.co/api/models/ProsusAI/finbert) identified this revision and its safetensors LFS SHA-256. The [pinned model card](https://huggingface.co/ProsusAI/finbert/blob/0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031/README.md) identifies **CC BY-NC-SA 4.0** for the weights. Attribution: ProsusAI / MIH AI B.V., FinBERT (Dogu Araci, 2019). The observed licence supports considering this noncommercial synthetic research smoke run, not unrestricted commercial deployment, publisher-data use or every downstream output use. Attribution, noncommercial/share-alike terms and third-party training-data responsibilities remain separate from our MIT software. No weights or model-card copy is committed or redistributed in Git.

For this requested backend test, explicitly prepared six official files in ignored `models/finbert/<revision>/`: README.md, config.json, special_tokens_map.json, tokenizer_config.json, vocab.txt and model.safetensors. This was a deliberate pinned asset-preparation step, **not an automatic download by the inference backend**. `finscope/finbert_manifest.json` commits only file sizes/hashes and model/licence metadata. The 437,965,908-byte safetensors file matched official LFS SHA-256 `e5897858ff819aad7629b96ce521ae5477952d03634ef5dd30ed2d76357a9f00`; all six file hashes are checked before loading. Missing, modified, symlinked or additional snapshot files are rejected, including unverified adapter configuration.

The loader requires explicit weight-licence acknowledgement, exact runtime versions, the verified local directory, `local_files_only=True`, `trust_remote_code=False`, and safetensors-only weights. It forces hub offline/telemetry-disabled settings before optional imports, uses CPU/eval/inference_mode with one CPU thread, and has no remote fallback. A licence acknowledgement is an operator attestation, not an automatic legal determination. No model weight use is enabled for API or Streamlit startup.

The tokenizer checks lengths **including special tokens** with truncation disabled, before padding or any model forward. More than 512 tokens is rejected, rather than silently shortened. Batch/character bounds remain 32/2,000. The 512/513-token branch tests use a fake tokenizer and are explicitly unit tests; an actual tokenizer probe produced 702 tokens and was blocked before model forward in each real smoke run. The loader validates the pinned configuration and maps named scores from `id2label` rather than guessing class order. Use it through FinBERTInterface/EvaluationText, preserving synthetic/licensed provenance; its low-level `predict` method is a backend seam, not permission to pass real news.

### Observed actual CPU inference, separate from mocks

The three fixture texts are invented in `SYNTHETIC_FIXTURES`: Solara reports profit growth, reports a loss, and schedules a shareholder meeting. They are not copied headlines, publisher descriptions or a labelled benchmark. Two explicitly invoked local runs each processed these same three texts in **one model-forward batch**, with no news-provider calls, training, model services or remote inference. Their probabilities reproduced exactly on this local environment. This is runtime/contract evidence, not an accuracy or general determinism claim.

| Synthetic fixture | Actual tokens incl. special | Actual label | P(positive) | P(negative) | P(neutral) |
|---|---:|---|---:|---:|---:|
| synthetic_growth | 16 | positive | 0.959612 | 0.017436 | 0.022952 |
| synthetic_loss | 15 | negative | 0.008401 | 0.973977 | 0.017622 |
| synthetic_notice | 14 | neutral | 0.018273 | 0.095831 | 0.885896 |

First run load-stage/inference: **5,555.54 / 80.86 ms**. Verified rerun: **4,700.08 / 80.38 ms**. The load stage includes snapshot hash verification, runtime imports and model loading. Inference includes interface validation/tokenization/padding/forward/softmax. These are single-machine measurements, not service latency guarantees. Exactly two smoke runs were made, not six distinct evaluation examples. The over-limit probe never added a forward batch. No independent labels, held-out corpus, accuracy/calibration metric or finance-event matching evaluation exists.

Ignored evidence: `reports/finbert_real_synthetic_20261026.json`, `reports/finbert_real_synthetic_verified_20261026.json`, dependency-install log and preservation manifest. The committed table is rounded; full probabilities remain local. All core CI tests run offline with mocks and without optional runtime/weights; those results are **not** described as real inference. Eight new backend unit tests validate hashes, safe loading flags, version/licence gates, token bounds and offline defaults.

Preview with the lightweight environment (no model/files loaded):

```powershell
.venv/Scripts/python.exe -m finscope.finbert_backend --dry-run
```

To reproduce the synthetic-only smoke run after explicitly installing the optional pinned runtime and manually preparing/verifying the six files, use the isolated environment:

```powershell
.venv-ai/Scripts/python.exe -m finscope.finbert_backend --synthetic-demo --accept-weight-license --model-dir models/finbert/0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031
```

The command cannot download missing files and does not authorize real-news evaluation. The embedding interface remains mock-tested only; no embedding weights/backend were selected or loaded. Model-quality, provider input/output rights and all source release gates remain open. **Production integration stays NO-GO.**
