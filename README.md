# FinScope

Local-first financial news intelligence. Run Streamlit on your own computer, fetch and preview news, analyze permitted text with pinned CPU FinBERT and MiniLM, and keep originals/results in local SQLite.

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
- **NewsData.io:** latest feed, approximately 48 hours, possible free-plan delay. Its existing manual pause remains active; the connector does not override it.
- **Finnhub:** user key and company ticker. This is company news, not sector-wide coverage; historical entitlement depends on the account.
- **Local sources:** fixed RBA RSS/HTML, ABS releases (CC BY 4.0) and NIST official news (unmarked public-information text; copyright exceptions apply). Automatic runs select at most 20 records/source: ABS uses ≤3 GETs including one permitted body, NIST ≤5 including up to three bodies. Legacy ABS index preview remains two GETs. No pagination, arbitrary URL crawling or retries; source attribution, text basis, raw date and exclusions persist. ACCC remains disabled after HTTP 403.

Enter keys in masked Settings fields for Windows Credential Manager, or configure the project's ignored `.env`. Keys never enter SQLite/jobs, Git, reports or exports. API budgets expire with their attested UTC date. Explicit updates continue through the existing dual-ledger reservations, 3-actions/provider/UTC-day cap and 60-second spacing. NewsData stays manually paused; failures/unknown outcomes and Retry-After holds are preserved. Refreshing, filtering or reopening the app never starts a fetch or inference.

The launcher owns the single worker; direct `streamlit run` serves the UI without starting it. SQLite schema changes create a consistent backup under ignored `reports/backups/`. Jobs persist queued/running/terminal states and checkpoints, support cancellation and explicit resume, and never automatically repeat unknown requests. Full permitted text and content revisions remain local; lead-excerpt offsets/coverage and model history are recorded. The independent two-level catalogs are FinScope US business v1 (11/56, not GICS) and official CSRC JR/T 0020—2024 Table 2 (19/91); unknown news topics never become CSRC S/91.

API success is separate from permission to display, retain, process or send publisher text. Preview is local personal noncommercial access; storage/NLP/transmission remain off until a permission reference and the relevant rights are supplied. Full publisher pages are never fetched. Approved self-authored or licensed text can be saved and analyzed independently. Missing publication times remain unknown.

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
