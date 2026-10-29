# Local-first product redesign — 29 October 2026 Sydney

The user's architecture correction supersedes cloud product/acceptance assumptions.
FinScope runs on the operator's own computer, bound to localhost, with persistent
local SQLite. Existing hosted/deployment and frozen evaluation evidence is history,
not a requirement to redeploy. Teammates own the academic report.

## Milestone 1: local source → preview → permitted FinBERT → SQLite

- Implemented first-run guide with persistent completion and a reopen action;
  local source selection, masked credentials or project-only `.env`, explicit
  quota-confirmed Fetch, normalized preview and separate downstream permissions.
- All three API adapters accept explicit credentials without changing omitted-key
  benchmark behavior. Finnhub supports a validated company ticker; NewsData's
  existing manual pause remains enforced. No GDELT route/retry was introduced.
- Local product requests use their own durable SQLite reservation, read existing
  provider/study holds, enforce 60-second spacing and at most three requests per
  provider/UTC day, stop on failure/unknown outcomes, and never retry/paginate.
  The separately planned study sampler and its date/window/budget rules are
  unchanged; a local product request is not a study result or study authorization.
- Originals and all analysis versions persist locally. FinBERT reuses the actual
  pinned CPU/MiniLM pipeline, its unchanged probabilities and predeclared candidate
  rules. No calibrated LLM scores or fake fallback are introduced.

**Actual checks, not mocks:** Browser first-run Get Started succeeded. The user
reported no Marketaux requests today. A conservative one-request budget was used
with the existing local `.env` key. One GET started **2026-10-29T09:18:28.562382Z**,
completed **09:18:29.715948Z**, **HTTP 200**, three normalized preview records,
technology topic / semiconductor keyword / 2-day lookback / `group_similar=false`.
No pagination, publisher page, API retry or model processing of these news records
occurred. No headlines, response bodies or credentials are committed. This is
local personal preview evidence, not new public-provider approval, a provider
winner or a multi-day coverage result. Downstream retention/NLP permissions remain
unverified; those uses stay gated.

The browser separately saved the approved authored development chipmaker text,
ran actual local FinBERT/MiniLM and showed one persisted Positive analysis and
Technology sector analytics. Probabilities: positive **0.9529756307601929**,
negative **0.021392226219177246**, neutral **0.025632165372371674**; combined
inference **136.73 ms** (not full request/model-load time). FinBERT revision
`0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`; MiniLM
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. This is engineering smoke evidence,
not accuracy measurement or a frozen-challenge rerun.

**Offline regression:** 202 tests passed (182 retained + 20 new local product
checks); benchmark dry run passed with no provider calls. Legacy demo UI tests
now explicitly call the retained legacy fixture entrypoint; new AppTest coverage
exercises the actual local-first entrypoint. Exact-commit CI is checked after push.

Remaining milestones: shared visual analytics/heatmap/evidence graph/drill-down;
external structured LLM/local Ollama/fixed collectors and UI polish. The complete
real-Marketaux-to-FinBERT acceptance remains gated by actual downstream permission,
not replaced by the authored-text result.
