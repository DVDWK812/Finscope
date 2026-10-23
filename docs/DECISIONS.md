# Phase 1 decision memo — 2026-10-24

Select **GDELT as the provisional primary for continued metadata feasibility work**. No provider is yet accepted as a reliable production source, and Phase 1's complete exit criteria are not satisfied.

**Phase 2: NO-GO after the follow-up review.** Remain in Phase 1 until source reliability, usable input and deployment rights are supported. The different-day retest is scheduled, not yet completed; no new GDELT result is claimed.

GDELT has the strongest verified reuse basis among the reviewed options: its [dataset terms](https://www.gdeltproject.org/about.html#termsofuse) allow reuse and redistribution with attribution. One real healthcare query returned three usable metadata records. However, two of three API requests returned HTTP 429, the successful request took 20.2 seconds, and all three accepted records lacked descriptions and publication timestamps. This supports further metadata research only; it does not establish adequate text input for a future sentiment model.

Marketaux is the next finance-specific candidate to test when a local key exists, but public-display, retention and derived-analysis rights need written clarification under its [reviewed terms](https://www.marketaux.com/tos). NewsData.io has overlapping personal/internal and external-derivative/sharing clauses; it remains unapproved, rather than categorically prohibited for every public use. Finnhub personal-plan sharing of data or derived results requires written approval and its company-symbol scope differs. An API response does not clear any fallback. See the [current evidence and rights review](API_EVALUATION.md#follow-up-review--2026-10-24-australiasydney).

## Evidence and outstanding gates

- Baseline: 11 existing offline tests passed. Current pilot: 27 offline tests and dry run passed locally. GitHub Actions [tests run 39977138588](https://github.com/DVDWK812/Finscope/actions/runs/39977138588) completed successfully for PR head `44ba4bc`.
- Actual API requests: three GDELT requests, one per topic, no retries. Two HTTP 429 failures; one HTTP 200. All nine optional-provider query rows are skipped because this project's `.env` has no keys. No live auth/schema/empty-result claim is made.
- The three healthcare headlines yielded two relevant trade items and one uncertain partnership item. Two stories likely describe the same event. Original links/times and manual annotations are in ignored `reports/phase1_live_20261023.json`; no article text is committed.
- Before closing Phase 1: obtain another-day availability/relevance evidence when practical, resolve rate-limit handling operationally without bypass, test available keyed alternatives at minimum cost, verify retention/history entitlements, and secure necessary public-display/storage/derived-output rights. If summaries are required later, reevaluate the data requirement rather than adding a crawler.
- GitHub connector login is DVDWK812. After the initial Not Found responses, the user created public [DVDWK812/Finscope](https://github.com/DVDWK812/Finscope). Its initial README and MIT licence were reconciled with local milestone history on `phase1/api-evaluation`, preserving both histories. The feature branch was pushed and its remote SHA verified; [PR #2](https://github.com/DVDWK812/Finscope/pull/2) is open against unchanged remote `main` (`7614590`). [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) tracks remaining evaluation gates. Publication and CI verification are recorded in DEVELOPMENT_LOG.md.
- Confirm the official course code in Moodle. Record Codex assistance accurately in the assignment. No FinBERT, embeddings, crawler or dashboard development was started.

## Follow-up release gates

PR #2 was reviewed at `7a656df` and remains unmerged. Commit `2ce44d6` fixes persistent Retry-After/cooldown handling, malformed text/timestamp completeness and missing NLP metrics; 36 offline tests and the local dry run pass. New keyed-provider checks produced three skipped healthcare rows and zero HTTP requests. Reanalysis of the original sample found mean title length 77 characters / 11.3 whitespace words, zero descriptions and zero publication timestamps. These are the same three records, not new sampling.

The one-shot follow-up is scheduled for 25 October 2026, 09:00 Australia/Sydney, subject to local app/computer availability. It allows one GDELT healthcare request only after checking the different-day/24-hour and persisted-hold conditions. An HTTP 429 ends that attempt with no retry. Optional keys are checked locally at that time; absent keys stay skipped. New evidence, or a continuing blocker, must update the evaluation, log and Issue #1.

| Gate | Current status | Required evidence before Phase 2 |
|---|---|---|
| Repeat availability | Pending | Actual different-day result after cooldown; no conclusion from queued work or one lucky response |
| Financial NLP input | Not established | Manually reviewed finance-relevant samples for intended topics; adequate permitted descriptions, or an explicitly accepted and validated headline-only scope |
| Time semantics | Scope gap | Publication timestamps from an approved source, or explicit acceptance of discovery-time-only analysis |
| Public use and retention | GDELT dataset reuse basis strongest; alternatives unresolved | Field/plan-specific display, retention and derived-output basis; separately resolve publisher rights and training if relevant |
| Operational readiness | Pilot only | Verified CI on pushed head and a request budget that respects saved provider holds |

GO applies to continued bounded Phase 1 research only. No production provider selection, FinBERT, embeddings, crawler or dashboard work is authorized by this recommendation.
