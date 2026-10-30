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
without invented probabilities or external fallback. Start the installed server
with `lms server start --port 1234 --bind 127.0.0.1`; keep LAN/CORS disabled.

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

This local-product task uses the explicitly requested `local` branch and isolated worktree; the concurrent web task keeps its original `main` checkout. No PR or merge is opened. No GDELT retry/task recreation, challenge tuning/rescoring, Moodle access or coursework submission. Internal target: 31 October; the official deadline remains user-confirmed, with the historical conflicting values preserved in [assessment notes](docs/ASSESSMENT_VERIFICATION.md).
