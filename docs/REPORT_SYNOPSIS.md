# FinScope — team report synopsis

Evidence current: **29 October 2026 Sydney**. The three team members write the
academic report independently. This is a concise factual reference, not a submission
manuscript or PDF. The user confirmed there are **no required section headings**;
the organization below is optional. No Moodle access or coursework submission.

## Objective and current scope

- Inspect financial news text through sentiment, explainable sectors, original
  evidence and possible semantic overlap; no price forecasting or market-impact claim.
- **Latest architecture:** single-user Streamlit on localhost, persistent local
  SQLite, `.env`/masked credentials, default pinned CPU FinBERT/MiniLM, optional
  local Ollama or explicitly consented external LLM. This task now uses the
  user-requested **local** branch; a separate task owns the web showcase on main.
- Historical approved-input public hosting remains dated engineering evidence;
  cloud hosting/session/cache work is not a local-product requirement.

## Architecture and methods

Source adapter / fixed RBA collector / approved text → preview and distinct usage
permissions → local originals → selected model → versioned SQLite results → shared
filters → Overview, Sector sentiment, Trends, Heatmap, Evidence graph and Explorer.
[Implementation/evidence](LOCAL_REDESIGN.md), [local setup](../README.md).

- Provider calls require explicit Fetch, current available budget, durable intent,
  spacing and existing holds; no retries/pagination. Finnhub is ticker-specific,
  NewsData remains manually paused and GDELT has no new route/retry. Source URLs,
  exact published/first-seen/submitted meanings and date-only precision are preserved.
- FinBERT supplies genuine three-class text-tone probabilities. MiniLM uses
  attention-mask mean pooling and normalized 384-dimensional vectors. Pretrained
  pinned/hash-verified models; no team training or fine-tuning. Preparation is explicit,
  with local-only inference and no download/remote-code fallback.
- Keyword sectors are multi-label, with Unclassified. Cosine ≥0.80 within 72 hours
  compares representatives and creates **unverified candidates**; order matters.
  Exact-time absence disables temporal grouping. Raw originals remain the counting
  basis; model history and candidate members are retained. Neither event deduplication
  nor factual contradiction detection is validated.
- All views share raw-article filters and latest matching model per original.
  Heatmaps retain missing/low-sample counts. Graph links show source metadata,
  matched sector terms, ticker-query provenance and unverified candidates; no causation.
- Optional OpenAI structured labels/rationales require transmission permission and
  explicit send consent, and have **no invented calibrated probabilities**. Ollama
  uses installed local GGUF metadata/digests at loopback only. Keys never enter the
  database/export/logs. Stored permissions do not themselves grant publisher rights.

## Verified results and qualifications

| Evidence | Result | Qualification |
|---|---|---|
| Frozen challenge sentiment | **12/16 scorable agreement (75%); macro-F1 0.730159** | B02/B07 mixed/uncertain excluded; all 18 outputs retained; reviewer independence/completion unverified |
| Selected-pair cosine candidates | **Precision 0.666667**, recall 1.000000, F1 0.800000 | Ten scorable pairs: TP2/FP1/FN0/TN7; P07/P12 uncertain identity excluded; unannotated pairs are not negatives |
| Selected final groups | TP2/FP0/FN0/TN8 on those ten | Does not validate deduplication; uncertain P07 still groups |
| Earlier authored pilot | 12/12 sentiment agreement; group-pair precision 0.60 across 66 pairs | AI-assisted convenience labels; development evidence, not independent accuracy |
| Local redesign regression | **233 offline tests + benchmark dry run passed** | Mocks/authored fixtures; actual provider/model/browser observations recorded separately |
| Actual local Marketaux preview | First request HTTP 200 / three records | Second bounded request failed transport, no HTTP response observed, no retry; downstream rights remain gated |
| Actual licensed RBA import | One attributed RSS record imported, publisher URL opened, actual FinBERT Neutral saved | RBA-authored title/summary only, reviewed CC BY 4.0 terms; no new collection or external transmission; original 14 October publication time retained |
| Actual RBA model smoke | Positive .240000412 / Negative .010126807 / Neutral .749872804; **148.81 ms** combined inference | Excludes model loading/download; one engineering probe, not accuracy evidence |
| Actual authored local smoke | Positive .952975631 / Negative .021392226 / Neutral .025632165; **136.73 ms**, later per-article **58.67 ms** | Two versions retained with the original; no consumed-challenge input |
| Historical hosted checks, 29 October | p1/p2/n3 inference 170/128/119 ms; 6.944 s prepared-file cold load; 880.2 MiB current RSS | Historical approved-text checks, not peak memory/SLA/hibernation or current showcase behavior |

Frozen risks: **P02** crosses Celadon quarters at cosine **0.813457**; incidental
representative selection kept final groups apart. **P07** has uncertain identity /
opposed Tern outcomes and groups at **0.962896**. B01/B10 Positive references and
B08/B16 Neutral references were predicted Negative. All evaluation submission times
were equal; publication/period extraction was not evaluated. [Frozen method/results](CHALLENGE_EVALUATION.md).
The consumed packet, locked reference and original human evidence are unchanged;
never rerun/tune/rescore it. [Freeze](DELIVERY_FREEZE.md).

## Completed and outstanding evidence

Completed: local source/permission/model interfaces, persistent originals/history,
visual views, real authored/RBA local inference and original-link/import checks.
M1 and the M2 compatibility repair passed both exact-commit Python 3.11 CI jobs;
the initial M2 Streamlit-1.50 failure is preserved, not hidden. Local code commit
`94dc5a0` also passed both exact-commit jobs and all 233 tests in [Actions
40856308281](https://github.com/DVDWK812/Finscope/actions/runs/40856308281). [Full dated evidence and limits](LOCAL_REDESIGN.md).

Pending: Marketaux downstream rights and stable availability; NewsData resumption
if explicitly authorized; live Ollama inference (discovery reported unavailable);
live external API account/model verification (zero real article transmissions);
reviewer provenance/attestations, **three actual human usability records**, rehearsal
and team-authored contributions. Agent-operated browsers are not participants.
Small fictional/provisional references do not estimate general news accuracy or
calibration. Source scopes and model/publisher licences remain distinct.

Internal target: **31 October**. Historical Friday/Week 8 23:59 Sydney and
10 November 00:00 remain unverified conflicting deadline information; the user
will confirm personally. [Assessment notes](ASSESSMENT_VERIFICATION.md).

## Reference suggestions

Teammates should read and format their own references; literature results are not
FinScope validation. Primary-source details checked 29 October.

- Dogu Araci (2019), [FinBERT](https://arxiv.org/abs/1908.10063), arXiv:1908.10063 — domain sentiment background.
- Nils Reimers and Iryna Gurevych (2019), [Sentence-BERT](https://aclanthology.org/D19-1410/), EMNLP-IJCNLP, pp. 3982–3992, DOI 10.18653/v1/D19-1410 — embeddings/cosine, not event-identity validation.
- [Pinned FinBERT card](https://huggingface.co/ProsusAI/finbert/blob/0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031/README.md) and [pinned MiniLM card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md) — CC BY-NC-SA 4.0 / Apache-2.0 model terms and exact revisions.
- [Local interface/licence sources](LOCAL_REDESIGN.md), [provider evidence](API_EVALUATION.md), [development log](DEVELOPMENT_LOG.md) and [AI assistance record](CONTRIBUTIONS_AND_AI_DISCLOSURE.md) — actual engineering assistance and pending human claims.

Maintenance: update dated verified facts and preserve historical qualifications;
the team owns academic interpretation, authorship and submission.
