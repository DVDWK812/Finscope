# FinScope

**AI-powered sector financial news sentiment and event intelligence (FINS5557 Track A).**

This repository starts with a deliberately small **news API feasibility pilot**. The planned final app will collect financial news metadata, classify sentiment using FinBERT (or a supported user-provided model), categorize articles by sector, identify duplicate event coverage via embeddings, and display time/source/sector trends in Streamlit.

> Status: API research scaffold only. No claim of a working dashboard or validated live API coverage.

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

# Real calls: GDELT needs no key; others skip if not configured
python -m finscope.benchmark --providers gdelt --topics technology healthcare materials

# Compare up to four providers × three sectors = up to twelve low-volume calls
python -m finscope.benchmark --providers gdelt marketaux newsdata finnhub \
    --topics technology healthcare materials --limit 3 --days 2
```

Reports receive unique names under `reports/` (excluded from Git); `--output reports/name.json` selects an explicit local path. Each row preserves its UTC query time, safe query parameters, outcome, latency, quota headers when supplied, normalization metrics and up to ten title/URL/source/time samples. Descriptions and article bodies are not saved. URL checks validate syntax only; publisher pages are not fetched. A failed live attempt writes its report and exits with code 1; missing credentials are skipped.

Keys are read only from this project's `.env`, without shell inheritance or interpolation. Requests run provider first, with conservative spacing between GDELT requests and no automatic retries or redirects. HTTP 429 stops further requests to that provider for the run; later topics are marked skipped. API keys must **never** be committed or pasted into logs and GitHub Issues.

## Interpreting results

This is a **feasibility study**, not an objective leaderboard. Finnhub uses ticker-specific queries; the other providers use keywords. GDELT often supplies only titles/URLs and its article timestamp is first seen, **not** a confirmed publication timestamp. A successful API response does not prove full-text availability or lawful reuse.

See [evaluation protocol](docs/API_EVALUATION.md), [Codex task](CODEX_TASK.md), [developer instructions](AGENTS.md) and [development log](docs/DEVELOPMENT_LOG.md).

## GitHub setup and version control

Create `DVDWK812/FinScope` as a public repository, initialize with a README, then clone it and copy scaffold files into it. Make meaningful incremental commits. Example:

```bash
# Run from the parent folder containing the extracted FinScope/ directory
git clone https://github.com/DVDWK812/FinScope.git FinScope-repo
cp -a FinScope/. FinScope-repo/  # macOS/Linux; use Explorer/Copy-Item on Windows
cd FinScope-repo
git add .
git commit -m "chore: bootstrap FinScope API comparison"
git push -u origin main
```

If using Codex, supply `CODEX_TASK.md` as its phase-1 objective. All team-authored changes and AI coding assistance must be disclosed in the course report. For public deployment, verify each provider's usage and redistribution rights.

## Known limitations

- Requires network to perform live tests; token-based APIs require individual developer keys.
- Limited pilot size, provider-specific queries, and no full article text extraction.
- No sector impact inference, sentiment module, or embedding deduplication yet.
- Marketaux free-tier result cap and NewsData latest-news window reduce comparability.
