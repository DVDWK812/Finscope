# Local-first product redesign — 29 October 2026 Sydney

The user's architecture correction supersedes cloud product/acceptance assumptions.
FinScope runs on the operator's own computer, bound to localhost, with persistent
local SQLite. Existing hosted/deployment and frozen evaluation evidence is history,
not a requirement to redeploy. Teammates own the academic report.

## Milestone 1: local source → preview → permitted FinBERT → SQLite

- Implemented first-run guide with persistent completion and a reopen action;
  local source selection, masked credentials or project-only `.env`, explicit
  quota-confirmed Fetch, normalized preview and separate downstream permissions.
- All three API adapters accept explicit credentials without changing omitted-key
  benchmark behavior. Finnhub supports a validated company ticker; NewsData's
  existing manual pause remains enforced. No GDELT route/retry was introduced.
- Local product requests use their own durable SQLite reservation, read existing
  provider/study holds, enforce 60-second spacing and at most three requests per
  provider/UTC day, stop on failure/unknown outcomes, and never retry/paginate.
  The separately planned study sampler and its date/window/budget rules are
  unchanged; a local product request is not a study result or study authorization.
- Originals and all analysis versions persist locally. FinBERT reuses the actual
  pinned CPU/MiniLM pipeline, its unchanged probabilities and predeclared candidate
  rules. No calibrated LLM scores or fake fallback are introduced.

**Actual checks, not mocks:** Browser first-run Get Started succeeded. The user
reported no Marketaux requests today. A conservative one-request budget was used
with the existing local `.env` key. One GET started **2026-10-29T09:18:28.562382Z**,
completed **09:18:29.715948Z**, **HTTP 200**, three normalized preview records,
technology topic / semiconductor keyword / 2-day lookback / `group_similar=false`.
No pagination, publisher page, API retry or model processing of these news records
occurred. No headlines, response bodies or credentials are committed. This is
local personal preview evidence, not new public-provider approval, a provider
winner or a multi-day coverage result. Downstream retention/NLP permissions remain
unverified; those uses stay gated.

The browser separately saved the approved authored development chipmaker text,
ran actual local FinBERT/MiniLM and showed one persisted Positive analysis and
Technology sector analytics. Probabilities: positive **0.9529756307601929**,
negative **0.021392226219177246**, neutral **0.025632165372371674**; combined
inference **136.73 ms** (not full request/model-load time). FinBERT revision
`0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`; MiniLM
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. This is engineering smoke evidence,
not accuracy measurement or a frozen-challenge rerun.

**Offline regression:** 202 tests passed (182 retained + 20 new local product
checks); benchmark dry run passed with no provider calls. Legacy demo UI tests
now explicitly call the retained legacy fixture entrypoint; new AppTest coverage
exercises the actual local-first entrypoint. Exact-commit CI is checked after push.

Milestone 1 exact commit `f411de2691376f4b89ae6f0fa795c7d134a3afbd` matched origin/main;
both Python 3.11 / Streamlit-version jobs passed in [Actions run 40849128698](https://github.com/DVDWK812/Finscope/actions/runs/40849128698).
Remaining after milestone 2: external structured LLM/local Ollama/fixed collectors and UI polish. The complete
real-Marketaux-to-FinBERT acceptance remains gated by actual downstream permission,
not replaced by the authored-text result.

## Milestone 2: shared visual analytics and evidence drill-down

Implemented Overview, Sector sentiment, Trends, Date × Sector heatmap,
interactive evidence graph and News Explorer. One shared date/sector/source/
sentiment/model/search filter selects originals before every view; latest matching
model analysis per original avoids double counting reanalyses. Sector membership
is multi-label, explicitly separate from raw counts. Unknown times remain unknown;
date-only records retain that precision. Missing heatmap cells have null sentiment
balance, sample counts and n<3 flags rather than fabricated neutral observations.

Graph edges are limited to source metadata, matched sector keywords, ticker-feed
query provenance and unverified cosine candidates. Article selections resolve
original IDs; no company causation or confirmed event identity is inferred. Explorer
shows originals, source links, separate probabilities/rationales, history and
candidate members outside the filters. Fetched previews use cards rather than an
export-enabled grid before retention permission is supplied.

213 offline tests and benchmark dry run pass. Actual localhost browser reload after
a process restart retained the milestone-1 original/model result. All six views,
heatmap controls and the node graph rendered; graph/article interaction is checked
separately from data-unit tests. No provider request or frozen packet/model rerun
was made during milestone 2. Exact-commit CI is checked after push.

Milestone-2 commit `59ce95a068511e379b8e77d80e447cf9adaf7dcb` initially
failed the Streamlit 1.50 CI job: layered Vega-Lite server selections were not
supported. The newer-version job's test steps passed but the matrix job was
cancelled. This is retained as failed evidence, not reported as a clean pass.
The compatibility repair uses client-side graph pan/zoom plus the browser-verified
accessible article-reference selector, with no layered server-selection callback.
No tests or supported-version checks were removed. The repaired full offline suite
and benchmark dry run pass; exact repaired-commit CI is verified after push.

## Milestone 3: local models, explicit external interface and fixed collectors

Implemented a shared sentiment-provider interface: the unchanged pinned local
FinBERT/MiniLM pipeline, installed localhost Ollama GGUF models and OpenAI Responses
with one allowlisted snapshot, `gpt-5.4-mini-2026-03-17`. OpenAI calls require both
recorded external-text permission and an explicit send-consent action, use a masked
or project `.env` key, request `store=false`, have no tools/retries and preserve
validated labels/rationales/revisions independently of FinBERT probabilities.
Durable unknown-request/Retry-After state blocks accidental repeats. No account
availability, calibrated LLM confidence or live external inference is claimed.
Official contracts checked 29 October: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[model snapshot](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[Ollama tags](https://docs.ollama.com/api/tags), [model details](https://docs.ollama.com/api-reference/show-model-details),
[chat](https://docs.ollama.com/api/chat). Ollama is fixed to 127.0.0.1:11434,
rejects cloud/remote aliases, verifies installed completion metadata/digests and
never exposes a tunnel or pulls weights. Actual explicit localhost discovery
returned a safe transport-unavailable message; local Ollama inference is not live
verified. The external provider was tested with mocks and actual browser consent
controls only; the real local model-request table remained empty.

Fixed RBA RSS/HTML collectors are connected behind explicit local actions, with
robots/source bounds retained. Existing collector JSON can be strictly imported
without collection/network calls. Separate retention/NLP permission and attribution
remain required. Date-only/unknown publication times remain unchanged; permitted
text can be classified while temporal grouping is disabled if exact time is absent.
The UI preserves originals and all model versions, exposes per-article reanalysis
and audited permission updates, and shares date/sector/model filters with analysis.
Repeated identical provider payloads use stable original IDs (exact content identity,
not event deduplication). Local setup now has requirements-local.txt and a localhost
Windows launcher; credentials, assets, databases and reports remain ignored.

### Actual final local checks and qualifications

- A second explicit, bounded Marketaux check started **2026-10-29T10:00:32.985771Z**
  and ended **10:00:48.838748Z** in **transport failure**, with **no observed HTTP
  response**. It was not retried. Two product request reservations now exist:
  the earlier HTTP-200 / three-record preview, then this failure. Further Marketaux
  product requests are stopped for this UTC day. No empty-coverage claim follows
  from unavailable records; no quota/header or server-receipt fact is invented.
  Downstream Marketaux retention/NLP/transmission remains unverified and gated.
- Separately, the existing **RBA-authored media-release RSS metadata** was reviewed
  under [RBA copyright sections 2-3](https://www.rba.gov.au/copyright/) (CC BY 4.0;
  attribution retained, no endorsement, no third-party data/media or linked bodies).
  Browser import of the existing local RSS `articles.json` validated one original,
  recorded that specific licence reference and local storage/NLP rights, and opened
  its genuine publisher URL successfully. This was the collector import path,
  not relabelling provider news as a synthetic submission. No new collector/feed
  request occurred and the original collector store is unchanged.
- Actual local RBA title/summary FinBERT+MiniLM analysis saved **Neutral** at
  **2026-10-29T10:09:01.596219Z**. Probabilities: positive **0.2400004118680954**,
  negative **0.010126806795597076**, neutral **0.7498728036880493**; combined
  inference **148.81 ms**, excluding load/download time. Original publication time
  **2026-10-14T03:00:00+00:00** and original feed-time string/attribution remain
  distinct from import/analysis times. This is a narrow licensed metadata smoke,
  not new sentiment accuracy, broad financial-news coverage or Marketaux clearance.
- Actual authored-text per-article reanalysis also succeeded (**58.67 ms**, same
  stored probabilities as milestone 1). Two originals and three historical actual
  analysis versions remain; no original was replaced by reanalysis. The local
  browser retained the library across process/worktree changes. Optional external
  transmission remained disabled; no external article request was made.
- **233 offline tests** and benchmark dry run passed in the isolated local branch.
  Mocks exercise all adapters, consent/failures, local endpoint boundaries,
  collector import, permissions, credential exclusion, filters, graph/heatmap and
  persistent originals/history. Actual browser/model/provider observations above
  are separate. Frozen evaluation was neither rerun nor tuned/rescored. A 171-file
  preservation manifest found the original evidence unchanged; configured-key
  scans found no source/database leak. Exact final-commit CI is checked after push.

### Branch and concurrent work

The user explicitly requested branch **local** after the first two milestones
and compatibility repair were already pushed to main. A managed isolated worktree
was created from `422e86f2c0e6a29e91079644e023ddb6115b9a2e`, and only the local
product's 12 then-uncommitted files were transferred, with byte/hash checks before
restoring those owned paths in the original checkout. The original checkout stayed
on main for the separately owned web-showcase task; its edits were preserved and
excluded. This local task makes subsequent commits/pushes only on local, with no
PR/merge. Existing ignored credential/model/report state is reused locally so
moving worktrees does not clear provider holds or restart budgets. That local
runtime state and all private/raw evidence are excluded from Git.

The Streamlit-1.50 graph compatibility repair `422e86f` passed both exact-commit
Python 3.11 jobs in [Actions run 40851879632](https://github.com/DVDWK812/Finscope/actions/runs/40851879632).
The earlier failed M2 run remains recorded above. Three-human usability and reviewer
attestations remain pending; agent-operated checks are not participants.

