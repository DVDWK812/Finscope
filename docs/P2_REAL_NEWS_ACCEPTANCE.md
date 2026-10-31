# P2 real API news acceptance — 1 November 2026 Sydney

## Follow-up from `0c50164` — formal session inspected

Latest fetched remote and clean worktree at start were
`0c50164ac3fca45190e20a74b8dae80bdf9c1307`. Browser control of the existing
localhost:8511 tab now works. Both source managers were inspected without
refreshing/restarting the app: each shows its historical HTTP-200 receipt, but
neither shows News preview or selected-preview processing controls. The **current
session has no usable retained Marketaux/Finnhub preview**. This establishes the
current session state, not the contents of another browser's earlier session.

The saved UTC 31 October budgets still each total one, with one existing request
used. Marketaux's Account usage link was inspected in a separate tab and reached
its login form; authenticated account allowance is not available to the agent.
No local receipt or public plan limit is substituted for actual remaining quota.
The original local permission/budget panel was expanded for the user without
editing values. A fresh, legal single-request allowance and explicit confirmation
were requested; no capture is dispatched while that confirmation is pending.
After a capture the user must select the article, fields and actual storage/NLP
basis locally. Current new API-news retained/classified/analyzed counts remain
zero, and actual API-news Dashboard/Explorer drill-down remains pending.

### NewsData correction and adapter scope

The earlier categorical multi-Key statement below was incomplete. The official
[multiple-Key article](https://newsdata.io/blog/multiple-api-key-newsdata-io/)
describes up to five keys within one paid/trial account; downgraded free accounts
lose created keys. This coexists with restrictive wording in the
[terms](https://newsdata.io/terms). It does not establish this user's entitlement,
permit multiple accounts or increase the shared account allowance. Clarify the
actual subscription and applicable terms with the provider before resumption;
keep the manual pause, headers/holds and existing keys unchanged.

The [response schema](https://newsdata.io/documentation/response-object) distinguishes
`description` (short description) and `content` (full content). The
[latest endpoint](https://newsdata.io/documentation/latest-news-api) documents
`full_content=1` as an availability filter, not a publisher-page fetch. The adapter
now accepts typed `NewsDataTextAccess`: unknown/free and paid-without-opt-in keep
headline/description only. Body opt-in requires both verified paid-plan entitlement
and a separate content-use reference; invalid policy fails before dispatch. Only
then is the filter set and real API `content` mapped to a separate `Article.body`,
with its evidence reference. Missing/malformed/upgrade-placeholder content never
becomes a body or an invented full text. `NewsItem` retains the separate body and
reference for existing preprocessing, storage/NLP gates and content history.
Existing title/summary-only article identities remain compatible.

No paid-body Settings control is enabled while the actual account and manual
pause are unresolved; passing a paid policy to the local service still fails
before request reservation or credential resolution. Body mapping is authored
offline adapter evidence, **not a real NewsData request or analysis**. Existing
primary selection/explicit promotion remains sequential, with no automatic
backup loop or retry and no bypass of source/account ledgers or unknown outcomes.

The following sections preserve the earlier checkpoint and its qualifications.

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


## Authorized single capture — 1 November 2026 Sydney

The user subsequently attested at least one lawful remaining Marketaux request,
confirmed the current primary and a UTC 31 October total of two, and explicitly
authorized one bounded preview with no retry, backup switch, retention or NLP.
The saved UI/SQLite value was still one; the agent applied exactly the newly
confirmed total of two through the existing Settings form and saved the draft,
leaving storage/NLP/external grants false. No credential or primary changed.

The formal 8511 action reserved at 2026-10-31T17:27:04.274583+00:00 and completed
at 17:27:05.123136+00:00: **HTTP 200, three returned, three previewed**. Exactly
one new request and its nonsecret receipt/key-use metadata were observed. The
current expanded browser session contains all three actual title/description/
source/time/link previews and is retained for user selection without reload.
No article text, headline, publisher URL or raw response is copied into this
record or other durable acceptance artifacts. A receipt-only screenshot stays
local; the request budget is now 2/2 used. No additional fetch is authorized.

All 47 originals, 83 analysis rows, four tasks, model-request/history/cache
tables, earlier requests and 171 frozen files remain intact. New persisted API
originals, classifications, actual FinBERT analyses and external LLM calls are
zero. The user will separately select an article, fields and storage/NLP basis.
The current formal preview did not render the repository's selected-preview
processing controls; that runtime/UI qualification remains for the next step.
No restart, inference, processing permission edit or attempt to reconstruct news
from receipts was performed. Source code remains the tested 938c73d revision;
this checkpoint changes non-article documentation only.


## Third-preview selection and runtime diagnosis — 1 November 2026 Sydney

The user selected the third current Marketaux preview and prohibited new news
requests, external LLM calls, page refresh, tab closure and server restart. The
formal tab was inspected through normal sidebar navigation only: all three
previews, including the selected third one, remain in the session. Selection,
text-scope and local-analysis controls are absent. No permission was entered or
checked and no news text or screenshot containing article text was persisted.

Observed version evidence: disk/origin/local was 43af714c5763601c4253aa962a861ca8f5686897;
8511 PID 27264 started at 02:43:22 Sydney, before the selected-preview UI commit
0c50164 at 03:35:39 Sydney. `.streamlit/config.toml` explicitly sets
`fileWatcherType = "none"` and documents restart after source edits. Disk
`news_source_ui.py` contains the controls at lines 129–156. These facts explain
the observed UI as an older imported-module runtime; the exact loaded Git SHA
is not directly verified and is not inferred solely from process start time.
No watcher setting, source file or running process was changed to activate code
while the existing unretained preview is at risk. Browser-controller state was
reset to recover its handle without refreshing the page or restarting Streamlit.

The current local queue API supports a source-free selected-preview checkpoint
with local FinBERT. After explicit applicable rights, approved fields from the
still-visible selected preview can be handed to that existing local queue
without requesting news or replacing the 8511 process. This path has not been
executed for the selected article; it does not establish formal UI activation.
FinBERT snapshot, revision and installed runtime pins passed read-only checks,
and its resource preflight passed. No weights were downloaded and no inference
was run.

Rights review: [Business Standard terms](https://www.business-standard.com/terms-conditions),
Prohibited Use 1.1(3), address development/operation of AI systems, not only
training; 1.1(5) addresses caching/archiving without prior written consent.
[Marketaux terms](https://www.marketaux.com/tos) provide a limited personal
noncommercial access/download basis and separately address third-party content;
[its FAQ](https://www.marketaux.com/faq) does not establish a field-specific
retention/NLP licence. These public pages do not resolve the user's applicable
API-supplied headline/description entitlement. No jurisdictional or statutory
exception, separate permission or downstream sublicence is assumed. The user
was asked for an actual applicable basis, permitted fields and retention period.
No publisher article body was fetched and no provider was contacted.

This turn added zero news requests, originals, classifications, actual FinBERT
analyses or external LLM calls. The prior 2/2 budget, ten request rows, 47
originals, 83 analyses, four tasks, credentials and all 171 frozen files remain
intact. Only normal persisted view preferences may change through sidebar
navigation. Actual API-news Dashboard drill-down remains pending. Code is
unchanged; exact 43af714 CI completed successfully (run 41224843519).
