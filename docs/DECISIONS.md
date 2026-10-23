# Phase 1 decision memo — 2026-10-24

Select **GDELT as the provisional primary for continued metadata feasibility work**. No provider is yet accepted as a reliable production source, and Phase 1's complete exit criteria are not satisfied.

GDELT has the strongest verified reuse basis among the reviewed options: its [dataset terms](https://www.gdeltproject.org/about.html#termsofuse) allow reuse and redistribution with attribution. One real healthcare query returned three usable metadata records. However, two of three API requests returned HTTP 429, the successful request took 20.2 seconds, and all three accepted records lacked descriptions and publication timestamps. This supports further metadata research only; it does not establish adequate text input for a future sentiment model.

Marketaux is the next finance-specific candidate to test when a local key exists, but public-display, retention and derived-analysis rights need written clarification under its [reviewed terms](https://www.marketaux.com/tos). NewsData.io and Finnhub are not cleared for public deployment under their reviewed standard terms. Finnhub also has a distinct company-symbol scope. Do not promote any of these as an approved fallback merely because an endpoint responds successfully. See the [evidence and permissions comparison](API_EVALUATION.md#first-evidence-review--2026-10-24-australiasydney).

## Evidence and outstanding gates

- Baseline: 11 existing offline tests passed. Current pilot: 27 offline tests and dry run passed. These are local results; GitHub Actions has not run.
- Actual API requests: three GDELT requests, one per topic, no retries. Two HTTP 429 failures; one HTTP 200. All nine optional-provider query rows are skipped because this project's `.env` has no keys. No live auth/schema/empty-result claim is made.
- The three healthcare headlines yielded two relevant trade items and one uncertain partnership item. Two stories likely describe the same event. Original links/times and manual annotations are in ignored `reports/phase1_live_20261023.json`; no article text is committed.
- Before closing Phase 1: obtain another-day availability/relevance evidence when practical, resolve rate-limit handling operationally without bypass, test available keyed alternatives at minimum cost, verify retention/history entitlements, and secure necessary public-display/storage/derived-output rights. If summaries are required later, reevaluate the data requirement rather than adding a crawler.
- GitHub connector login is DVDWK812. Intended repository [DVDWK812/FinScope](https://github.com/DVDWK812/FinScope) returned Not Found through both the connector and Git transport. Local `main` was initialized and work continues on `phase1/api-evaluation`. Repository creation is pending the user; no push, PR, Issue or CI success is claimed. Reconcile any initial remote README before pushing; never force-push over it.
- Confirm the official course code in Moodle. Record Codex assistance accurately in the assignment. No FinBERT, embeddings, crawler or dashboard development was started.
