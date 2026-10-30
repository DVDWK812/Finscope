# FinScope — team report synopsis

Evidence current: **31 October 2026 Sydney**. The three team members will write the academic report independently. This concise reference supplies facts and expansion cues; it is not a submission manuscript or PDF.

**31 October public closeout:** final link/setup corrections pass 236 offline tests,
syntax checks and seven previews; exact-commit CI for
`4b1e409941a7861a34658e7fde15d15d3e41a0b8` passes both regression jobs and
showcase isolation. All six hosted pages passed four-size acceptance; maintenance-only status and
limitations are recorded in the
[freeze record](SHOWCASE_FREEZE.md). The site retains 24 authored fictional
records, readable article labels, three unverified multi-report topic groups,
exact headline-frequency lookup and the premium presentation. These are agent
engineering checks, not human usability or accuracy evidence. No frozen metric or
fixture changed; this task leaves the separate local product untouched.
`main` stays the deployed/default branch; the
proposed `web` rename is deferred to protect the existing app and administration.

**Latest architecture correction, 29 October:** the product is now a local-first
single-user Streamlit application on localhost with persistent local SQLite.
The existing public URL is now designated an independent synthetic-only product showcase; the functional AI application stays local. See [surface separation](PUBLIC_SHOWCASE.md).

The showcase is deployed and browser-checked: six views, 24 fictional records,
synthetic dashboard/graph/explorer and full-local setup guidance. It has no
provider/model/database runtime or credential input. The isolated committed-main
separation baseline passed 220 tests; the earlier 1.50 test-API incompatibility and repair
are retained in the separation evidence. Existing local inference remains verified
by a separate approved authored-text smoke; frozen challenge results below are unchanged.
Milestone 1 delivered first-run guidance, masked/.env provider connectors and
separate fetch/preview/storage/NLP permissions. One actual local Marketaux request
returned HTTP 200 / three preview records; their downstream rights remain gated.
A separate approved authored-text browser run verified pinned local FinBERT/MiniLM,
saved probabilities and sector analytics; 202 offline tests passed. Details and
remaining milestones: [local redesign evidence](LOCAL_REDESIGN.md). Historical
measurements below retain their original scope; the frozen challenge is unchanged.

**Structure:** the user confirmed on 29 October that there are **no required section headings**. The outline below is for team reference and can be expanded freely ([assessment notes](ASSESSMENT_VERIFICATION.md)). No Moodle access is permitted.

## Objective and scope

- Demonstrate inspection of approved financial text: sentiment, explainable sectors and possible report overlap. No price forecasting or market-impact inference.
- Delivered local product: provider preview, permitted FinBERT/MiniLM, persistent SQLite and raw-original analytics. The [public site](https://finscope-dvdwk812.streamlit.app/) is an illustrative showcase, with fictional previews and local setup guidance; it has no provider/model/database runtime.
- Expansion cue: explain the finance use case and why preserving original reports matters; distinguish an approved-input demonstration from production news ingestion.

## Architecture and methods

Approved text → provenance/length/time checks → pinned local FinBERT probabilities + MiniLM embeddings → keyword sectors/cosine candidates → persistent local SQLite → Overview, Trends, heatmap, evidence graph, News Explorer and JSON export. The public showcase is a separate presentation path. [Implementation](../finscope/demo_pipeline.py); [model evidence/pins](AI_PROTOTYPE.md).

- FinBERT: Positive/Negative/Neutral text tone. MiniLM: attention-mask mean pooling, normalized 384-dimensional vectors. Pretrained models; no team training or fine-tuning.
- Cosine ≥0.80 within 72 hours compares representatives and creates **unverified candidates**. Order/representative selection matters. Raw articles are the default; candidate summaries are optional. Explorer/export retain originals. Opposing model tone is a review flag, not factual contradiction detection.
- Explicit asset preparation; hash-verified local-only inference, no remote code/download fallback. Source and published/first-seen/submitted meanings remain distinct; submitted URLs are not fetched. The current local library persists across restarts. Temporary session storage/purge-on-access describe the historical hosted demo, not the new showcase.
- Evaluation: one unchanged-pipeline run on 18 fictional texts, using a reference locked before predictions. User supplied two reviewer submissions and adjudication decisions. **Reviewer independence and completion attestations remain unverified.** All evaluation submission times were equal; publication/period extraction was not tested. [Frozen method](CHALLENGE_EVALUATION.md).

## Actual results

| Evidence | Verified result | Qualification |
|---|---|---|
| Frozen challenge sentiment | **12/16 scorable agreement (75%); macro-F1 0.730159** | Two mixed/uncertain references, B02/B07, excluded from three-class scoring; all 18 outputs retained; 16/18 coverage |
| Selected-pair cosine candidates | **Precision 0.666667**, recall 1.000000, F1 0.800000 | Ten scorable pairs: TP2/FP1/FN0/TN7; P07/P12 uncertain identity excluded; unannotated pairs never negatives |
| Selected final groups | TP2/FP0/FN0/TN8 on those ten | Does not validate deduplication; uncertain P07 still groups |
| Earlier authored pilot | 12/12 sentiment agreement; final-group pair precision 0.60 across 66 pairs | AI-assisted convenience labels; development evidence, not independent accuracy ([pilot](MVP_EVALUATION.md)) |
| Engineering checks, 29 October | 182 offline tests; benchmark dry run; hosted p1/p2/n3 inference and filtered export passed | Mocks and agent-operated development-text checks, not human usability or challenge repeats ([freeze checks](DELIVERY_FREEZE.md)) |
| Same hosted smoke | 170/128/119 ms combined inference; 6.944 s prepared-file cold model load; 880.2 MiB current RSS | Three probes; not installation/download time, peak memory, load guarantee or SLA |

Failures to explain: **P02** crosses Celadon reporting quarters at cosine **0.813457**; incidental representative selection kept final groups separate. **P07** has uncertain identity/opposed Tern outcomes and groups at **0.962896**. B01/B10 Positive references and B08/B16 Neutral references were predicted Negative. [Complete retained results](CHALLENGE_EVALUATION.md).

## Limitations and outstanding evidence

- Small, dependent fictional examples and provisional user-adjudicated references do not estimate general financial-news accuracy or calibration. No challenge sector ground truth. Neither event deduplication nor contradiction detection is validated; sentiment is not investment advice.
- Completed: actual model integration, public approved-input demo, preserved frozen evaluation, regression/host checks and [three-human test template](USABILITY_EVIDENCE_TEMPLATE.md).
- Pending: reviewer provenance/attestations, three actual human usability records, rehearsal and team-authored contribution confirmations. Programmatic sessions are not people. Long-term hosting endurance/hibernation/peak memory remain unverified. Cloud displays no build SHA; the release record distinguishes exact-commit CI from actual served behavior.
- Production provider rights/quality remain unresolved; provider query scopes differ ([source evaluation](API_EVALUATION.md), [decisions](DECISIONS.md)). Model licences do not authorize publisher-content reuse. Internal target: 31 October; both historical deadline values remain unverified in the assessment notes.

## Reference suggestions and factual sources

Primary-source details checked 29 October; teammates should read relevant sections and format their own references. Literature results are not FinScope validation.

| Suggested reference | Use in the team's writing |
|---|---|
| Dogu Araci (2019), [*FinBERT: Financial Sentiment Analysis with Pre-trained Language Models*](https://arxiv.org/abs/1908.10063), arXiv:1908.10063 | Financial-domain sentiment background |
| Nils Reimers and Iryna Gurevych (2019), [*Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*](https://aclanthology.org/D19-1410/), EMNLP-IJCNLP, pp. 3982–3992; DOI 10.18653/v1/D19-1410 | Sentence embeddings/cosine rationale; does not establish event identity |
| [ProsusAI pinned FinBERT card](https://huggingface.co/ProsusAI/finbert/blob/0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031/README.md); [pinned MiniLM card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md) | Exact model/configuration and weight terms: CC BY-NC-SA 4.0 / Apache-2.0 |
| Repository evidence linked above; [development log](DEVELOPMENT_LOG.md), [AI-assistance record](CONTRIBUTIONS_AND_AI_DISCLOSURE.md) | FinScope-specific measurements, provenance, known assistance and pending human claims |

Maintenance: update only when new evidence is verified; attach its date/source and distinguish completed/pending. Preserve historical measurements and all frozen artifacts byte-for-byte; never rerun/tune/rescore the consumed challenge. Retain the user-confirmed absence of required headings; adapt only if the team supplies revised requirements. Codex maintains this synopsis and technical documentation; the members own academic prose, interpretation and final submission. No final-report PDF or coursework submission is generated.

## Local product visual update — 29 October 2026

Milestone 2 adds six shared-filter raw-article views, sample-aware heatmap and
selectable source/sector/ticker-query/unverified-candidate graph with original
article details/history. 213 offline tests and a local browser/restart check passed;
these are engineering checks, not human usability or new model accuracy evidence.
[Current local evidence](LOCAL_REDESIGN.md).
