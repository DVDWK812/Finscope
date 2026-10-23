# Development log

Use this document for milestones supported by links to GitHub commits, PRs, or Issues. Do not claim results until verified.

| Milestone | Status | Evidence / next step |
|---|---|---|
| Initial repository scaffold | Committed locally, not pushed | Baseline `3c7c738`; intended GitHub repository returned Not Found |
| API candidates and evaluation plan | Official documentation and terms reviewed | See `docs/API_EVALUATION.md` |
| Offline adapter unit tests | Verified locally (27 passed) | `python -m unittest discover -s tests -v`; dry run passed; CI not run |
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
