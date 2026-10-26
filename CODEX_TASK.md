# Current Codex task: guarded live-runner preparation and pinned local FinBERT

**Date:** 2026-10-26 (Australia/Sydney)
**Repository:** DVDWK812/Finscope; main only.

## Scope and controls

Review AGENTS.md, README, API_EVALUATION.md, DECISIONS.md, DEVELOPMENT_LOG.md, PHASE15_MARKETAUX_PLAN.md, MARKETAUX_RUNNER.md and AI_PROTOTYPE.md. The completed GDELT one-shot has a retained execution marker/report and its automation was deleted. It failed at transport with no observed HTTP response. Do not retry, recreate or reschedule it.

Prepare the Marketaux live runner around the existing guarded sampler. Default/preflight is offline; explicit future dispatch requires separate actual human authorization scoped to dates/sectors, fresh operator-confirmed account quota/reset evidence and credentials. Do not make approval/quota files on the user's behalf or execute/schedule Marketaux in preparation work. Retain SQLite pre-dispatch reservations, unknown/crash/duplicate protection, fixed windows/dates, three daily/nine total caps, 60-second spacing, cooldowns and no retries/pages/automatic waits. Do not catch up missed dates or silently change the plan. NewsData remains manually paused.

The user independently authorizes a minimal local FinBERT backend using only synthetic/explicitly licensed evaluation text. Optional runtime/model asset preparation is explicit, separate setup, never an automatic import/inference download. Pin model revision, weights/tokenizer/config hashes, weight licence and runtime versions; use local-files-only, safetensors, no remote code, CPU inference mode, validated labels and no silent token truncation. Keep weights/runtime environments ignored and out of the API/UI environment. Separate actual smoke outputs from mock tests; smoke predictions are not independently validated accuracy. Embedding interfaces remain mock-only unless separately implemented/authorized.

No real API record is an AI input, and no AI/API data is connected to Streamlit. No crawler, training, public data/model pipeline, provider contact, new branch or PR. Phase 2 production integration remains **NO-GO** until every source/model/data-rights and evaluation gate is independently satisfied.

## Workflow and verification

1. Inspect status/README/tests, fetch origin, safely switch/pull --ff-only main. Preserve unrelated work; stop on divergence; never force push or discard changes.
2. Preserve GDELT completed proof, keyed pilot reports and full shared cooldown. No new news-provider calls. Model/package source reads and explicitly prepared model artifacts are separate from news sampling.
3. Run the entire lightweight unittest suite, including mocked loader/runner/token-limit tests. Run all five no-network previews: benchmark, sampling, ai_prototype, marketaux_runner and finbert_backend with --dry-run. CI must not install weights or perform trained-model inference.
4. If performing an explicitly prepared local synthetic smoke run, record actual model/revision/licence/runtime, fixture IDs, probabilities, token counts, elapsed times and limits separately from mocks, with no accuracy claim. Do not reuse old report filenames or recover discarded news text.
5. Update development log at milestones and evaluation/decision/task documentation with observed facts and open gates. Record Codex assistance.
6. Commit tested coherent changes directly to main, push, verify exact full remote SHA and exact-head PUSH-triggered Actions. Record post-push evidence in Issue #1 without keys, publisher text, local reports or weights. Do not claim push/CI succeeded until verified.

Never print key values/fragments/hashes or commit .env, article text, restricted data, model weights, local runtime/SQLite files or raw reports. Local source-provenance/licence acknowledgements are operator attestations, not general deployment approval.
