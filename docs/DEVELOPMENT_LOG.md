# Development log

Use this document for milestones supported by links to GitHub commits, PRs, or Issues. Do not claim results until verified.

| Milestone | Status | Evidence / next step |
|---|---|---|
| Initial repository scaffold | Pushed on feature branch; PR open | [PR #2](https://github.com/DVDWK812/Finscope/pull/2); remote initial commit `7614590` preserved |
| API candidates and evaluation plan | Official documentation and terms reviewed | See `docs/API_EVALUATION.md` |
| Offline adapter unit tests | 36 passed locally; updated CI success verified for `5f99533` | [CI run](https://github.com/DVDWK812/Finscope/actions/runs/39981319191); unit tests and CLI dry run passed |
| Live API comparison | First GDELT run recorded; optional providers skipped | 3 requests: one HTTP 200, two HTTP 429; keys absent |
| Source selection | GDELT provisional; exit gates remain open | See `docs/DECISIONS.md`; no deployment approval |
| FinBERT pipeline | Not started | Phase 2 |
| Event deduplication | Not started | Phase 2 |
| Public dashboard deployment | Not started | Later milestone |

Suggested rhythm: one meaningful commit per completed unit of work; use small PRs for group review and keep a weekly changelog. Commit frequency is not a proxy for real contribution or functional completeness.

## 2026-10-24 — Phase 1 baseline milestone

- Read AGENTS.md, CODEX_TASK.md, README, evaluation protocol and existing tests before edits.
- Original directory had no `.git`, remote or current branch. Initialized local `main` without overwriting any files. Git identity is configured as DVDWK812.
- GitHub connector authenticated as DVDWK812; repository lookup and `git ls-remote` for `https://github.com/DVDWK812/FinScope.git` returned Not Found. `gh` is unavailable. Repository creation/push is blocked; requested creation under the specified account, as CODEX_TASK.md requires. No remote push or CI success claimed.
- Baseline: Python 3.12.3; all 11 offline unit tests passed; `python -m finscope.benchmark --dry-run` passed (zero API calls). No `.env` file; dry run found no optional provider credentials.
- Codex is assisting with code, tests, documentation and research. Team must disclose this assistance in the assignment; official course code still requires Moodle confirmation.

## 2026-10-24 — Adapter and audit-report milestone

- Baseline saved as `3c7c738`; subsequent work is on `phase1/api-evaluation`.
- Confirmed request contracts against official GDELT DOC docs, Marketaux documentation, NewsData authentication/latest/credit docs and Finnhub-maintained OpenAPI. Existing NewsData header authentication is supported and retained; Marketaux grouping remains disabled. NewsData requests explicitly select UTC; date filters convert aware local times to UTC.
- Fixed silent missing-array successes, URL host validation, invalid publication timestamps and pre-cap normalization ratios. Empty arrays remain explicit `ok/empty`; nonempty unusable arrays fail. Local `.env` is the only key source (no shell inheritance or dotenv interpolation).
- Reports now preserve per-query UTC time, endpoint and allowlisted query parameters, status/error category, safe numeric quota headers, pre-cap counts and small local title/URL/source/time samples. No article bodies or descriptions are persisted. Default reports have unique names; provider-first order, duplicate-input removal and conservative GDELT spacing reduce quota risk. Failed live attempts return nonzero after writing evidence.
- All 26 offline tests passed; dry run passed with zero requests. Added mocked regression checks for error classification, secret redaction, strict schemas, timestamp/URL validation, truncation, ordering and no-network dry runs. No CI result claimed.
- Official usage terms reviewed; deployment comparison and actual live evidence follow in the next milestone. No primary provider declared from documentation alone.

## 2026-10-24 — First live experiment milestone

- Executed commit `05a7bdb` with three GDELT requests, one per topic, followed by optional-provider credential checks. Local report: `reports/phase1_live_20261023.json` (ignored). UTC start: 2026-10-23 15:09:11; Sydney date: 2026-10-24. No retries or pagination.
- GDELT semiconductor: HTTP 429, 11,962.4 ms; pharmaceutical: HTTP 200, 20,217.3 ms, 3 raw/3 normalized/3 sampled records, 3 domains; copper: HTTP 429, 12,342.2 ms. No captured numeric quota/Retry-After headers. The run correctly exited 1. The configured requests timeout of 15 seconds is not a total wall-clock deadline.
- Successful sample: 3/3 original HTTP(S) URLs, 3/3 first-seen timestamps, 0/3 descriptions. Technology/materials coverage is unmeasured; failures are not zero-coverage observations. No live auth failures, empty arrays or schema errors were observed; those scenarios were checked offline only.
- Marketaux, NewsData.io and Finnhub: three skipped queries each, zero requests, missing local `.env` keys. These are not provider failures or coverage evidence.
- Manually reviewed all three healthcare headlines: two concern pharmaceutical exports (relevant to sector business activity, likely same event); one partnership announcement is uncertain for finance relevance. Direct publisher-page checks through browsing: Pajhwok accessible; Zawya and Prokerala unavailable through that tool. No anti-bot/paywall bypass, body extraction or local full-text storage.
- Two rate-limit responses despite sparse calls mean service availability is unresolved. No further live provider requests in this milestone. Full comparisons and a conditional recommendation are being recorded in API_EVALUATION.md / DECISIONS.md.

## 2026-10-24 — Rate-limit handling milestone

- The first run continued to different topics after a 429; retained that actual report unchanged except for clearly labelled manual annotations. Tightened subsequent runs to stop that provider immediately after HTTP 429 and mark remaining topics `skipped/provider_rate_limited`; other providers can still proceed. Added explicit attempted-request flags/times for future reports.
- Regression verified that a GDELT 429 allows exactly one GDELT request, skips its remaining topics without sleeping/retrying, and continues optional-provider checks. All 27 offline tests and the dry run passed. No live API calls were repeated to test this change.

## 2026-10-24 — Evidence and decision milestone

- Added the official endpoint/metadata/history, free quota and deployment-permission comparison to API_EVALUATION.md, with source links and explicit unknowns. Finnhub's dynamically embedded company-news documentation was inspected via its official page; a current free per-minute quota could not be confirmed. No unsupported quota was substituted.
- Recorded exact GDELT query times, HTTP statuses and latencies, sample completeness, manual relevance uncertainty, source overlap and publisher-link accessibility limitations. Only aggregate findings are committed; local report retains the small metadata sample and original URLs/times without bodies.
- DECISIONS.md selects GDELT provisionally for continued metadata research. Availability, summary coverage, additional-day sampling and deployment rights for alternatives remain open; Phase 1 is not declared complete. FinBERT/dashboard development remains unstarted.
- Local milestones: `3c7c738` baseline, `05a7bdb` adapter/report corrections, `0a74486` stop-on-rate-limit guard. GitHub repository lookup was rechecked and still returned Not Found; no remote writes or GitHub CI were possible. User creation request remains pending. Documentation commit follows these verified milestones.

## 2026-10-24 — GitHub reconciliation milestone

- User confirmed repository creation. Verified canonical public repository `DVDWK812/Finscope`, connector push/admin permission and remote default branch `main` at `761459093be13757f9891b4ae5505e4727304d24`.
- Added canonical `origin` and fetched remote history. Remote initial commit contains README.md and an MIT LICENSE. Reconciled the two README versions into the existing detailed Phase 1 README, preserved the remote licence, and joined the previously unrelated histories on `phase1/api-evaluation`. No force push or remote-main replacement.
- Re-ran all 27 offline tests and the dry run successfully before reconciliation; no new news-API calls were made and optional credentials remain absent.
- Created [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) with actual local test/live outcomes and remaining rate-limit, credential, rights and evidence gates. Updated repository instructions and decision status. Push/PR and CI verification follow; no CI pass claimed yet.

## 2026-10-24 — Verified publication and CI milestone

- Pushed reconciliation commit [`44ba4bc`](https://github.com/DVDWK812/Finscope/commit/44ba4bcc1989d7efb152350a195e47ba13321fef) and its four local milestone ancestors to `origin/phase1/api-evaluation`. Verified the remote feature SHA exactly matched local HEAD using `git ls-remote`; remote `main` remained at `7614590`.
- Opened [PR #2](https://github.com/DVDWK812/Finscope/pull/2) against `main` and attached it to the Codex chat. The PR is open for review, not merged. [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) remains open because API-evaluation gates are unresolved.
- Verified GitHub Actions [tests run 39977138588](https://github.com/DVDWK812/Finscope/actions/runs/39977138588) completed successfully for PR head `44ba4bc`; this is an observed CI result. The local pre-publication run passed all 27 tests and the dry run. A following documentation-only commit records this evidence and will trigger its own checks.
- Tracked-file audit found no ignored report/.env paths or secret-like token/private-key patterns; `.env` and the live report remain ignored. No new provider requests were made during publication. GDELT remains provisional; FinBERT/dashboard work is unstarted.

## 2026-10-24 — PR #2 correctness, security and maintainability review

- Reviewed open PR #2 at `7a656df2436cc12538595b796cbb26313fa1fc00` against `main` (`7614590`), including adapters, CLI, tests, workflow, report paths and documentation. Reconfirmed a clean branch and re-ran all 27 baseline tests plus dry run before changes. PR was not merged.
- Found a request-budget defect: valid HTTP-date Retry-After values were discarded and restarting the CLI lost a 429 hold. Added validated seconds/date parsing and atomic local cooldown persistence; missing headers on 429 use a conservative 24-hour hold. Invalid state fails closed. Direct API transport still has no automatic retry or redirect. Local serial-run assumption is documented.
- Found input-quality defects: dictionaries/lists could become nonempty text through `str()`, whitespace descriptions counted as usable, and date-only/zero-epoch placeholders could inflate publication completeness. Normalization now rejects malformed text/credential-bearing URLs and incomplete timestamp sentinels. Added title length/word and timestamp-kind metrics without an NLP model or tokenizer.
- Restricted CI token permission to read-only contents and added the no-network dry run as a CI step. Existing transport redaction and ignored-report/key rules remain in place. No API keys or bodies were read into diagnostics or added to commits.
- All 36 tests and dry run passed after corrections, including new date-header, persisted-hold, corrupt-state, malformed-field, sentinel-timestamp and NLP-metric regressions. An intermediate timestamp test failure exposed a misplaced validation guard; it was corrected before this milestone passed.
- Optional-provider follow-up: `reports/phase1_optional_followup_20261024.json` records one healthcare query plan each for Marketaux, NewsData.io and Finnhub as skipped/missing_credentials; zero HTTP requests. The earlier live healthcare metadata was reanalyzed offline into `reports/phase1_nlp_input_review_20261024.json`, not refetched.
- Both the original live sample and this review are dated 24 October in Sydney (23 October UTC), so another-day evidence is still pending. Seeded the local conservative GDELT hold from the last recorded 429 through 2026-10-24T15:09:44.173494+00:00; this is local policy derived from saved evidence, not a new provider header or response.

## 2026-10-24 — Follow-up evidence, permission and scheduling milestone

- Saved tested review fixes in `2ce44d6`. Offline reanalysis of the three original healthcare titles: lengths 71–83 characters, mean 77.0; whitespace words 10–13, mean 11.3; descriptions 0/3, publication times 0/3, first-seen times 3/3. Original relevance judgments remain 2 relevant / 1 uncertain with likely event overlap; no new headline or precision evidence was invented.
- Reread GDELT, Marketaux, NewsData.io and Finnhub official terms. Added separate public-display, metadata-retention and derived-analysis/output decisions. Corrected the overly narrow NewsData interpretation to include its external-derivative/sharing clauses alongside API restrictions and publisher rights; no permission was inferred for the free public MVP. No provider was contacted.
- Added explicit NO-GO for Phase 2 and a release-gate table in DECISIONS.md. GDELT stays provisional; missing keys, different-day availability, usable finance input and timestamp scope remain open. No full-text crawling, FinBERT, embeddings or dashboard work was introduced.
- Created and verified active one-shot chat automation `finscope-different-day-feasibility-check` for 25 October 2026 at 09:00 Australia/Sydney (24 October 22:00 UTC); host timezone is AUS Eastern Standard Time. Its saved prompt enforces both new calendar dates, 24-hour separation, persisted cooldowns, one GDELT healthcare request, no retry/pagination, optional-provider skips, evidence updates and exact-head CI verification. This is pending work, not a completed retest. Local computer/app availability is required.
- Updated API_EVALUATION.md and DECISIONS.md with source-backed limits and recommendations. Issue #1 and PR publication/CI are updated after the documentation milestone is committed and pushed; earlier successful CI is not presented as a check of new commits.

## 2026-10-24 — Follow-up publication and CI verification

- Pushed `2ce44d6` (review fixes) and `5f99533` (NLP/rights evidence and Phase 2 gates) to the existing PR branch. Verified remote feature head equals local `5f995338fb88e57e8e72ac4c7776aded6f8853f8`; remote `main` remained `7614590`.
- Submitted a [COMMENT review on PR #2](https://github.com/DVDWK812/Finscope/pull/2#pullrequestreview-5630804704) describing findings, fixes, review scope and remaining feasibility gates. This is a Codex-assisted review, not an independent approval. Updated [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) with NO-GO, current skips, offline NLP metrics, corrected permission interpretation and the pending one-shot retest.
- Verified [GitHub Actions run 39981319191](https://github.com/DVDWK812/Finscope/actions/runs/39981319191) completed successfully for head `5f99533`. This following documentation-only record triggers its own checks, to be verified separately. PR remains unmerged; different-day GDELT evidence remains pending.
