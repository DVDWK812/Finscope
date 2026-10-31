# Phase 1 / 1.5 decision memo — 2026-10-26 Sydney

**29 October 2026 Sydney — reporting responsibility clarified:** The team independently authors the academic report. Codex maintains a concise [evidence synopsis](REPORT_SYNOPSIS.md), with verified metrics/method qualifications, completed/pending work and primary-source reference suggestions. The old final-report path becomes a pointer; no submission-ready report or PDF is generated. The user confirmed there are no required section headings; the synopsis uses a practical outline without inventing assignment requirements. No Moodle access. The consumed challenge, actual outputs and original private human evidence remain unchanged. Continue technical verification and documentation on main only.

**29 October 2026 Sydney — final delivery freeze:** Preserve the consumed challenge, locked reference, actual outputs and original private human annotation/amendment evidence. No challenge rerun or tuning. Report 12/16 scorable sentiment agreement (75%), macro-F1 0.730159, two mixed/uncertain exclusions and pairwise cosine precision 0.666667. P02 falsely matches reporting periods (cosine 0.813457); uncertain opposed-outcome P07 groups (0.962896). Reviewer independence and completion attestations remain unverified. Raw articles remain the default; event deduplication and contradiction detection are not validated. [Freeze verification](DELIVERY_FREEZE.md), [three-human template](USABILITY_EVIDENCE_TEMPLATE.md) and [demo checklist](DEMO_CHECKLIST.md) preserve these limits. No human sessions, attestations or rehearsal are claimed complete; no private records are published.

**29 October 2026 Sydney — provisional adjudicated challenge:** Proceeded on the user's explicit instruction with a pre-prediction locked user-adjudicated reference; reviewer independence attestations/completion metadata remain unverified. Real FinBERT/MiniLM ran once on 18 fictional texts with no errors or downloads/API calls. Sentiment 12/16 scorable (75%, macro-F1 .730), two mixed/uncertain cases retained. Pair cosine 2 TP/1 FP/0 FN/7 TN on 10 scorable selected pairs, precision .667; uncertain opposing-outcome P07 also grouped. No threshold/model/rule changes. [Complete evidence](CHALLENGE_EVALUATION.md). Preserve raw-default/originals/warnings. GO for limited approved-input demonstration; production source integration and validated event identity remain NO-GO. Independent-human provenance and three-user feedback are not complete.

**27 October 2026 Sydney — grouping display safety:** approved-input counts default to raw articles and Reset restores raw counts. Semantic matches are unverified candidates; candidate chart summaries are opt-in. Explorer lists all matching originals regardless of summary mode, and candidate details include all workspace members even outside filters. Opposing positive/negative model tones trigger a potential contradictory-financial-outcome review flag, without asserting a factual contradiction. Model loading/inference, cosine threshold .80, grouping algorithm, persistence and provider disconnection are preserved. Historical evaluation numbers are unchanged. Four new offline regressions cover opposing-tone detection, original visibility/filter transparency and raw default/reset. 135 tests and benchmark dry run pass; zero news API calls.

**MVP delivery decision (26 October 2026 UTC, latest user scope): GO for a limited noncommercial approved-input demonstration; NO-GO for production provider integration.** Reused the actual local FinBERT backend, added pinned MiniLM mean-pooling embeddings, keyword sectors, session SQLite and the working Streamlit pipeline. [Public inference](https://finscope-dvdwk812.streamlit.app/) is observed, with source/timestamp/permission and raw/candidate semantics retained. No API calls, scheduled requests, provider records or credentials enter the app. The completed/deleted GDELT task remains untouched.

The [12-text authored pilot](MVP_EVALUATION.md) matches all provisional sentiment labels but is not independent accuracy validation. Candidate-group pair precision is .60 (3 TP/2 FP), including opposite-outcome reports; no event-identity or production deduplication claim. Three programmatic workspaces passed isolation/concurrency, not three-human testing. [Human protocol](USER_TESTING.md), [report](FINAL_REPORT.md), [demonstration](DEMO_SCRIPT.md) and [remaining sprint gates](MVP_SPRINT.md) are prepared. Human annotation/usability, hosting wake/restart endurance and assessment signoff remain pending. Model licences permit this scoped noncommercial setup but do not settle publisher rights. Existing source relevance/descriptions/timestamps/history/quota/public display/retention/inference/derived-output gates remain open; no additional API research is prioritized during this sprint.

Recommend **Marketaux as the conditional primary financial-news candidate for continued local sector-keyword evaluation**, based on the staged keyed experiment below. GDELT remains a provisional keyless comparator. No provider is approved as the production source, and Phase 1's complete exit criteria are not satisfied.

**Latest preparation/backend checkpoint (26 October Sydney):** the guarded Marketaux runner is prepared with explicit approval/quota-file gates and no automatic execution; no round has been authorized or scheduled. The completed/deleted GDELT task is not recreated/retried. A pinned local FinBERT CPU backend produced actual outputs on three authored synthetic texts, separately from mock unit tests; accuracy is unmeasured and no real API record entered AI/Streamlit. See [runner preparation](MARKETAUX_RUNNER.md) and [actual synthetic smoke evidence](AI_PROTOTYPE.md#local-finbert-backend--26-october-2026-sydney). Model weights remain subject to CC BY-NC-SA 4.0; the narrow noncommercial smoke run does not clear production/provider rights. **Production remains NO-GO.**

**Latest one-shot evidence (25 October Sydney):** actual GDELT healthcare execution at 2026-10-25T09:02:15.024915+00:00 / 20:02 Sydney is verified by the saved report plus CLI stdout/exit code. The scheduled trigger arrived about eleven hours later than the intended 09:00 Sydney time; the reason is unknown. Exactly **one client request attempt, zero observed HTTP responses**, transport failure after **26,381.9 ms**, exit code 1. Raw/normalized/sample parse counters are zero because no reply was available; coverage, titles, descriptions, relevance and timestamps are **unobserved**, not empty successful results. No retry, optional-provider call, new task or reschedule. Existing holds were honored, not edited. See [the execution audit](API_EVALUATION.md#scheduled-gdelt-one-shot-audit--25-october-2026-sydney). **Production integration remains NO-GO**; Marketaux remains conditional and GDELT provisional.

**Latest readiness checkpoint (25 October Sydney):** description review, durable attempt reservations and budget/spacing/cooldown guards are implemented with offline synthetic tests. The sampler has no default backend/approval and the old keyed Marketaux live CLI is blocked. No sampling round is authorized, executed or scheduled. Independently authorized FinBERT/embedding **interfaces** accept synthetic/licensed evaluation inputs only; no model was loaded or evaluated and no API/UI connection exists. See [implementation safeguards](PHASE15_MARKETAUX_PLAN.md#implemented-safeguards--25-october-2026-sydney) and [AI prototype boundaries](AI_PROTOTYPE.md). Marketaux permissions and all production source/evaluation gates remain open.

**Earlier Phase 1.5 design checkpoint (25 October Sydney):** the [multi-day plan](PHASE15_MARKETAUX_PLAN.md) is designed, not run or scheduled: at most nine new Marketaux requests over three dates, with no retries or catch-up. This review makes zero provider requests and preserves all existing evidence, the NewsData hold and the GDELT schedule. NewsData remains manually paused pending clarification of HTTP 200 with Retry-After, even though its historical timestamp has elapsed. Official Marketaux date filters and free pricing do not establish this account's full historical reach or field-specific display, retention, inference and derived-output rights. Separate [offline findings](API_EVALUATION.md#phase-15-review--25-october-2026-sydney) refine sample quality without establishing model accuracy. **Phase 2 production integration remains NO-GO.**

**Phase 2: NO-GO after the keyed experiment.** Seven successful requests improve observed text/metadata availability but do not resolve multi-day reliability, NLP quality, account/history limits or public display/retention/derived-output rights. The separate GDELT retest remains scheduled and unchanged; no GDELT request was made in this task.

**Parallel UI exception (24 October 2026):** The team may build an offline Streamlit interface using conspicuously labeled synthetic fixtures and a swappable repository contract. This UI-only development is independent of source approval and is **not** Phase 2 model/data integration or a production news dashboard. Live data, model-generated sentiment and provider content remain blocked pending the gates below.

GDELT has the strongest verified reuse basis among the reviewed options: its [dataset terms](https://www.gdeltproject.org/about.html#termsofuse) allow reuse and redistribution with attribution. The original pilot healthcare query returned three usable metadata records. In that original three-request pilot, two replies were HTTP 429, the successful request took 20.2 seconds, and all three accepted records lacked descriptions and publication timestamps. This supports further metadata research only; it does not establish adequate text input for a future sentiment model.

Marketaux now has actual responses for healthcare, technology and materials: nine sampled records across seven reported sources, all with descriptions/publication timestamps, eight business-relevant titles and one off-topic title. Its sector-keyword contract is the closest fit to the project; public use still needs clarification under its [terms](https://www.marketaux.com/tos). NewsData returned promising healthcare metadata but supplied a hold, so other topics were skipped. Finnhub supplied company-scoped short text, with narrower source attribution and indirect matches; its personal-plan sharing restriction remains material. See the [keyed evidence](API_EVALUATION.md#keyed-provider-experiment--2026-10-24), including the distinct query scopes and [rights comparison](API_EVALUATION.md#rights-decision-by-intended-use).

## Keyed decision evidence — 24 October 2026

All three ignored local `.env` keys were configured and authenticated by actual successful endpoint requests. Stage A made exactly one healthcare request per provider. Only Marketaux/Finnhub passed the expansion timing gate: two more requests each, one per remaining topic. NewsData's HTTP 200 included Retry-After=900; its two omitted topics are skipped/provider_cooldown, not failures or empty coverage. Total **7 requests, 7 HTTP 200, no retry/pagination**. No adapter, UI or model code was changed.

| Candidate | Observed strengths | Decision limits |
|---|---|---|
| Marketaux | 9 sampled records / 7 sources over all three keyword topics; 9/9 descriptions and publication times; mean latency 880.9 ms; 8 relevant / 1 off-topic title | Small single-day sample; source/ranking/geography bias and overlapping healthcare policy items; short descriptions; public-use/retention/derived-output rights unresolved |
| NewsData.io | Healthcare 3 records / 3 sources, 3/3 descriptions and publication times; 2 relevant / 1 uncertain title | Only one topic observed; advertised delay/latest window; saved provider hold; rights clauses need reconciliation |
| Finnhub | PFE/NVDA/FCX access; 274 normalized rows across three symbols, 9 sampled; summaries/publication times present in all samples | Not sector-keyword coverage; sampled source label Yahoo, Finnhub-hosted links; indirect company attribution; personal-plan sharing of data/derived results requires written approval |
| GDELT | Broad dataset reuse basis with attribution; no key | No new call in this task; original rate limits, missing summaries and first-seen-only timestamps remain; scheduled comparator is preserved |

Recommend Marketaux for the next **separately authorized** local reliability/representativeness test and plan-specific permission clarification. Keep NewsData as an unproven broader-news alternative and Finnhub as a company-news comparator. This is a conditional engineering recommendation, not a licence grant or deployment approval. No real records or provider sentiment are connected to Streamlit; the synthetic-only UI exception remains unchanged.

## Historical baseline evidence and outstanding gates

The following baseline predates configured keys and the keyed experiment. Missing-key rows are preserved as historical skips, not current credential status. Current validation uses the isolated project `.venv`: all 66 tests and the keyed dry run pass; exact-head CI is pending at commit time and its post-push result is recorded in Issue #1.

- Baseline: 11 existing offline tests passed; the reviewed pilot has 36 passing offline tests and a passing dry run on `main`. Push-triggered [Actions run 39983651007](https://github.com/DVDWK812/Finscope/actions/runs/39983651007) passed for synchronized main `f432102`; later documentation commits require their own checks.
- Actual API requests: three GDELT requests, one per topic, no retries. Two HTTP 429 failures; one HTTP 200. All nine optional-provider query rows are skipped because this project's `.env` has no keys. No live auth/schema/empty-result claim is made.
- The three healthcare headlines yielded two relevant trade items and one uncertain partnership item. Two stories likely describe the same event. Original links/times and manual annotations are in ignored `reports/phase1_live_20261023.json`; no article text is committed.
- Before closing Phase 1: obtain another-day availability/relevance evidence when practical, resolve rate-limit handling operationally without bypass, test available keyed alternatives at minimum cost, verify retention/history entitlements, and secure necessary public-display/storage/derived-output rights. If summaries are required later, reevaluate the data requirement rather than adding a crawler.
- GitHub connector login is DVDWK812. The user merged [PR #2](https://github.com/DVDWK812/Finscope/pull/2) into public [DVDWK812/Finscope](https://github.com/DVDWK812/Finscope) as `6ae8e00`. Local `main` was safely fast-forwarded through the user's workflow updates to `f432102`; all Phase 1 implementation/tests/evidence files match the merged head. The fully merged feature branch was deleted locally and remotely after verifying zero unique commits. **Use main only: no feature branches, new PRs or force pushes.** [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) tracks feasibility gates; historical unmerged-PR statements describe earlier milestones.
- Confirm the official course code in Moodle. Record Codex assistance accurately in the assignment. No FinBERT, embeddings, crawler or live-data dashboard integration is approved; the separate synthetic-only UI exception remains in force.

## Follow-up release gates

PR #2 was reviewed at `7a656df` and subsequently merged by the user. Commit `2ce44d6` fixes persistent Retry-After/cooldown handling, malformed text/timestamp completeness and missing NLP metrics; these fixes and all 36 passing tests are now on main. The earlier keyed-provider follow-up produced three skipped healthcare rows and zero HTTP requests. Reanalysis found mean title length 77 characters / 11.3 whitespace words, zero descriptions and zero publication timestamps. These are the same three original records, not new sampling.

The one-shot follow-up is scheduled for 25 October 2026, 09:00 Australia/Sydney, subject to local app/computer availability. The 24 October pre-run audit found no execution report and the task is not yet due; this is pending work, not a cooldown skip or a successful test. Updated instructions use main only and allow the already authorized single GDELT healthcare request only after checking for an existing attempt, different-day/24-hour conditions and saved holds. A hold means skipped/provider_cooldown; HTTP 429 ends the attempt without retry. The audit makes no additional provider calls, including optional providers. New evidence or missing execution must update all three documents and Issue #1, and reassess every release gate rather than promote a provider after one success.

| Gate | Current status | Required evidence before Phase 2 |
|---|---|---|
| Repeat availability | OPEN; GDELT different-day attempt failed/transport with no HTTP response; keyed pilot is one-day evidence | Successful multi-day availability and representative samples, not a schedule, failed attempt or seven one-day keyed replies |
| Financial NLP input | OPEN; 21 samples have short text but description semantics not retained | Prospective informative-description labels and independent permitted review; separate validation of the eventual NLP task. Title/URL judgments and presence/length are not model accuracy |
| Time semantics | OPEN; all 9 Marketaux times fit the request window, ages 1.524–42.707 hours | Validate provider timestamp accuracy and required historical window; GDELT remains first-seen only |
| Source / duplicate representativeness | OPEN; 7 Marketaux sources, 9 distinct URLs, 0 exact title repeats, suspected healthcare event overlap | Review per-day/sector concentration, source/URL attribution and event overlap; exact uniqueness is not event recall or model validation |
| Public use and retention | OPEN; GDELT dataset reuse basis strongest; Marketaux API-field rights unresolved | Written free-plan display, cache/retention, team review, local inference and derived-output basis; separately resolve publisher rights and training if relevant |
| History and quota sustainability | OPEN; 100/day and cap 3 documented; X-RateLimit is 60-second window per docs; free-history depth unspecified | Account-specific history/reset/usage evidence; date parameters do not prove historical entitlement. No quota/history probe was made |
| Operational readiness | 115 offline tests pass, including runner/backend mocks; actual synthetic CPU smoke is recorded separately; all five previews pass; exact-head CI pending at commit time | Verify pushed head CI; never repeat/reschedule the completed one-shot. Marketaux sampling still requires explicit authorization and quota/rights checks. NewsData remains manually paused |

GO applies to readiness engineering and separately authorized synthetic/licensed AI-interface testing only. No sampling, production provider selection, real-news inference, crawler or live-data dashboard integration is approved. Synthetic-only UI prototyping remains permitted. No actual FinBERT/embedding model or model accuracy is claimed.

## Execution audit checkpoint — 24 October 2026, 03:20 Sydney

The saved one-shot is **not yet due** (25 October 09:00 Sydney). No execution report or attempt marker was found; no HTTP status, latency, record count or new NLP text can be attributed to it. It was not classified as a cooldown skip. The audit made zero provider calls and preserved the existing schedule and cooldown. Only the original three GDELT responses remain measured evidence; optional-provider rows remain skipped for missing credentials. Every source gate above remains open, so Phase 2 is **NO-GO** and GDELT provisional.

Current main includes the user's authorized offline UI prototype (`8f7d730`), preserved during safe fast-forward. Its invented fixtures and manually assigned illustrative labels are not real provider coverage, model output or permission evidence. All 47 offline tests and the dry run pass; exact-head push CI is checked after publishing this audit. Keep the local computer awake/online and Codex running at the scheduled time through completion; it need not stay on continuously beforehand.
# Local-first architecture supersedes cloud product requirements — 29 October 2026

Latest user correction: primary runtime is Streamlit on the user's own localhost,
with persistent local SQLite, `.env`/masked credentials, local FinBERT/MiniLM and
optional localhost Ollama/consented external LLM. Cloud deployment/session/cache
work is no longer a product acceptance target. Historical evidence below remains
dated and preserved. Main-only milestones and exact-commit CI remain required.

Explicit local product fetching is authorized within available quota and existing
holds, separately from the unchanged research sampler. Marketaux returned HTTP
200 / three preview records in one local browser request on 29 October; downstream
storage/NLP/transmission remain unverified and gated. NewsData remains manually
paused. See [actual local evidence](LOCAL_REDESIGN.md); no public-use approval,
provider winner or model-accuracy claim follows.

## Local product branch and model/source boundaries — 29 October 2026 Sydney

Latest user direction separates this work onto `local`; the original main checkout
is reserved for the concurrent web task. The full localhost product persists raw
originals/results locally and supports FinBERT by default, optional installed
Ollama models and explicitly consented OpenAI structured sentiment. No external
LLM probability calibration or live service/account availability is claimed.
Local RBA import of reviewed, attributed RBA-authored metadata passed actual
FinBERT/storage/original-link smoke. Marketaux's first preview succeeded but its
second bounded check had transport failure and stopped further daily requests;
NLP/retention rights remain gated. NewsData stays manually paused; Finnhub company
scope is distinct. No provider winner/public rights approval or frozen-evaluation
change. See LOCAL_REDESIGN.md for actual evidence and interface/licence references.

- 30 October 2026 Sydney — local usability milestone: separate pending-analysis queue from result filters, select one results model (FinBERT default), preserve publication precision and explicit date widening, source status from existing holds/ledger, selected-preview and next-step actions. No provider/model call on reads; offline verification only.

- 30 October 2026 Sydney — local chart milestone: dependency-free local Components v1 graph/heatmap return scoped click selections; no external scripts, inference or data requests. Graph focuses one sector with capped nodes, source layer off, literal entities/keyword themes and inspectable snippets; ticker-query edges remain query provenance.

- 30 October 2026 Sydney — local interface milestone: compact original details with collapsed technical history, retained filter preferences, explicit current OpenAI/Ollama states, aligned selected-sector chart rows, fixed-source collector configuration. No general crawler or extra news source added.

- 30 October 2026 Sydney — console repair: explicit chart axes and finite donut angles replace implicit categorical scale bindings/empty stack extents; counts, filters and local data are unchanged.

- 30 October 2026 Sydney: request protection repair separates local_rows and study_rows; both guards apply independently, using UTC completion days for failure pauses. No ledger reset, hold reduction or live API dispatch.

- 30 October 2026 Sydney: add bounded ABS headline/date collection under [ABS CC BY 4.0 terms](https://www.abs.gov.au/website-privacy-copyright-and-disclaimer), with [citation guidance](https://www.abs.gov.au/how-cite-abs-sources), publisher/date/original URL/access time, attribution and derivative/no-endorsement notice retained. Exclude third-party content, logos, trademarks, microdata and separately restricted material. ACCC has applicable [CC BY 4.0 terms](https://www.accc.gov.au/about-us/using-our-website/disclaimer-and-copyright), but its fixed RSS returned HTTP 403 and is disabled; no retry/alternate endpoint. Source-level local NLP/storage permission does not authorize external-model transmission. Each new collector action budgets two GETs (robots + fixed entry) independently of its 1–50 parsed records, using existing durable action guards; API budgets are unchanged.

- 31 October 2026 Sydney: distinguish refused connections, timeouts, HTTP errors, empty Ollama registries and filtered models. Read-only API diagnostics report project-scoped .env provenance, historical HTTP evidence separately from current status, and retained holds with UTC/Sydney expiry. At 30 October 13:12 UTC, Marketaux's 29 October failure-day stop had expired naturally at 30 October 00:00 UTC / 11:00 Sydney; no state was cleared. Three news keys exist, OpenAI key is absent; current quota/preview attestations and downstream rights remain separate gates. NewsData's code-level manual pause remains.

- 31 October 2026 Sydney: independent LMStudioProvider uses only fixed loopback endpoints and [official JSON Schema Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/structured-output). [Native model metadata](https://lmstudio.ai/docs/developer/rest/list) distinguishes downloaded files and loaded instances; exposed IDs alone do not prove inference. Loading is explicit through the installed lms CLI with [resource estimation](https://lmstudio.ai/docs/cli/local-models/load), 2048 context, one prediction, 50% offload and measured RAM/VRAM reserves; it refuses a second loaded model. No download, LAN bind, tool/search execution or external fallback.

- 31 October actual-load correction: this installed CLI accepts a uniquely matched model key, not the API's @quantization alias; its estimates arrive on stderr. GGUF rejects even negative vLLM engine-config/CWD flags, so those are omitted (no engine script supplied). Close stdin and validate the CLI catalog/unique variant before load; use 80% offload for ≤8 GiB downloads and 50% for larger models, preserving resource reserves. Real Gemma JSON Schema inference succeeded; Qwen resource preflight refused before loading. No safeguard was relaxed to pass the smoke check.

- 31 October local P0: the launcher owns one OS-locked worker and a versioned,
  backed-up SQLite task queue. UI update/reanalysis submits jobs; refresh/filter
  only reads. Durable source/inference intents prevent unknown outcomes from
  replaying on resume; credentials stay in project .env/Windows vault.
- The default US-BUSINESS-1 catalog is authored 11/56 business topics, independent
  of issuer classification and frozen rules. The user selected the official
  [JR/T 0020—2024 Table 2](https://www.csrc.gov.cn/csrc/c101954/c7520291/content.shtml):
  exact 19/91, with manufacturing auxiliary groups retained as source metadata.
- Add fixed [NIST RSS](https://www.nist.gov/coo/nist-rss-feeds) under its
  [copyright/disclaimer policy](https://www.nist.gov/copyrights-disclaimers):
  unmarked staff-authored text only, attribution/no endorsement; special-rights,
  third-party content and media excluded. One action allows at most five GETs
  (robots/feed/up to three bodies); automatic ABS allows three GETs (one body)
  under its existing CC BY 4.0 terms. Legacy preview/API budgets are unchanged.
  NIST body-layout failure fell back to permitted summaries and retained its
  failure-day hold; no retry or alternate URL bypass. ABS body extraction and
  excerpt provenance succeeded. Actual coverage is three primary/four secondary
  topics, with 35/42 real originals unclassified; not broad market coverage.

- 31 October P1: use main `f2fade9` presentation tokens without importing showcase
  records. Local graph/table components retain actual click identities, scoped
  events and keyboard alternatives; literal keyword highlights use only permitted
  article text. Persist only allowlisted view preferences in a separate settings
  row; free text/credentials/endpoints and pipeline configuration are excluded.
  Catalog switching reads saved classification versions and never triggers a
  reclassification or fetch. An unclassified catalog retains the original list.
- 31 October P1.1: persist only allowlisted ui_theme and ui_language in separate
  SQLite settings rows. Translate presentation labels and chart tooltip fields;
  preserve raw taxonomy/article/model IDs, source attribution, evidence and model
  outputs. Language-specific widget presentations synchronize canonical values;
  durable article selections survive widget cleanup. Keep framework calendar and
  auxiliary labels as a disclosed limitation rather than injecting DOM mutations.

- 31 October settings/runtime refinement: keep one persistent source/key/model
  editor; separate offline drafts from worker submission readiness. A single
  explicit LM Studio action starts the installed runtime on loopback and checks
  both catalogs under a process lock; no weights or inference are started.
- DeepSeek remains a distinct authored-text interface test, outside automatic
  news processing. Fixed official endpoints, cached actual model IDs, JSON Output
  plus strict local schema validation, separate durable reservations and at most
  three serial inferences preserve provider identity/history and stop on errors.
  Saving credentials is not transmission consent. No live DeepSeek claim exists
  without a local key, explicit action and observed validated response.

- 31 October credential incident closure: native Credential Manager access lives
  only in `windows_credentials.py`; UI/business/diagnostics use the shared facade.
  Unittest/AppTest default to temporary files and per-case memory stores, with
  process-lifetime fail-closed native/path guards and inherited Python-child
  isolation. [CPython audit events](https://docs.python.org/3.11/library/audit_events.html)
  supplement entry-point checks against omitted mocks; they are not a hostile-code
  security sandbox. Windows CI exercises mocked Win32 marshalling, not real vault
  reads/writes. Preserve the incident and unverified prior-value qualification;
  recovery of any different Marketaux key belongs to the user in the local editor.

- 31 October news multi-key management: use news-provider UUID slots and a single
  primary pointer, with immutable protected credential versions. Verify a newly
  written target before publishing its reference; preserve old versions against
  cross-store failures. Confirmed deletion removes only that managed slot's known
  versions, never legacy/model targets or `.env`. A failed write may leave an
  unused protected target; it is neither selected nor enumerated for cleanup.
- Retain legacy selection unless the user explicitly changes it; no automatic
  migration, backup rotation or retries. New task snapshots pin nonsecret slot
  and version IDs. Worker reservations check rights, account budget and all
  provider/study holds before resolving plaintext; a disabled/replaced snapshot
  skips its source. Key count cannot increase quota. Store only fixed error codes:
  401 marks that version invalid; 403/429 retain permission/rate-limit meaning.
- Use the same mandatory memory/native-I/O guards for slot tests, including mocked
  Windows deletion. Real-browser acceptance runs a visibly labeled temporary
  Streamlit fixture with memory credentials and injected offline responses; its
  local listener exception permits no outgoing connection. No user's key is
  added, copied, replaced, deleted or inventoried during acceptance.
