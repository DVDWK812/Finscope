# Current Codex task: Phase 1.5 Marketaux validation design

**Date:** 2026-10-25 (Australia/Sydney)
**Repository:** DVDWK812/Finscope
**Branch policy:** main only; no feature branches, PRs, force pushes or discarded work.

## Objective and current evidence

Validate Marketaux as the preferred conditional financial-news candidate before production integration. Read AGENTS.md, README.md, docs/API_EVALUATION.md, docs/DECISIONS.md, docs/KEYED_API_TEST_PLAN.md and docs/PHASE15_MARKETAUX_PLAN.md. The prior staged keyed experiment is completed: 7 requests, 7 HTTP 200, with 2 NewsData expansion topics skipped for its hold. Preserve original local reports unchanged. Do not rerun the old staged commands as a new task.

This Phase 1.5 checkpoint audits saved evidence, investigates official documentation and designs the bounded multi-day study. It makes **zero new news-provider requests** and creates **no automation**. Proposed dates in the study are not scheduled work or executed results. Future collection must satisfy the plan's attempt ledger, quota/hold checks, spacing and transient description-review safeguards first. Do not re-query to recover text omitted from reports.

## Required work

1. Inspect status, fetch origin, safely switch to main and pull --ff-only origin main before editing. Stop on unrelated edits/divergence; preserve all work.
2. Review existing keyed evidence with sample denominators and query scopes intact. Relevance from title/URL is distinct from description informativeness and independently validated NLP accuracy. Keep publication time separate from retrieval/first-seen time and exact duplicates separate from event overlap.
3. Use the Phase 1.5 plan: proposed three Marketaux-only manual rounds, one request per sector per round, at most 9 new requests total. The study is designed, not dispatched by this instruction. No retries, extra pages, catch-up requests or entitlement/history probes.
4. Investigate NewsData HTTP 200 plus Retry-After=900 using saved evidence and official sources. Preserve the cooldown file unchanged. The historical timed deadline has elapsed; live NewsData testing remains manually paused until header meaning/account constraints are clarified. The generic CLI's expiry check alone does not enforce that manual pause.
5. Verify documented Marketaux free history, quota windows and intended-use permissions separately. Record unknowns rather than infer rights from a free account or a successful response. Prepare questions covering public display, per-field retention/deletion, team review, pretrained inference and derived outputs. Do not contact providers without explicit messaging authorization.
6. Preserve the existing 25 October 09:00 Sydney GDELT one-shot, its attempt marker state and saved cooldown. Do not make a duplicate/catch-up request, alter its schedule or clear a hold. Its authorized execution is governed separately by the existing automation, not by this design task.
7. Update evaluation, decision and development-log documents and Issue #1 with observed, non-sensitive evidence. Keep historical statements dated. Record Codex assistance accurately.
8. Add meaningful offline regression coverage for observed HTTP-200 Retry-After behavior. Run `.venv/Scripts/python.exe -m unittest discover -s tests -v` and `.venv/Scripts/python.exe -m finscope.benchmark --dry-run`; all tests must use synthetic fixtures/mocks with no provider calls. Commit/push coherent tested changes directly to origin main, verify full remote SHA and exact-commit push CI. Record post-push evidence in Issue #1; do not claim CI passed before observing it.

## Safety and release decision

Load keys only from ignored project-local .env. Never print key values/fragments/hashes, persist raw HTTP payloads or put keys/real news content in Git/Issues/CI. Keep existing reports, cooldowns and local audit notebooks ignored. Do not extend publisher-text retention without a verified basis. Future description labels must be produced from the same permitted response in memory and persisted as categories/counts only; no raw descriptions or body snippets.

Keep **Phase 2 production integration NO-GO** until every documented gate is satisfied: multi-day reliability/representativeness, useful permitted short text and intended NLP validation, timestamp accuracy, history/quota sustainability and display/retention/inference/derived-output rights. No real Streamlit data, FinBERT, embeddings, inference, crawling or public provider pipeline is authorized. The synthetic-only UI exception is unchanged.

The completed keyed experiment's protocol and actual results remain in KEYED_API_TEST_PLAN.md, API_EVALUATION.md, DEVELOPMENT_LOG.md, ignored local reports and Git history.
