# Instructions for Codex agents working on FinScope

## Mission and scope
- Course: FINS5557 / INFS5557 (confirm official course code in Moodle). Track A Tech Team, three members.
- Current phase: find a reliable and legally suitable API for news **metadata**, not price forecasts, text sentiment, or a general-purpose crawler.
- **Parallel UI exception:** A Streamlit front-end using only explicitly synthetic, offline fixtures may be developed and tested on `main`. This does **not** approve live ingestion, FinBERT, embedding inference, real sentiment conclusions or public redistribution of news content. Keep UI reads behind a repository interface and make demo status unmistakable.
- **Independent AI prototype authorization (25 October 2026):** Modular FinBERT/embedding interfaces and offline tests with synthetic or explicitly licensed evaluation text are permitted separately from production integration. No real news inputs, automatic model downloads, provider/UI connection or accuracy claims. Sampling safeguards may be implemented/tested, but Marketaux rounds require separate explicit authorization and must not be scheduled/executed by readiness work.
- Keep implementation small, testable and safe to run on the free API tiers.
- Prefer Python 3.11+, `requests`, `python-dotenv`, `unittest`; avoid heavyweight ML libraries in API pilot.

## Required workflow
1. Inspect `git status`, the README and current tests before changing code.
2. Read `docs/API_EVALUATION.md`; do not pretend providers have comparable scopes when they do not.
3. Verify current official endpoint documentation and free/academic/public-deployment licence before declaring a winner.
4. Run `python -m unittest discover -s tests -v` and `python -m finscope.benchmark --dry-run`.
5. With access to the network and user-supplied environment keys, conduct the lowest-cost real provider requests. Keep query and UTC timestamp metadata in the local report.
6. Review errors (auth failure, rate limit, empty response, unexpected schema); distinguish `skipped` from `failed`.
7. Add a concise, evidence-based result to `docs/API_EVALUATION.md` or `docs/DECISIONS.md` and update `docs/DEVELOPMENT_LOG.md`.
8. Use `main` as the only active development branch. Before editing, run `git fetch origin`, check for uncommitted work, switch to `main`, and fast-forward safely with `git pull --ff-only origin main`. Do not create or switch to feature branches or open new PRs. Commit each coherent, tested change with a meaningful message and push to `origin main`; verify the remote SHA and GitHub Actions. If main has diverged or contains unrelated edits, stop rather than force push or overwrite work.

## Safety and integrity
- Never commit `.env`, actual API keys, copied article full text, bulk article datasets, or licence-restricted data.
- Never put API keys in issue comments, PRs, diagnostic logs, README, screenshots, or error messages.
- Do not bypass paywalls, robots policies, anti-bot measures or rate limits.
- Marketaux supports `group_similar=false`; keep it off in experiments to preserve raw overlap for future dedup evaluation.
- Keep original source URLs and timestamps, and distinguish first-seen time from publication time.
- Document AI coding assistance accurately, per course assessment rules.
