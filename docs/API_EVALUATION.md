# API evaluation protocol — Phase 1

## Objective
Choose one sustainable news metadata source for a **publicly deployed**, non-commercial student MVP. The API test does **not** evaluate the sentiment model, sector labelling or event deduplication yet.

## Candidates (verify plan limits and rights before deployment)

| Provider | Query strategy in pilot | Credential | Important caveat |
|---|---|---|---|
| GDELT DOC API | English keyword, past N days | None | GDELT `seendate` means first seen, not necessarily published; source noise; often no summaries |
| Marketaux | English keyword, `group_similar=false` | `MARKETAUX_API_KEY` | Free tier caps results per request; provider grouping must be off to test our own deduplication |
| NewsData.io | English keyword, latest news | `NEWSDATA_API_KEY` | Latest endpoint is approximately 48h; historical access is plan-dependent |
| Finnhub | North-American ticker (e.g. NVDA) | `FINNHUB_API_KEY` | Company news is **not** equivalent to sector-wide keyword coverage |

Official docs: [GDELT](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [Marketaux](https://www.marketaux.com/documentation), [NewsData.io](https://newsdata.io/documentation), [Finnhub OpenAPI](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml).

## Experiment

1. Sample the same three *topics*: technology (semiconductor), healthcare (pharmaceutical), materials (copper).
2. Make **one low-volume request** per provider/topic (3 topics × 4 APIs = up to 12 calls). Record UTC query time.
3. Measure request outcome, response latency, raw and valid article counts, distinct sources, valid URLs, nonempty descriptions and timestamp completeness. Completeness ratios among accepted records are conditional on successful normalization; use the raw-to-valid ratio to disclose discarded records.
4. Manually inspect relevance of up to ten returned articles per topic/provider. Report judged relevance and **classification uncertainty**. Count missing fields separately.
5. Check actual source diversity, access permissions, usage quotas, date range, and whether the free tier permits deployment, storage and derived NLP analysis.
6. Do NOT compare raw article counts as if all providers implemented the same query semantics. Finnhub symbol scope differs from keyword search; GDELT first-seen timestamps differ from publication timestamps.
7. Repeat on at least two different days before settling on a primary provider (if project time allows). Summarize trade-offs and choose one primary provider plus optional fallback.

## Preferred decision hierarchy

1. Validity of public deployment and permitted use of returned data (pass/fail).
2. Quality and relevance of news coverage by topic and source (most important).
3. Publication timestamps, source IDs and access to summaries.
4. Stability, quota, documented history and ease of scheduled ingestion.
5. Latency and cost.

## What this pilot does not prove

- API success alone is not proof that HTML pages can legally be scraped or their full text redistributed.
- Lexical overlap between a keyword and a title is not a ground-truth relevance metric.
- Headline sentiment is not sector impact or market-return forecasting.
- Provider-generated sentiment or event grouping must **not** substitute for our own FinBERT and embedding evaluation.

## Evidence and Git hygiene

- Commit this plan, scripts, unit tests and a short Markdown summary of the experimental conclusions.
- Save local machine-generated JSON reports under `reports/`, excluded by `.gitignore`.
- No API keys, full text dumps or copied copyrighted article bodies in commits.
- Log APIs tested, sampling date, rate limit response, observed failures and whether deployment rights were verified.

## First evidence review — 2026-10-24 (Australia/Sydney)

Official sources were checked on this date. Documentation describes provider capabilities; it is not evidence that this account received those capabilities. No special academic exemption was verified for the keyed providers.

### Endpoint, metadata and scope comparison

| Provider | Verified contract and expected metadata | Scope / history limitation |
|---|---|---|
| GDELT | DOC `artlist`, JSON, English source-language filter, `timespan=2d`, `maxrecords=3`; titles, original URLs, domains and first-seen times; no promised summary field | General news full-text keyword matching, not a finance feed. DOC documentation describes a rolling three-month search window; older wording about January 2017 is not a guarantee of unrestricted archive access. Maximum 250 records, no exhaustive coverage claim. [Official DOC documentation](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) |
| Marketaux | `/v1/news/all`, `api_token`, English keyword search, UTC `published_after`, `group_similar=false`; source, publication time and meta description | Finance-specific corpus; full-body/title matching can return records whose headlines omit the keyword. Date filters exist, but earliest free-tier retention was not established. [Documentation](https://www.marketaux.com/documentation). Full article content is not supplied. [FAQ](https://www.marketaux.com/faq) |
| NewsData.io | `/api/1/latest`, `X-ACCESS-KEY`, `q`, English, size 1–10 on free; UTC selected explicitly. Description, source and publication fields need live validation | General news, not restricted to financial coverage. Latest covers past 48 hours; the free plan advertises a 12-hour delay. Archive entitlement must be checked separately. [Authentication](https://newsdata.io/documentation/api-authentication), [latest endpoint](https://newsdata.io/documentation/latest-news-api), [plan overview](https://newsdata.io/documentation) |
| Finnhub | `/company-news`, token, company symbol and inclusive calendar-date parameters; headline, summary, source, URL and Unix time | North-American company feed: NVDA/PFE/FCX are proxies, not sector keyword equivalents. Official embedded company-news documentation advertises one year of free-tier history; not exercised with a key. [Provider OpenAPI](https://github.com/Finnhub-Stock-API/finnhub-go/blob/master/api/openapi.yaml), [company-news documentation](https://finnhub.io/docs/api/company-news) |

### Quotas and deployment gate

| Provider | Documented free limits / observed behaviour | Public student MVP, storage and derived analysis |
|---|---|---|
| GDELT | No numeric DOC request quota or SLA verified in reviewed official pages. Observed two HTTP 429s; no captured numeric quota or Retry-After headers. Six-second request-start spacing is our precaution, not an official entitlement. | Dataset use and redistribution allowed with GDELT citation and website link. This supports a metadata pilot; it does not license linked publishers' bodies or images. [Terms of use](https://www.gdeltproject.org/about.html#termsofuse) |
| Marketaux | 100 requests/day, 3 articles/news request; this account's quota not exercised. [Pricing](https://www.marketaux.com/pricing) | Reviewed terms grant personal non-commercial content access, without a clear public redistribution grant. Public display, retention and derived NLP permissions require provider clarification before deployment. API availability is not a deployment licence. [Terms](https://www.marketaux.com/tos) |
| NewsData.io | 200 credits/day, up to 10 articles/credit; 30 credits/15 minutes. No live quota observations. [Credits](https://newsdata.io/documentation/api-credit-limits), [rate limits](https://newsdata.io/documentation/api-rate-limit) | API licence covers personal/internal business use; restrictions include making the API available to others over a network, and publishers retain content rights. A public MVP is not cleared under the reviewed terms; obtain specific written permission covering public output, storage and analysis. [Terms](https://newsdata.io/terms) |
| Finnhub | Terms impose 30 calls/second in addition to plan limits. Current free per-minute allowance was not independently extracted from the pricing page; do not assume it. No live quota observations. [Terms](https://finnhub.io/terms-of-service), [pricing](https://finnhub.io/pricing) | Personal plans prohibit sharing data **or derived results** without written approval; data deletion is required when the data subscription ends. Public deployment is blocked absent an appropriate agreement. The SDK/OpenAPI Apache licence does not license news data. [Terms](https://finnhub.io/terms-of-service) |

### Actual first run

Code: `05a7bdb`. Command:

```bash
python -m finscope.benchmark --providers gdelt marketaux newsdata finnhub --topics technology healthcare materials --limit 3 --days 2 --timeout 15 --output reports/phase1_live_20261023.json
```

Local evidence is excluded from Git. Run start: **2026-10-23T15:09:11.991259+00:00**, corresponding to 24 October in Sydney. Each row records its own UTC time, query, endpoint and outcome. Three news-API HTTP requests were made, all to GDELT, with no retry or pagination. Official-documentation reads and three manual publisher-page checks are separate from this API request count.

| Provider / topic | Request start UTC (2026-10-23) | Actual result | Observed elapsed time |
|---|---|---|---|
| GDELT / semiconductor | 15:09:11.991259 | Failed: HTTP 429 | 11,962.4 ms |
| GDELT / pharmaceutical | 15:09:23.955366 | HTTP 200; 3 raw, 3 normalized, 3 sampled; 3 unique URLs / 3 domains | 20,217.3 ms |
| GDELT / copper | 15:09:44.173494 | Failed: HTTP 429 | 12,342.2 ms |
| Marketaux / all three topics | No requests | 3 skipped: missing `MARKETAUX_API_KEY` in local `.env` | Not measured |
| NewsData.io / all three topics | No requests | 3 skipped: missing `NEWSDATA_API_KEY` in local `.env` | Not measured |
| Finnhub / all three symbols | No requests | 3 skipped: missing `FINNHUB_API_KEY` in local `.env` | Not measured |

The live command exited **1**, as expected when any attempt fails. No live authentication error, empty response array or unexpected schema was observed; these are covered by offline mocks only. The requests timeout is a socket/connect-read timeout, not a strict total deadline, so the observed successful elapsed time can exceed 15 seconds.

For the successful healthcare sample, title and syntactically usable URL completeness was 3/3, first-seen timestamp completeness 3/3, publication timestamp availability 0/3, and description availability 0/3. Original URLs and UTC first-seen timestamps are retained locally. The three domains were `zawya.com`, `pajhwok.com` and `prokerala.com`; three domains do not imply three independent events.

Manual headline review: two pharmaceutical export/trade stories were financially relevant to the sector, with likely event overlap; the partnership announcement was uncertain for finance relevance. That is **2 relevant, 1 uncertain, 0 clearly irrelevant**, not an unbiased precision estimate. [One publisher page](https://pajhwok.com/2026/10/22/pakistans-pharmaceutical-exports-fall-by-over-30pc/) was accessible and confirmed the trade topic; the other two URLs were unavailable through the browsing tool. This does not establish that they are universally broken. No access restriction was bypassed and no full text was saved.

Technology/materials coverage, relevance and metadata quality are **unmeasured** because their API requests failed. Optional-provider coverage and latency are **unmeasured** because they were skipped. A one-day, three-record, relevance-ranked sample cannot establish general reliability, comparative source diversity, historical completeness or sustainable ingestion performance.

After the experiment, commit `0a74486` tightened future runs to stop a provider after its first HTTP 429 and mark later topics skipped. The actual first run above predates this guard and was not rerun. See [decision memo](DECISIONS.md) for the conditional choice and remaining gates.
