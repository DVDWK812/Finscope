# Keyed news API feasibility experiment — Phase 1

**Status: staged local experiment executed on 24 October 2026 UTC/Sydney.** All three local credentials were confirmed configured without displaying values; `.env` is ignored and untracked. Stage A made three healthcare requests. Stage B made four requests to eligible Marketaux/Finnhub only; NewsData's two remaining topics were skipped for its saved hold. Total: seven HTTP 200 responses, no retry/pagination and no GDELT requests. See API_EVALUATION.md for exact evidence and limitations. Successful access does not establish public-deployment permission.

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

## Observed results — 24 October 2026

| Provider | Authentication | Actual live responses | Summary text? | Publication timestamp? | Relevance | Public rights | Next action |
|---|---|---|---|---|---|---|---|
| Marketaux | Valid requests succeeded | 3 HTTP 200; 9 raw/normalized/sampled records across 3 topics | 9/9 sampled meta descriptions | 9/9 sampled | 8 relevant / 1 off-topic by title+URL; 7 sources | Unresolved | Conditional primary candidate; clarify rights and repeat reliability sampling in a separately authorized run |
| NewsData.io | Valid request succeeded | 1 HTTP 200; 3 raw/normalized/sampled healthcare records; 2 topics skipped for hold | 3/3 sampled descriptions | 3/3 sampled | 2 relevant / 1 uncertain; 3 sources | Unresolved | Retain hold; no automatic retry or expansion in this experiment |
| Finnhub | Company-news entitlement demonstrated | 3 HTTP 200; 274 raw/normalized records, 9 sampled across PFE/NVDA/FCX | 9/9 sampled summaries | 9/9 sampled | 7 contextual sector-relevant / 2 uncertain; one source label; company attribution differs | Restricted without approval | Company-news comparator for private evaluation; not a sector-coverage winner |

Evidence is local in ignored `reports/keyed_healthcare_initial.json`, `reports/keyed_followup_topics.json`, `reports/keyed_expansion_gate_decisions.json` and `reports/keyed_aggregate_review.json`. Description availability/length is measured; description semantics and model quality were not independently tested. The raw-to-valid ratio is pre-cap; all text/source ratios refer to the sampled rows. NewsData returned Retry-After=900 even with HTTP 200; its hold was honored. Finnhub's numeric quota headers were recorded without inferring an account-specific daily allowance or unlimited history. Phase 2 remains NO-GO and the synthetic-only UI remains disconnected from providers.
