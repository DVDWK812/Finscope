# FinScope

Local-first financial news intelligence. Run Streamlit on your own computer, fetch and preview news, analyze permitted text with pinned CPU FinBERT and MiniLM, and keep originals/results in local SQLite.

## Launch locally

```powershell
# Python 3.11+; the model runtime uses the pinned requirements below.
python -m venv .venv-ai
.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt
# Explicit preparation only; inference never downloads models automatically.
.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses
.venv-ai/Scripts/python.exe -m streamlit run streamlit_app.py --server.address localhost
```

Open the localhost URL printed by Streamlit. Read the four-step first-run guide, then choose **Add news → Analyze → Dashboard**. Returning users enter the dashboard directly. The guide can be reopened from the sidebar.

On Windows, after setup, `./launch_local.ps1` starts the product bound to localhost;
`./launch_local.ps1 -Port 8511` chooses a different port. This task continues on
the user-requested `local` branch, separately from the web showcase work on `main`.

The local library is `reports/finscope_local.sqlite3` (ignored by Git); set `FINSCOPE_LOCAL_DB` to use another local file. News/results persist across browser and application restarts. This is a single-user desktop-hosted product, not an authenticated multi-user service. Keep it bound to localhost.

## Sources and permissions

- **Marketaux:** user key, financial keyword feed, `group_similar=false`, at most 3 records/request on the free plan. Lookback filters do not guarantee free archive access.
- **NewsData.io:** latest feed, approximately 48 hours, possible free-plan delay. Its existing manual pause remains active; the connector does not override it.
- **Finnhub:** user key and company ticker. This is company news, not sector-wide coverage; historical entitlement depends on the account.
- **Local Collector:** fixed RBA RSS/HTML or ABS release index (headlines/dates, source-level CC BY 4.0 attribution saved). ACCC RSS is unavailable after HTTP 403; its adapter is offline-tested only. ABS uses at most two GETs (robots + one index), separately selecting up to 50 response records, with no pagination/retry/body crawling. RBA local-output import remains available; date-only records retain that precision.

Enter keys in masked fields or copy `.env.example` to `.env` and configure them locally. No key enters SQLite, Git, reports, export or global caches. The benchmark retains its original `.env` behavior. **Fetch news** is explicit, quota-confirmed and never triggered by page load. A durable local reservation, existing shared/study holds, a conservative 3-request/provider/UTC-day cap and 60-second spacing precede dispatch. There are no automatic retries or pagination. A failure/unknown outcome stops further requests pending the applicable hold/review. Do not delete request ledgers or shorten holds.

API success is separate from permission to display, retain, process or send publisher text. Preview is local personal noncommercial access; storage/NLP/transmission remain off until a permission reference and the relevant rights are supplied. Full publisher pages are never fetched. Approved self-authored or licensed text can be saved and analyzed independently. Missing publication times remain unknown.

## Models and evidence

FinBERT is the default local model and requires no API key. Its genuine three-class probabilities and exact revision are preserved with MiniLM revision and unverified candidate groups. No mock prediction is substituted on failure. FinBERT weights: **CC BY-NC-SA 4.0**, ProsusAI / MIH AI B.V.; MiniLM: **Apache-2.0**. These weight licences do not grant publisher rights. See [model evidence](docs/AI_PROTOTYPE.md).

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
