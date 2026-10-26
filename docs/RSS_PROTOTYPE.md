# Optional local RSS collection prototype

Scope authorized 27 October 2026 Sydney. This is a separate manual experiment;
evaluation, deployment and final delivery take priority. There is no scheduler,
UI ingestion, model call, article-page fetch or provider benchmark registration.
Existing FinBERT, embeddings, approved-input persistence and UI behavior are unchanged.

## Source and permitted local reuse

The RBA [official RSS directory](https://www.rba.gov.au/rss/) explicitly offers a
[Media Releases feed](https://www.rba.gov.au/rss/rss-cb-media-releases.xml).
Reviewed 27 October Sydney: the [copyright notice](https://www.rba.gov.au/copyright/)
sections 2–3 permits reuse of RBA-authored material under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with required RBA/year
attribution and no implied endorsement. This supports the intended small local
collection of RBA-authored feed titles/descriptions, preserving their source links.
It does not license every item or linked page indiscriminately. Third-party
material and expressly excluded material require their own permissions; cash-rate
and financial-data material have special terms (sections 4–5). Those sections also
permit attributed reuse subject to their conditions, third-party rights and no
endorsement/misrepresentation. No logo, image, multimedia or linked body is collected.
The project MIT license does not replace source terms.

The [robots policy](https://www.rba.gov.au/robots.txt), checked during each manual
run, allowed the fixed `/rss/` endpoint during the smoke reads. A robots allowance
is an access check, not a copyright grant. Terms and robots can change: recheck
terms before later collection or any new use. Public display, downstream model
processing and release remain separate review decisions. Do not copy this sample
into Streamlit's approved-input form or blind evaluation packet as a shortcut.

## Operation and storage

```powershell
python -m finscope.rss_collector             # preview; no network or file writes
python -m finscope.rss_collector --dry-run
python -m finscope.rss_collector --collect --limit 3
```

No credentials or additional dependency is required. Explicit collection checks
robots once and makes at most one GET to the fixed official feed, with no redirects,
automatic retries, pagination or article visits. Limits: 1–10 new records (default
3), one MB decoded response per GET, 5-second connect/10-second read timeout and a
20-second elapsed check between chunks. A blocked read can outlast the elapsed
check by its read timeout; this is not a strict 20-second process deadline.
HTTP errors, redirects, Retry-After, robots denial, unsafe/malformed XML and unexpected
schemas stop collection. No automatic retry after failure; review the saved category
and any server restrictions before another manual invocation. No Yahoo crawling,
GDELT retry, Marketaux round, NewsData request or account action occurs.

The RSS 1.0/RDF and RSS 2.0 parser reuses `finscope.api_sources.Article` directly:
provider `rba_rss`, title, unchanged original URL, source `Reserve Bank of Australia`,
available description, UTC publication timestamp and `timestamp_kind=published`.
Missing/invalid/zone-free publication times remain blank, never replaced by the
collection time. The sidecar retains original date text, per-record RBA/year
attribution, feed URL, source element when present, terms/license links and separate
collection UTC. Whitespace around fields is stripped; XML escapes are decoded.
Descriptions can contain feed-provided HTML, retained as data, never rendered.
Full article content and RSS extensions are not extracted.

Only official RBA media-release links are accepted. Exact stripped URLs are
deduplicated before title/date/summary processing, both within the response and
against the local store. First occurrence wins; distinct query strings/fragments
are retained. This is not canonical-URL, updated-release or semantic event matching.
No article URLs are fetched to validate them.

Ignored `reports/rss/articles.json` holds at most 100 records/five MB, separate from the
public SQLite store and app fixtures. After capacity is reached, collection skips
without network. A local exclusive lock prevents overlapping CLI writers; review
a stale lock after a crash rather than bypassing it. Atomic replacement protects
the existing store; malformed prior stores stop without collection. Unique local
`run_*.json` files retain UTC/endpoint/limit/counts and `ok`, `skipped` or `failed`
outcomes, without copied titles or summaries. No retention/deletion scheduler is
provided. Run serially on this checkout and keep all captured material out of Git.

## Smoke evidence and limitations

On **27 October Sydney / 26 October UTC**, two manually bounded live reads were
performed. Each made one robots GET and one feed GET; no article pages or other
news providers were requested. The first at **17:11:10.838 UTC** received XML but
failed safely with `unexpected_feed_schema`: the initial parser assumed RSS 2.0.
The second diagnostic read at **17:11:36.160 UTC** captured a **2,107-byte** RSS 1.0/RDF
response, both HTTP statuses **200**, and again recorded the initial schema failure.
These are explicit manual attempts, not an automatic transport retry.

After adding RDF/Dublin Core support, the captured response was replayed **offline**
through collection/persistence at **17:12:01 UTC**: one raw/eligible/stored record,
zero exact duplicates/invalid records, publication time and summary present. Its
publication date was **14 October 2026**: this is not evidence of daily freshness,
broad sector/company coverage, timestamp correctness or summary quality. There was
no third live request and no model inference. The replay report/store explicitly
identify offline replay and reference the transport evidence; replay processing
time must not be described as a new feed query. Captured XML, transport metadata,
two failed reports, replay report and one stored record remain ignored locally.

Offline tests use authored synthetic text only. They cover RSS 1/2 normalization,
source/time preservation, exact deduplication including prior runs, malformed and
hostile XML, invalid/foreign links, missing fields, robots refusal, HTTP/transport
stops, byte/timeout settings, default no-op behavior, locking/corrupt-store handling
and a two-run bounded local collection smoke with fake HTTP. These are distinct
from the real feed reads and from trained-model evidence. CI runs tests and the
no-network preview only. Rights exclusions, freshness, relevance, summary usefulness,
timestamp meaning and representativeness require review before any public connection.
