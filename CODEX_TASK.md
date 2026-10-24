# Current Codex task: Phase 1 keyed financial-news provider evaluation

**Date:** 2026-10-24 (Australia/Sydney)
**Repository:** DVDWK812/Finscope
**Branch policy:** `main` only. This task supersedes the original GitHub bootstrap instructions. Prior changes remain in Git history.

## Objective

Run a bounded, evidence-based, **local-only** news metadata feasibility comparison using the user's newly registered **Marketaux**, **NewsData.io**, and **Finnhub** free API accounts. The existing adapters are in `finscope/api_sources.py`, and the benchmark CLI is in `finscope/benchmark.py`. Do not rebuild them unnecessarily. **Do not activate real news in the public dashboard.** Phase 2 remains NO-GO until the documented source gates are independently resolved.

## Pre-flight and credential handling

1. Verify `git status`, fetch `origin`, and fast-forward `main` using `git pull --ff-only origin main` **only when it is safe**. If working-tree changes or divergent commits exist, preserve them and resolve safely; never force-push, reset, delete uncommitted work, or create a new branch/PR.
2. Review `AGENTS.md`, `docs/API_EVALUATION.md`, `docs/DECISIONS.md`, `.env.example`, `.gitignore`, and both API modules.
3. The user reports registering the three API keys. **Do not assume keys are already installed locally.** Load only `FinScope/.env` (already supported); ask the user to enter missing credentials *on their own machine*, never in chat, logs, commits, GitHub issues or CI secrets. Keep `.env`, local JSON reports, and cooldown state ignored. Never print any part of a key.
4. Run `python -m unittest discover -s tests -v` and `python -m finscope.benchmark --dry-run --providers marketaux newsdata finnhub --topics healthcare`. Confirm the dry run reports three configured credentials without issuing HTTP requests.
5. Verify endpoint contracts and current free-plan limits from each provider's official documentation. Marketaux free: 100 news API calls/day and maximum 3 articles/request; group_similar=false for independent dedup evaluation. NewsData free: 200 credits/day, up to 10 articles/credit, approximately 12-hour delay and limited latest window. Finnhub: use the actual free account entitlement; never infer rate limits from the 30-calls/second aggregate cap. NewsData's free AI tag/sentiment entitlements conflict across published materials; do not rely on provider sentiment as project FinBERT output.

## First live experiment (only after the local keys exist)

Use **one real request per provider** for the *healthcare* topic to validate authentication and payload shape, with no pagination, retries or extra calls:

```powershell
python -m finscope.benchmark --providers marketaux newsdata finnhub --topics healthcare --limit 3 --days 2 --output reports/keyed_healthcare_initial.json
```

- This is **three possible provider requests, not twelve**; missing credentials count as skipped and spend no quota.
- Stop testing any provider immediately after HTTP 429, or auth/permission error, and log the failure category; do not try another topic merely to circumvent failure or a provider hold.
- Do not run GDELT in this task. Preserve the existing 25 October 09:00 Sydney scheduled one-shot and its local attempt/cooldown state; do not create a duplicate, delete any marker, or make a catch-up request.
- Check reports manually for authentication, status, latency, response shape, normalization loss, finance relevance, title length, description coverage, original URLs, source diversity and **published** timestamp coverage. Provider return counts cannot be compared without conditioning on their different query scopes.
- Finnhub's `PFE` company-symbol query is **not** sector-wide pharmaceutical coverage; report it separately.

## Expansion gate

Only if the initial test succeeded with valid news records and provider limits permit, test the remaining topics once each per *eligible* provider:

```powershell
python -m finscope.benchmark --providers marketaux newsdata finnhub --topics technology materials --limit 3 --days 2 --output reports/keyed_followup_topics.json
```

Do not blindly run this with failed or rate-limited providers: remove ineligible providers from the command. Do not add multiple pages, excessive retries, or a long-running scheduler. If the initial evidence is inconclusive, state the limitation rather than escalating traffic.

## Required evaluation

For each attempted provider/topic, distinguish `ok`, `failed` and `skipped`, with exact UTC query time, HTTP status, latency, raw/valid/sample counts, unique sources and metadata completeness. Manually review relevance for actual titles and mark uncertainty. Record distinct timestamp semantics, query scope and accessible history. Evaluate **text suitability** for future FinBERT and sentence embeddings, not just whether HTTP 200 was returned.

**Rights are a separate GO/NO-GO gate:** a free personal account and successful local API response do **not** authorize a publicly deployed app to display, retain, or share publisher articles or derived results. Confirm endpoint-/plan-/field-specific permissions; Marketaux public display rights are unclear, NewsData restrictions/derivative permissions require reconciliation, and Finnhub personal terms prohibit sharing raw or derived data without written approval. Do not upload publisher text, actual article dumps or copyrighted extracts to GitHub. Retain permitted evidence only locally in ignored `reports/`; commit concise aggregate metrics and source links.

## Deliverables and checks

- Update `docs/API_EVALUATION.md`, `docs/DECISIONS.md` (conditional recommendation), and `docs/DEVELOPMENT_LOG.md` with **only observed results**, dates, sample limitations, rights and remaining gates.
- Update the existing [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) with non-sensitive outcomes; do not close it unless all required gates are satisfied.
- Add/fix regression tests if adapters or benchmarking code require changes. Otherwise avoid changing working code unnecessarily.
- Run the complete offline test suite and dry run. Commit and push verified updates **directly to main**, without force pushing or creating feature branches/PRs; verify exact remote commit SHA and corresponding GitHub Actions status.
- Report to the user: keys configured (yes/no **without revealing them**), request attempts and outcomes for each provider, finance relevance, timestamp and text completeness, source-licensing restrictions, and a recommendation for the next data-source test.
- **Do not** wire any provider to Streamlit, run FinBERT, implement embeddings, start crawling, or claim Phase 2 GO. No automated public-news pipeline yet.
