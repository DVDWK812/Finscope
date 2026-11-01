# Report handoff — 2 November 2026

Prepared and checked **1 November 2026 Australia/Sydney** for the internal **2 November 18:00** handoff to the three report authors. Readiness is due before noon. This milestone preserves a technical/report baseline while development continues on `local`; it is not the official deadline, project completion or a permanent feature freeze. The user will arrange final submission freeze/full regression separately. Main remains read only.

## Version and evidence ownership

Runtime/data acceptance SHA: **`97f0529f32bcbec012368fe1138b4187d3d7d8ae`**. [Exact CI: two Linux jobs and one Windows job successful](https://github.com/DVDWK812/Finscope/actions/runs/41284045331). The handoff changes are technical reference/demo documentation and the current mission clarification; no provider, model or classification behavior is changed. During preparation the user separately approved one Reuters-domain Marketaux query, recorded as an additive receipt below. The package's final commit/CI is recorded in the final delivery and the private sealed `delivery.json` below; do not substitute a later branch HEAD.

Technical sources: [synopsis](REPORT_SYNOPSIS.md), [6:15 operator flow](DEMO_SCRIPT.md), [checklist](DEMO_CHECKLIST.md), [P3 batch acceptance](P3_BATCH_ACCEPTANCE.md), [ABS real FinBERT](ABS_P2_ACCEPTANCE.md), [media continuity](P3_MEDIA_CONTINUOUS_ACCEPTANCE.md). These are evidence/reference materials for members to write their own report. No submission prose, human feedback, participation, contribution signature or formal deadline determination is supplied by Codex.

## Readiness observed

- Desktop `FinScope.cmd` invokes the installed local launcher. Actual execution reused the healthy8511 instance. A controlled cold start, after confirming zero active/queued tasks, then started8511 and one worker under the same launcher parent. A repeat launch retained the same process IDs. Health endpoint returned200/ok. No installation, credential edit or extra instance was needed.
- SQLite `PRAGMA quick_check` returned `ok`. Cold start restored the saved date/model/source/search preferences and the same266-original/232-analysis database. Old pending-provider/unknown-request and pause rules were not cleared. All20 existing task states are terminal (16 completed, three partial-failed, one blocked), not falsely described as20 successful jobs.
- Formal8511 Dashboard, Industries, Graph and News Explorer rendered against the real local database. ABS heatmap and Food-and-beverages graph-node clicks reached the retained original. Source/date-only precision, original URL, attribution, both topic levels, literal evidence, real FinBERT probabilities/revision and selected-text coverage were inspected. No Streamlit exception was shown in the checked page.
- Current-content results match the input fingerprint. The ABS body version displays its actual Negative result; the later title-only Neutral row remains historical. It was not rerun merely to reproduce a desired label.
- The UI/startup rehearsal generated **zero news/API/RSS/collector requests, zero inference and zero external-LLM requests**. The separately authorized Reuters diagnostic added one API request afterward, as recorded below. Counts stayed266 originals /232 historical analyses /136 media discoveries. This is current UI/startup verification of previously completed real ingestion/inference, not a new model or provider experiment.

## Exact reporting denominators

| Metric | Handoff value | Evidence/meaning |
|---|---:|---|
| Local originals |266|261 real-source records plus five authored development inputs |
| Real official announcements |141|ABS80, NIST40, RBA1, SEC press20 |
| Real regulatory disclosures |120|Six issuers ×20 filings; seven suitable operating-event excerpts |
| Current-content real FinBERT results |148|141 announcements + seven disclosure excerpts |
| Not-applicable disclosures |113|Not counted as Neutral or failed inferences |
| Historical analysis versions |232|Across retained inputs/models; not a distinct-article denominator |
| US topic-classified real originals |17|Six parent/nine child dictionary labels;244 Unclassified |
| CSRC classified real originals |0|261 Unclassified under current English vocabulary |
| Separate media URL discoveries |136|Bloomberg18, CNBC30, WSJ59, FT10, Yahoo19 |
| Saved mainstream-media publisher text / NLP |0 /0|Yahoo supplied reader fields RAM-only; other text scopes unverified |

Read-only calculations are preserved in local `statistics.json`; they use current content pointers, the same source-type resolver and current-input FinBERT matching as the UI. UI counts depend on the visible date/source/status filters; the full official-announcement screenshot shows141, while the prepared ABS drill-down intentionally shows1.

## Local screenshot and snapshot index

Files are in the Git-ignored **`reports/report_handoff_20261102/`** of the local worktree. They are not a public corpus or a package to email automatically. Do not publish the database, account settings, private evidence or copyrighted text merely because it exists locally. ABS text captures retain attribution and are for the reviewed licensed example. Yahoo RAM-only titles/summaries are excluded from saved screenshots.

| Local file | Recorded view |
|---|---|
| `01_dashboard.jpg` | Formal Dashboard:141 official announcements,266 total originals,120 disclosures, FinBERT selected |
| `02_industries_abs.jpg` | Industries: selected ABS original, source/date-only precision, both industry levels and attribution |
| `03_explorer_finbert.jpg` | Explorer: actual pinned FinBERT revision, timestamp and three probabilities |
| `04_classification_evidence.jpg` | Expanded literal-evidence/classification history |
| `05_graph.jpg` | Actual ABS original → Food and beverages → Consumer Staples graph; child-node click |
| `06_dashboard_heatmap.jpg` | Actual30 October /Consumer Staples heatmap selection |
| `07_heatmap_drilldown.jpg` | Retained ABS original reached from Dashboard heatmap |
| `08_media_counts.jpg` | Media source/status counts only, no RAM-only publisher text |
| `baseline.sqlite3` / `baseline.json` | Consistent private SQLite backup and per-table count/hash snapshot before rehearsal |
| `statistics.json` / `restart.json` | Read-only denominators and actual launcher restart/reuse evidence |
| `frozen_manifest.json` |171 protected-file reference hashes; original evidence remains untouched |
| `preservation.json` / `delivery.json` / `manifest.json` | Final data/ledger preservation, exact handoff SHA/CI and evidence-file hashes, sealed after checks |

The final source bundle, screenshots, logs, acceptance receipts and manifests stay local/ignored; credentials are never exported from Windows Credential Manager. A database snapshot may contain private nonsecret configuration/contact metadata and is not a team/public attachment. The repository contains only technical reference facts and evidence pointers.

## Baseline preservation and next development

Use the exact handoff commit for report citations, and the sealed local manifest to verify files. Do not overwrite this dated directory, its SQLite snapshot or screenshots. Store later evidence in a new dated directory and append dated comparisons; never update old measurements to make the baseline appear newer. Do not restore the snapshot over ongoing product data. A Git source bundle is retained locally for recovery, without creating/pushing another branch or tag.

The171 frozen files, consumed challenge, reference labels, original annotations and actual evaluation outputs remain byte-for-byte protected. The old `DELIVERY_FREEZE.md` is historical evidence and is deliberately not edited to express this newer product scope.

During preparation, a later explicit user confirmation verified quota and authorized one additional Marketaux Reuters-domain query. At **2026-11-01 07:36:19 UTC** it returned **HTTP200 / empty / zero records**. The primary key was used once; there was no retry, fallback, publisher-page request, text persistence or NLP. The news-request ledger grew13→14; the preserved13-row baseline prefix and all originals/analyses/media indices remain unchanged. The private additive audit is `reports/p3b1_reuters_20261101/query.json`; the earlier snapshot/receipts are not rewritten. This verifies query transport, not Reuters article coverage. The one-request budget is consumed.

Continue P3-B.1 after handoff: require a new legitimate budget before any further Reuters query; complete source-level display/cache/storage/NLP policy reviews; validate permitted conditional polling where validators actually exist. Bloomberg and FT have new successful transport evidence, but their ongoing polling/text-use gates remain. These do not block the real ABS/official-source demonstration. Further priorities are mainstream-media diversity, incremental collection, dictionary/semantic topic quality and user experience. No extra provider request is authorized by this handoff document.

Before formal final submission, agree the separate functional-freeze date, run full regression and exact-SHA CI, then record real usability/rehearsal evidence supplied by the members. Official submission time remains user-confirmed; no Moodle access or coursework submission is performed by Codex.
