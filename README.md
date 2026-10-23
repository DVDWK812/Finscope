# FinScope

**AI-powered sector financial news sentiment and event intelligence (FINS5557 Track A).**

This repository starts with a deliberately small **news API feasibility pilot**. The planned final app will collect financial news metadata, classify sentiment using FinBERT (or a supported user-provided model), categorize articles by sector, identify duplicate event coverage via embeddings, and display time/source/sector trends in Streamlit.

> Status: Phase 1 pilot tested locally. First live GDELT run: one successful healthcare query, two HTTP 429 failures; keyed providers skipped. GDELT is provisional for further metadata research. See [actual evidence](docs/API_EVALUATION.md) and [decision gates](docs/DECISIONS.md). No dashboard or sentiment model has been built.

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
- No sector impact inference, sentiment module, or embedding deduplication yet.
- Marketaux free-tier result cap and NewsData latest-news window reduce comparability.
