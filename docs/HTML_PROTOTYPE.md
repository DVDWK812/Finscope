# Optional RBA HTML index collection prototype

This is a separate manually activated **non-API, non-RSS** fallback for the RBA
media-release index at https://www.rba.gov.au/media-releases/. It is not an
independent news publisher or a replacement for company/sector coverage.

## Usage

\`\`\`powershell
python -m finscope.html_collector --dry-run
python -m finscope.html_collector --collect --limit 3
\`\`\`

Default and \`--dry-run\` perform zero requests and write no files. \`--collect\`
makes at most one https://www.rba.gov.au/robots.txt GET and one fixed index
GET, subject to robots allowance. There are no article-page visits, API calls,
RSS requests, pagination, redirects, retries, schedulers, or new dependencies.
Manual limits: 1–10 new rows/run, maximum 1 MB/request, 5s connection/10s read
timeouts, checked 20s elapsed bound on chunks (not a hard process deadline).
429/403, redirects, Retry-After, robots denial, unexpected content type and
HTML schema all fail closed; do not retry blocked reads without review.

The source's https://www.rba.gov.au/copyright/ covers RBA-authored material
generally under CC BY 4.0, subject to attribution, exclusions and third-party
rights. No endorsement is implied. Robots allowance does not grant a licence.
Only attributed release-list titles and URLs are retained, no article bodies,
images, logos, financial data tables or third-party content. Source rights
and quality still require record-level review before display or model use.

Records use \`api_sources.Article\`, \`provider=rba_html\`, source RBA, title
and exact original URL. Summary and exact UTC timestamp remain empty because
the index does not supply reliable values. The observed *day-level* release
date is saved only in sidecar metadata with \`timestamp_precision=date_only\`,
along with attribution, original date text, index URL, query UTC and terms
links. Do not manufacture a midnight publication timestamp.

Records and run summaries are in ignored \`reports/html/\`, up to 100 rows /
5 MB, with exclusive local lock, atomic write and classified error outcomes.
HTML duplicate URLs are removed within and across runs. Existing RBA RSS URLs
are read-only checked to avoid duplicating them in HTML storage; **the reverse
direction is not implemented**. Do not run RSS and HTML writers simultaneously.
This is exact-URL matching, not article/event semantic deduplication.

## Verification limits

The synthetic offline tests validate parsing, provenance, day-only timestamp
handling, disallowed links, bounded robots/index reads, local persistence and
RSS URL exclusion. At this stage **no actual local HTML request or live ingest
is confirmed**. Public index browser inspection is not local collector smoke
evidence, and fixtures are not representative news data.

No Streamlit, FinBERT, MiniLM, benchmark or approval-gate changes; source
integration remains NO-GO. Freeze evaluation labels independently. Follow the
31 October internal delivery priority over further source expansion.
