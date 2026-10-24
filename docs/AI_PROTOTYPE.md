# Independent AI interface prototype — 25 October 2026 Sydney

**Implemented contracts and synthetic tests only. No weights loaded, real model inference, model downloads, provider data or Streamlit connection. Accuracy and model latency are unmeasured.** This is the user's separately authorized prototype work; it does not close the Phase 1.5 source gates or approve Phase 2 production integration.

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

Marketaux display, metadata/description retention, team review, inference and derived-output permissions remain unresolved. None of its nine prior samples is an AI prototype input. NewsData remains manually paused; GDELT's scheduled one-shot is untouched. Synthetic Streamlit data remains on its existing separate repository path.

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
