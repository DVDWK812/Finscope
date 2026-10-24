# Keyed news API feasibility experiment — Phase 1

**Status: protocol prepared; no keyed requests executed by this document update.** User reports registration of free Marketaux, NewsData.io and Finnhub accounts, but their `.env` content and real entitlement are not visible to GitHub or this chat.

## Phase 1 staged testing

| Stage | Provider | Query | Max HTTP requests per provider | Cap / query |
|---|---|---|---:|---|
| A | Marketaux, NewsData.io, Finnhub | Healthcare: keyword pharmaceutical; Finnhub symbol PFE | 1 | 3 displayed/sample records |
| B (only eligible providers) | Same providers | Technology/semiconductor, Materials/copper; Finnhub NVDA/FCX | 2 | 3 sampled records |
| Separately scheduled | GDELT | Healthcare, at most 1 request | **Do not run in this experiment** | Governed by existing local one-shot |

Use `python -m finscope.benchmark` via commands in `CODEX_TASK.md`. Keep reports ignored in `reports/`; redact credentials and restrict the committed writeup to aggregate measures. Do not claim data/source quality for skipped queries.

## Test measures

| Dimension | What to inspect | Decision importance |
|---|---|---|
| Authentication & availability | HTTP outcomes and error type | Basic eligibility |
| Text usability | Title word/character length, nonempty descriptions, sample financial relevance | Critical for future FinBERT and semantic dedup |
| Metadata | Valid URLs, source domains, publication timestamps vs discovery timestamps | Critical for time/source filters |
| Scope | Sector keyword vs company-symbol query; coverage and overlap | Avoid misleading cross-provider counts |
| Sustainable operation | Actual free quota, response latency, 429s, temporal access, query delays | Operational feasibility |
| Public/student reuse | Field-specific display, retention, derived model inference/output rights | Required before public deployment |

The free-plan limits are **request/credit limits**, not a promise of fresh or finance-relevant news. Marketaux has 100 requests/day and 3 articles/request. NewsData free has 200 credits/day, up to 10 results/credit, ~12-hour delay, and no full article bodies. The NewsData published feature matrix conflicts with an apparent AI-tag/sentiment free-plan badge; test only what the key is allowed to return, and independently implement FinBERT later. Finnhub's account-specific free news entitlement and limits must be checked in the dashboard, and its company endpoint cannot substitute for industry-wide keyword search.

## Permission caveats

- [Marketaux news API](https://www.marketaux.com/documentation), [pricing](https://www.marketaux.com/pricing), [terms](https://www.marketaux.com/tos).
- [NewsData.io API](https://newsdata.io/documentation), [free credit limits](https://newsdata.io/documentation/api-credit-limits), [terms](https://newsdata.io/terms).
- [Finnhub pricing](https://finnhub.io/pricing), [terms](https://finnhub.io/terms-of-service), [company news endpoint](https://finnhub.io/docs/api/company-news).

API access is not a publisher full-text licence. Public use must be resolved separately from local evaluation. See `docs/DECISIONS.md`.

## Results (complete after live execution)

| Provider | Authentication | Actual live responses | Summary text? | Publication timestamp? | Relevance | Public rights | Next action |
|---|---|---|---|---|---|---|---|
| Marketaux | Not tested with user's key | None in this phase yet | Unknown observed | Unknown observed | Not measured | Unresolved | Local low-volume test |
| NewsData.io | Not tested with user's key | None in this phase yet | Unknown observed | Unknown observed | Not measured | Unresolved | Local low-volume test |
| Finnhub | Not tested with user's key | None in this phase yet | Unknown observed | Unknown observed | Not measured | Restricted without approval | Local low-volume test |

Do not replace the untested labels based on official examples or inferred limits. Record actual UTC test date and per-request outcome after running.
