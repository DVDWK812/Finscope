# FinScope — team report synopsis

Evidence current: **31 October 2026 Sydney**. The three team members write the
academic report independently. This is a concise factual reference, not a submission
manuscript or PDF. The user confirmed there are **no required section headings**;
the organization below is optional. No Moodle access or coursework submission.

## Objective and current scope

- Inspect financial news text through sentiment, explainable sectors, original
  evidence and possible semantic overlap; no price forecasting or market-impact claim.
- **Latest architecture:** single-user Streamlit on localhost, persistent local
  SQLite, `.env`/masked credentials, default pinned CPU FinBERT/MiniLM, optional
  local LM Studio/Ollama or explicitly consented external LLM. This task now uses the
  user-requested **local** branch; a separate task owns the web showcase on main.
- Historical approved-input public hosting remains dated engineering evidence;
  cloud hosting/session/cache work is not a local-product requirement.

## Architecture and methods

Configured, permitted fixed sources → one explicit update action → single local
worker and durable SQLite queue → text/content versions → independent two-level
industry classification → selected local sentiment model → versioned results.
Dashboard, Industries, Knowledge Graph and News Explorer share filters; Settings
retains advanced manual operations. Migration backs up the existing database.
[Implementation/evidence](LOCAL_REDESIGN.md), [local setup](../README.md).

- Provider calls require explicit Fetch, current available budget, durable intent,
  spacing and existing holds; no retries/pagination. Finnhub is ticker-specific,
  NewsData remains manually paused and GDELT has no new route/retry. Source URLs,
  exact published/first-seen/submitted meanings and date-only precision are preserved.
- FinBERT supplies genuine three-class text-tone probabilities. MiniLM uses
  attention-mask mean pooling and normalized 384-dimensional vectors. Pretrained
  pinned/hash-verified models; no team training or fine-tuning. Preparation is explicit,
  with local-only inference and no download/remote-code fallback.
- Product industry topics use versioned US-BUSINESS-1 (11/56, authored business
  topics, not GICS) or CSRC-JRT0020-2024 (official Table 2: 19/91). Literal evidence,
  method and classification history are retained; company business is separate
  and unverified. Macro themes are separate, not a third industry level. The old
  five-sector evaluation rules remain unchanged. Historical cosine ≥0.80 within 72 hours
  compares representatives and creates **unverified candidates**; order matters.
  Exact-time absence disables temporal grouping. Raw originals remain the counting
  basis; model history and candidate members are retained. Neither event deduplication
  nor factual contradiction detection is validated.
- All views share raw-article filters and latest matching model per original.
  Heatmaps retain missing/low-sample counts. Graph links show source metadata,
  matched sector terms, ticker-query provenance and unverified candidates; no causation.
- LM Studio uses local loaded IDs/quantization and JSON Schema sentiment/rationale,
  with explicit resource-checked load/unload and no downloads or tool/search calls.
  Optional OpenAI structured labels/rationales require transmission permission and
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

30 October local usability check: **261 offline tests** plus dry run; actual browser RBA local import, pinned FinBERT reanalysis (Neutral), SQLite history, sector results, original URL, and heatmap/graph node clicks verified. Two originals remain two after reanalysis; no new news API or external LLM requests. Ollama service discovery unavailable; live inference remains pending. This is engineering acceptance, not accuracy or human usability evidence.

30 October real-source follow-up: ABS robots/index HTTP 200 at 29 October 16:18 UTC yielded **20 new licensed headlines/date-only records**, saved and actually analyzed by pinned local FinBERT/MiniLM; one reanalysis added history, not an original. Real library: ABS 20 + existing RBA 1, 27 August–29 October; Energy 1, Financials 1, Unclassified 19 (authored development text excluded). Three classified sectors remain unmet. ACCC RSS returned 403 once and is disabled. Browser heatmap/article/sector-node clicks and ABS original verified; source text is headline-only. These checks are engineering acceptance, not an accuracy evaluation; frozen evidence remains unchanged.

31 October local LLM check: actual `google/gemma-4-e4b` GGUF/Q4_K_M, context 2048, returned valid structured Positive labels in four authored-text requests (single, two-item batch and detail reanalysis), 1.72–2.69 s per request excluding load. SQLite retained originals and all versions; no probability invented. `qwen/qwen3.8-27b` Q4_K_M was discovered but not loaded/inferred: observed free RAM 9.10 GiB / VRAM 8.25 GiB were below the conservative 15.09 / 11.42 GiB thresholds. These are engineering checks, not accuracy evidence. No news/OpenAI requests or frozen-challenge inference occurred.

31 October Qwen retry, explicitly requested by the user: free RAM/VRAM had risen to 18.08/12.07 GiB immediately before load, so the unchanged safety checks permitted `qwen/qwen3.8-27b` Q4_K_M at context 2048 / 50% GPU offload, with Gemma unloaded. One actual browser-triggered request on the same authored fixture returned HTTP 200, valid structured Positive output and rationale in 15.47 s; SQLite retained 23 originals and increased history from 29 to 30 versions. Dashboard and detail displayed the Qwen result. This supersedes the earlier resource blockage for this measured attempt only, not an accuracy or sustained-load claim.

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

31 October local P0 engineering acceptance: two explicit browser updates fetched
21 new real originals (20 NIST, one ABS); the real library is ABS 21 / NIST 20 /
RBA one, dated 29 June–30 October. Three actions used eight bounded collector GETs,
separate from parsed-record counts. ABS successfully supplied one licensed body
(1,675 characters); analysis used a traceable leading 1,349-character excerpt.
NIST supplied permitted RSS summaries, but its first body extraction failed on
changed markup. Summary fallback and the existing failure-day hold remained;
the selector repair was checked offline against actual browser-observed DOM,
not claimed as a second successful body fetch. No news API/OpenAI dispatch.

At the user's request Qwen was unloaded and Gemma selected. Fifty real Gemma
HTTP-200/schema-valid versions were added (including one explicit body reanalysis),
covering 40 current real originals; two older originals remain pending. No LLM
probabilities were invented. Dictionary classification currently evidences three
primary/four secondary topics across seven originals; 35 are unclassified.
This is limited official/research coverage, not broad US-equity coverage or an
independent accuracy evaluation. Optional local LLM classification has mock
validation only. All prior database rows and 171 frozen files are unchanged.

The worker continued while the only app tab was closed; reopening showed the
same advancing job. Actual graph, word-cloud and date/sector heatmap clicks
opened matching originals. A graph-detail insertion could move and blank the
cloud iframe: a failing-before regression now verifies stable host positions.
370 offline tests and benchmark dry run pass; no external calls occur from
view/filter/refresh actions. Browser operation is engineering evidence, not
three independent human usability participation.

31 October P1 presentation acceptance: local pages adapt the read-only main
`f2fade9` dark palette, icon navigation and chart cards. A shared accessible
article-row picker/details component is used by Explorer, Industries, graph,
cloud and heatmap; keyword snippets highlight literal body/summary matches.
Date/model/catalog/page/article-focus preferences survive reload without new
jobs. Missing CSRC classifications are explicitly pending, not evidence of no
relevant news. Desktop, 820px tablet and 390px mobile checks use the existing real
library; no new collection, inference or accuracy evaluation. 384 offline tests
and benchmark dry run pass; all protected data and frozen evidence are unchanged.

31 October P1.1: persistent dark/light and English/Chinese presentation covers
five local pages, advanced controls and chart iframes, preserving original news
and model outputs. 400 offline tests and dry run pass; browser assertions cover
60 page/mode/viewport combinations. Native framework English calendar/auxiliary
labels and Codex-preload MutationObserver exceptions qualify browser acceptance.
No new news collection, model inference or evaluation was performed.

31 October settings/runtime refinement: three settings tabs, conditional source
and key editors, offline drafts and separate run checks reduce duplicate controls.
Actual browser startup restored installed LM Studio on 127.0.0.1:1234; refresh
reused the process and showed both downloaded models unloaded. DeepSeek has a
separate capped authored-text test with strict JSON/history validation, but no
local key or live request; mock success is not real inference evidence. All 442
offline tests pass on Streamlit 1.50 and 1.66.1, plus dry run. Protected news,
history, jobs and frozen evidence are unchanged. A test initially wrote a dummy
Marketaux vault entry; it was removed and tests isolated. The .env is unchanged;
any previously different vault value cannot be reconstructed (development log).
