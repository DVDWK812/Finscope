# Current Codex task: Phase 1.5 safeguards and independent AI interfaces

**Date:** 2026-10-25 (Australia/Sydney)
**Repository:** DVDWK812/Finscope
**Branch policy:** main only; no branches/PRs, force pushes or discarded work.

## Authorized scope

Read AGENTS.md, README.md, docs/PHASE15_MARKETAUX_PLAN.md, API_EVALUATION.md, DECISIONS.md and AI_PROTOTYPE.md. Implement/test the bounded in-memory description reviewer and persistent attempt ledger with duplicate, quota, budget, spacing, crash and cooldown safeguards. **Do not execute or schedule Marketaux sampling rounds without separate explicit authorization.** No default network backend or saved approval is installed; the old keyed Marketaux live benchmark path is blocked.

Independently implement modular FinBERT inference and embedding similarity contracts using **synthetic or explicitly licensed evaluation text only**. This explicit prototype scope supersedes earlier blanket instructions against interface-only AI work. Do not feed API records, download/load weights automatically, add heavy model libraries, connect Streamlit or claim model accuracy. All current backends in tests are synthetic mocks; real model execution/evaluation is not established.

## Required workflow

1. Inspect status/README/tests, fetch origin, safely switch/pull --ff-only main before edits. Preserve unrelated work and stop on divergence. No feature branches or new PRs.
2. Preserve original keyed evidence and the existing GDELT automation/attempt/cooldown state. No duplicate task, catch-up, retry or hold edits. NewsData remains manually paused pending HTTP-200 Retry-After clarification, even after its historical timed deadline elapsed.
3. Implement the prospective study policy from PHASE15_MARKETAUX_PLAN.md: fixed three dates/sectors, at most three daily/nine total requests, cap three records, two-day slice, group_similar=false, committed pre-dispatch reservations, verified recent account quota and existing holds, at least 60 seconds after completion. A pending/ambiguous attempt consumes budget and blocks collection; never clear it automatically.
4. Keep descriptions transient. Return/persist only bounded indices, categories, annotation basis and lengths/counts; never raw text, keys, callback errors or payloads. Missing/exact-repeat rules are distinct from manual informativeness annotation. One annotation is not independent NLP accuracy.
5. Keep AI contracts independent from API/UI modules. Require provenance and explicit local backend identity/revision; validate complete probabilities and finite equal-dimensional vectors. No heuristics masquerading as FinBERT or embeddings. Review model weight/input/output licences separately before any real model use.
6. Run the complete offline unittest suite and all previews: `python -m unittest discover -s tests -v`, `python -m finscope.benchmark --dry-run`, `python -m finscope.sampling --dry-run`, `python -m finscope.ai_prototype --dry-run`, using the existing .venv. Tests use synthetic fixtures, mocks and temporary ledgers only; no real provider calls, training or inference.
7. Update DEVELOPMENT_LOG.md after coherent milestones and keep evaluation/decision/README/task docs current. Record Codex assistance and remaining permission/evaluation gaps accurately. Commit meaningful tested milestones directly to main; push and verify full remote SHA and exact-head GitHub Actions. Record post-push evidence in Issue #1 without keys or publisher content.

## Production gate

Marketaux remains a preferred conditional candidate, not an approved production source. Public display, retention/deletion, team review, pretrained inference and derived-output permission, free history/account quota, multi-day reliability, useful descriptions, timestamp accuracy, representative sources/events and independent intended-model evaluation remain open. **Phase 2 production integration stays NO-GO.** Synthetic UI and the independent synthetic/licensed interface prototype do not close any of these gates. No real news/model/UI pipeline, crawler or publication of publisher text is authorized.

Keep .env, original evidence, local reports and SQLite state/journals ignored. Never print key values/fragments/hashes, commit restricted news or silently reset the study ledger. No provider messages are authorized by this task.
