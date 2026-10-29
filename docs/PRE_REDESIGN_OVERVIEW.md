# Historical overview before the local-first redesign

Preserved 29 October 2026 Sydney. Superseded for current product architecture by the local-first request. Evaluation observations below remain dated historical evidence.

# FinScope

**Approved-text financial sentiment MVP — October 26–31 delivery sprint.**

**Final delivery freeze, 29 October:** The challenge packet is consumed: preserve its evaluation and original human evidence; do not rerun or tune on it. Reviewer independence and completion attestations remain unverified. [Freeze record](docs/DELIVERY_FREEZE.md), [three-human evidence template](docs/USABILITY_EVIDENCE_TEMPLATE.md) and [demo operator checklist](docs/DEMO_CHECKLIST.md). Raw articles remain the default; event deduplication and contradiction detection are not validated.

**[Open the public FinScope demo](https://finscope-dvdwk812.streamlit.app/)** — real hosted synthetic-text inference verified on 26 October 2026. No API key required. Free hosting can sleep; first-time model preparation/cold loading takes longer than warm inference.

The hosted app runs independently of the developer's computer. A later forced-reboot check measured 6.15 seconds prepared-file cold model load and 875.7–878.4 MiB current RSS (not peak or a load guarantee). Actual inference recovered after 326.5 seconds of interactive idleness; two tab sessions stayed isolated and filtered export preserved both originals. This does not verify hosting hibernation or sustained load. **Reboot cleared model assets and required the explicit preparation control again.** Export before leaving; temporary storage/workspaces can reset. See [actual hosting evidence and limitations](docs/HOSTING_VERIFICATION.md).

Submit synthetic, self-authored or explicitly licensed financial news text, attest processing/storage rights, run **real local FinBERT and MiniLM**, and inspect saved scores, explainable multi-label sectors and candidate event groups in Streamlit Overview, Trends and News Explorer. This is a noncommercial course research demo. No news API is connected; Marketaux/public data-source approval is not claimed. The completed GDELT one-shot is not retried.

## Run the working application

```powershell
python -m venv .venv-ai
.venv-ai/Scripts/python.exe -m pip install -r deploy/requirements.txt
# Explicit one-time preparation, not an inference-time download:
.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses
.venv-ai/Scripts/python.exe -m streamlit run streamlit_app.py
```

In the app choose **Approved-text AI demo**, provide text and its source/permission/timestamp meaning, confirm your rights and click **Run real AI analysis**. The result is saved to your session-scoped repository and reflected in all three views. The **Illustrative fixture tour** remains separately labelled; its predefined labels/events are not model evidence. If deployment has no prepared assets, an explicit **Prepare demo models** control performs the one-time setup before inference.

FinBERT weights: **CC BY-NC-SA 4.0**, attribution ProsusAI / MIH AI B.V.; MiniLM: **Apache-2.0**, sentence-transformers/all-MiniLM-L6-v2. Model revisions/config/tokenizer/weights are pinned and hash-verified. Do not infer commercial or publisher-input permission from the MIT software licence. See [model evidence](docs/AI_PROTOTYPE.md) and [source rights](docs/DECISIONS.md).

Records are isolated by browser-session workspace and can be exported as JSON. An app access purges records older than 24 hours; there is no background deletion service. Server storage on free hosts can reset after redeploy/reboot; refresh may start a new workspace. Do not submit private text. Original source and supplied/submitted timestamps are retained; published and first-seen meanings are never silently interchanged. Keyword sectors include **Unclassified** and expose matched terms. **Raw article counts are the approved-demo default**, including after Reset filters. Cosine ≥0.80 within 72 hours creates **unverified candidates**, not confirmed event identity. Optional candidate chart summaries use the earliest matching representative, not sentiment consensus. Explorer always lists all matching originals and shows all workspace members of a selected candidate, including members outside the active filters. Opposing positive/negative model labels trigger a potential contradictory-outcome warning; it is a review flag, not verified factual contradiction. Export retains every workspace original regardless of filters/counting mode.

## Deployment

Community Cloud entrypoint: **deploy/streamlit_app.py**, branch **main**, Python **3.12**, dependency file **deploy/requirements.txt**. Do not copy local `.env`/API keys, reports, SQLite data or weights into hosting secrets/source. The app requires no API key. Docker is an alternative build recipe, not yet built/tested here; its explicit build stage prepares pinned model assets. Community Cloud build and actual hosted inference succeeded; see [measured evidence and limitations](docs/MVP_EVALUATION.md).

## Verification and limitations

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m finscope.benchmark --dry-run
```

Unit/UI regression tests use labelled mocks; actual browser/model runs are recorded separately in DEVELOPMENT_LOG.md. The [12-text authored evaluation](docs/MVP_EVALUATION.md) matched all provisional sentiment labels but grouped-event pair precision was only .60 across 66 pairs. This is not independent accuracy validation. The later [18-text user-adjudicated challenge](docs/CHALLENGE_EVALUATION.md) produced **75% sentiment accuracy (12/16 scorable; macro-F1 .730)**; two mixed/uncertain texts were retained outside three-class scoring. Semantic-pair precision was .667 on 10 scorable pairs; an uncertain opposed-outcome pair also grouped. Reviewer independence/completion attestations remain unverified, so this is provisional evaluation rather than certified independent accuracy. The packet is now evaluated and cannot be used to tune and evaluate the same rules/thresholds. Three-human feedback remains pending: [test protocol](docs/USER_TESTING.md). See the [sprint plan](docs/MVP_SPRINT.md), [team-reference report synopsis](docs/REPORT_SYNOPSIS.md), [three-speaker 6:15 demo](docs/DEMO_SCRIPT.md) and [contribution/AI disclosure statements](docs/CONTRIBUTIONS_AND_AI_DISCLOSURE.md), with human names/signatures pending. No investment-return or confirmed-event claim follows from the demo. Unapproved provider ingestion/display remains **NO-GO**.

## Assessment verification

Earlier course notes identify **FINS5557 — Applied AI in Finance, T3 2026**, Track A, three members. **31 October is the internal delivery target**, not a verified Moodle deadline. The historical Friday/Week 8 23:59 Sydney wording and 10 November 2026 00:00 dropbox value are **unverified conflicting information**. The user will confirm the official deadline personally. **Further agent Moodle access, uploads, submissions and account actions are prohibited; previous sign-in permission is revoked.** No submission/message was sent. See [preserved assessment notes](docs/ASSESSMENT_VERIFICATION.md). Individual names/contribution claims remain unassigned as requested; the AI disclosure describes known assistance only.

## Retained Phase 1 tooling and history

## Optional local RSS prototype

The manually triggered [RBA RSS collector](docs/RSS_PROTOTYPE.md) saves a small,
attributed media-release sample in ignored `reports/rss/`. It is separate from
Streamlit, evaluation and inference. Default/preview mode makes no requests:

```powershell
python -m finscope.rss_collector --dry-run
# Explicit manual collection: robots check + at most one fixed RBA feed request
python -m finscope.rss_collector --collect --limit 3
```

This central-bank release feed is not a substitute for broad financial-news
coverage. Public integration remains deferred pending record-level rights and
quality review; delivery readiness takes priority.

## Phase 1 features

- Provider adapters for **GDELT, Marketaux, NewsData.io, Finnhub**.
- A comparable normalized article schema; first-seen vs published timestamps remain distinct.
- Low-volume per-sector queries and structured diagnostic metrics.
- `.env` keys (no key in code), masked HTTP error reporting.
- Offline unit tests and GitHub Actions CI.

## Installation

Requires Python 3.11+.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # set keys locally if available; Windows: copy .env.example .env
python -m unittest discover -s tests -v
```

## Commands

```bash
# 0 calls; inspect plans and missing credentials
python -m finscope.benchmark --dry-run

# Offline previews only; GDELT's completed/deleted one-shot must not be retried
python -m finscope.sampling --dry-run
python -m finscope.ai_prototype --dry-run
python -m finscope.marketaux_runner --dry-run
python -m finscope.finbert_backend --dry-run
```

Reports receive unique names under `reports/` (excluded from Git); `--output reports/name.json` selects an explicit local path. Each row preserves its UTC query time, safe query parameters, outcome, latency, quota headers when supplied, normalization metrics and up to ten title/URL/source/time samples. Descriptions and article bodies are not saved. URL checks validate syntax only; publisher pages are not fetched. A failed live attempt writes its report and exits with code 1; missing credentials are skipped.

The legacy benchmark blocks live Marketaux when its key is configured. The prepared runner can bind the nonretrying adapter only behind explicit execution, date/sector authorization and fresh operator-verified quota evidence. No approval/round is installed or executed by preparation. The SQLite ledger reserves before dispatch, enforces duplicate/budget/spacing/cooldown rules and stores only safe categories/counts. Do not delete/reset the ledger or bypass it with direct adapter calls. NewsData's additional manual pause remains in force beyond its historical timed hold. See the [runner contract](docs/MARKETAUX_RUNNER.md).

Keys are read only from this project's `.env`, without shell inheritance or interpolation. Requests run provider first, with conservative spacing between GDELT requests and no automatic retries or redirects. HTTP 429 stops further requests to that provider for the run; later topics are marked skipped. API keys must **never** be committed or pasted into logs and GitHub Issues.

Validated `Retry-After` seconds or HTTP dates are persisted in ignored `reports/provider_cooldowns.json`, so another CLI invocation cannot bypass the hold. A 429 without a usable header creates our conservative 24-hour hold. A malformed cooldown file blocks live requests until reviewed. Run the pilot serially on this checkout; its local state is not a distributed quota coordinator. Do not delete or shorten holds to retry a provider.

Reports also measure title character lengths, whitespace word counts (not model tokens), nonblank descriptions and publication/first-seen completeness separately. Malformed text fields and date-only/epoch sentinel timestamps do not count as usable NLP input.

## Interpreting results

This is a **feasibility study**, not an objective leaderboard. Finnhub uses ticker-specific queries; the other providers use keywords. GDELT often supplies only titles/URLs and its article timestamp is first seen, **not** a confirmed publication timestamp. A successful API response does not prove full-text availability or lawful reuse.

See [evaluation protocol](docs/API_EVALUATION.md), [Codex task](CODEX_TASK.md), [developer instructions](AGENTS.md) and [development log](docs/DEVELOPMENT_LOG.md).

## GitHub setup and version control

The public repository is [DVDWK812/Finscope](https://github.com/DVDWK812/Finscope). Phase 1 PR #2 was merged into `main`. **The project now uses `main` as its only active development branch.** Do not create new feature branches or PRs. Before editing, fetch and fast-forward `main`; push tested commits to `origin main` and verify GitHub Actions.

```bash
git clone --branch main https://github.com/DVDWK812/Finscope.git
cd Finscope
# In an existing checkout with a clean working tree:
git fetch origin
git switch main
git pull --ff-only origin main
```

Do not discard uncommitted work, force-push or overwrite diverged history. Older Phase 1 branch references in historical logs document past work rather than current instructions.

If using Codex, supply `CODEX_TASK.md` as its phase-1 objective. All team-authored changes and AI coding assistance must be disclosed in the course report. For public deployment, verify each provider's usage and redistribution rights.

The repository's MIT licence covers the project software; provider data and linked publisher content remain subject to their own rights. Track unresolved Phase 1 evidence and permission gates in [Issue #1](https://github.com/DVDWK812/Finscope/issues/1).

## Known limitations

- Requires network to perform live tests; token-based APIs require individual developer keys.
- Limited pilot size, provider-specific queries, and no full article text extraction.
- FinBERT has approved fictional-text evaluation with provisional user-adjudicated references: 12/16 scorable agreement (75%), macro-F1 0.730159; two mixed/uncertain references excluded. Pairwise cosine precision is 0.666667 on ten scorable selected pairs. Reviewer independence/completion attestations remain unverified; no evaluated real-news accuracy, sector-impact inference, validated event deduplication or contradiction detection is claimed.
- Marketaux free-tier result cap and NewsData latest-news window reduce comparability.

## Synthetic UI prototype

Run the offline interface after installing dependencies:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The demo provides Overview, Trends, News Explorer and System Status with sector/source/date/sentiment filters and raw-report versus unique-event views. All headlines, sources, timestamps and labels are synthetic. No real API calls, news storage or AI inference occur on UI startup. See [UI specification](docs/UI_SPEC.md). Phase 2 live-source/inference approval remains **NO-GO**.
