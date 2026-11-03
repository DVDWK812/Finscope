# FinScope

### Local model lifecycle

Batch analysis completes missing candidate embeddings, then missing topic decisions,
then missing sentiment results. MiniLM and FinBERT each use one owned, bounded CPU
subprocess per stage, with input sent through pipes and no model download. Stage
cleanup verifies process exit, including Windows launcher descendants. Resource
observations record RAM, process Working Set/Private Bytes and available GPU counters;
they never include news text or prompts. A resource failure permits one owned-resource
release and remeasurement before preserving checkpoints and pausing. Existing cold/hot
load thresholds remain unchanged. LM Studio instances without task ownership evidence
are external: FinScope does not unload them or stop their service. The batch does not
automatically create a Gemma instance; the selected instance must be available.

### Finite media text batches (local)

**Broad Financial News** is the default Marketaux draft mode. It omits company,
industry, search, source-ID and domain filters, including the old keyword fallback.
English and a configurable publication window remain; the provider's default
publication ordering applies. Optional specified-media filtering is off by default.
Company Tracking remains available separately. A draft never changes a saved
scope/budget or repeats an earlier collection.

Broad batches freeze their time window and page size, persist each permitted
title/actual description before analysis, and record response pagination metrics.
Their cursor is separate from company watchlists. Missing/inconsistent metadata or
repeated page identities stop further requests; failed/unknown requests never retry.
The distinct-record cap may stop partway through the last page; an explicitly
authorized later batch revisits that boundary page with URL deduplication. Stable
time bounds prevent newer publication times shifting pages, but cannot guarantee
snapshot isolation against supplier reindexing or backdated additions.

An optional explicit historical window end (timezone-aware ISO UTC) creates a
separate reviewed cursor, without clearing an earlier blocked cursor. Leave it
blank for latest news. This still needs a fresh batch/account budget confirmation;
it is not an automatic retry or a guarantee of supplier snapshot consistency.
Receipts record result-count drift, exact repeated-page numbers and publication
ranges without retaining additional article text. Classification cold-starts
MiniLM with the existing 5 GiB load reserve, records RAM/VRAM before dispatched
stages in finite storage, and releases the worker's unused FinBERT object before
classification-only tasks. It never unloads a user's model service automatically.

**Time-stratified broad batches** are optional; Latest news stays available.
Six adjacent four-hour UTC windows end one hour before task creation by default,
with a whole-second anchor or an explicit historical end. At most two pages per
window and 12 GETs total: first pages across all six precede second pages. Requests
deliberately extend both window edges by one second; existing ID/URL deduplication
handles boundary observations without assuming supplier inclusivity. Page caps
and mutable indexes mean this is sampling, not exhaustive 24-hour coverage.
Independent durable window/page fences block unknown redispatch and preserve old
broad-feed holds. No company, industry, keyword or domain filters are allowed.
Resource pauses record measured RAM/VRAM and a cumulative count; collection does
not require a loaded classifier or sentiment model.

**Grouped company watchlist** accepts `group | symbols | optional Marketaux
industries` lines in the existing media batch form. The six initial cohorts cover
technology, finance, energy, healthcare, industrial and consumer companies; they
are query cohorts, not inferred news industries. Marketaux combines each group
in one domain-filtered query; Finnhub uses one company request per ticker. The
offline plan shows bounded dates/pages and still needs a fresh explicit UTC-day
account/application budget. Full Marketaux pages retain their window/page cursor;
successful persistence advances checkpoints, while failed/unknown requests never
retry automatically. One bounded response does not establish exhaustive coverage.

Finite API/RSS records sharing the same normalized supplied URL reuse one original
and retain separate acquisition evidence. Similar headlines or events on different
publisher URLs are kept separate; unresolved intermediary URLs are not followed.
Deduplication never extends the original expiry. The details distinguish collection
service, supplier source, reviewed link-domain match and unverified originality.
**Live media source coverage and quality** reports active text amounts, separate
query/entity/topic distributions, NLP states and read-only output-failure types.
These engineering capabilities are not evidence of newly acquired publisher data.

For US-BUSINESS-1, **Industry classification** in the same advanced batch panel
selects an installed LM Studio classifier independently of FinBERT. Inspect/load
the exact local variant, disable LM Studio prompt/response and token logging, then
select the scheme. **Reclassify retained media only** reuses saved text and
sentiment; it makes no news request. MiniLM retrieves taxonomy candidates even
without dictionary hits, and a separate local semantic decision/support review
can retain a parent alone or leave an explicit unknown/failure reason. Similarity
is a retrieval score, not calibrated confidence. Model/resource guards still apply;
no new weights are downloaded. Future media batches adopt the selected scheme.
All four views use that version; earlier classifications, model-call checkpoints
and engineering notes remain only in the finite sidecar until the original expiry.

In **Batch collection and offline analysis → Media API text and local analysis**,
record one source-level basis: licence evidence, personal research with unresolved
applicability, or a concrete restriction. Research confirmation is not publisher
permission and cannot waive a known restriction. Choose actual returned fields,
finite expiry, article count and a verified current UTC-day account/application
budget. Saving makes no request. **Update & Analyze** saves before classification
and fixed FinBERT; **Save media text only** and **Analyze retained media offline**
separate the stages. The same saved batch never downloads again. Explicitly save
a new batch to confirm a new collection. Existing quota, 60-second spacing,
Retry-After, unknown-outcome and primary-key safeguards remain.

Marketaux defaults to its three-article free-plan limit; larger limits must match
the actual subscription. Finnhub reuses the selected number from one company-news
response. The dated application safety budget never renews automatically.

Finite originals, preprocessing, classification quotes, model history and caches
use `reports/finscope_local.sqlite3.expiring/live.sqlite3`, excluded from application
backups and exports. Permanent checkpoints contain IDs and response metrics only.
Reads and inference commits check expiry; the UI checks every two seconds.
Cleanup pauses when FinScope is closed and runs before the next startup read.
Delete the source's finite text/results immediately if its subscription or scope
ends sooner. This does not promise forensic erasure of OS/browser memory or user
backups. Finite RSS uses the same partition; finite local-file imports are rejected
before permanent checkpointing. No article-page fetch, training, external LLM or
corpus export is enabled. Group sharing/derived-result publication needs separate
scope review. Authored-fixture tests do not establish real-media NLP acceptance.

Local-first financial news intelligence. Run Streamlit on your own computer, fetch and preview news, analyze permitted text with pinned CPU FinBERT and MiniLM, and keep originals/results in local SQLite.

The **2 November 2026 18:00 Australia/Sydney report handoff** is an internal
technical baseline, not the final submission deadline or a permanent feature
freeze. Start with the [handoff record](docs/REPORT_HANDOFF_20261102.md),
[technical synopsis](docs/REPORT_SYNOPSIS.md) and [local demonstration](docs/DEMO_SCRIPT.md).
Local development continues afterward; the consumed evaluation remains frozen.

## Launch locally

```powershell
# Python 3.11+; the model runtime uses the pinned requirements below.
python -m venv .venv-ai
.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt
# Explicit preparation only; inference never downloads models automatically.
.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses
./launch_local.ps1 -Port 8511
```

Open the printed localhost URL. Read the concise first-run guide and configure sources, source permissions, current UTC-day budgets and the local model in **Settings**. Daily use is one **更新并分析** action: a persistent worker fetches, processes, classifies, analyzes and saves results while the UI remains usable. Dashboard / Industries / Knowledge Graph / News Explorer share filters; Settings retains the advanced manual workspace.

On Windows, after setup, `./launch_local.ps1` starts Streamlit and one OS-locked local worker bound to localhost;
`./launch_local.ps1 -Port 8511` chooses a different port. This task continues on
the user-requested `local` branch, separately from the web showcase work on `main`.

The local library is `reports/finscope_local.sqlite3` (ignored by Git); set `FINSCOPE_LOCAL_DB` to use another local file. News/results persist across browser and application restarts. This is a single-user desktop-hosted product, not an authenticated multi-user service. Keep it bound to localhost.

## Sources and permissions

- **Marketaux:** user key, financial keyword feed, `group_similar=false`, at most 3 records/request on the free plan. Lookback filters do not guarantee free archive access.
- **NewsData.io:** latest feed, approximately 48 hours, possible free-plan delay. Headline/description are the adapter default. API `content` is separately supported only with explicit verified paid-plan and content-use references; a paid plan alone does not enable it. The existing manual pause remains active, including for paid access. See [current acceptance and account constraints](docs/P2_REAL_NEWS_ACCEPTANCE.md).
- **Finnhub:** user key and company ticker. This is company news, not sector-wide coverage; historical entitlement depends on the account.
- **Local sources:** fixed RBA RSS/HTML, ABS releases (CC BY 4.0) and NIST official news (unmarked public-information text; copyright exceptions apply). Automatic runs select at most 20 records/source: ABS uses ≤3 GETs including one permitted body, NIST ≤5 including up to three bodies. Legacy ABS index preview remains two GETs. No pagination, arbitrary URL crawling or retries; source attribution, text basis, raw date and exclusions persist. ACCC remains disabled after HTTP 403.

Enter keys in masked Settings fields for Windows Credential Manager, or configure the project's ignored `.env`. Keys never enter SQLite/jobs, Git, reports or exports. API budgets expire with their attested UTC date. Explicit updates continue through the existing dual-ledger reservations, 3-actions/provider/UTC-day cap and 60-second spacing. NewsData stays manually paused; failures/unknown outcomes and Retry-After holds are preserved. Refreshing, filtering or reopening the app never starts a fetch or inference.

The launcher owns the single worker; direct `streamlit run` serves the UI without starting it. SQLite schema changes create a consistent backup under ignored `reports/backups/`. Jobs persist queued/running/terminal states and checkpoints, support cancellation and explicit resume, and never automatically repeat unknown requests. Full permitted text and content revisions remain local; lead-excerpt offsets/coverage and model history are recorded. The independent two-level catalogs are FinScope US business v1 (11/56, not GICS) and official CSRC JR/T 0020—2024 Table 2 (19/91); unknown news topics never become CSRC S/91.

API success is separate from permission to display, retain, process or send publisher text. Preview is local personal noncommercial access; storage/NLP/transmission remain off until a permission reference and the relevant rights are supplied. Full publisher pages are never fetched. Approved self-authored or licensed text can be saved and analyzed independently. Missing publication times remain unknown.

Reviewed source policies additionally record covered fields/purposes, retention
basis, attribution and exclusions. The first versioned policy covers official
ABS releases; unknown providers receive no policy grant. One retained ABS original
has completed actual local FinBERT and formal Dashboard/Explorer acceptance without
new collection: [evidence and policy rollout limits](docs/ABS_P2_ACCEPTANCE.md).

Advanced **Batch collection and offline analysis** adds separate store-only and
source-free analysis actions, reviewed SEC/NIST/ABS/RBA policies, bounded SEC
watchlists, strict local JSONL/CSV imports and source-type/status views. Saving
its scope supplies the default Update & Analyze pipeline. SEC requests require
your actual `FINSCOPE_SEC_USER_AGENT` contact identity; no placeholder is sent.
The ABS archive follows at most three linked numbered index pages, without
article bodies. Actual P3 evidence: **+219 real originals; 261 current records
(141 official announcements / 120 SEC disclosures), 148 current-text FinBERT
results and 113 not-applicable metadata records**. See
[P3 acceptance, exact denominators and remaining limits](docs/P3_BATCH_ACCEPTANCE.md).

**Global media monitor** adds the five fixed Bloomberg/CNBC/WSJ/FT/Yahoo feeds,
separate discovery and licensed-analysis counts, opt-in bounded worker polling,
conditional HTTP and durable deduplication/holds. Actual P3-B checks discovered
108 distinct CNBC/WSJ/Yahoo links; FT returned 301 and Bloomberg's initial client
indexing failure left incomplete evidence. No publisher titles/descriptions were
cached or analyzed without an applicable grant. Six-domain Marketaux filters can
be configured offline; actual API budgets remain unchanged. See
[per-media results, rights and remaining gates](docs/P3_MEDIA_ACCEPTANCE.md).

P3-B.1 adds current UTC-day budget confirmation,5–1440-minute intervals and
explicit coverage/exhaustion:15-minute all-day polling needs96 GETs/source/day;
the former12-request default is a short window, or120-minute all-day spacing.
Actual approved validation added18 Bloomberg and10 FT links, and performed two
real Yahoo rounds five minutes apart across a worker restart. Approved Yahoo
reader fields display in RAM only; media NLP remains0. See
[continuous-polling evidence and remaining Reuters/rights gate](docs/P3_MEDIA_CONTINUOUS_ACCEPTANCE.md).

```powershell
# Explicitly submit to the separately running local worker; no external LLM.
.venv-ai/Scripts/python.exe -m finscope.batch_cli collect --sources abs_archive --limit 100 --confirm
.venv-ai/Scripts/python.exe -m finscope.batch_cli analyze --confirm
```

## Models and evidence

FinBERT is the default local model and requires no API key. Its genuine three-class probabilities and exact revision are preserved with MiniLM revision and unverified candidate groups. No mock prediction is substituted on failure. FinBERT weights: **CC BY-NC-SA 4.0**, ProsusAI / MIH AI B.V.; MiniLM: **Apache-2.0**. These weight licences do not grant publisher rights. See [model evidence](docs/AI_PROTOTYPE.md).

**Local LM Studio** discovers downloaded LLMs through its fixed `127.0.0.1:1234`
server, using `/v1/models` and `/api/v1/models` to distinguish downloaded, loaded
and API-exposed states. Refresh never infers or downloads. Explicit Load checks
`lms` estimates and current RAM/VRAM first (2048 context, one prediction,
80% GPU for downloads up to 8 GiB, otherwise 50%);
unload another model explicitly before switching. Chat Completions uses JSON Schema
structured sentiment and saves actual IDs/quantization, rationale and history,
without invented probabilities or external fallback. In Settings → Analysis
models, use **Start service and refresh models** to start the installed runtime
on `127.0.0.1:1234`. Bounded API checks verify readiness; repeat clicks reuse a
running service. Starting/refreshing never loads or downloads models. Existing
authentication is preserved and port conflicts do not terminate other programs.

**Local Ollama** lists installed local GGUF models only after an explicit action,
then connects to `127.0.0.1:11434`. Cloud/remote tags, arbitrary endpoints and model
downloads are unsupported. **External LLM API** supports OpenAI Responses with
the allowlisted `gpt-5.4-mini-2026-03-17` snapshot, a masked key or local
`OPENAI_API_KEY`, recorded transmission permission and explicit send consent for
each Run action. This optional paid call sends only the permitted headline/summary;
`store=false` is requested and provider retention policies still apply. Structured
labels, rationale and model revision stay separate from FinBERT; no calibrated
probabilities are invented. External 429/Retry-After and unknown requests are
tracked locally, with no automatic retry. Both model options are optional; their
live availability depends on your local service/account.

Settings has three tabs: General, News sources and Analysis models, with retained
manual actions and logs under Advanced & diagnostics. Configuration can be saved
offline. Incomplete drafts preserve the last complete pipeline. Updates use the
latest saved draft, with explicit confirmation of its ready-source subset; they
never silently run the old pipeline. Unsaved form edits block updates until saved.
Saving settings never fetches news or calls a model.

**DeepSeek** is a separate, controlled interface test under Analysis models →
External API. Configure `DEEPSEEK_API_KEY` in the ignored project `.env` or its
masked Windows Credential Manager editor. Saving a key/configuration makes no
request. An explicit connection check reads the official model list once; a
separate per-action confirmation permits at most three fixed fictional financial
texts to be sent serially. No existing news is sent and the automatic worker
retains its local model. Strict JSON validation, usage and requested/response IDs
are saved as separate history; aliases are not fixed weight versions. An error or
unknown outcome stops the test without retry. This is interface verification,
not an accuracy evaluation. On 31 October, explicit browser acceptance succeeded
on three authored samples using actual request/response ID `deepseek-flash`:
strict JSON, usage and SQLite history passed; refresh made no repeat requests.
The response did not supply a fixed weight revision. See the dated provider log.

Shared date, sector, source, sentiment, model and search filters drive **Overview,
Sector sentiment, Trends, Heatmap, Evidence graph and News Explorer**. The heatmap
distinguishes missing analysis and low samples. The graph supports pan/zoom and an
accessible original-article selector; edges have metadata/keyword/candidate evidence.
Article details retain original links, permission history and every analysis
version, with optional individual reanalysis. A permitted headline alone can be
analyzed; temporal grouping is disabled when exact original time is unknown.

Raw originals remain the default. Cosine ≥0.80 within 72 hours creates unverified candidates; neither event deduplication nor contradiction detection is validated. The consumed challenge remains frozen: **12/16 scorable agreement (75%), macro-F1 0.730159**, two mixed/uncertain exclusions and selected-pair cosine precision **0.666667**, including P02/P07 risks. Reviewer independence/completion and three-human usability remain unverified. See [frozen evidence](docs/CHALLENGE_EVALUATION.md), [freeze](docs/DELIVERY_FREEZE.md) and [concise team report synopsis](docs/REPORT_SYNOPSIS.md). The team writes the final academic report.

## Verification and retained tools

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m finscope.benchmark --dry-run
```

Offline tests use mocks/authored text; actual provider/model/browser checks are recorded separately in [local redesign evidence](docs/LOCAL_REDESIGN.md). The [provider evaluation](docs/API_EVALUATION.md), [decisions](docs/DECISIONS.md), [RSS](docs/RSS_PROTOTYPE.md), [HTML](docs/HTML_PROTOTYPE.md), and [historical overview](docs/PRE_REDESIGN_OVERVIEW.md) preserve prior evidence. Existing deployment files are retained for compatibility; cloud deployment is not a product requirement or acceptance target.

Test discovery, programmatic unittest runs and AppTest use a temporary `.env`,
per-case in-memory credentials and temporary data by default. Python child
processes inherit the guards; a child that drops them is refused. Real Windows
credential adapter calls fail before DLL loading, and production data/`.env`
access is blocked even when an individual test omits its mock. Windows CI tests
the adapter with mocked native calls alongside both Linux/Streamlit jobs. These
are accidental-I/O regression guards, not a sandbox for hostile Python code.
For a standalone benchmark dry run, set `FINSCOPE_TESTING=1` only in that child
process (CI already does this) to avoid reading production credentials. Keep test
logs in ignored `.test-results/`, separate from the news database directory.

The earlier Marketaux vault-test incident remains recorded in the development
log. No previously different vault value is claimed restored. Only the user can
restore a different key through the local masked editor; no key enumeration,
guessing, deletion or credential export is part of verification.

Settings → News sources manages named Marketaux, Finnhub and NewsData.io keys:
one enabled primary and optional backups. Passwords are held only in Windows
Credential Manager; SQLite stores UUID references and nonsecret status metadata.
Existing single-key targets and the project `.env` remain usable without silent
migration or deletion. An explicit copy creates a separately verified managed key
and keeps the original. Replacements are verified in a new protected target before
switching references. Deleting a managed key requires confirmation and never
deletes an original single-key target or `.env` entry.

A newly submitted task records its selected slot/version IDs. Promoting a backup
affects subsequent explicit tasks; existing tasks do not silently switch keys or
retry failed requests. No-primary sources are skipped. All keys share the same
provider/account quota, daily cap, spacing, failure/Retry-After holds and study
ledger protections; NewsData's manual pause remains. A 403 is a permission or
subscription restriction, not proof of an invalid key. Verification uses fake
credentials and offline transports, with no real news API request.

Three source cards are always visible, even for disabled sources. Each separates
local save/readback evidence, exact-version API verification, primary/backup role
and last use. Default inspection reads only nonsecret SQLite metadata. Legacy key
existence stays unconfirmed until an explicit local check; it is never inferred
from a different key's historical HTTP 200. The selected-key action menu contains
promotion/replacement and separately confirmed availability/deletion operations.

API preview and automatic fetch-and-analysis have separate readiness conditions.
An explicit local check reads no network; an explicitly confirmed API check may
consume one preview request through the unchanged reservations and provider holds,
without saving articles or running models. An API verification is not a grant of
publisher storage/NLP rights. NewsData remains manually paused.

This local-product task uses the explicitly requested `local` branch and isolated worktree; the concurrent web task keeps its original `main` checkout. No PR or merge is opened. No GDELT retry/task recreation, challenge tuning/rescoring, Moodle access or coursework submission. Internal target: 31 October; the official deadline remains user-confirmed, with the historical conflicting values preserved in [assessment notes](docs/ASSESSMENT_VERIFICATION.md).

Local media collection offers **全部财经新闻** (default, unrestricted), **指定媒体新闻**
(six fixed publisher checkboxes, Latest only), and **指定公司新闻** (saved watchlist).
In Settings → News sources, select an existing primary credential manually and record
its subscription account and checked allowance. Keys in the same account share quota;
no fallback rotation occurs. Supplier live balance stays Unknown without a probe.
An explicitly revised same-day application budget keeps all historical request counts
and supplier cooldowns. Confirm account allowance and the batch total separately.
