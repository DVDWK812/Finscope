# Instructions for Codex agents working on FinScope

## Mission and scope
- Course: FINS5557 / INFS5557 (confirm official course code in Moodle). Track A Tech Team, three members.
- Current phase: find a reliable and legally suitable API for news **metadata**, not price forecasts, text sentiment, or a general-purpose crawler.
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
8. Commit each coherent change with a meaningful commit message, e.g. `test(api): add GDELT adapter fixtures`. Push only if the working repo and user access are configured. Prefer a branch + PR for nontrivial changes.

## Safety and integrity
- Never commit `.env`, actual API keys, copied article full text, bulk article datasets, or licence-restricted data.
- Never put API keys in issue comments, PRs, diagnostic logs, README, screenshots, or error messages.
- Do not bypass paywalls, robots policies, anti-bot measures or rate limits.
- Marketaux supports `group_similar=false`; keep it off in experiments to preserve raw overlap for future dedup evaluation.
- Keep original source URLs and timestamps, and distinguish first-seen time from publication time.
- Document AI coding assistance accurately, per course assessment rules.
