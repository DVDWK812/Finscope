# ABS real-news P2 acceptance — 1 November 2026 Sydney

**Accepted for one previously licensed local ABS original.** This is separate
from successful Marketaux/Finnhub HTTP previews and does not authorize third-party
API content analysis. No user-authored substitute or model mock was used.

## Input and permitted scope

- Original: [Australians buying more fruit and fewer vegetables](https://www.abs.gov.au/media-centre/media-releases/australians-buying-more-fruit-and-fewer-vegetables),
  Australian Bureau of Statistics, publication date **30 October 2026**. Exact
  publication time remains unknown; ingestion time is not substituted.
- Reused the already retained, reviewed ABS staff-authored release, including
  1,675 characters of permitted body. No new collection, API call or article-page
  request was made. Original ID: `2e5baa9cdbe2f1f2701cca2109b3fb75`.
- [ABS copyright policy](https://www.abs.gov.au/website-privacy-copyright-and-disclaimer)
  applies CC BY 4.0 with exclusions for third-party/specially restricted material,
  microdata, marks, logos and artwork. The retained record has positive source
  licence/body-extraction/byline evidence and existing storage/NLP permission.
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en) supplies
  reproduction/adaptation rights subject to its conditions, including attribution.
- Attribution is displayed in the app: ABS / Commonwealth of Australia; FinScope
  processing is marked as derived work with no ABS endorsement. The licence has
  no fixed deletion date; the policy records the copyright term while compliant,
  not an invented account retention allowance.

## Actual processing and persistence

Task `3ac7110aa148459e929137eafdc86b39` used a source-free local FinBERT submission
against the existing production SQLite database. It did not alter the incomplete
API draft, source budgets, selected credentials or the configured pipeline model.
The reviewed policy snapshot is retained with its existing worker checkpoint.
The current 8511 process and worker were not restarted; the worker consumed this
validated checkpoint using its existing saved-original processing interface.

| Check | Observed result |
|---|---|
| SQLite original save | Actual `ProductStorage.save` path; duplicate count 1, new originals 0 |
| Two-level topic | Consumer Staples / 必需消费 → Food and beverages / 食品饮料 (`staples` → `staples.food`) |
| Classification evidence | Exact current content-version cache reused; real-text rule recomputation matched, literal `beverages` offsets 923–932 and 1138–1147 verified |
| New classification rows | 0; previous classifications are retained |
| Actual inference | One local CPU FinBERT inference; no mock, external LLM or weight download |
| Model | `ProsusAI/finbert`, revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031` |
| Result | Negative; positive 0.0776657164, negative 0.8981406093, neutral 0.0241936296 |
| Analysis time | `2026-10-31T18:17:05.387871+00:00` (1 November Sydney) |
| Inference duration | 520.19 ms, excluding model loading/task time |
| Text basis | Title plus leading 1,349/1,675 body characters, coverage 0.805373; excerpt-level label, not a whole-document/accuracy conclusion |
| Analysis ID | `02734e61ed1a4b61b9b4a6351164f083` |

Content SHA-256 is
`5d730d992f8e582a8281c8210365ad828c3f53bcc1f157121cf2ddf76b54f98b`.
Historical originals/content/classifications and the two older LM Studio results
were not overwritten or rescored. This acceptance does not change frozen
challenge metrics or establish classification/sentiment accuracy.
The two-level catalog is FinScope US business v1, not GICS; labels describe news
topics and do not establish an issuer's main business.

Repeat task `f9421e6738124f8e8e82ec34c565cbc2` completed with duplicate count 1,
new/classified/analyzed/failed/skipped all zero. Total originals remain **47**;
total analysis history is **84**, up from 83. Exactly one new actual inference
occurred; repeat processing reused its cache.

## Formal 8511 browser acceptance

- Dashboard search narrowed to this original with `FinBERT · ProsusAI/finbert`:
  one original / one analyzed, zero unclassified or missing selected-model result.
- Clicked its 30 October / Consumer Staples heatmap cell and reached this actual
  article with Negative, both industry levels, source, date-only precision,
  permitted text, attribution and original link.
- News Explorer displayed the same original/model/label. Expanded model history:
  actual revision and all three probabilities, excerpt offsets/coverage, and all
  three analysis-history rows were visible. Classification evidence was expanded
  and both legal catalog IDs/literal evidence inspected.
- Browser navigation did not fetch news or infer. Screenshots are under ignored
  local reports. The original app session remains open; its earlier Marketaux
  preview is not promoted into the retained library or used as NLP evidence.

## Reusable policy implementation and limits

`source_policies.py` records policy ID/version, evidence URLs/review date,
covered fields and purposes, retention basis, attribution/adaptation notice and
exclusions. The first implemented automatic policy is reviewed ABS release text.
Unknown providers and unsupported purposes get no registry grant. Supplied fields
must all be covered; article-level restrictions still outrank the source policy.
External transmission is outside this automatic policy.

`submit_saved_local` explicitly confirms one current saved original, checks the
policy and existing permissions, and atomically creates a source-free FinBERT
job plus checkpoint. Saved API drafts need not become complete to process a
licensed local original. Policy evidence and its digest are auditable in that
checkpoint. Newly started workers also recheck the ABS policy before processing
and add it to output provenance; this extra worker check is not claimed loaded
into the unchanged old production process used above.

This is a staged policy rollout, not a completed review of every provider.
Existing NIST/RBA/ACCC source-specific guards remain; migration into structured
policies needs separate review. API contracts need field-specific entitlements,
purposes, retention/deletion conditions and required attribution before automatic
policy approval. Unknown policy or API HTTP 200 must never inherit ABS rights.
Timed contract expiry enforcement and deletion/backup handling are future work;
no historical data is deleted by this change. User-authored research inputs must
be labelled authored test text and cannot count as real API-news NLP acceptance.

## Preservation and verification

All ten news-request rows, collector/model/external request ledgers, credentials,
47 original payloads, historical content/classification rows, prior 83 analyses,
prior four tasks/checkpoints and **171 frozen files** are preserved. Added two
source-free tasks/checkpoints, one actual analysis/cache entry and ordinary view
preferences. No live provider/collector/LLM request occurred this round.

The final full isolated suite completed 546 tests (one POSIX-only Windows skip),
and the isolated benchmark dry run passed. Exact pushed-SHA CI is checked with
delivery.
Offline policy tests are software verification, separate from the actual model,
database and browser observations above. Codex assisted implementation and
verification; no academic submission or frozen evaluation rerun occurred.
