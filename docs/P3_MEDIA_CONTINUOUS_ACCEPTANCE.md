# P3-B.1: bounded media validation and real scheduled polling

Verified 1 November 2026 Sydney, local baseline
`57738a6dc07767d60bdd880eab1bbec76217c72b`. Main remains read only.
Real transport, source permission, RAM display, persistent metadata and NLP are
reported separately. FinBERT and ABS/NIST/SEC collection were not changed/run.

## Actual source evidence

| Feed | Latest actual HTTP | Valid/current response links | Stored distinct links | Publication domain | Latest publication UTC |
|---|---|---:|---:|---|---|
| Bloomberg | New200 | 18 | 18 | www.bloomberg.com | 2026-11-01 05:14:49 |
| FT | New301 →200 | 10 | 10 | www.ft.com | 2026-11-01 05:00:18 |
| CNBC | Prior200 | 30 | 30 | www.cnbc.com | 2026-10-31 23:56:40 |
| WSJ | Prior200 | 60 (one duplicate URL) | 59 | www.wsj.com | 2026-11-01 00:00:00 |
| Yahoo Finance | Two new200s | 18 each | 19 historical | 15 www.fool.com /4 finance.yahoo.com in historical index | 2026-11-01 04:41:00 |
| Reuters via Marketaux | Pending a new confirmed account budget | Unmeasured |0 | Unverified | Unknown |

The source index grew **108 →136**, adding18 Bloomberg and10 FT links. All108
previous source/identity/URL triples remain. This is a discovery index, not136
saved/licensed media articles. No source was substituted by ABS/NIST/SEC expansion.

The user explicitly approved Bloomberg ≤1 GET and FT ≤3 GETs including at most
two reviewed redirects. Actual new diagnostic requests:

- Bloomberg: one GET at06:38:20.254176 UTC; HTTP200,14859 bytes,18 valid RSS entries.
  ETag observed; safe headers, hash, field names and publication times persisted
  before/with indexing. The previous nine-column/ten-placeholder bug is fixed.
  The original `0fd74cb437084ba8b120a5f32de0e7a3` receipt, missing metrics,
  unresolved source checkpoint and prior hold remain unchanged; no news was
  reconstructed from that earlier receipt.
- FT: initial GET at06:38:20.577708 UTC returned301 with literal
  `Location: /rss/home/international`; this header was not retained in the old
  run and was not pretended to be recoverable. The second GET at06:38:23.389883
  used `https://www.ft.com/rss/home/international`, returned200/7993 bytes/10
  entries and an ETag. Only **two** of the allowed three GETs were used. The
  unused allowance was not repurposed into another conditional/news request.

The new diagnostic ledger reserves every hop before dispatch. Only HTTPS,
exact `www.ft.com`/`ft.com`, port443/default and reviewed `/rss/home` or
`/rss/home/international` routes are allowed. External hosts, login/content
routes, credentials, queries/fragments, downgrade, cycles and extra hops stop.
No automatic Requests redirect, alternate Bloomberg domain, article page,
paywall, cookie/login flow or unknown-request retry is used. Duplicate invocation
of the same diagnostic authorization reuses its terminal result, not its budget.

## Actual two-round polling, not an offline replay

The user confirmed Yahoo RSS applicability for personal local use, no conflicting
special terms, and **two additional GETs at five-minute intervals with RAM-only
supplied-feed display**. The starting UTC-day count was1, so the saved total cap
was3; it was not confused with three additional requests. Other media stayed off.

| Actual round | Request start UTC | HTTP | Valid entries | New | Duplicate observations | Revisions |
|---|---|---:|---:|---:|---:|---:|
|1|2026-11-01 06:56:08.670114|200|18|0|18|0|
|2|2026-11-01 07:01:08.923951|200|18|0|18|0|

Measured spacing **300.253837 seconds**. These were two new worker-dispatched
HTTP calls, not replayed XML, mock responses or refresh-triggered checks. The
feed did not deliver a newer article timestamp, so its watermark correctly stayed
04:41:00 rather than being replaced by collection time. The two response-body
hashes differ, while the selected article content fingerprints remain unchanged.

The actual Yahoo endpoint supplied **neither ETag nor Last-Modified** in either
response, and returned no304. Conditional-header and304 branches are tested
offline; this run does **not** claim an actual Yahoo304 or validator support.
Bloomberg and FT did provide real ETags during their approved diagnostics, but
no extra request was spent to force a304. Actual429 behaviour was not induced.

After round1, the verified worker alone was stopped and restarted while the
formal8511 UI remained running. SQL next-due, budget, validator fields and request
count were identical before/after restart; no immediate replay occurred. The UI
kept only an approved Windows RAM reader mapping, permitting the new worker to
reuse the display representation. Round2's receipt confirms that representation
was available. This verifies **worker restart** recovery; a complete application
exit releases RAM-only text and cannot restore it from SQLite.

At round2 completion the panel showed **3/3 GETs used**, zero remaining rounds,
and “Budget exhausted; stopped until explicitly renewed.” The worker remains
running but cannot dispatch a third new Yahoo call, or renew the attestation at
UTC midnight. Old Bloomberg/FT guards did not prevent the independently approved
Yahoo source from being polled. No deliberate real failure request was added.

## Rights, permitted presentation and persistence

| Source | RSS title / supplied summary display | Short-term disk cache | Persistent publisher text | Local NLP |
|---|---|---|---|---|
| Yahoo | Recorded RSS reader scope and user-confirmed applicability; unmodified, attributed, links retained; RAM only | Not granted | Not granted | Not granted |
| Bloomberg | Applicable display scope unverified; metadata shown | Not established | Not established | Not established |
| FT | Applicable display scope unverified; metadata shown | Not established | Not established | Not established |
| CNBC | Applicable display scope unverified; metadata shown | Not established | Not established | Not established |
| WSJ | Applicable display scope unverified; metadata shown | Not established | Not established | Not established |
| Reuters / Marketaux | New query pending; no retained text or NLP grant | Not established | Not established | Not established |

The [official Yahoo RSS clause](https://legal.yahoo.com/ca/en/yahoo/terms/otos/)
describes supplied-feed display with attribution and links; country/entity and
product-specific conditions still apply. The user confirmed applicability for
this personal local reader. It is not an archive, publisher-body or NLP licence.
The recorded scope covers Yahoo-supplied RSS fields on the reviewed Yahoo/Fool
publication domains; it does not license arbitrary text on those websites or
unreviewed future publisher domains. No per-article consent repetition is needed
inside that applicable source scope. Other sources' read-access success alone
does not establish their text rights. Primary references and research-browser
access limitations are retained in [the source review](P3_MEDIA_ACCEPTANCE.md).

Formal8511 browser verification confirmed actual approved title/summary columns,
feed provider, original publishing domain, publication times, original-link
action and exhausted-budget status. Approved display fields travel only through
bounded checksummed named Windows RAM mappings and Streamlit/browser memory.
They are not copied into SQLite, local archives, exports, model jobs or logs.
Non-Windows builds have same-process RAM preview only, without silently creating
a disk cache. Full restart without an approved cached representation requests a
full feed on the next separately budgeted action; it cannot invent text from304.

The delivery screenshot contains **only counts/metadata**, not RSS headline or
summary text. SQLite publisher-title/summary cache rows remain **0**. Original
news count remains266, analysis history232; new media original saves and NLP
inferences are both **0**. No external LLM or publisher-page request occurred.

## Budget correction and remaining source gate

Intervals are configurable from5 to1440 minutes in the existing compact source
form. Full-day mode requires `ceil(1440 / interval)` GETs/source/day:15 minutes
requires96,5 requires288;12/day can cover a full day only at120-minute spacing.
Bounded-window mode displays its shorter span, remaining rounds constrained by
UTC midnight, budget expiry and explicit stopped/exhausted state. A current
UTC-day date and actual budget confirmation are required before scheduling;
neither configuration nor refresh creates an HTTP request. This is local-worker
scheduling, not a24×7 service/SLA. Redirect diagnostics count individual HTTP
hops separately from ordinary one-GET polling of a verified resolved feed URL.

Reuters's one-shot preparation uses the current primary Marketaux key only,
`domains=reuters.com`, no broad search keyword, ≤3 previews, and existing holds,
spacing and ledgers. Old31 October budgets are not valid for1 November. No
Reuters request has been made without a new account-budget confirmation. Its
audit stores only API source, URL, publication domain/time and outcome; it does
not treat syndicated URLs or a textual wire credit as direct Reuters licensing
or independent proof of editorial originality. No repeat or key fallback occurs.

Consistent pre-P3-B.1 backups, original receipt bytes, old index identities,
266 originals,232 analyses and all171 frozen files are preserved. Full offline
regression:631 tests, one platform skip; isolated benchmark dry run passed. Exact
final SHA and its CI are reported at delivery. Remaining gates are the newly
confirmed Reuters request budget, source-specific text/archive/NLP grants, and
actual validator/304 support where a provider does not emit them.
