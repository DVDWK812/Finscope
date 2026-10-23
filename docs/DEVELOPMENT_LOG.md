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
