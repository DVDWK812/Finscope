# Codex task: bootstrap FinScope GitHub and benchmark finance news APIs

Work inside the extracted FinScope scaffold.

**Repository first**
- Check the authenticated account with `gh auth status` and look for `DVDWK812/FinScope` using `gh repo view DVDWK812/FinScope`.
- If `gh` is available and authenticated and the repository does not exist, create a **public** `DVDWK812/FinScope` repository using the current project directory, following GitHub CLI prompts. Never create under another user or organization. If repository creation is blocked, stop that step and request the user to create it at `https://github.com/new` before pushing; continue local tests without claiming anything was pushed.
- If the repo already exists and contains an initial README, clone it first or reconcile the histories rather than force pushing.
- Make the initial commit `chore: initialize FinScope API evaluation scaffold` with README, `.gitignore`, `.env.example`, tests and CI.

**First experiment**
- Verify API docs/usage rights for GDELT, Marketaux, NewsData.io, and Finnhub.
- Inspect `finscope/api_sources.py`. Fix protocol mismatches and add a regression test for each correction.
- Run offline unit tests, then `python -m finscope.benchmark --dry-run`.
- Run keyless GDELT live test in an environment with normal network access.
- For the 3 optional token-based providers, use credentials **only** from local `.env` (never hardcode or ask to paste them into GitHub). Missing keys must be reported as `skipped`.
- Keep initial live tests to at most one request per topic/provider; do not exhaust free quotas.
- Save generated report locally under `reports/`; interpret success, latency, source diversity, missing summaries, usable links and timestamp semantics.
- Manually check sample topical relevance, sources, exact usage licences, supported historical access, and whether public deployment is permitted. Do not infer this from a 200 response.
- Keep Finnhub company-symbol results distinct from sector-wide keyword results; do not equate raw article counts.
- Write a short decision memo in `docs/DECISIONS.md` and update `docs/DEVELOPMENT_LOG.md`.

**GitHub update cadence**
- `main` is the only active development branch. Start by safely switching to and fast-forwarding local `main` from `origin/main`; do not create feature branches or new pull requests. Commit after each tested and reviewable milestone and push directly to `origin main`, checking remote SHA and CI. Never force-push or overwrite divergent/uncommitted changes.
- Use Issues for blockers and test outcomes; never claim a CI pass without checking GitHub Actions.
- At the end, report repository URL, commit SHAs, tests run (with pass/fail), API requests made, which providers were skipped, and recommended primary source.
- Disclose Codex-assisted code in the written assignment report.

**Exit criteria for phase 1**
- Runnable pilot, all offline tests passing, no secrets in repo.
- Actual results and limitations documented, no invented provider test outcomes.
- One primary API chosen on licence suitability, finance relevance, usable text, reliability, history and quota.
- No dashboard, FinBERT integration or crawling until phase 1 evidence is ready.
