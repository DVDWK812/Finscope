# Phase 1 decision memo — 2026-10-24

Recommend **Marketaux as the conditional primary financial-news candidate for continued local sector-keyword evaluation**, based on the staged keyed experiment below. GDELT remains a provisional keyless comparator. No provider is approved as the production source, and Phase 1's complete exit criteria are not satisfied.

**Phase 2: NO-GO after the keyed experiment.** Seven successful requests improve observed text/metadata availability but do not resolve multi-day reliability, NLP quality, account/history limits or public display/retention/derived-output rights. The separate GDELT retest remains scheduled and unchanged; no GDELT request was made in this task.

**Parallel UI exception (24 October 2026):** The team may build an offline Streamlit interface using conspicuously labeled synthetic fixtures and a swappable repository contract. This UI-only development is independent of source approval and is **not** Phase 2 model/data integration or a production news dashboard. Live data, model-generated sentiment and provider content remain blocked pending the gates below.

GDELT has the strongest verified reuse basis among the reviewed options: its [dataset terms](https://www.gdeltproject.org/about.html#termsofuse) allow reuse and redistribution with attribution. One real healthcare query returned three usable metadata records. However, two of three API requests returned HTTP 429, the successful request took 20.2 seconds, and all three accepted records lacked descriptions and publication timestamps. This supports further metadata research only; it does not establish adequate text input for a future sentiment model.

Marketaux now has actual responses for healthcare, technology and materials: nine sampled records across seven reported sources, all with descriptions/publication timestamps, eight business-relevant titles and one off-topic title. Its sector-keyword contract is the closest fit to the project; public use still needs clarification under its [terms](https://www.marketaux.com/tos). NewsData returned promising healthcare metadata but supplied a hold, so other topics were skipped. Finnhub supplied company-scoped short text, with narrower source attribution and indirect matches; its personal-plan sharing restriction remains material. See the [keyed evidence](API_EVALUATION.md#keyed-provider-experiment--2026-10-24), including the distinct query scopes and [rights comparison](API_EVALUATION.md#rights-decision-by-intended-use).

## Keyed decision evidence — 24 October 2026

All three ignored local `.env` keys were configured and authenticated by actual successful endpoint requests. Stage A made exactly one healthcare request per provider. Only Marketaux/Finnhub passed the expansion timing gate: two more requests each, one per remaining topic. NewsData's HTTP 200 included Retry-After=900; its two omitted topics are skipped/provider_cooldown, not failures or empty coverage. Total **7 requests, 7 HTTP 200, no retry/pagination**. No adapter, UI or model code was changed.

| Candidate | Observed strengths | Decision limits |
|---|---|---|
| Marketaux | 9 sampled records / 7 sources over all three keyword topics; 9/9 descriptions and publication times; mean latency 880.9 ms; 8 relevant / 1 off-topic title | Small single-day sample; source/ranking/geography bias and overlapping healthcare policy items; short descriptions; public-use/retention/derived-output rights unresolved |
| NewsData.io | Healthcare 3 records / 3 sources, 3/3 descriptions and publication times; 2 relevant / 1 uncertain title | Only one topic observed; advertised delay/latest window; saved provider hold; rights clauses need reconciliation |
| Finnhub | PFE/NVDA/FCX access; 274 normalized rows across three symbols, 9 sampled; summaries/publication times present in all samples | Not sector-keyword coverage; sampled source label Yahoo, Finnhub-hosted links; indirect company attribution; personal-plan sharing of data/derived results requires written approval |
| GDELT | Broad dataset reuse basis with attribution; no key | No new call in this task; original rate limits, missing summaries and first-seen-only timestamps remain; scheduled comparator is preserved |

Recommend Marketaux for the next **separately authorized** local reliability/representativeness test and plan-specific permission clarification. Keep NewsData as an unproven broader-news alternative and Finnhub as a company-news comparator. This is a conditional engineering recommendation, not a licence grant or deployment approval. No real records or provider sentiment are connected to Streamlit; the synthetic-only UI exception remains unchanged.

## Historical baseline evidence and outstanding gates

The following baseline predates configured keys and the keyed experiment. Missing-key rows are preserved as historical skips, not current credential status. Current validation uses the isolated project `.venv`: all 66 tests and the keyed dry run pass; exact-head CI is pending at commit time and its post-push result is recorded in Issue #1.

- Baseline: 11 existing offline tests passed; the reviewed pilot has 36 passing offline tests and a passing dry run on `main`. Push-triggered [Actions run 39983651007](https://github.com/DVDWK812/Finscope/actions/runs/39983651007) passed for synchronized main `f432102`; later documentation commits require their own checks.
- Actual API requests: three GDELT requests, one per topic, no retries. Two HTTP 429 failures; one HTTP 200. All nine optional-provider query rows are skipped because this project's `.env` has no keys. No live auth/schema/empty-result claim is made.
- The three healthcare headlines yielded two relevant trade items and one uncertain partnership item. Two stories likely describe the same event. Original links/times and manual annotations are in ignored `reports/phase1_live_20261023.json`; no article text is committed.
- Before closing Phase 1: obtain another-day availability/relevance evidence when practical, resolve rate-limit handling operationally without bypass, test available keyed alternatives at minimum cost, verify retention/history entitlements, and secure necessary public-display/storage/derived-output rights. If summaries are required later, reevaluate the data requirement rather than adding a crawler.
- GitHub connector login is DVDWK812. The user merged [PR #2](https://github.com/DVDWK812/Finscope/pull/2) into public [DVDWK812/Finscope](https://github.com/DVDWK812/Finscope) as `6ae8e00`. Local `main` was safely fast-forwarded through the user's workflow updates to `f432102`; all Phase 1 implementation/tests/evidence files match the merged head. The fully merged feature branch was deleted locally and remotely after verifying zero unique commits. **Use main only: no feature branches, new PRs or force pushes.** [Issue #1](https://github.com/DVDWK812/Finscope/issues/1) tracks feasibility gates; historical unmerged-PR statements describe earlier milestones.
- Confirm the official course code in Moodle. Record Codex assistance accurately in the assignment. No FinBERT, embeddings, crawler or live-data dashboard integration is approved; the separate synthetic-only UI exception remains in force.

## Follow-up release gates

PR #2 was reviewed at `7a656df` and subsequently merged by the user. Commit `2ce44d6` fixes persistent Retry-After/cooldown handling, malformed text/timestamp completeness and missing NLP metrics; these fixes and all 36 passing tests are now on main. The earlier keyed-provider follow-up produced three skipped healthcare rows and zero HTTP requests. Reanalysis found mean title length 77 characters / 11.3 whitespace words, zero descriptions and zero publication timestamps. These are the same three original records, not new sampling.

The one-shot follow-up is scheduled for 25 October 2026, 09:00 Australia/Sydney, subject to local app/computer availability. The 24 October pre-run audit found no execution report and the task is not yet due; this is pending work, not a cooldown skip or a successful test. Updated instructions use main only and allow the already authorized single GDELT healthcare request only after checking for an existing attempt, different-day/24-hour conditions and saved holds. A hold means skipped/provider_cooldown; HTTP 429 ends the attempt without retry. The audit makes no additional provider calls, including optional providers. New evidence or missing execution must update all three documents and Issue #1, and reassess every release gate rather than promote a provider after one success.

| Gate | Current status | Required evidence before Phase 2 |
|---|---|---|
| Repeat availability | Pending; keyed pilot is one-day evidence | Actual multi-day results after provider holds; seven responses and a queued GDELT test do not establish stability |
| Financial NLP input | Availability demonstrated in 21 keyed samples; quality not established | Manually review retained/permitted text quality and validate the intended model task; presence/length is not model accuracy |
| Time semantics | Published fields present in all 21 keyed samples | Validate provider timestamp accuracy and required historical window; GDELT remains first-seen only |
| Public use and retention | GDELT dataset reuse basis strongest; alternatives unresolved | Field/plan-specific display, retention and derived-output basis; separately resolve publisher rights and training if relevant |
| History and quota sustainability | Endpoint access/headers observed; full account/history entitlement unresolved | Confirm plan-specific usable history and quota periods; do not infer daily allowance from aggregate or different-window headers |
| Operational readiness | Pilot only; 66 local tests and keyed dry run pass, hold honored | Exact-head push CI and safe request budget; software success does not establish provider reliability |

GO applies to continued bounded Phase 1 research only. No production provider selection, FinBERT, embeddings, crawler or live-data dashboard work is authorized by this recommendation. Synthetic-only UI prototyping is explicitly permitted.

## Execution audit checkpoint — 24 October 2026, 03:20 Sydney

The saved one-shot is **not yet due** (25 October 09:00 Sydney). No execution report or attempt marker was found; no HTTP status, latency, record count or new NLP text can be attributed to it. It was not classified as a cooldown skip. The audit made zero provider calls and preserved the existing schedule and cooldown. Only the original three GDELT responses remain measured evidence; optional-provider rows remain skipped for missing credentials. Every source gate above remains open, so Phase 2 is **NO-GO** and GDELT provisional.

Current main includes the user's authorized offline UI prototype (`8f7d730`), preserved during safe fast-forward. Its invented fixtures and manually assigned illustrative labels are not real provider coverage, model output or permission evidence. All 47 offline tests and the dry run pass; exact-head push CI is checked after publishing this audit. Keep the local computer awake/online and Codex running at the scheduled time through completion; it need not stay on continuously beforehand.
