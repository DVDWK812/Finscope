# API evaluation protocol — Phase 1

> Latest review: Phase 1.5 on 25 October 2026 Sydney reanalysed the existing 24 October keyed pilot without new provider requests. Marketaux remains the preferred conditional candidate. See the Phase 1.5 section and [bounded multi-day plan](PHASE15_MARKETAUX_PLAN.md); that study is designed, not executed or scheduled. No provider is approved for public deployment. Earlier missing-key statements are dated historical evidence.

## Objective
Choose one sustainable news metadata source for a **publicly deployed**, non-commercial student MVP. The API test does **not** evaluate the sentiment model, sector labelling or event deduplication yet.

## Candidates (verify plan limits and rights before deployment)

| Provider | Query strategy in pilot | Credential | Important caveat |
|---|---|---|---|
| GDELT DOC API | English keyword, past N days | None | GDELT `seendate` means first seen, not necessarily published; source noise; often no summaries |
| Marketaux | English keyword, `group_similar=false` | `MARKETAUX_API_KEY` | Free tier caps results per request; provider grouping must be off to test our own deduplication |
| NewsData.io | English keyword, latest news | `NEWSDATA_API_KEY` | Latest endpoint is approximately 48h; historical access is plan-dependent |
| Finnhub | North-American ticker (e.g. NVDA) | `FINNHUB_API_KEY` | Company news is **not** equivalent to sector-wide keyword coverage |

Official docs: [GDELT](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [Marketaux](https://www.marketaux.com/documentation), [NewsData.io](https://newsdata.io/documentation), [Finnhub OpenAPI](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml).

## Experiment

1. Sample the same three *topics*: technology (semiconductor), healthcare (pharmaceutical), materials (copper).
2. Make **one low-volume request** per provider/topic (3 topics × 4 APIs = up to 12 calls). Record UTC query time.
3. Measure request outcome, response latency, raw and valid article counts, distinct sources, valid URLs, nonempty descriptions and timestamp completeness. Completeness ratios among accepted records are conditional on successful normalization; use the raw-to-valid ratio to disclose discarded records.
4. Manually inspect relevance of up to ten returned articles per topic/provider. Report judged relevance and **classification uncertainty**. Count missing fields separately.
5. Check actual source diversity, access permissions, usage quotas, date range, and whether the free tier permits deployment, storage and derived NLP analysis.
6. Do NOT compare raw article counts as if all providers implemented the same query semantics. Finnhub symbol scope differs from keyword search; GDELT first-seen timestamps differ from publication timestamps.
7. Repeat on at least two different days before settling on a primary provider (if project time allows). Summarize trade-offs and choose one primary provider plus optional fallback.

## Preferred decision hierarchy

1. Validity of public deployment and permitted use of returned data (pass/fail).
2. Quality and relevance of news coverage by topic and source (most important).
3. Publication timestamps, source IDs and access to summaries.
4. Stability, quota, documented history and ease of scheduled ingestion.
5. Latency and cost.

## What this pilot does not prove

- API success alone is not proof that HTML pages can legally be scraped or their full text redistributed.
- Lexical overlap between a keyword and a title is not a ground-truth relevance metric.
- Headline sentiment is not sector impact or market-return forecasting.
- Provider-generated sentiment or event grouping must **not** substitute for our own FinBERT and embedding evaluation.

## Evidence and Git hygiene

- Commit this plan, scripts, unit tests and a short Markdown summary of the experimental conclusions.
- Save local machine-generated JSON reports under `reports/`, excluded by `.gitignore`.
- No API keys, full text dumps or copied copyrighted article bodies in commits.
- Log APIs tested, sampling date, rate limit response, observed failures and whether deployment rights were verified.

## First evidence review — 2026-10-24 (Australia/Sydney)

Official sources were checked on this date. Documentation describes provider capabilities; it is not evidence that this account received those capabilities. No special academic exemption was verified for the keyed providers.

### Endpoint, metadata and scope comparison

| Provider | Verified contract and expected metadata | Scope / history limitation |
|---|---|---|
| GDELT | DOC `artlist`, JSON, English source-language filter, `timespan=2d`, `maxrecords=3`; titles, original URLs, domains and first-seen times; no promised summary field | General news full-text keyword matching, not a finance feed. DOC documentation describes a rolling three-month search window; older wording about January 2017 is not a guarantee of unrestricted archive access. Maximum 250 records, no exhaustive coverage claim. [Official DOC documentation](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) |
| Marketaux | `/v1/news/all`, `api_token`, English keyword search, UTC `published_after`, `group_similar=false`; source, publication time and meta description | Finance-specific corpus; full-body/title matching can return records whose headlines omit the keyword. Date filters exist, but earliest free-tier retention was not established. [Documentation](https://www.marketaux.com/documentation). Full article content is not supplied. [FAQ](https://www.marketaux.com/faq) |
| NewsData.io | `/api/1/latest`, `X-ACCESS-KEY`, `q`, English, size 1–10 on free; UTC selected explicitly. Description, source and publication fields need live validation | General news, not restricted to financial coverage. Latest covers past 48 hours; the free plan advertises a 12-hour delay. Archive entitlement must be checked separately. [Authentication](https://newsdata.io/documentation/api-authentication), [latest endpoint](https://newsdata.io/documentation/latest-news-api), [plan overview](https://newsdata.io/documentation) |
| Finnhub | `/company-news`, token, company symbol and inclusive calendar-date parameters; headline, summary, source, URL and Unix time | North-American company feed: NVDA/PFE/FCX are proxies, not sector keyword equivalents. Official embedded company-news documentation advertises one year of free-tier history; not exercised with a key. [Provider OpenAPI](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml), [company-news documentation](https://finnhub.io/docs/api/company-news) |

### Quotas and deployment gate

| Provider | Documented free limits / observed behaviour | Public student MVP, storage and derived analysis |
|---|---|---|
| GDELT | No numeric DOC request quota or SLA verified in reviewed official pages. Observed two HTTP 429s; no captured numeric quota or Retry-After headers. Six-second request-start spacing is our precaution, not an official entitlement. | Dataset use and redistribution allowed with GDELT citation and website link. This supports a metadata pilot; it does not license linked publishers' bodies or images. [Terms of use](https://www.gdeltproject.org/about.html#termsofuse) |
| Marketaux | 100 requests/day, 3 articles/news request; this account's quota not exercised. [Pricing](https://www.marketaux.com/pricing) | Reviewed terms grant personal non-commercial content access, without a clear public redistribution grant. Public display, retention and derived NLP permissions require provider clarification before deployment. API availability is not a deployment licence. [Terms](https://www.marketaux.com/tos) |
| NewsData.io | 200 credits/day, up to 10 articles/credit; 30 credits/15 minutes. No live quota observations. [Credits](https://newsdata.io/documentation/api-credit-limits), [rate limits](https://newsdata.io/documentation/api-rate-limit) | Personal/internal API restrictions coexist with external Data Derivatives and sharing-at-customer-risk clauses. This is unresolved scope, not a categorical ban on every public use. Publisher rights remain separate; clarify free-plan display, retention and AI use before approval. [Terms](https://newsdata.io/terms) |
| Finnhub | Terms impose 30 calls/second in addition to plan limits. Current free per-minute allowance was not independently extracted from the pricing page; do not assume it. No live quota observations. [Terms](https://finnhub.io/terms-of-service), [pricing](https://finnhub.io/pricing) | Personal plans prohibit sharing data **or derived results** without written approval; data deletion is required when the data subscription ends. Public deployment is blocked absent an appropriate agreement. The SDK/OpenAPI Apache licence does not license news data. [Terms](https://finnhub.io/terms-of-service) |

### Actual first run

Code: `05a7bdb`. Command:

```bash
python -m finscope.benchmark --providers gdelt marketaux newsdata finnhub --topics technology healthcare materials --limit 3 --days 2 --timeout 15 --output reports/phase1_live_20261023.json
```

Local evidence is excluded from Git. Run start: **2026-10-23T15:09:11.991259+00:00**, corresponding to 24 October in Sydney. Each row records its own UTC time, query, endpoint and outcome. Three news-API HTTP requests were made, all to GDELT, with no retry or pagination. Official-documentation reads and three manual publisher-page checks are separate from this API request count.

| Provider / topic | Request start UTC (2026-10-23) | Actual result | Observed elapsed time |
|---|---|---|---|
| GDELT / semiconductor | 15:09:11.991259 | Failed: HTTP 429 | 11,962.4 ms |
| GDELT / pharmaceutical | 15:09:23.955366 | HTTP 200; 3 raw, 3 normalized, 3 sampled; 3 unique URLs / 3 domains | 20,217.3 ms |
| GDELT / copper | 15:09:44.173494 | Failed: HTTP 429 | 12,342.2 ms |
| Marketaux / all three topics | No requests | 3 skipped: missing `MARKETAUX_API_KEY` in local `.env` | Not measured |
| NewsData.io / all three topics | No requests | 3 skipped: missing `NEWSDATA_API_KEY` in local `.env` | Not measured |
| Finnhub / all three symbols | No requests | 3 skipped: missing `FINNHUB_API_KEY` in local `.env` | Not measured |

The live command exited **1**, as expected when any attempt fails. No live authentication error, empty response array or unexpected schema was observed; these are covered by offline mocks only. The requests timeout is a socket/connect-read timeout, not a strict total deadline, so the observed successful elapsed time can exceed 15 seconds.

For the successful healthcare sample, title and syntactically usable URL completeness was 3/3, first-seen timestamp completeness 3/3, publication timestamp availability 0/3, and description availability 0/3. Original URLs and UTC first-seen timestamps are retained locally. The three domains were `zawya.com`, `pajhwok.com` and `prokerala.com`; three domains do not imply three independent events.

Manual headline review: two pharmaceutical export/trade stories were financially relevant to the sector, with likely event overlap; the partnership announcement was uncertain for finance relevance. That is **2 relevant, 1 uncertain, 0 clearly irrelevant**, not an unbiased precision estimate. [One publisher page](https://pajhwok.com/2026/10/22/pakistans-pharmaceutical-exports-fall-by-over-30pc/) was accessible and confirmed the trade topic; the other two URLs were unavailable through the browsing tool. This does not establish that they are universally broken. No access restriction was bypassed and no full text was saved.

Technology/materials coverage, relevance and metadata quality are **unmeasured** because their API requests failed. Optional-provider coverage and latency are **unmeasured** because they were skipped. A one-day, three-record, relevance-ranked sample cannot establish general reliability, comparative source diversity, historical completeness or sustainable ingestion performance.

After the experiment, commit `0a74486` tightened future runs to stop a provider after its first HTTP 429 and mark later topics skipped. The actual first run above predates this guard and was not rerun. See [decision memo](DECISIONS.md) for the conditional choice and remaining gates.

## Follow-up review — 2026-10-24 (Australia/Sydney)

### PR #2 review and remediation

Reviewed original head `7a656df` against `7614590` for adapter correctness, secret handling, report integrity, request budgets, tests and CI permissions. The review did not merge the PR.

| Finding in reviewed head | Impact | Remediation / evidence |
|---|---|---|
| Valid HTTP-date Retry-After was discarded; cooldown disappeared on CLI restart | A fresh invocation could request before a provider's hold expired | `2ce44d6`: validated seconds/date parsing, atomic ignored local cooldown state, fail-closed corrupt-state handling and cross-invocation regression. No automatic retries. A missing/invalid header on HTTP 429 uses our 24-hour hold, not a claimed provider quota. [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after) |
| Arbitrary JSON values were stringified into title/description fields; whitespace summaries and date-only/zero-epoch placeholders could appear complete | Inflated usable-text or publication completeness | Strict text normalization, timestamp sentinel checks, separate first-seen/publication metrics and synthetic regression cases |
| Report lacked title-length evidence; CI did not execute the CLI dry run | NLP input feasibility and CLI regression coverage incomplete | Added character and whitespace-word metrics, dry-run CI step, read-only CI contents permission; all 36 offline tests and local dry run pass |

URL credentials are rejected before samples are retained; original accepted publisher URLs remain unchanged. Request-token parameters, arbitrary error bodies and nonvalidated quota headers are not included in reports. This is a bounded source review and tracked-file audit, not a penetration test or a dependency vulnerability certification. The cooldown file supports serial pilot runs on one checkout, not simultaneous processes or a distributed deployment.

### Current sampling status and NLP evidence

The first run and this follow-up are on the **same Sydney day, 24 October**, and same UTC day, 23 October. No GDELT request was made in this follow-up. A different-day retest is pending, not a second observed result. A one-shot local chat follow-up is scheduled for **25 October 2026 at 09:00 Sydney** (24 October 22:00 UTC), subject to the computer/app being available. Its budget is **one pharmaceutical query, maxrecords=3, two-day lookback**, with no retry, pagination or additional GDELT topic. The follow-up must first verify different UTC/Sydney dates, elapsed time and any provider hold.

The local conservative GDELT hold was initialized from the saved last 429, through `2026-10-24T15:09:44.173494+00:00`. No header was observed in that response; this deadline is local policy. Future valid Retry-After deadlines persist across CLI invocations, and a still-active hold produces skipped/provider_cooldown without a request.

Marketaux, NewsData.io and Finnhub each have **one new skipped healthcare row**, not failures, in ignored `reports/phase1_optional_followup_20261024.json`: local `.env` remains absent. **New news-API HTTP requests this follow-up: zero.** Documentation retrieval is separate from news-API sampling.

Offline reanalysis of the three original GDELT healthcare records is in ignored `reports/phase1_nlp_input_review_20261024.json`:

| Input property | Actual original-sample evidence | Implication |
|---|---|---|
| Title length | 71, 77 and 83 characters; mean 77.0 | Technically usable short headline strings; length alone proves no model suitability |
| Whitespace words | 10, 11 and 13; mean 11.3 | Descriptive word count, not tokenizer/model-token count |
| Description availability | 0/3; no description text reconstructed or fetched | No observed title-plus-summary input; context must not be invented |
| Publication timestamp availability | 0/3 | Publication-time analysis is unsupported by this sample |
| First-seen timestamp availability | 3/3 | Suitable only for explicitly labelled discovery-time analysis |
| Manual financial relevance | 2 relevant export/trade headlines, 1 uncertain partnership headline | Small, relevance-ranked, single-topic sample; two records likely share an event |

Headline-only NLP might be a separately scoped experiment, but accepting that narrower input and validating it is still a project decision. There is no universal title-length threshold here, no tokenizer/model evaluation, and no evidence of sector-impact validity. The skipped providers have **unknown observed** title/summary/publication quality; documented fields are not measured availability.

### Rights decision by intended use

Official terms were reread on 24 October. The following is the project's evidence interpretation for the actual metadata pilot, rather than a guarantee about all third-party content:

| Provider | Public metadata display | Metadata retention | Derived AI analysis / output |
|---|---|---|---|
| GDELT | Released dataset redistribution is supported with GDELT citation/link | Broad dataset reuse supports retention; no stated dataset time limit found | Broad research/analysis grant supports analysis of released metadata; no AI-specific exclusion found. This does not grant publisher full-text/image rights. [Terms](https://www.gdeltproject.org/about.html) |
| Marketaux | Public redistribution grant not established by reviewed personal/non-commercial website terms | Specific retention period/rights unresolved | Specific derived-analysis/output scope unresolved; obtain plan-specific confirmation. [Terms](https://www.marketaux.com/tos) |
| NewsData.io | External derivatives/sharing clauses must be reconciled with API restrictions and attribution | Free-plan retention duration and post-termination scope not established | Publisher copyright and applicable contractual scope remain unresolved. [Terms](https://newsdata.io/terms) |
| Finnhub | Written approval required to share personal-plan data | Deletion required when data subscription ends | Sharing derived results also requires written approval. [Terms](https://finnhub.io/terms-of-service) |

Before clearing a keyed provider, obtain plan-specific written terms covering the exact endpoint, title/description fields, anonymous public display, local retention period, derived inference results and any training use. Do not equate inference permission with model training permission. No provider was contacted and no new permission was granted during this review.

**Phase 2 recommendation: NO-GO.** GDELT remains provisional. Different-day availability, financially relevant usable input and publication-time scope are unresolved; alternatives lack local credentials and a cleared public-use basis. A scheduled test is not completed evidence. See DECISIONS.md and Issue #1 for release gates.

## Main-only handover and pre-run execution audit — 2026-10-24

Verified that the user merged PR #2 as `6ae8e00`. Main at `f432102` contains the complete Phase 1 implementation, tests, CI, cooldown logic and evidence documents; its only differences from the former feature head are the user's main-only workflow updates in AGENTS.md, CODEX_TASK.md and README.md. Local and remote feature branches were removed after confirming zero unique commits. Future changes, including scheduled-task evidence, go directly to main after safe synchronization and testing.

The automation remains scheduled for **25 October 2026, 09:00 Sydney**. At the 24 October audit, that time is still in the future, its saved schedule is active, and no new execution report exists. The schedule alone proves no execution. No provider request was made during this handover.

| Audit field | Verified current status |
|---|---|
| Scheduled one-shot execution | Not yet due; no observed execution report |
| Requests made by this handover | 0 |
| One-shot HTTP status / latency | Unobserved / not applicable; no response to assess |
| One-shot raw / normalized / sampled records | Unobserved; do not label this an empty successful response |
| One-shot available NLP text | No new observed title/description; original sample metrics remain unchanged |
| Cooldown skip | Not observed: task has not executed. Existing hold remains unchanged through 2026-10-24T15:09:44.173494+00:00 |

The saved one-shot instructions now require main-only development and evidence-based execution auditing. They retain only the previously authorized one-request GDELT check, forbid extra optional-provider calls, and prevent a second attempt if a prior execution/attempt marker is found. A marker without result evidence is unknown execution, not proof of an HTTP request or success. After execution, record exact attempts versus received responses, HTTP status, latency, raw/normalized/sample counts, title lengths, descriptions, relevance and timestamp semantics. A hold is skipped/provider_cooldown; no HTTP 429 is retried. No catch-up call is authorized merely because execution evidence is absent.

All 36 offline tests and the dry run pass on synchronized main. [Push-triggered Actions run 39983651007](https://github.com/DVDWK812/Finscope/actions/runs/39983651007) passed for `f432102`; publication of this documentation needs exact-head verification. Phase 2 remains **NO-GO** across all release gates, independent of merge status or a future isolated HTTP 200.

## Saved-result execution audit — 24 October 2026, 03:20 Sydney

Audited the active automation configuration, attempt-marker path and all saved report types at **2026-10-23T16:20:27.754470+00:00**. The scheduled time is **25 October at 09:00 Sydney** (24 October 22:00 UTC), still future. No attempt marker or one-shot result report exists. Status is **not yet due / no execution evidence**, not failed, successful or skipped for cooldown. This audit made **zero news-API requests**; the scheduled task's HTTP status, latency, records and new NLP input remain unobserved. A local inventory/assessment is saved in ignored `reports/phase1_execution_audit_20261024.json`.

Only the original live report contains actual provider responses:

| Original GDELT topic | HTTP | Latency | Accepted records / available NLP text |
|---|---|---|---|
| Technology | 429 | 11,962.4 ms | Unobserved due to failure; not evidence of empty coverage |
| Healthcare | 200 | 20,217.3 ms | 3 title-only records; mean 77 characters / 11.3 whitespace words; no descriptions or publication times |
| Materials | 429 | 12,342.2 ms | Unobserved due to failure; not evidence of empty coverage |

Thus there are still **three historical GDELT requests and no different-day sample**. The optional-provider follow-up contains three explicit missing-credential skips with `request_attempted=false`; dry-run plans and offline reanalysis are not additional live requests. The original report predates explicit attempt flags; its three requests are supported by recorded HTTP responses and the original run log. The saved cooldown was not changed, and no retry was attempted.

Main was fast-forwarded to the user's newer `8f7d730`, preserving the authorized synthetic-only Streamlit prototype. Its 12 invented records/illustrative events are excluded from news-source feasibility evidence. All **47 offline tests** (36 API/report/cooldown plus 11 synthetic-UI data tests) and the benchmark dry run pass. This does not establish a Streamlit browser/runtime pass.

Phase 2 remains **NO-GO**: repeat availability, representative financial input, timestamp scope, usable history/quota and public-display/retention/derived-output rights remain unresolved. Local checks and synthetic fixtures cannot close those source gates. The local computer and desktop app must be running for the scheduled task's local-file access; have them ready before the due time and leave them available through completion. [Official scheduling guidance](https://developers.openai.com/training/walkthroughs/scheduled-tasks)

## Synthetic UI verification — 2026-10-24

Reviewed UI commit `8f7d730` and continued on safely synchronized main (`39a1c06`). The synthetic-only interface now has tested runtime filters, empty states, explicit raw/event counting, event-source drill-down and responsive styling. Local validation passed all 66 tests and benchmark dry runs on Streamlit 1.50.0 and 1.66.1 (Python 3.12.3); browser checks are recorded in UI_SPEC.md / DEVELOPMENT_LOG.md. These 12 invented reports / 10 predefined events remain excluded from provider, sentiment-model and deduplication evidence. This UI milestone made **zero news-API requests** and ran no FinBERT or embeddings. **Phase 2 remains NO-GO**, with every existing source and rights gate unchanged.

## Keyed provider experiment — 2026-10-24

Followed CODEX_TASK.md and KEYED_API_TEST_PLAN.md on clean main `0c95397`. All three project-local `.env` keys were nonempty; ignore/untracked status was verified without displaying key values or fragments. The default shared Python lacked Streamlit, so the existing isolated `.venv` was used: all 66 tests and the healthcare-only dry run passed before sampling. No adapter or benchmark code was changed.

Stage A command (using `.venv/Scripts/python.exe`):

```powershell
python -m finscope.benchmark --providers marketaux newsdata finnhub --topics healthcare --limit 3 --days 2 --output reports/keyed_healthcare_initial.json
```

All three initial responses passed authentication/shape/normalization checks with valid records. NewsData also returned Retry-After=900, producing a hold through **2026-10-24T13:02:57.734634+00:00**. At the Stage B decision time (12:49:39 UTC), that hold was active. Only Marketaux and Finnhub were eligible:

```powershell
python -m finscope.benchmark --providers marketaux finnhub --topics technology materials --limit 3 --days 2 --output reports/keyed_followup_topics.json
```

Exactly **7 keyed requests**, all HTTP 200; no authentication/schema/transport failures, HTTP 429, empty responses, retries or pagination occurred. NewsData's two omitted topics are **skipped/provider_cooldown**, with no request/status/latency/coverage observation, recorded separately in ignored `reports/keyed_expansion_gate_decisions.json`. They are not failed queries. GDELT was not called or changed by this task.

### Per-query observations

All request dates below are **24 October 2026 UTC**. Parameters, endpoint, exact UTC start, headers and local title/URL/time samples are retained in the ignored reports. Marketaux used pharmaceutical/semiconductor/copper keywords, English, a two-day published-after filter, cap 3 and `group_similar=false`; NewsData used pharmaceutical, English, UTC and size 3 on latest; Finnhub used PFE/NVDA/FCX and calendar dates 22–24 October, without a server-side result-limit parameter.

| Provider / topic | Query start UTC | HTTP / latency | Raw / normalized / sampled | Sample sources | Mean title chars / words | Mean description chars | Descriptions / published times |
|---|---|---|---|---:|---|---:|---|
| Marketaux healthcare | 12:47:55.943001 | 200 / 907.4 ms | 3 / 3 / 3 | 1 | 85.7 / 13.3 | 126.7 | 3/3 / 3/3 |
| NewsData healthcare | 12:47:56.851083 | 200 / 882.7 ms | 3 / 3 / 3 | 3 | 96.3 / 13.0 | 206.3 | 3/3 / 3/3 |
| Finnhub PFE | 12:47:57.735637 | 200 / 975.3 ms | 18 / 18 / 3 | 1 | 91.3 / 16.3 | 272.0 | 3/3 / 3/3 |
| Marketaux technology | 12:49:39.283253 | 200 / 896.4 ms | 3 / 3 / 3 | 3 | 92.7 / 13.3 | 181.0 | 3/3 / 3/3 |
| Marketaux materials | 12:49:40.180301 | 200 / 839.0 ms | 3 / 3 / 3 | 3 | 69.3 / 9.3 | 140.3 | 3/3 / 3/3 |
| Finnhub NVDA | 12:49:41.019919 | 200 / 1,663.6 ms | 250 / 250 / 3 | 1 | 92.0 / 14.7 | 86.0 | 3/3 / 3/3 |
| Finnhub FCX | 12:49:42.684423 | 200 / 1,028.5 ms | 6 / 6 / 3 | 1 | 68.3 / 12.3 | 125.0 | 3/3 / 3/3 |
| NewsData technology/materials | Not requested | Skipped: provider hold | Unobserved | Unobserved | Unobserved | Unobserved | Unobserved |

Normalization acceptance was 100% before the local cap for all seven replies; all 21 sampled rows retained a title, syntactically valid HTTP(S) URL, nonblank description/summary and valid provider-labelled publication time. Finnhub's sampled completeness is not a completeness review of all 274 normalized rows. Publication fields were not independently checked against publisher pages. Distinct original URLs and provider timestamps are retained; source pages were not fetched. First-three sampling and differing ranking/filter scopes prevent a coverage leaderboard.

### Relevance, traceability and usable NLP input

Manual labels use actual returned titles and URLs, with business/investment/earnings/regulatory relevance as the rubric; descriptions were assessed by measured presence/length only and are not persisted. These judgments are neither independent annotations nor model precision estimates.

| Provider | Aggregate sampled evidence | Manual relevance / limitations |
|---|---|---|
| Marketaux | 9 records, 7 reported source domains; mean title 82.6 chars / 12.0 words; mean description 149.3 chars; mean request latency 880.9 ms | Healthcare: 2 pharma-regulation items and 1 off-topic AI-skills headline; technology/materials: all 6 business-relevant. Total 8 relevant / 1 off-topic. Healthcare has likely event overlap; source/ranking/geography bias remains. One copper record's source label differs from its URL host, so preserve both rather than silently rewriting attribution. |
| NewsData | 3 healthcare records, 3 sources; mean title 96.3 chars / 13.0 words; mean description 206.3 chars; latency 882.7 ms | 2 biotech/manufacturing-finance headlines and 1 uncertain healthcare-policy item. No evidence for other sectors because held; general-news scope and delayed latest window differ from Marketaux. |
| Finnhub | 274 raw/normalized rows across 3 symbols, **9 sampled**, all source label Yahoo; mean sampled title 83.9 chars / 14.4 words; mean summary 161.0 chars; mean latency 1,222.5 ms | PFE: 3 relevant titles. NVDA: 2 contextual technology-finance items / 1 uncertain crypto-AI item; none explicitly names NVDA/Nvidia. FCX: 2 relevant copper/company items / 1 uncertain other-company item. Total 7 contextual relevant / 2 uncertain; only 5/9 titles explicitly identify the requested company. Body-level association remains unverified. |

Marketaux/NewsData returned publisher-site links; Finnhub returned Finnhub-hosted news links, not resolved ultimate publisher URLs. Yahoo may aggregate underlying publishers; its one source label is not proof of only one original newsroom. Finnhub's 250-row NVDA return is not evidence of exhaustive retrieval or comparable sector breadth. No extra news-link fetch was made.

All three now demonstrate more promising **title-plus-short-description** candidates than the earlier title-only GDELT sample. Presence and length alone do not establish informative, nonboilerplate text, finance sentiment accuracy or semantic dedup performance. A summary may repeat the title or omit decisive context. No tokenizer, FinBERT, embeddings, provider sentiment substitution, body extraction or model-quality evaluation was run. Only short metadata is handled; no descriptions, extracts or full bodies are committed.

### Quotas, history and permissions

- Marketaux official pricing HTML was rechecked and confirms 100 daily requests / 3 articles per news request. Actual replies supplied numeric limit 30, remaining 29/29/28; these may describe a different quota window, whose period was not established. They do not replace the published daily cap. UTC date filters are documented, but this experiment proves only the requested two-day slice, not earliest free-history retention. [Pricing](https://www.marketaux.com/pricing), [documentation](https://www.marketaux.com/documentation).
- NewsData docs state 200 daily credits, up to 10 results/credit, a 48-hour latest window and advertised 12-hour free delay. Actual healthcare response supplied limit 60/remaining 59/reset 1792846980 and Retry-After 900. The runtime hold was honored even though HTTP was 200; no interpretation was used to authorize extra traffic. Differing published AI-feature badges are not treated as entitlement or FinBERT evidence. [Credits](https://newsdata.io/documentation/api-credit-limits), [plan overview](https://newsdata.io/documentation).
- Finnhub actual company-news requests succeeded and supplied limit 60, remaining 59/59/58 and reset headers. This demonstrates endpoint access, not an independently verified account-dashboard daily allowance or broad historical entitlement. The aggregate 30/second cap was not used as a free-plan quota. Header values and UTC dates remain local evidence; account limits must be confirmed before scheduled ingestion. [Company endpoint](https://finnhub.io/docs/api/company-news), [OpenAPI](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml).

Rights remain separate from these successes. Marketaux's reviewed website terms grant personal noncommercial access but do not establish field/plan-specific public display, retention or derived-output permission. NewsData's personal/internal API restrictions coexist with external-derivative/sharing-at-risk clauses; free public-use scope and publisher rights require clarification. Finnhub explicitly restricts sharing personal-plan data or derived results without written approval and requires deletion when the data subscription ends. No new licence or written permission was obtained. [Marketaux terms](https://www.marketaux.com/tos), [NewsData terms](https://newsdata.io/terms), [Finnhub terms](https://finnhub.io/terms-of-service).

**Recommendation:** Marketaux is the most suitable **conditional primary financial-news candidate** for FinScope's sector-keyword design among the tested keyed options. It supplied relevant business metadata across all three requested topics, multiple sources and usable short-text/publication fields with low observed latency. Finnhub remains a distinct company-news comparator; NewsData is a potential general-news alternative with only healthcare evidence so far. This one-day sample does not choose a production provider. Multi-day reliability, representativeness, NLP quality, account/history limits and deployment/retention/derived-analysis rights remain open: **Phase 2 NO-GO**. No real data was connected to Streamlit; the separate scheduled GDELT test and its own hold/marker are preserved.


## Phase 1.5 review — 25 October 2026 Sydney

This is a **saved-evidence audit and study design**, not another provider test. New news-provider requests: **0**. Original keyed request/response reports, gate decisions and aggregate review are preserved byte-for-byte; their seven HTTP 200 replies remain the only keyed traffic measured. The GDELT automation and complete shared cooldown file were fingerprinted before work and preserved; no duplicate task or catch-up call was created. Reproducible offline code/notebook and aggregate output are local and ignored: `reports/phase15_saved_evidence_audit.py`, `.ipynb` and `.json` (run from the repository root). Source-document HTTP reads spend no news API quota and are not provider-availability tests.

### Refined Marketaux sample quality

Grain is a saved article appearance among the three original Marketaux replies, nine records total. Review does not recreate discarded descriptions or expand the sample.

| Check | Observed result | Interpretation / remaining risk |
|---|---|---|
| Financial relevance | Existing title/URL judgments: 8 relevant / 1 off-topic | Single Codex-assisted review, not independent labels or sentiment/model accuracy |
| Description informativeness | 9/9 present, mean 149.3 characters in original in-memory measurements; description text not saved | Added information, repetition and boilerplate cannot be reconstructed; semantic usefulness remains unobserved |
| Publication validity / requested window | 9/9 parse as published times; 0 future and 0 before requested lower bound | Internal consistency only; publisher accuracy not independently checked |
| Retrieval minus provider publication | Minimum / median / maximum **1.524 / 22.970 / 42.707 hours** | Article age, not measured ingestion latency or proof of news delay; search relevance ordering can select older articles |
| Diversity | 7 reported source domains and 7 normalized URL hosts; largest source 3/9 appearances; healthcare entirely one source | Pooled diversity hides sector concentration; global coverage and original-newsroom counts unproven |
| Traceability | 2/9 reported-source/normalized-host differences | One technology label differs from its URL host and one materials label uses a different domain. Differences survive stripping leading www/numbered-www prefixes; preserve both, no unsupported claim of invalid links |
| Exact duplicates | 9 distinct URLs; 0 repeated normalized titles | URL comparison lowercases scheme/host and drops fragment, preserving path/query; title comparison casefolds and normalizes words/punctuation. These exact-key checks do not measure event uniqueness |
| Event overlap | The existing healthcare title review suspects 2 articles cover the same regulatory event | Unconfirmed cluster; distinct URLs/titles can still repeat an event. No event-ground-truth corpus, precision/recall or embedding evaluation |

The [multi-day plan](PHASE15_MARKETAUX_PLAN.md) proposes three manual rounds on 26, 28 and 31 October at 12:00 Sydney, at most three requests per round/nine total. These are proposed windows, not automations or completed samples. It defines safe stopping, quota checks, transient description review, independent-review prerequisites, timestamp/source/duplicate measures and prospective screening criteria. The current CLI does not implement its attempt ledger, 60-second spacing or in-memory description annotation; those safeguards must be ready and offline-tested before collection. No raw text persistence or recovery re-query is permitted.

### NewsData HTTP 200 plus Retry-After investigation

Saved healthcare request began **2026-10-24T12:47:56.851083+00:00**: HTTP 200, 882.7 ms, three valid records. Safe saved headers are Retry-After=900, X-RateLimit-Limit=60, Remaining=59 and Reset=1792846980. The benchmark recorded a hold through **2026-10-24T13:02:57.734634+00:00**, then expansion topics were skipped. That historical deadline has now elapsed; its saved bytes are unchanged, and **NewsData live testing remains manually paused** while meaning/constraints are unresolved. Do not misreport the elapsed timestamp as an active timed hold or release testing simply because it has expired.

The official [rate-limit documentation](https://newsdata.io/documentation/api-rate-limit) and [provider usage article](https://newsdata.io/blog/newsdata-rate-limit/) describe 30 free credits per 15 minutes and HTTP 429 on exceeding the threshold. They do not explain Retry-After on a successful response, or reconcile the observed numeric limit of 60 with the credit window. A 900-second hint is consistent with a 15-minute window, **an inference, not proof of exhausted quota or permission to ignore it**. If Reset is Unix seconds, it maps to 13:03:00 UTC, near the saved hold deadline; the header's units/semantics have not been confirmed. Remaining=59 cannot establish the daily remaining allowance. Do not declare the successful reply a 429/failure or infer that 60 equals daily entitlement.

[RFC 9110 section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) defines Retry-After as follow-up waiting guidance, supporting seconds or an HTTP date; it does not settle this provider's success-header policy. The existing benchmark conservatively records a hold whenever a validated Retry-After is present, including HTTP 200. An offline regression test now verifies records remain successful while subsequent topics and a second invocation make no provider call, do not sleep/retry and preserve the hold. The generic CLI only enforces unexpired deadlines: the additional manual pause must be observed separately. No adapter policy was weakened, hold edited, live probe made or provider contacted. Draft clarification questions are in the plan.

### Marketaux free history and permission findings

Rechecked public documentation on 25 October Sydney. Official pricing returned HTTP 200 on a direct public-document read (web extraction timed out) and confirms **100 daily requests / 3 articles per news request**. [API documentation](https://www.marketaux.com/documentation) documents UTC publication-date filters, meta descriptions, similarity grouping and subscription-dependent caps. Its error table distinguishes subscription-usage headers from the **60-second X-RateLimit window**, resolving the earlier uncertainty about the type of observed limit 30; the account's current daily remaining usage/reset is still unverified. Documentation defines default search ranking by relevance, explaining why the sample cannot establish latest-news freshness. These are documented contracts, not new endpoint observations. [Pricing](https://www.marketaux.com/pricing), [FAQ](https://www.marketaux.com/faq).

No reviewed public pricing/FAQ clause specifies the earliest retrievable date or an explicit free-account history duration. Supported date parameters and the observed two-day slice do not prove unlimited history or a successful older-data entitlement. No authenticated dashboard entitlement was inspected and no history API probe was made: this gate remains **unverified**.

| Intended use | Evidence / unresolved permission | Phase 1.5 status |
|---|---|---|
| Public student-app display of title, meta description, URL/source/time | Generic Site terms cover personal noncommercial access, not a clear field-specific public API-data grant; noncommercial does not itself settle redistribution | OPEN; no real display |
| Metadata/text retention, caching, backups and deletion | No verified plan-specific duration or post-cancellation allowance for these API fields | OPEN; preserve existing evidence, do not expand retention |
| Three-person private review | Personal account access is not verified permission to share publisher metadata with the team | OPEN before independent shared review |
| Local pretrained-model inference | No verified express permission for input processing under the intended API/publisher terms; technical API access is not a usage grant | OPEN; no inference performed |
| Retention/publication of derived scores, labels, event groups or aggregates | No verified output-sharing basis or post-deletion rule; provider sentiment fields do not grant rights for project analysis | OPEN; no real derived outputs published |

The [terms](https://www.marketaux.com/tos), marked last updated 10 January 2021, describe the Site and third-party content; they are insufficient evidence to assert the intended API uses are approved. Absence of an express AI clause is neither permission nor a categorical finding that every inference use is prohibited. Written plan-/field-/publisher-specific clarification is required. Questions are prepared in the plan, **not sent**. Training/fine-tuning is distinct from inference and is outside this task.

**Decision:** Marketaux stays the preferred conditional financial-news candidate. This review improves evidence discipline and study readiness, not production authorization. Multi-day reliability, description informativeness, independent NLP validation, timestamp accuracy, representativeness, free history/quota and intended-use permissions remain open. Phase 2 production integration remains **NO-GO**; Streamlit remains synthetic-only. No FinBERT, embeddings or crawling was run.
