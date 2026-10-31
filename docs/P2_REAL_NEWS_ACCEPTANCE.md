# P2 real API news acceptance — 1 November 2026 Sydney

**Real-news end-to-end acceptance is incomplete.** Baseline and fetched
`origin/local` at start: `b1e1ab8ab995f4b30db7fb529e3d70872afdc167`. Work uses the
existing `local` worktree; the separate dirty `main` checkout remains preserved.

## Existing connections, previews and budget

Read-only production SQLite receipts confirm the earlier formal localhost:8511
requests. These are historical connection evidence, not new P2 requests:

| Provider | Request start (31 October 2026 UTC) | HTTP | Returned / previewed |
|---|---|---|---|
| Marketaux | 15:48:17.667827 | 200 | 3 / 3 |
| Finnhub, NVDA | 15:49:00.190191 | 200 | 250 / 3 |

Both saved profiles allow personal preview, with retain/analyze/external false.
Each attested one request for UTC 31 October and has used that request. A date
rollover does not attest a new allowance. New news-provider/collector requests,
model calls, retries and key rotations this round: **zero**.

The existing 8511 listener (PID 27264) was healthy. Browser inspection was stopped
by the tool because it could not reliably establish the Windows browser URL.
Original session previews are **not verified present or lost**. No restart,
memory extraction or reconstruction from receipts was attempted. On the user's
request, opening the existing localhost URL in the Codex panel was requested;
opening a panel does not inspect the earlier browser session.

The user was asked to select an existing preview and supply the account-specific
storage/NLP basis, fields and retention period. At this checkpoint no selection
or additional rights evidence was supplied. P2 API article counts: **0 retained,
0 classified, 0 sentiment-analyzed**. Historical official-source articles are not
substituted for this acceptance.

## Text scope and rights review

Official sources checked on 1 November Sydney:

| Provider | API text and implemented normalization | Unresolved scope |
|---|---|---|
| Marketaux | [Documentation](https://www.marketaux.com/documentation) distinguishes title, description (meta description) and snippet (short body excerpt). FinScope uses description, not snippet or publisher full text. | [Terms](https://www.marketaux.com/tos) allow personal noncommercial access/download, reserve other rights and separately address third-party content. Account-specific field retention and NLP rights are unverified. |
| Finnhub | [Official company-news schema](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml) supplies headline, summary, source, publication time and original URL. FinScope uses summary, not full text. | [Terms](https://finnhub.io/terms-of-service) reserve IP rights, restrict sharing data/derived results without written approval and require deletion when the data subscription ends. Account eligibility and retention/NLP rights remain unverified. |

Titles/source/time/URLs, API summaries/snippets and publisher bodies are separate
scopes. API access and model weight licences do not establish storage/NLP rights.
Only existing nonsecret request metadata is retained without additional article
permission; no broader metadata/text permission, public use or team sharing is
claimed. No publisher body was fetched and no permission checkbox was changed.

## Minimal retained-preview handoff

The existing session preview now supports exactly one selected article, headline
only or headline plus API summary, an article-specific rights reference and
explicit storage/NLP/selection confirmation. Checkboxes default off; a changed
selection, scope or reference requires fresh confirmation. A receipt alone cannot
create this action.

The queue atomically writes the approved fields into the existing saved-originals
checkpoint with a source-free **local FinBERT** task. Saved source/model drafts,
budgets and request ledgers are unchanged. Body, old preprocessing and preview
sector labels are excluded; headline-only also removes summary before SQL writes.
Existing explicit article restrictions remain authoritative. The unchanged worker
performs preprocessing, canonical-original matching, evidence-backed two-level
classification (or Unclassified), local pinned inference and versioned result
storage. No external LLM is selected. Failed checkpoint insertion rolls back the
task; repeated identical text reuses originals and cached results.

Authored offline fixtures and mocked inference verify handoff, scope removal,
rollback, permission restrictions and no fetch/replay. Streamlit AppTest verifies
selection and confirmation changes. These are software checks only. **Actual API
article FinBERT inference, metadata correctness and Dashboard/News Explorer
click-through remain unverified**, because no selected article with verified
processing rights was available and formal-browser inspection stopped.

## NewsData resumption conditions

The original 24 October healthcare HTTP 200 response included Retry-After 900,
numeric limit 60 and remaining 59. The historical timed hold expired; the manual
pause remains. Earlier 30-credits/15-minutes guidance did not explain those
successful-response headers; preserve [the evaluation](API_EVALUATION.md) and
[clarification questions](PHASE15_MARKETAUX_PLAN.md).

Current [NewsData terms](https://newsdata.io/terms), API KEY/API RESTRICTIONS,
expressly prohibit multiple accounts and use of multiple API Keys. Existing
primary/backup entries prove neither compliance nor an entitlement to use them.
No key was tried, promoted, deleted or changed. Resumption needs:

1. Provider/account evidence explaining successful-response Retry-After and the
   applicable quota/credit window.
2. A compliant single-key arrangement or explicit supplier exception to its
   multiple-key prohibition; backups cannot increase the allowance.
3. Account eligibility and API-field storage/NLP/retention evidence. Its terms
   separately reserve third-party raw-data rights.
4. Explicit user approval to lift the manual pause, a reviewed code change
   preserving safeguards, current UTC-day allowance and bounded request consent.

No supplier contact or pause change occurred.

## Verification and preservation

The configured `.venv-ai/Scripts/python.exe` runs the isolated full unittest suite;
the benchmark dry run uses FINSCOPE_TESTING=1. Initial bare Python lacked Streamlit
and failed; it is not counted as successful verification. Final configured-runtime
results, exact pushed SHA and CI are reported with delivery and ignored evidence.

The before/after preservation audit covers all 22 production data tables excluding
worker heartbeat, 47 originals, 83 analyses, nine news requests, four tasks and
the existing 171 frozen files. Credentials, .env, assets, ledgers and real article
text stay local and outside commits. Tests/push/CI do not close real acceptance.
Codex assisted implementation/verification; no frozen evaluation rerun, tuning,
coursework submission or Moodle access occurred.
