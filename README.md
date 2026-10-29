# FinScope

**Branch policy:** `main` serves the synthetic-only public showcase; `local` maintains the full local product. [Open the showcase](https://finscope-dvdwk812.streamlit.app/). The guide below describes the separate local product; obtain it with `git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git`. Showcase development never modifies or merges the `local` branch.

Local-first financial news intelligence. Run Streamlit on your own computer, fetch and preview news, analyze permitted text with pinned CPU FinBERT and MiniLM, and keep originals/results in local SQLite.

**[Public product showcase](https://finscope-dvdwk812.streamlit.app/)** — an illustrative tour with fictional data, not the functional AI application. The root `streamlit_app.py` remains the full local product; `deploy/streamlit_app.py` runs the independent showcase. [Architecture and verification](docs/PUBLIC_SHOWCASE.md).

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

The local library is `reports/finscope_local.sqlite3` (ignored by Git); set `FINSCOPE_LOCAL_DB` to use another local file. News/results persist across browser and application restarts. This is a single-user desktop-hosted product, not an authenticated multi-user service. Keep it bound to localhost.

## Sources and permissions

- **Marketaux:** user key, financial keyword feed, `group_similar=false`, at most 3 records/request on the free plan. Lookback filters do not guarantee free archive access.
- **NewsData.io:** latest feed, approximately 48 hours, possible free-plan delay. Its existing manual pause remains active; the connector does not override it.
- **Finnhub:** user key and company ticker. This is company news, not sector-wide coverage; historical entitlement depends on the account.
- **Local Collector:** existing fixed RBA RSS/HTML collectors remain available from their offline-preview/manual CLIs; UI integration is the third milestone. No arbitrary-site scraper.

Enter keys in masked fields or copy `.env.example` to `.env` and configure them locally. No key enters SQLite, Git, reports, export or global caches. The benchmark retains its original `.env` behavior. **Fetch news** is explicit, quota-confirmed and never triggered by page load. A durable local reservation, existing shared/study holds, a conservative 3-request/provider/UTC-day cap and 60-second spacing precede dispatch. There are no automatic retries or pagination. A failure/unknown outcome stops further requests pending the applicable hold/review. Do not delete request ledgers or shorten holds.

API success is separate from permission to display, retain, process or send publisher text. Preview is local personal noncommercial access; storage/NLP/transmission remain off until a permission reference and the relevant rights are supplied. Full publisher pages are never fetched. Approved self-authored or licensed text can be saved and analyzed independently. Missing publication times remain unknown.

## Models and evidence

FinBERT is the default local model and requires no API key. Its genuine three-class probabilities and exact revision are preserved with MiniLM revision and unverified candidate groups. No mock prediction is substituted on failure. FinBERT weights: **CC BY-NC-SA 4.0**, ProsusAI / MIH AI B.V.; MiniLM: **Apache-2.0**. These weight licences do not grant publisher rights. See [model evidence](docs/AI_PROTOTYPE.md).

Raw originals remain the default. Cosine ≥0.80 within 72 hours creates unverified candidates; neither event deduplication nor contradiction detection is validated. The consumed challenge remains frozen: **12/16 scorable agreement (75%), macro-F1 0.730159**, two mixed/uncertain exclusions and selected-pair cosine precision **0.666667**, including P02/P07 risks. Reviewer independence/completion and three-human usability remain unverified. See [frozen evidence](docs/CHALLENGE_EVALUATION.md), [freeze](docs/DELIVERY_FREEZE.md) and [concise team report synopsis](docs/REPORT_SYNOPSIS.md). The team writes the final academic report.

## Verification and retained tools

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m finscope.benchmark --dry-run
```

Offline tests use mocks/authored text; actual provider/model/browser checks are recorded separately in [local redesign evidence](docs/LOCAL_REDESIGN.md). The [provider evaluation](docs/API_EVALUATION.md), [decisions](docs/DECISIONS.md), [RSS](docs/RSS_PROTOTYPE.md), [HTML](docs/HTML_PROTOTYPE.md), and [historical overview](docs/PRE_REDESIGN_OVERVIEW.md) preserve prior evidence. The public showcase installs only Streamlit/pandas from `deploy/requirements.txt`; run its preview with `python -m streamlit run deploy/streamlit_app.py`. It never imports the local runtime, asks for keys, fetches news, prepares models or opens a news database. Full local installation uses `requirements-local.txt`; the retained Docker recipe also uses that full local runtime.

Main-only tested commits, no feature branches or PRs. No GDELT retry/task recreation, challenge tuning/rescoring, Moodle access or coursework submission. Internal target: 31 October; the official deadline remains user-confirmed, with the historical conflicting values preserved in [assessment notes](docs/ASSESSMENT_VERIFICATION.md).
