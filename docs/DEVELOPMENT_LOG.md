# Development log

Use this document for milestones supported by links to GitHub commits, PRs, or Issues. Do not claim results until verified.

| Milestone | Status | Evidence / next step |
|---|---|---|
| Initial repository scaffold | PR #2 merged by user; main-only workflow active | Merge `6ae8e00`; complete Phase 1 work preserved on main; merged feature branches deleted |
| API candidates and evaluation plan | Official documentation and terms reviewed | See `docs/API_EVALUATION.md` |
| Offline adapter unit tests | 36 passed locally on synchronized main; main push CI verified for `db296c5` | [CI run](https://github.com/DVDWK812/Finscope/actions/runs/39984381988); later documentation requires exact-head CI |
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

## 2026-10-24 — Main-only synchronization and branch cleanup milestone

- Initial working tree was clean. Verified through GitHub that PR #2 was merged by the user on 2026-10-23T16:03:24Z as `6ae8e00b7984181697c3bd16ac65e7e91587a88e`; no attempt was made to change its merged state. The later instruction to keep it unmerged cannot describe the verified current state, so no further PR/merge action was taken.
- Fetched origin, switched safely to existing local main and ran `git pull --ff-only origin main`, fast-forwarding to `f43210275141ae7a5dd44cd2a276b29847e73394`. Preserved the user's newer main-only changes to AGENTS.md, CODEX_TASK.md and README.md; configured main to track origin/main. No force push, reset, discarded work, new branch or new PR.
- Verified `1ef306a` is an ancestor of main and the old branch has zero unique commits. Compared all Phase 1 source/test/CI/evidence/dependency/ignore/licence files with the old head: no differences. Deleted the merged local branch with `git branch -d` and remote branch with normal `git push origin --delete`; remote ref inspection confirmed only main remains.
- Re-ran all 36 offline tests and benchmark dry run successfully on main, with zero provider requests. Verified PUSH-triggered Actions run [39983651007](https://github.com/DVDWK812/Finscope/actions/runs/39983651007) succeeded for full main SHA `f43210275141ae7a5dd44cd2a276b29847e73394`. Queried push runs directly because the PR-specific workflow helper excludes them.
- Updated the existing one-shot automation in place, preserving its name, active status and 25 October 09:00 Sydney schedule. Its prompt now uses main only, prohibits new branches/PRs, checks prior execution evidence, retains at most the previously authorized one GDELT request, forbids extra optional-provider calls, and requires exact metrics/skips, all-gate reassessment and exact-main CI. Missing report/intent evidence cannot justify a repeat request.
- As of this handover (24 October Sydney / 23 October UTC), the scheduled time is still future and no execution report was found. No one-shot HTTP status, latency, records or new NLP text can be reported yet. This is pending, not a cooldown skip. Saved cooldowns and ignored reports are preserved; no live API calls were made. Phase 2 remains NO-GO and GDELT provisional.
- Updated API_EVALUATION.md and DECISIONS.md to distinguish verified merge/main status, pending task execution and actual provider evidence. Issue #1 and this documentation's publication/CI status are updated after commit and push.

## 2026-10-24 — Main handover publication verification

- Committed the three-document handover/audit update directly on main as `db296c50a521c946984e44212c9dff1ba2184546` and pushed normally to origin main. Verified exact local/remote SHA equality, a clean working tree and absence of the deleted remote feature ref. Updated Issue #1 to the merged/main-only status and pending one-shot evidence audit.
- Verified PUSH-triggered [Actions run 39984381988](https://github.com/DVDWK812/Finscope/actions/runs/39984381988) completed successfully for `db296c5`, including the unit-test and benchmark dry-run steps. This following log-only commit requires its own exact-head check before claiming final CI success.
- The active one-shot's saved configuration retains its original one-occurrence schedule and chat target, with main-only, no-repeat/no-extra-call auditing instructions. No scheduled execution is claimed early; the original provider results and all NO-GO gates remain unchanged. No additional news API requests were made.

## 2026-10-24 — Parallel synthetic UI prototype

- User approved parallel UI work despite Phase 2 NO-GO. No production data-source decision changed.
- Added Streamlit Overview, Trends, News Explorer and System Status with sidebar filters, raw/event count toggle, source traceability fields and prominent synthetic-data warnings.
- Added `NewsRepository` contract and 12 invented article records containing 10 illustrative events (not embedding-derived); synthetic URLs are absent and the app performs no provider requests or model inference.
- Offline test environment ran 11 new UI-data unit tests successfully and compiled the new Python files. This does not establish a successful Streamlit browser/runtime test, full-project test run or GitHub Actions result; verify those independently after push.
- Development remains on `main` only. Follow-up: use Codex to visually verify Streamlit, test empty filters and runtime compatibility, and capture screenshots labeled synthetic for user testing.

## 2026-10-24 — Saved-results-only execution audit checkpoint

- Began with a clean main, fetched origin and pulled with `--ff-only` to `8f7d730`, preserving the user's synthetic-only UI work and updated instructions. No branch/PR, UI code or live provider call was introduced by this audit.
- At 2026-10-23T16:20:27.754470+00:00 (24 October 03:20 Sydney), verified the active one-shot is scheduled for 25 October 09:00 Sydney, still future. No attempt marker or one-shot result report was found. Classified as not yet due/no execution evidence, not a cooldown skip or failure. Its status/latency/records/NLP input remain unobserved; no result was invented.
- Audited all saved report types and saved a compact local inventory in ignored `reports/phase1_execution_audit_20261024.json`. Actual historical evidence remains 3 GDELT HTTP responses: technology 429 / 11,962.4 ms, healthcare 200 / 20,217.3 ms / 3 title-only records, materials 429 / 12,342.2 ms. No different-day result exists. Optional follow-up rows are explicit missing-key skips; plans, offline metrics and synthetic fixtures are not extra provider requests.
- Ran the full suite: all 47 tests passed, including 11 tests for the newly fetched synthetic UI data adapter. Benchmark dry run passed with zero HTTP provider requests. No Streamlit browser/runtime pass is claimed. Preserved the schedule, attempt guard and cooldown without a retry or catch-up call.
- Reassessed every release gate, adding explicit history/quota sustainability to the decision table. Repeat availability, representative finance/NLP input, publication-time scope, usable history/quota and field/plan-specific display/retention/derived-output rights remain open. Operational local checks pass but cannot clear the source gates. Phase 2 stays NO-GO; synthetic-only UI exception is unchanged.
- Updated API_EVALUATION.md and DECISIONS.md with the timestamped audit and local-host requirement. This machine need not stay on continuously beforehand, but must be awake/online with Codex running at the scheduled time and through completion. Issue #1, push SHA and exact-head Actions are verified after this documentation checkpoint is committed.

## 2026-10-24 — Synthetic UI runtime, filter and responsive verification

- Started from clean main at `39a1c06`, fetched origin and confirmed `git pull --ff-only origin main` was current. Reviewed `8f7d730`, the complete Streamlit scaffold, data contract, tests, UI specification and existing API/decision evidence. All work stays on main; no branch or PR was created.
- Installed requirements into ignored `.venv` (Python 3.12.3, Streamlit 1.66.1, pandas 2.3.3), with a separate ignored `.venv/compat` for minimum Streamlit 1.50.0. An initial shared-Anaconda install exposed an unrelated Jina/uvicorn constraint; removed only the newly installed packages and restored the original uvicorn 0.23.1 before continuing in isolation. Both project environments pass `pip check`.
- Launched Streamlit on loopback `127.0.0.1:8501` with usage statistics disabled. Baseline AppTest rendered correctly but emitted deprecated `use_container_width` warnings. Replaced those options with `width="stretch"`, verified supported behavior against official Streamlit documentation and both supported-version test environments. A running server briefly retained an older imported helper signature during edits; restarting it resolved that development-session error before final browser validation.
- Improved consistent page titles, sentiment colors, theme, metric sizing/wrapping, selected-view captions and count-axis labels. Empty results now give recovery guidance and an unavailable positive share. Added a reset button, stable per-session fixture dates and an explicit non-synthetic-data guard. Daily counts use UTC even for offset-aware records, fill missing dates and use daily chart categories.
- Browser testing found a reset bug missed by AppTest: deleting state keys left old frontend values that returned on the next interaction. Reset now assigns explicit defaults; confirmed empty-filter reset clears the displayed widgets and subsequent raw/event interaction retains all 12 records. No warning is hidden to achieve a pass.
- Verified browser navigation among Overview, Trends, News Explorer and System Status. Narrowed UTC dates from 19–23 to 22–23 (6 articles / 5 events), then Healthcare (1 article / 1 event), preserving both filters into Explorer. A Negative filter produced an empty Explorer and Overview without a crash. Reset restored the fixture range and all results. Switching to raw mode retained 12 articles / 10 distinct events and changed positive share from 40% to 50%.
- Verified multi-sector event e07 in Explorer: article a09 links to both a08/a09, carrying Healthcare + Technology labels; changing from raw to event mode safely replaces an excluded representative. Added article IDs and a filtered source-report table to make event grouping inspectable. Full-data sector totals are 14 raw memberships versus 11 event memberships, not 12 versus 10, because multi-sector items contribute to each label. Grouping remains predefined demo IDs and earliest matching representatives, not a model or consensus.
- Responsive browser presets requested 390×844 and 768×1024; this host's scaling reported 407 and 800 CSS-pixel widths. At both sizes document width matched viewport width, metric cards wrapped, and phone sidebar navigation remained available. This is a limited local browser check, not an exhaustive device certification or user study. Screenshots are saved only under ignored `reports/ui_*_synthetic.jpg`.
- Added 8 data regressions and 11 Streamlit AppTest cases (66 total tests). Runtime cases block requests transport and assert it was unused. All 66 tests pass on both Streamlit 1.50.0 and 1.66.1; benchmark dry runs pass without provider requests. CI now runs the full suite and dry run against minimum/current Streamlit on Python 3.11. Final remote SHA and push-triggered Actions are checked after publication; no CI result is claimed in advance here.
- Updated UI_SPEC.md and API_EVALUATION.md with observed UI evidence and limits. AI assistance: Codex reviewed, implemented and tested these interface changes; they are not independent human usability or model evaluations. Phase 2 NO-GO and DECISIONS.md are unchanged. No live ingestion, FinBERT, embeddings, credentials, provider content or stored cooldowns were activated/modified; no scheduled feasibility task was run.
