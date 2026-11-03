# FinScope

**Choose your version:** [Open the public showcase](https://finscope-dvdwk812.streamlit.app/) or [get the functional local product](https://github.com/DVDWK812/Finscope/tree/local). `main` contains the synthetic-only showcase; `local` contains the full application. The instructions below launch the separate local product. Showcase maintenance never modifies or merges `local`.

Local-first financial news intelligence. Run Streamlit on your own computer, fetch and preview news, analyze permitted text with pinned CPU FinBERT and MiniLM, and keep originals/results in local SQLite.

**[Public product showcase](https://finscope-dvdwk812.streamlit.app/)** — an illustrative tour with fictional data, not the functional AI application. The root `streamlit_app.py` remains the full local product; `deploy/streamlit_app.py` runs the independent showcase. [Architecture and verification](docs/PUBLIC_SHOWCASE.md).

The showcase sidebar offers **English / 简体中文** and **Dark / Light** display choices, retained while navigating the six pages in the current session. English and the existing dark palette are the defaults. Fictional headlines/summaries and headline-frequency calculations retain their original English source text; the controls and explanations are translated locally without a service or model.

## Launch locally

```powershell
# Python 3.11+; the model runtime uses the pinned requirements below.
git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git
cd Finscope
python -m venv .venv-ai
.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt
# Explicit preparation only; inference never downloads models automatically.
.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses
./launch_local.ps1 -Port 8501
```

The Windows launcher starts both Streamlit and the local worker. Direct Streamlit startup serves only the UI. Configure **Settings → General / News sources / Analysis models**, review source scope, permissions and the current account/application budget, then use **Update & Analyze**. Inspect **Dashboard / Industries / Knowledge Graph / News Explorer** with shared local filters. Settings retains advanced collect-only and saved-record offline analysis. Saving settings or changing filters does not fetch.

This guide reflects local source `7e6c5158c56ac0a520119f91ddfbb2fae9041782`, reviewed 3 November 2026; see the [source-backed sync matrix and release status](docs/SHOWCASE_SYNC.md). The public site remains a passive 24-example illustration. Consult the [local branch](https://github.com/DVDWK812/Finscope/tree/local) for current runtime configuration; no installation, model preparation or collection command was executed by showcase maintenance.

The local library is `reports/finscope_local.sqlite3` (ignored by Git); set `FINSCOPE_LOCAL_DB` to use another local file. News/results persist across browser and application restarts. This is a single-user desktop-hosted product, not an authenticated multi-user service. Keep it bound to localhost.

## Sources and permissions

- **Marketaux:** Broad Financial News, Selected media (six publisher filters, Latest only) or Company Tracking. Free-plan page size remains limited; use the actual subscription and current account/application budget. Fixed windows and page caps do not ensure exhaustive coverage.
- **NewsData.io:** latest feed, approximately 48 hours, possible free-plan delay. Its existing manual pause remains active; the connector does not override it.
- **Finnhub:** user key and company ticker. This is company news, not sector-wide coverage; historical entitlement depends on the account.
- **Reviewed sources and imports:** bounded RBA/ABS/NIST/SEC adapters and approved JSONL/CSV imports have source-specific policies; SEC requires actual contact information. ACCC remains disabled. No arbitrary-site scraper.
- **Media discovery:** fixed feeds and optional bounded monitoring track links separately from licensed text/NLP. Discovered URLs, company query cohorts and article text topics are different evidence. See the local [source limitations](https://github.com/DVDWK812/Finscope/tree/local#sources-and-permissions).

Configure keys only in the local masked Settings editor or ignored `.env`. Current primary selection and dated account/application budgets are explicit; supplier balance can remain Unknown. Keys in one account share quota, holds and request history. Bounded batches can paginate where implemented, but failures/unknown outcomes do not automatically retry or rotate keys. Settings, filters and reopening the app do not fetch. NewsData's manual pause remains. Do not clear ledgers or shorten holds.

API success is separate from permission to display, retain, process or send publisher text. Preview is local personal noncommercial access; storage/NLP/transmission remain off until a permission reference and the relevant rights are supplied. Full publisher pages are never fetched. Approved self-authored or licensed text can be saved and analyzed independently. Missing publication times remain unknown.

## Models and evidence

FinBERT is the default local model and requires no API key. Its genuine three-class probabilities and exact revision are preserved with MiniLM revision and unverified candidate groups. No mock prediction is substituted on failure. FinBERT weights: **CC BY-NC-SA 4.0**, ProsusAI / MIH AI B.V.; MiniLM: **Apache-2.0**. These weight licences do not grant publisher rights. See [model evidence](docs/AI_PROTOTYPE.md).

Optional LM Studio, Ollama and explicitly consented external LLM integration are implemented on `local`, subject to local services, model assets, accounts and input rights. This showcase does not exercise them or establish their live availability. Consult the [local product documentation](https://github.com/DVDWK812/Finscope/tree/local#models-and-evidence) for current configuration.

Industry classification is independent of sentiment selection and company metadata. Preserve Unclassified/Unknown and not-applicable states. DeepSeek's controlled authored-text interface acceptance does not make it the automatic real-news pipeline. Later multi-round model checks were resource-preflight-blocked; repeated-load stability remains unverified.

Raw originals remain the default. Cosine ≥0.80 within 72 hours creates unverified candidates; neither event deduplication nor contradiction detection is validated. The consumed challenge remains frozen: **12/16 scorable agreement (75%), macro-F1 0.730159**, two mixed/uncertain exclusions and selected-pair cosine precision **0.666667**, including P02/P07 risks. Reviewer independence/completion and three-human usability remain unverified. See [frozen evidence](docs/CHALLENGE_EVALUATION.md), [freeze](docs/DELIVERY_FREEZE.md) and [concise team report synopsis](docs/REPORT_SYNOPSIS.md). The team writes the final academic report.

## Verification and retained tools

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m finscope.benchmark --dry-run
```

Offline tests use mocks/authored text; actual provider/model/browser checks are recorded separately in [local redesign evidence](docs/LOCAL_REDESIGN.md). The [provider evaluation](docs/API_EVALUATION.md), [decisions](docs/DECISIONS.md), [RSS](docs/RSS_PROTOTYPE.md), [HTML](docs/HTML_PROTOTYPE.md), and [historical overview](docs/PRE_REDESIGN_OVERVIEW.md) preserve prior evidence. The public showcase installs only Streamlit/pandas from `deploy/requirements.txt`; run its preview with `python -m streamlit run deploy/streamlit_app.py`. It never imports the local runtime, asks for keys, fetches news, prepares models or opens a news database. Full local installation uses `requirements-local.txt`; the retained Docker recipe also uses that full local runtime.

The public showcase is frozen in [maintenance-only status](docs/SHOWCASE_FREEZE.md): critical bug fixes and security updates. The proposed `main` → `web` rename is deferred to preserve the existing Streamlit deployment and administration; `main` remains the default and deployed branch. No GDELT retry/task recreation, challenge tuning/rescoring, Moodle access or coursework submission. The official deadline remains user-confirmed, with historical conflicting values preserved in [assessment notes](docs/ASSESSMENT_VERIFICATION.md).
