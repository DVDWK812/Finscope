# P3-A: bounded collection and independent local analysis

Verified 1 November 2026 Australia/Sydney. Baseline:
`5df7ae1dee84f9089fb21daa5f6ba21809c8425b`. Real official-source collection,
local persistence, independent FinBERT and formal 8511 drill-down were executed.
The first implementation commit was `f789488c504d82ee496fb1e72aaff2ada6f688c0`
with all three CI jobs passing. After the user supplied an actual SEC contact,
additional live SEC acceptance exposed and repaired two client boundaries; the
final delivery SHA/CI includes these repairs and the results below.

## Actual data and separate denominators

| Source | Before | Added distinct originals | Current | Covered text |
|---|---:|---:|---:|---|
| ABS | 21 | 59 | 80 | Official title/date; one retained reviewed body |
| NIST | 20 | 20 | 40 | RSS title/description; three reviewed bodies |
| RBA | 1 | 0 | 1 | Previously retained official release feed text |
| SEC official press RSS | 0 | 20 | 20 | Official title and supplied description; no linked pages |
| SEC EDGAR | 0 | 120 | 120 | Structured filing metadata; seven eligible event excerpts |

**266 originals: 261 real records plus five pre-existing authored development
records.** Real records comprise 141 government/official announcements and 120
regulatory disclosures, with zero media-news/company-IR-release originals.
The corpus grew from 42 to 261 real originals (+219), within the 100–300-record
target. Scientific/macro announcements and corporate filings are not presented
as one media-news coverage metric.

Six issuers each contribute 20 filings: Microsoft, JPMorgan Chase, Caterpillar,
Johnson & Johnson, Exxon Mobil and Amazon. CIK, ticker, issuer name and SIC come
from the returned SEC metadata. Issuer SIC is retained separately and never used
as the sole news-topic evidence. The generated issuer/form/date display title
is excluded from SEC topic matching. Publication, calendar filing date, SEC
acceptance/disclosure time and collection time have separate fields/precision;
a filing day is not an invented publication timestamp.

## Real requests, scope and corrections

The initial ABS/NIST stages selected 140 records: 79 new and 61 duplicates,
using 13 GETs (five NIST; three ABS current; five ABS archive), all HTTP 200.
The archive follows only the next three actually linked numbered ABS index
pages, with no bodies. Minimum observed public-source spacing: 1.175277 seconds.

After the user explicitly provided an actual SEC contact identity, a two-GET
pilot saved five Microsoft filings and one event excerpt. FinBERT genuinely
analyzed that excerpt; the other four records remained not applicable. A
six-issuer expansion was bounded at 18 further GETs / 12 new document requests.
It stopped after four GETs when the older 10,000-row guard rejected JPMorgan's
large, HTTP-200 recent-history response. The request receipt was preserved;
no article was fabricated from it. A corrected continuation used at most the
remaining 14 GETs, including one explicit re-retrieval of that known HTTP-200
schema failure. It did not reissue unknown requests, clear a ledger or use a
new key. All six issuers now have 20 persisted originals. One additional bounded
GET selected 20 SEC official press-feed records without fetching linked pages.

**Total new collector HTTP: 34 GETs, all HTTP 200 (13 public-source + 21 SEC).**
SEC spacing is at least 1.5 seconds and its ledger shares timing across tasks.
Six SEC HTTP-200 responses were rejected by the client: the initial JPMorgan
schema failure and five current-report bodies without a suitable operating-event
excerpt. These are distinct from HTTP/network failures. The latter records keep
permitted filing metadata and no fabricated sentiment. Completed primary-document
bodies are reused; metadata refreshes are explicit bounded operations. Failed
and unknown request checkpoints never automatically resend.

The large-history parser is still bounded at 8 MiB / 100,000 column rows, and
selects only the configured 20 relevant filings/company. One failed issuer no
longer prevents the remaining watchlist from being processed. Rejected-response
hashes and safe schema diagnostics are retained without copying unselected body
text or request headers. The actual contact identity is local only, absent from
Git, job snapshots, reports and screenshots.

Marketaux/Finnhub/NewsData requests, alternate-key attempts and external-LLM calls
were **zero**. Their ledgers/holds remain intact; NewsData is still manually
paused. Existing API HTTP-200 receipts remain separate connection evidence.
Browser assets/health checks and official-documentation research are separate
from these 34 collector GETs.

## Actual analysis and evidence

The store-only actions left prior inference history untouched. Source-free jobs
performed **148 actual local FinBERT inferences** during the round, bringing
analysis history from **84 to 232**. The current 261-record corpus has **148
matching-text FinBERT results and 113 not-applicable filing metadata records**:
141 official announcements plus seven operating-event excerpts are analyzable.
No missing/unsuitable disclosure is forced into Neutral.

Model: `ProsusAI/finbert`, revision
`0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`, preprocessing
`product-lead-span-2`. Genuine probabilities, input fingerprints, selected spans,
coverage, model/policy/task versions and prior results are retained. There is no
mock output, automatic weight download or external fallback. Long 10-K/10-Q
records remain metadata only; current-report results describe their selected
operating-event excerpt, never whole-filing sentiment.

The first index refresh exposed an existing-body downgrade. The repair retains
a previously reviewed body for unchanged title/filing/publication metadata and
stores a separate current-version pointer. Every old text/result version remains;
no result was deleted to conceal the issue. Changed titles/dates or new body
restrictions prevent reuse. The ABS P2 body/result remains current.

Repeated source-free work reuses current text/model caches with zero new
inferences or HTTP. Both taxonomies are run independently of source collection.
US-BUSINESS-1 currently has 17 classified originals and 244 Unclassified, spanning
six parent and nine child dictionary labels. Multi-label memberships are not
summed as distinct articles. These are provisional lexical topic assignments;
chip "packaging" is a known semantic ambiguity, not validated materials-industry
coverage. CSRC-JRT0020-2024 retains these English-source records Unclassified
under the current vocabulary, without forcing S/91. Fixed dictionaries, literal
issuer-name evidence and article keywords are limited entity/topic extraction,
not a high-recall general NER system.

## Independent user workflow and durability

In Dashboard/Industries/Graph/Explorer, expand **Batch collection and offline
analysis**. Save a reviewed, bounded source/model/watchlist scope; this supplies
the default **Update & Analyze** action and its existing review/confirmation.
**Collect and save only** performs no model inventory, resource checks, loading
or inference. **Analyze saved records offline** reads local originals independently
of incomplete API drafts and never invokes a news collector. Pinned FinBERT
prioritizes uncached/new/changed rows beyond the first 300; each explicit offline
batch is bounded at 300 records.

Closing the browser does not terminate the OS-locked worker. Interrupted batch
work returns to durable checkpoints on worker restart. Successful caches are
reused; failed/unknown HTTP/model dispatches are never automatically repeated.
Model/resource blocks retain downloaded records for explicit offline continuation.
Generic source interruption before its completed-source checkpoint requires
review rather than speculative replay; SEC has finer per-URL/company checkpoints.
Legacy interruption rules remain unchanged.

JSONL/CSV import is local only. Required: `title`, `source`, `url`; optional:
`id`, `summary`, `body`, `source_type`, `document_type`, `company`, `ticker`, `cik`,
`publication_date`, `timestamp`. Supply actual licence/legal evidence, covered
fields/uses, retention, attribution and expiry where applicable. Narrow-field,
expired or invalid imports fail closed. Imported text is not an API response.
The parser cap is 5 MiB / 300 records; the existing Streamlit upload cap is 1 MiB.
No production import or authored text is counted as real-source acceptance.

Canonical publisher/URL identities keep independent reporting separate. SEC
accession identity survives corrected primary filenames. Content revisions,
current pointers, classification/model caches and per-version download/analysis
states use SQLite. Covered SEC checkpoint data uses a content-addressed ignored
archive with hashes and SQL references; no news corpus is committed.

## Policies and browser/verification evidence

`SECSourcePolicy` records fields, local purposes, retention basis, attribution,
exclusions and version. It covers reviewed SEC-hosted public factual text, not
external issuer/publisher websites, exhibits, copyrighted/specially restricted
material, seals, logos or media. Official policy and endpoint references:
[APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[RSS](https://www.sec.gov/about/rss-feeds),
[dissemination](https://www.sec.gov/about/privacy-information#dissemination),
[Fair Access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
Defaults use conservative 1.5-second spacing rather than the published maximum.
HTTP 401/403/429 or unknown dispatch stops subsequent automatic SEC access;
other licensed sources continue. No account/key rotation bypasses a hold.

Other reviewed bases:
[ABS](https://www.abs.gov.au/website-privacy-copyright-and-disclaimer),
[NIST](https://www.nist.gov/copyrights-disclaimers),
[RBA](https://www.rba.gov.au/copyright/). Record restrictions always win. Expired
grants stop processing; automatic deletion of historical/backup text and
contract-specific retention enforcement remain outside this delivery. Company
IR automation needs its own source review; SEC policy never licenses arbitrary
externally linked press articles.

Formal localhost:8511 uses the real SQLite corpus. Dashboard/Explorer drill-down
checks include a newly collected NIST release and an actual SEC 8-K, selected
model probabilities/revision, permitted text, source/filing/acceptance evidence,
issuer-versus-topic distinction and original URLs. Source types/status filters
keep denominators separate; mixed libraries use an explicitly selected source-type
chart cohort. Exact screenshots, task IDs, HTTP/model metadata and preservation
hashes are ignored local `reports/p3_*` evidence.

Offline tests cover independent phases, unavailable models, cache reuse,
revisions/current-body preservation, restart/unknown dispatch, request/rate/URL
bounds, large SEC histories, per-issuer isolation, generated-title exclusion,
policy expiry/revocation, imports and counting consistency. The benchmark dry run
is isolated with `FINSCOPE_TESTING=1` and spends no provider budget. Final test
count, exact pushed SHA and its CI accompany the delivery.

All 171 frozen files and original 84 analysis rows are hash-checked unchanged.
Original news/request/model/permission/credential-registry row prefixes are
unchanged. Existing product preferences change only for views; new batch/contact
settings are separate. Additive schema changes have SQLite backups. Main remains
read only; no showcase change, frozen evaluation rerun or coursework submission.
