# Development log

Use this document for milestones supported by links to GitHub commits, PRs, or Issues. Do not claim results until verified.

| Milestone | Status | Evidence / next step |
|---|---|---|
| Initial repository scaffold | Prepared locally, not pushed | Push `FinScope` scaffold to GitHub and link the commit |
| API candidates and evaluation plan | Prepared; dry-run verified | See `docs/API_EVALUATION.md` |
| Offline adapter unit tests | Verified locally (11 passed) | `python -m unittest discover -s tests -v`; CI not run yet |
| Live API comparison | Not started | Run with network access and real environment variables |
| Source selection | Not started | Review test findings and licensing |
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
