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
