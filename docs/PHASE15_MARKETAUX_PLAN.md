# Phase 1.5 Marketaux validation plan — 25 October 2026 Sydney

**Status: safeguards implemented and offline-tested; sampling remains unauthorized, unexecuted and unscheduled. Zero new news-provider requests in this work.** Marketaux remains the preferred conditional candidate; production integration is NO-GO. Preserve the 24 October keyed reports unchanged. The separate GDELT one-shot retains its own authorization and controls; this plan does not start, replace or duplicate it.

## Sample and request budget

Use the same sector proxies as the keyed pilot: healthcare=`pharmaceutical`, technology=`semiconductor`, materials=`copper`. These are keyword samples, not comprehensive sector universes. Keep English, `group_similar=false`, limit 3, first page, and the existing two-day `published_after` filter. Do not add entity, sentiment, country or source filters, change ranking, or query extra pages to improve observed relevance. Marketaux documents relevance ordering by default when search is used, so the first three are not necessarily the newest articles. Record the actual request parameters and UTC time.

| Proposed manual round | Sydney time | UTC | Maximum requests / sampled appearances |
|---|---|---|---|
| 1: Monday 26 October 2026 | 12:00 AEDT | 26 October 01:00 | 3 / 9 |
| 2: Wednesday 28 October 2026 | 12:00 AEDT | 28 October 01:00 | 3 / 9 |
| 3: Saturday 31 October 2026 | 12:00 AEDT | 31 October 01:00 | 3 / 9 |

These are proposed collection windows, **not booked tasks or execution claims**. Maximum **9 new requests and 27 new sampled appearances**, across three different UTC/Sydney dates including weekdays and a weekend. Keep the original 9 records as a separate baseline, not additional independent observations. The sample is too small to estimate uptime, exhaustive coverage, model precision or rare failure rates. Repeated articles reduce effective sample size.

Before each round, a single operator checks the local request ledger, configured key, actual account usage/plan and saved holds. Mark each date/topic attempt **before** dispatch so a crash cannot cause a duplicate; an ambiguous completion is `attempted_outcome_unknown`, never permission to rerun. Skip a missed window without catch-up, and do not execute a previously attempted date/topic. Use unique report names; never overwrite original reports or clear a cooldown. Run serially with at least 60 seconds between sector requests, and longer if required by a saved hold/provider instruction. The guarded sampler enforces spacing and the persistent attempt ledger. The legacy keyed Marketaux live benchmark path is blocked; use the offline preview until sampling is explicitly authorized.

Budget at most three requests in any provider quota day and at most nine total, counting all attempts/errors. Three calls are 3% of the published 100/day allowance, **not proof that the account has three calls left**. Other tools share the account budget: if the remaining allowance or reset boundary cannot be checked, skip the round. Marketaux documents X-RateLimit as a 60-second window and X-UsageLimit as subscription usage; do not substitute the observed 30-rate header for the daily cap. Do not spend quota on entitlement probes or history searches in this design.

Stop the round immediately after auth/permission/quota failure, HTTP 429, transport ambiguity or unexpected schema. No retries, redirects, extra topics, key switching or extra pages. Record an empty successful reply distinctly from failure. Honor Retry-After even on HTTP 200: retain that reply's records, persist the hold and skip remaining topics. Reassess eligibility on the next planned date; never sleep through or bypass a hold to fill the sample. NewsData/Finnhub/GDELT are excluded from these Marketaux commands.

The existing CLI can preview the request shape without traffic:

```powershell
.venv/Scripts/python.exe -m finscope.benchmark --dry-run --providers marketaux --topics healthcare technology materials --limit 3 --days 2
```

Do not remove `--dry-run`: the old keyed Marketaux live path now fails closed. `finscope.sampling.MarketauxSampler` provides the guarded single-request seam, with **no default network backend or authorization**. The same response is passed to the in-memory description reviewer; no recovery re-query or description persistence is allowed. See the implemented safeguards below. This work does not authorize a round, configure a live backend or collect another day.

## Assessment and evidence contract

Grain: one sampled article appearance per request/date/topic. Link repeated appearances by exact URL or provider UUID if available; retain original values locally. Label whether a measure describes appearances, distinct URLs, distinct titles or manually suspected events. Report denominators per day and sector, plus pooled values; missing/skipped rows are unobserved, not zero coverage.

| Dimension | Record from each permitted response | Review rule and limit |
|---|---|---|
| Availability / shape | Attempt time, status/outcome, HTTP, latency, raw/normalized/sampled counts, cap/truncation, safe quota headers | Keep failures and skips in the ledger; never select only successful days |
| Financial relevance | Relevant / off-topic / uncertain, reason category, reviewer and evidence basis | Relevant means a sector-linked business event such as earnings, financing, investment, demand, regulation or a transaction. Title/URL-only labels remain explicitly title/URL-only; unseen body matches are unverified |
| Description informativeness | Missing / title repetition / boilerplate / adds concrete fact / uncertain; character/word lengths; title repetition flag | Inspect title plus meta description transiently. An added fact must contribute an actor, action, amount, timing or business consequence beyond the title. Length alone is not informativeness; do not substitute body snippets or provider sentiment |
| Publication time | Original provider field, parsed UTC, retrieval UTC, age, missing/invalid/future/out-of-window flags | Compare against the requested minute-precision lower bound; document rounding. Age is retrieval minus provider publication, **not measured ingestion delay**. No publisher fetching to verify accuracy in this task |
| Source diversity | Distinct reported domains and normalized URL hosts, largest-source share, per-sector/day distribution, label/host discrepancies | Strip only leading `www`/numbered `www` host prefixes for comparison. Host differences are review flags, not proof of fabrication; preserve both values. Marketing source counts are not observed coverage |
| Duplicate coverage | Exact URL/UUID repetitions, normalized-title repetitions, within/across-day appearances, manual suspected-event groups and uncertainty | For exact URL comparison lower-case scheme/host and omit fragment; keep path/query. For title comparison casefold and normalize word spacing/punctuation. Distinct URLs/titles can still cover one event. `group_similar=false` preserves overlap but does not provide ground truth or recall |

Only aggregate counts, reviewer label categories and source documentation links belong in Git/Issue #1. Review descriptions in memory without console echo, logging, screenshots or persistence. Keep safe original title/URL/source/time samples and annotation IDs in ignored local reports only, within confirmed permitted retention. Do not add raw payload logging, publisher-page requests, snippets, article bodies or real Streamlit data. Do not broaden retention while rights are unresolved. A second team member may independently annotate the same permitted sample **only after team sharing/review rights are confirmed**. Record agreement/disagreement and adjudication separately; a Codex label or one person's second pass is not independent validation. No sentiment or embedding accuracy claim follows from a relevance/informativeness label.

## Proposed screening criteria and release gates

These are prospective engineering screening criteria, **not measured results, statistical guarantees or a production GO rule**:

- Review all nine planned date/sector attempts, their skips and failures. Fewer than three observed dates or fewer than six distinct sampled URLs per sector leaves repeatability/representativeness inconclusive; do not enlarge quota automatically.
- Aim for at least 80% explicitly relevant sampled appearances overall and at least two-thirds in every sector, counting uncertain cases in the denominator. Report both appearance and distinct-URL counts so repeats cannot inflate apparent evidence.
- Aim for at least two-thirds of sampled appearances overall **and in every sector** to have descriptions that add a concrete fact. Missing, repeated, boilerplate and uncertain descriptions do not pass. Publish category counts rather than an NLP accuracy score.
- Require valid publication fields and no unexplained future/out-of-window values in the reviewed sample. Independently established timestamp accuracy remains a separate unresolved gate.
- Flag a source contributing over half of a sector's appearances and every suspected event cluster. No minimum duplicate rate is required: no duplicates in 27 rows would leave duplicate-evaluation suitability inconclusive. Do not claim event recall without an independent reference corpus.
- Resolve account-specific history/quota and written field-specific public display, retention, inference and derived-output permissions. Record account dashboard evidence privately without exposing tokens. Passing the sample criteria cannot override an unresolved permission or intended-NLP-validation gate.

## Provider clarification checklist — prepared, not sent

Marketaux public [pricing](https://www.marketaux.com/pricing), [documentation](https://www.marketaux.com/documentation), [FAQ](https://www.marketaux.com/faq) and [terms](https://www.marketaux.com/tos) were reviewed on 25 October Sydney. They document date filters, but do not establish the earliest history accessible with this free account. Generic Site terms are not a field-specific API/publisher licence. Seek a written, plan-specific answer covering:

1. Earliest retrievable publication date, rolling history window, pagination ceiling, usage/reset periods and actual free-account entitlement for `/v1/news/all`; whether date-filter support has a separate historical restriction.
2. A publicly accessible, noncommercial UNSW student Streamlit app displaying title, meta description, source URL/domain and publication time: permitted fields, attribution/link requirements, audience and limits. Separately cover private review by the three-person team.
3. Local/server/database/cache retention of each field, permitted duration, backups, deletion on cancellation and whether identifiers/aggregate audit counts may be kept longer.
4. Local pretrained-model **inference**, distinct from training/fine-tuning: whether title/meta description may be processed for sentiment and duplicate-event analysis. No inference is run in Phase 1.5.
5. Retention and public display of derived labels, scores, event groups and aggregate charts; whether those outputs remain restricted after source data deletion, whether commercial use changes rights, and how publisher rights are handled. Provider-generated sentiment is a separate field, not an inference permission grant.

NewsData clarification should describe only the nonsensitive saved HTTP 200, Retry-After 900, numeric limit 60/remaining 59/reset value and timestamp. Ask whether Retry-After is a mandatory wait on every successful reply or merely reset metadata, what the numeric header window/units represent versus the documented 30 credits/15 minutes, and which constraint governs the free account. No message has been sent and no new API request is needed to draft these questions. Preserve its saved hold byte-for-byte; keep NewsData live testing manually paused even though that historical deadline has elapsed, until interpretation is resolved. The generic CLI's expired timestamp does not enforce this additional manual pause.

**Decision:** continue Phase 1.5 readiness work only. Phase 2 production integration remains **NO-GO**. Sampling is not authorized or scheduled. Independently authorized AI interfaces use synthetic/explicitly licensed evaluation text only; no real-news/model/UI connection is approved.


## Implemented safeguards — 25 October 2026 Sydney

- `finscope.description_review`: at most 3 normalized articles, title cap 500 characters and description cap 2,000. Oversized text is flagged uncertain without truncation or invoking the annotator. Missing/exact normalized-title repetition are deterministic checks. Boilerplate/added-fact categories require a supplied local annotator; other descriptions remain uncertain. Callback errors are sanitized. Returned/persisted review rows contain only sample indices, categories, basis, lengths and bounds flags; the enclosing ledger record also keeps validated latency/count metrics and attempt/status times. No description/title text, callback or error body is persisted. This is annotation infrastructure, not independently validated NLP accuracy.
- `finscope.sampling`: SQLite unique date/sector reservations committed with synchronous FULL before dispatch, transaction locking, three slots per UTC day and verified provider quota period, nine total. Fixed three dates/sectors, limit 3 and days 2. A bounded round window is 01:00–02:00 UTC (12:00–13:00 Sydney) on each proposed date; missed windows are blocked, not caught up. The operator must approve the exact date via an explicit authorization object and confirm a current dashboard quota snapshot (maximum age five minutes, known 24-hour reset period). No authorization or backend is installed by default; merely importing, previewing or running tests cannot collect news.
- Minimum spacing is 60 seconds after the previous response completion; the sampler raises a safe reason instead of sleeping/retrying. Shared cooldowns are reread before reservation and left untouched. New Marketaux Retry-After holds live durably in the study ledger, including on HTTP 200; any such reply stops the entire round even after its deadline expires. HTTP 429 without a header uses the existing conservative 24-hour policy. Failures/annotation failures stop that day's round. An unresolved dispatch/crash reservation blocks the study and consumes budget until investigated; it is never automatically cleared or repeated.
- Persist only category/count output in ignored `reports/marketaux_phase15.sqlite3`; protect it from deletion/reset/copying. The ledger guards cooperating local samplers sharing that file, not other machines or account clients. Quota snapshots are explicit operator attestations, not provider verification performed by this code. Other account activity must be coordinated separately. Do not issue study calls through the low-level adapter or a separate ledger.
- There is deliberately no live CLI or scheduler. `python -m finscope.sampling --dry-run` previews the policy without credentials, ledger writes or requests. A future explicitly authorized operator must separately install a compliant nonretrying adapter/annotator and provide the quota/authorization objects; synthetic tests do not supply that authorization.

The 20 new synthetic/mock tests verify durable reservations, duplicate/concurrent connection blocking, quota exhaustion, spacing, corrupt state, successful-reply holds, failure stops and text omission. The 87-test full-suite milestone passes; no real API call was made. Subsequent prototype tests are recorded in DEVELOPMENT_LOG.md.
