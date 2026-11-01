# P3-A: bounded collection and independent local analysis

Verified 1 November 2026 Australia/Sydney, starting at local commit
`5df7ae1dee84f9089fb21daa5f6ba21809c8425b`. This is a partial P3-A closeout:
real local growth and FinBERT/browser acceptance succeeded; live SEC collection
requires the user's truthful contact identity. SEC mock coverage is not live
SEC ingestion evidence. No issuer/SEC industry-diversity target is claimed met.

## Actual local data

| Source | Before | Added distinct originals | Current | Permitted text |
|---|---:|---:|---:|---|
| ABS | 21 | 59 | 80 | Official release title/date; one previously reviewed body retained |
| NIST | 20 | 20 | 40 | Official RSS title/description; three reviewed bodies |
| RBA | 1 | 0 | 1 | Previously retained official release feed text |
| SEC | 0 | 0 | 0 | Adapter implemented; requests wait for actual User-Agent/contact |

SQLite contains **126 originals: 121 real official announcements and five
pre-existing authored development records**. There are zero media-news,
company-press-release or regulatory-disclosure originals in this accepted corpus.
The official announcements include science/macro topics; their count does not
establish 121 company financial-news items or comprehensive market coverage.

The real corpus grew from 42 to 121 distinct originals (+79). The numerical
100–300-record engineering target is reached for official announcements, while
corporate disclosure diversity and six-industry coverage remain incomplete.
Publication dates span 2025-12-22 through 2026-10-30. ABS date-only evidence is
never converted to an invented publication timestamp.

## Real requests and analysis

Three explicitly submitted collection actions returned 140 selected records:
79 new and 61 duplicate originals. They made **13 collector GETs, all HTTP 200**:
five NIST requests; three ABS current-index/body requests; five ABS archive
requests (robots, current index, three actually linked numbered index pages).
Minimum observed within-action request spacing was 1.175277 seconds. Bounds
were NIST ≤5 GETs, ABS current ≤3, ABS archive ≤5. There were no retries,
alternate-key attempts, SEC requests, Marketaux/Finnhub/NewsData requests or
external-LLM requests. Browser assets/health checks and official terms research
are separate from this collector ledger count.

The source-only actions retained data while the analysis-history count stayed
84. A separate source-free task then performed **121 actual local FinBERT
inferences**, with no mock/fallback and no model downloads. Model:
`ProsusAI/finbert`, revision
`0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`; preprocessing
`product-lead-span-2`. All outputs record genuine three-class probabilities,
input fingerprint, excerpt spans/coverage, task ID and reviewed source policy.
Current text bases: 79 titles, 38 summaries and four bodies. These are selected
text/excerpt sentiment results, not publication-wide or market-return claims.

History is append-only: **84 → 205 analyses**. During incremental acceptance an
index-only refresh exposed an existing-body downgrade. The repair retains a
previously reviewed body for unchanged title/publication metadata and stores a
separate current-revision pointer. Both text/analysis versions remain in history;
no result was removed to conceal the issue. The ABS P2 body/current result is
again selected. New body restrictions or a changed title/date prevent this reuse.

After that repair, an independent offline rerun completed with zero new
inferences. A CSRC classification pass added 121 classification records with
zero new inferences. The formal UI's **Analyze saved records offline** action
was also submitted and completed with zero downloads, new originals or
inferences. The current 121 originals each have a matching-text FinBERT result.

US-BUSINESS-1 has evidence-backed dictionary assignments for 14 originals and
107 Unclassified originals: five parent labels (technology, healthcare,
industrials, materials, consumer staples) and seven child labels. Multi-label
counts are not summed as distinct articles. Labels remain provisional lexical
topic assignments; for example chip “packaging” is an ambiguity requiring
semantic review, not validated packaging-industry coverage. The six-parent
target is not met. CSRC-JRT0020-2024 retains all 121 English-source originals
Unclassified under its current vocabulary; nothing is forced into S/91.

## User workflow and durability

Dashboard/Industries/Graph/Explorer → **Batch collection and offline analysis**:

1. Review the bounded sources, CIK watchlist, form types, HTTP/document caps,
   minimum spacing and local model. Save the batch settings. This supplies the
   default **Update & Analyze** scope; the existing review/confirmation remains.
2. **Collect and save only** saves permitted text without model inventory,
   resource checks, loading or inference. **Analyze saved records offline**
   selects local originals independently of incomplete API drafts and never
   invokes a news collector. Pinned FinBERT prioritizes uncached/new/changed rows
   beyond the first 300 records. Each explicit offline batch is bounded at 300.
3. Closing the browser does not terminate the separate OS-locked worker. Batch
   work interrupted by a worker restart returns to its durable checkpoints.
   Successful content/model caches are reused; failed or unknown HTTP/model
   dispatches are never automatically repeated. A model/resource block retains
   downloads and can be explicitly resumed. Legacy non-batch interruption rules
   remain unchanged.
4. JSONL/CSV import is local only. Required fields are `title`, `source`, `url`;
   optional fields are `id`, `summary`, `body`, `source_type`, `document_type`,
   `company`, `ticker`, `cik`, `publication_date`, `timestamp`. Supply an actual
   permission/legal basis, covered text fields/uses, retention, attribution and
   expiry where applicable. Narrow-field/expired/invalid imports are rejected;
   import does not confer publisher rights or become an API response. The parser
   bound is 5 MiB / 300 records; the existing Streamlit upload limit is 1 MiB.

Canonical publisher/URL identity preserves independent reporting. SEC accession
identity survives a corrected primary-document filename. Content revisions,
classification caches, per-version download/analysis state and current revision
pointers use the existing SQLite library. Covered SEC response data/event text
uses one content-addressed ignored checkpoint archive, with hashes and SQL
indexes; no article corpus, contact identity or credential is committed.
Generic source dispatches interrupted before their completed-source checkpoint
require review rather than speculative replay. SEC has finer per-URL checkpoints.

## SEC policy, configuration and remaining live gate

Reviewed official sources:

- [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
  describe submissions metadata and update behavior.
- [SEC RSS](https://www.sec.gov/about/rss-feeds) documents official feeds.
- [Website dissemination](https://www.sec.gov/about/privacy-information#dissemination)
  permits copying/distribution of covered SEC-hosted public information with
  attribution; seals, logos, trademarks and external websites are excluded.
- [Fair Access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
  requires a declared contact identity and moderated access. FinScope defaults
  to ≥1.5 seconds between SEC requests, not the published maximum request rate.

`SECSourcePolicy` records fields, local purposes, retention basis, attribution,
exclusions and version. The watchlist starts with six CIKs for Microsoft,
JPMorgan Chase, Caterpillar, Johnson & Johnson, Exxon Mobil and Amazon; returned
SEC identity/ticker/SIC metadata is retained as evidence, not silently guessed
from these display names. Users can configure up to 20 CIKs. The initial bounds
are 20 filings/company, 12 current-report documents shared across companies,
20 SEC requests/task and 120 selected records/source. No bulk ZIP, historic-file
pagination, exhibits, arbitrary URLs, external issuer sites or attachments.

8-K/6-K extract an identified operating-event narrative with document offsets
and coverage. Unsuitable or specially restricted bodies remain metadata only;
10-K/10-Q are never ordinary-news whole-document sentiment inputs. Issuer SIC
is separate from literal news-topic evidence. Fixed dictionaries, literal issuer
name evidence and article keywords provide limited entity/topic extraction;
this is not a high-recall general NER system.

**The user has not supplied an actual SEC contact identity.** No email was
invented or inferred from unrelated accounts. Enter a truthful contact-bearing
User-Agent in the advanced batch control and save, or set local
`FINSCOPE_SEC_USER_AGENT`. Then explicitly start a bounded SEC batch. First-live
SEC schema/access/body acceptance and issuer diversification remain pending.
HTTP 401/403/429 or an unknown dispatch stops subsequent automatic SEC access;
other licensed sources continue. No rotation or alternative route bypasses it.

Company IR press-release automation also needs individually reviewed source
rights; SEC policy never licenses arbitrary externally linked press articles.
Marketaux/Finnhub HTTP-200 receipts remain connection evidence only. NewsData
remains manually paused, with its subscription/multiple-key ambiguity unresolved.

ABS, NIST and retained RBA policy bases:
[ABS terms](https://www.abs.gov.au/website-privacy-copyright-and-disclaimer),
[NIST terms](https://www.nist.gov/copyrights-disclaimers),
[RBA terms](https://www.rba.gov.au/copyright/). Record-level restrictions always
win. Expired grants stop processing; this delivery does not automatically delete
historical/backup text or implement contract-specific legal retention workflows.

## Browser, offline validation and preservation

Formal localhost:8511 was updated while no task was running. Dashboard and
Explorer were checked on the real SQLite corpus, with publication-date/model
filters and source/analysis-state controls. Source-type counts are separate;
mixed selections use one explicitly labelled source-type chart denominator.
Original links, permitted text, two-level topic evidence, probabilities and
historical versions remain inspectable. Screenshots and exact task/HTTP/model
metadata are ignored local evidence under `reports/p3_*`.

Offline tests cover independent phases, unavailable models, cache reuse,
incremental revisions, current-body preservation, restart/unknown dispatch,
request/rate/URL bounds, publisher separation, policy expiry/revocation, imports,
issuer-versus-topic separation and counting consistency. The benchmark dry run
is isolated with `FINSCOPE_TESTING=1`; no provider budget is used by tests.

All 171 frozen files and the original 84 analysis rows were hash-checked
unchanged. Existing news/HTTP/model ledgers, permissions and credential-registry
row prefixes are unchanged. Only view/new-batch settings change existing product
preferences. SQLite backups precede additive schema changes. Main remains read
only; no public showcase/runtime change, frozen evaluation rerun or coursework
submission occurred. Final pushed local SHA and its exact CI run accompany the
delivery, separately from these live-data claims.
