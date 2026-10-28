# Optional RBA HTML index collection prototype

This is a separate manually activated **non-API, non-RSS** fallback for the RBA
media-release index at https://www.rba.gov.au/media-releases/. It is not an
independent news publisher or a replacement for company/sector coverage.

## Usage

```powershell
python -m finscope.html_collector --dry-run
python -m finscope.html_collector --collect --limit 3
```

Default and `--dry-run` perform zero requests and write no files. `--collect`
makes at most one https://www.rba.gov.au/robots.txt GET and one fixed index
GET, subject to robots allowance. There are no article-page visits, API calls,
RSS requests, pagination, redirects, retries, schedulers, or new dependencies.
Manual limits: 1–10 new rows/run, maximum 1 MB/request, 5s connection/10s read
timeouts, checked 20s elapsed bound on chunks (not a hard process deadline).
429/403, redirects, Retry-After, robots denial, unexpected content type and
HTML schema all fail closed; do not retry blocked reads without review.
Each actual dispatch records its endpoint, UTC query time, HTTP status (null if
unobserved), received bytes and total attempt count, including failed runs.

The source's https://www.rba.gov.au/copyright/ (rechecked 29 October 2026 Sydney) covers RBA-authored material
generally under CC BY 4.0, subject to attribution, exclusions and third-party
rights. No endorsement is implied. Robots allowance does not grant a licence.
Only attributed release-list titles and URLs are retained, no article bodies,
images, logos, financial data tables or third-party content. Source rights
and quality still require record-level review before display or model use.

Records use `api_sources.Article`, `provider=rba_html`, source RBA, title
and exact original URL. Summary and exact UTC timestamp remain empty because
the index does not supply reliable values. The observed *day-level* release
date is saved only in sidecar metadata with `timestamp_precision=date_only`,
along with attribution, original date text, index URL, query UTC and terms
links. Invalid, ambiguous or wrong-year dates remain unknown; missing dates
cannot leak across release rows. Do not manufacture a midnight publication timestamp.

Records and run summaries are in ignored `reports/html/`, up to 100 rows /
5 MB, with exclusive local lock, atomic write and classified error outcomes.
HTML duplicate URLs are removed within and across runs. Existing RBA RSS URLs
are read-only checked to avoid duplicating them in HTML storage; **the reverse
direction is not implemented**. Do not run RSS and HTML writers simultaneously.
This is exact-URL matching, not article/event semantic deduplication.

## Python 3.11 CI repair — 29 October 2026 Sydney

Starting commit: `ecd2646`. The [original failed run](https://github.com/DVDWK812/Finscope/actions/runs/40714872072)
executed 159 tests with five HTML errors. Python 3.11.17's `HTMLParser.close()`
joined its internal `_pending` buffer, which the collector had overwritten with
a release tuple containing a list. Custom state is now `_pending_release`.
An incremental-feed/close regression exercises incomplete tags/entities and
checks inherited buffer integrity when the runtime supplies it. Existing tests
were not removed, skipped or weakened. Text chunks now concatenate without
injecting spaces into words; release-row boundaries prevent date leakage, and
multiple nearby dates remain unknown.

All **176 tests pass locally on Python 3.12.3**: the original nine HTML tests plus
17 new HTML regressions, alongside existing application/model/API tests. Benchmark,
RSS and HTML dry runs pass without provider requests. Both Python 3.11 CI jobs
run the full suite and previews, including the newly added HTML preview; their
exact-commit results supply actual 3.11 compatibility evidence separately from
local 3.12 results.

Synthetic regressions cover parser/nested/malformed markup, calendar validity
and date precision, exact dedup/limits, URL validation, robots denial/invalid
responses, HTTP errors/redirects/Retry-After/content types, timeout/byte/deadline
settings, transport failures, default/dry-run no-op behavior, request auditing,
RSS exclusion across repeated runs, row/byte capacity, locks/corrupt stores and
data preservation on parse/HTTP/atomic-write failures. They use mocked HTTP and
temporary stores, not live news or trained models.

## Actual bounded collection — 29 October 2026 Sydney

Exactly **one** explicit local invocation of
`python -m finscope.html_collector --collect --limit 3` began at
**28 October 2026 15:36:29.904067 UTC / 29 October 02:36:29.904067 Sydney**.
The refreshed robots policy allowed the fixed index. Actual client requests:

| Endpoint | Query UTC, 28 October | HTTP | Response bytes |
|---|---|---|---|
| `https://www.rba.gov.au/robots.txt` | 15:36:29.905071 | 200 | 476 |
| `https://www.rba.gov.au/media-releases/` | 15:36:30.900749 | 200 | 75,597 |

Completed **15:36:31.457810 UTC**, exit 0, `ok/records`: 91 recognized release
links, one exact URL excluded by the existing RSS record, zero invalid recognized
entries, 90 eligible unseen URLs, **three new stored records** under limit 3.
These counters are not coverage estimates or 90 fetched articles. Article pages,
RSS/feed requests, other news-provider requests and retries: **zero**. Source-term
review was a separate public documentation read.

Read-only checks confirmed three unique original RBA release URLs, no RSS overlap,
the unified Article schema, source/year attribution, original date text and
separate collection time. Dates: **1 October, 29 September and 23 September 2026**,
all `date_only`; summaries and exact UTC publication timestamps remain blank.
These historical dates do not establish freshness or date accuracy independently
of the index; no linked page was fetched for stronger evidence. Existing RSS and
provider cooldown bytes remained unchanged; no HTML store existed before the run.

Ignored local evidence: `reports/html_fix_20261029_attempt.json` and
`reports/html/run_20261028T153629904067Z.json`; stored records remain in
`reports/html/articles.json`. No real titles, datasets or credentials enter Git.

## Remaining limitations

The synthetic offline tests validate parsing, provenance, day-only timestamp
handling, disallowed links, bounded robots/index reads, local persistence and
RSS URL exclusion. The live evidence above is separate from these mocks. The index has no reliable
summary or exact time; historical titles, dates and URL validity are not independently
verified against article pages. Coverage, representativeness and public-use rights
remain review gates. Fixtures are not representative news data.

No Streamlit, FinBERT, MiniLM, benchmark or approval-gate changes; source
integration remains NO-GO. Freeze evaluation labels independently. Follow the
31 October internal delivery priority over further source expansion.

No Moodle access or coursework submission. Codex assisted with the repair, tests and evidence.
