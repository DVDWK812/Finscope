# P3-B global financial-media discovery

Verified 1 November 2026 Sydney, from local baseline
`bdbd3fd3402b3326a143d63595198ea9036ba139`. Main is read only. This is actual
feed discovery, **not newly licensed publisher-text or FinBERT acceptance**.

## Actual bounded checks

Exactly one GET to each user-specified feed; no redirects, retries, alternate
domains, article pages, remote images, API keys or external LLMs. Checks were
at 05:13:49 and 05:15:43–47 UTC on 1 November. Official-documentation research
and localhost assets/health checks are separate from these five collector GETs.

| Media | Actual outcome | Valid feed entries / distinct new links | Latest publication UTC | Available fields observed |
|---|---|---|---|---|
| Bloomberg | HTTP 200 reached parsing; initial client indexing failed | Not retained / unknown | Not retained | Complete field/count receipt unavailable |
| CNBC | HTTP 200; RSS | 30 / 30 | 2026-10-31 23:56:40 | title, link, description, pubDate, guid/id, type, sponsored |
| WSJ | HTTP 200; RSS | 60 / 59 (one duplicate URL) | 2026-11-01 00:00:00 | title, link, description, pubDate, guid, creator; content extension ignored |
| FT | HTTP 301; stopped | 0 inspected / 0 | Unknown | Redirect body not downloaded; Location not followed |
| Yahoo Finance | HTTP 200; RSS | 19 / 19 | 2026-11-01 04:41:00 | title, link, description, pubDate, guid |
| Reuters | No request; aggregator capability assessed offline | Unmeasured | Unknown | Account/source coverage not verified |

The Bloomberg check exposed an initial nine-column/ten-placeholder INSERT bug.
It was corrected, but the first process had already exited without saving its
response/counts. Its HTTP-200 audit is explicitly attributed to the executed
client control path, not a durable raw response or restored news. The original
request ID, incomplete checkpoint and hold remain. It was **not requested again**
to fill missing evidence. It is not counted as a complete RSS acceptance.
Received HTTP/schema metadata is now committed before indexing; a known received
metadata checkpoint can finish offline after an indexing crash. Unretained text
cannot be recovered, and missing/unknown checkpoints remain blocked.

**108 distinct discovery links** were persisted in separate SQLite media tables:
CNBC 30, WSJ 59, Yahoo 19. Offline replays of the actual obtained responses found
0 new / 30, 60 and 19 duplicates respectively. Those are post-response local
replays, **not second HTTP checks or a measured live polling interval**.
CNBC/WSJ/Yahoo latency was 488.93 / 868.54 / 936.63 ms; FT 1512.68 ms. No 429
occurred. ETag/Last-Modified and 304 behaviour are implemented and offline-tested;
no second live conditional request was spent in this round.

## Fields and rights

The durable default index contains source-specific URL identities, publication
and observation dates, content hashes, version fingerprints and HTTP receipts.
It contains **zero cached publisher titles/descriptions**, no raw RSS document,
no article bodies and no remote images. Unverified text is not classified,
embedded, sent externally or copied into the permanent news library. The panel
therefore distinguishes discovered links, licensed saved originals and actual
matching-text FinBERT results. Source-topic distributions use only licensed,
saved classifications; unknown discovery topics are not fabricated.

Reviewed primary references and limits:

- [Bloomberg terms](https://www.bloomberg.com/notices/tos/) and
  [licensed distribution](https://www.bloomberg.com/distribution): no automatic
  archive/NLP grant established for this application.
- [CNBC RSS information](https://www.cnbc.com/rss-feeds/): research-browser access
  was robots-denied; the user-specified actual RSS GET succeeded. These are
  different observations. Application storage/NLP terms remain unverified.
- [WSJ agreement](https://www.wsj.com/policy/subscriber-agreement): the public
  feed is reachable; actual archive/NLP entitlement was not established.
- [FT terms](https://help.ft.com/legal-privacy/terms-and-conditions/): research
  access was blocked. The specified feed's 301 was not bypassed or replaced.
- [Yahoo RSS clause](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html):
  unmodified attributed RSS display with original links is described; it does
  not establish this account/region's persistent archive or local NLP scope.
  The Australian terms URL could not be verified. No broader grant was assumed.
- [Marketaux documentation](https://www.marketaux.com/documentation): `domains`,
  `symbols`, `industries` and UTC `published_after` are official request filters.
  They do not prove a particular account receives Reuters or any named publisher.
- [LSEG developer news overview](https://developers.lseg.com/en/product/news/overview)
  and [licensed news data](https://www.lseg.com/en/data-catalogue/news): Reuters
  machine-readable products are a subscription/entitlement upgrade, not a free
  fallback. No account, subscription or request was created.

Each source has an initially empty field/use grant. A supplied actual basis,
covered title/summary fields, display/retention/local-NLP/polling purposes and
expiry are separate controls. No authorization is preselected or invented.
Finite caches require an enforceable expiry and remove covered text on the next
worker tick/read after expiry (there is no deletion service while the app is off);
expiry/revocation hides text immediately. The legacy append-only originals/history
cannot enforce finite-term deletion, so finite grants cannot be promoted there.
Only explicitly applicable `no_fixed_expiry` storage/display/NLP grants can enter
the normal SQLite originals and existing source-free FinBERT queue. Revoked NLP
scope overrides a previously promoted record. Actual licensed media originals,
new media classifications and new media FinBERT inferences this round are **0**.

Reuters wire attribution uses only an explicit feed credit, kept separately from
the feed provider and publication domain; it never grants direct Reuters access.
No Reuters credit was retained in the initial live index; this is reported as
not captured, not reconstructed from hashes. Future credited records preserve it.
A Reuters-labelled syndicated article on another domain does not pass an exact
`reuters.com` publication-domain whitelist.

## Incremental operation and UI

Dashboard/Industries/Graph/News Explorer retain their existing shell and add one
collapsed **Global media monitor**. It shows source-specific counts, last success,
publication freshness, latency, failures/holds, duplicate/change counts, current
licensed NLP counts, original links and saved industry assignments. Reuters via
Marketaux is explicitly untested, not labelled connected. The panel and refresh
perform no collection or inference. Advanced source permissions remain empty.

Opt-in polling uses the existing OS-locked local worker, 5–15-minute intervals,
configurable per-source UTC-day request caps (default 12), conditional headers,
atomic reservations, source-local watermarks and independent failure isolation.
Late arrivals still deduplicate by publisher/URL rather than being dropped solely
because they precede the watermark. Hash-only version history records revisions.
429 uses Retry-After plus conservative exponential backoff; other HTTP/schema
failures, redirects and unknown dispatches stop that source for review. Restart
does not discard reservations, caps, timing or holds. There is no unattended
24×7/SLA claim. **All five actual source schedules remain disabled**.

Licensed scheduled discoveries can use the same save/classify/local-FinBERT
worker with exact-text/model caching. No model is loaded to monitor or save.
Model failure does not remove discovery/original records. Conditional/recovery,
licence expiry and scheduling are authored offline regression evidence, separate
from the real five checks above.

Marketaux's six-domain whitelist was validated and saved through formal 8511 UI
without a request. The local dispatch uses the saved structured media scope in
place of the broad keyword; symbols/industries are optional entity filters,
not news-topic proof. A blank explicit publication bound uses the existing UTC
lookback. All existing primary-key, quota, pause, reservation and cooldown checks
are retained. Historical benchmark keyword experiments remain reproducible.
Marketaux/Finnhub/NewsData and external-LLM requests this round: **zero**.

## Preservation and verification

The formal instance was restarted only with no active tasks to load Python source
(file watching is intentionally disabled). SQLite discovery state survived.
Browser checks use that real 8511 database and inspect the actual monitoring
table, original links, zero NLP counts, empty permissions and offline Marketaux
request construction. Screenshots and per-request IDs remain ignored local
`reports/p3b_*` evidence, not a committed publisher dataset.

All prior 266 originals, 232 analysis-history rows, 13 API reservations, 46 prior
collector receipts, model/permission histories and previous content/classification
cache rows are hash-identical to the P3-B starting snapshot. The 171 frozen files
are unchanged. A consistent pre-P3-B SQLite backup and additive media-schema
backup were retained. Only local is committed/pushed; main is read only.

Full offline test count, dry run, final local SHA and exact-commit CI accompany the
delivery. Remaining gates: publisher-specific applicable archiving/NLP grants,
a newly authorized Bloomberg check if complete feed metrics are needed, approval
to inspect FT's redirect destination, and a confirmed Marketaux account request
budget before measuring actual Reuters coverage. This round does not claim a
real mainstream-media FinBERT acceptance or six successfully licensed sources.
