# Local-product content sync — 3 November 2026 Sydney

This is the user's explicit content/preview maintenance exception to the showcase
freeze, not a redesign. Work is on main only. No branch rename, deployment
coordinate change or application deletion/recreation is in scope.

**Evidence commit:** `7e6c5158c56ac0a520119f91ddfbb2fae9041782` on local, fetched
and read without switching to or modifying its worktree. It matches the supplied
review baseline. Main started at `f2fade938350fbe6db3fb9faeee43598eca26d14`.
The public review note is confined to About: date and short source SHA.

## Source-backed capability matrix

“Implemented” means present in the pinned source, not newly exercised by the
showcase. Dated acceptance is limited to its recorded inputs/platform/scope.

| Capability | Implemented / actually verified scope | Configuration, restriction or pending evidence |
|---|---|---|
| Settings and daily tasks | General, News sources, Analysis models; Update & Analyze; durable worker checkpoints. Formal local UI acceptance is recorded. | Saved settings/filters do not fetch. Source scope, current account/application budget, permissions and model readiness remain prerequisites. |
| Three acquisition modes | Broad Financial News; Selected media with six fixed publisher filters; Company Tracking. Latest three-mode controls were UI-checked without submitting a request. | Media mode is Latest-only. Query cohorts are not inferred news industries; no exhaustive or six-publisher coverage claim. |
| Account management | Explicit primary selection, shared-account quota, dated budgets and persistent holds. | Supplier balance can be Unknown. No automatic backup-key rotation, next-day renewal or failed/unknown-request replay. |
| Official/regulatory sources | Reviewed bounded ABS/NIST/RBA/SEC adapters; dated actual collection, retained local FinBERT and original drill-down evidence. | Route/field/attribution policies differ. SEC needs actual contact information; ACCC remains disabled. No arbitrary-site crawler. |
| Media-link discovery | Fixed feeds and opt-in bounded worker monitoring. Dated Yahoo polling/restart acceptance exists. | Discovery is separate from text retention/NLP. Actual Yahoo responses supplied no validators/304; Reuters query transport yielded no articles. Other ongoing source-use/polling gates remain. |
| Imports and finite text | Strict local JSONL/CSV imports; separate finite API/RSS retention, expiry and stage checkpoints. Later private API collection/local analysis is documented separately. | Finite private-research file imports restricted. Research confirmation does not establish publisher permission or group/public redistribution rights. No private corpus/receipt is published here. |
| Defaults and alternatives | Pinned FinBERT sentiment and MiniLM embeddings/recall; configured installed LM Studio/Ollama. Dated local authored-model checks exist. | Service readiness is not model loading. Resource guards remain; no automatic weights or external fallback. |
| Industry classification | Versioned parent/child topic evidence and selected local semantic classification, separate from sentiment, issuer/company metadata and query cohorts. | Unknown/Unclassified/failure states retained; retrieval similarity is not calibrated confidence or independent accuracy. |
| External models | Explicitly consented external API path and separate output provenance. DeepSeek has a three-authored-text interface acceptance. | DeepSeek is not the automatic real-news worker pipeline or an accuracy test; aliases are not fixed weight revisions. |
| Analytics and history | Dashboard / Industries / Graph / Explorer share local filters and source/input/model history; formal local drill-downs recorded. | Historical handoff figures are a sealed dated baseline, not live totals. No private library figures replace the website's 24 examples. |
| Startup | `launch_local.ps1` starts the Windows UI and worker; dated launcher cold-start/reuse acceptance. Worker CLI is in source. | Direct Streamlit starts the UI only. Manual macOS/Linux instructions are source-derived, not platform acceptance. |
| Resource lifecycle | Latest code separates cached model stages and releases owned processes; offline regression and an earlier authored FinBERT smoke documented. | Latest multi-round attempts were preflight-blocked before inference. Repeated-load stability/leak remediation is not established. Larger future batches require separate approval/verification. |

Pinned evidence paths (all read, no runtime receipts opened or published):

- [README](https://github.com/DVDWK812/Finscope/blob/7e6c5158c56ac0a520119f91ddfbb2fae9041782/README.md),
  [development log](https://github.com/DVDWK812/Finscope/blob/7e6c5158c56ac0a520119f91ddfbb2fae9041782/docs/DEVELOPMENT_LOG.md)
  including the 3 November acquisition-mode and model-lifecycle entries,
  [technical synopsis](https://github.com/DVDWK812/Finscope/blob/7e6c5158c56ac0a520119f91ddfbb2fae9041782/docs/REPORT_SYNOPSIS.md)
  and [sealed handoff description](https://github.com/DVDWK812/Finscope/blob/7e6c5158c56ac0a520119f91ddfbb2fae9041782/docs/REPORT_HANDOFF_20261102.md).
- Acceptance documents at that same SHA: `docs/ABS_P2_ACCEPTANCE.md`,
  `P2_REAL_NEWS_ACCEPTANCE.md`, `P3_BATCH_ACCEPTANCE.md`,
  `P3_MEDIA_ACCEPTANCE.md`, `P3_MEDIA_CONTINUOUS_ACCEPTANCE.md`.
- Current entry/UI/launcher code at that SHA: `streamlit_app.py` delegates to
  `finscope/pipeline_ui.py`; also `settings_ui.py`, `batch_ui.py`,
  `media_batch_ui.py`, `media_modes.py`, `local_worker.py`,
  `industry_classifier.py`, `dashboard_ui.py`, `product_presentation.py`,
  retained advanced `product_ui.py`, and `launch_local.ps1`.

**Dated contradictions:** early API-preview-only/zero-media-NLP statements remain
historical; later explicit private-research continuations document local analysis
without creating publisher permission. The handoff table stays historical even
when later libraries grow or expire. Earlier model success does not establish the
later preflight-blocked multi-round stability test. None is silently promoted into
a current public coverage, accuracy, licence or resource-stability claim.

## Website changes

| Existing surface | Previous copy / preview | Prepared update |
|---|---|---|
| Home | Same hero/sample illustration and three copy-edited cards in v1 | Local architecture illustration in the hero; visible four-card Local Product Capabilities section with implemented/optional/limited-test scopes; original sample overview retained |
| User Guide | Four copy-edited cards in v1 | Connected, numbered Settings → Update & Analyze → Background Worker → Dashboard diagram; detailed source/model qualifications remain collapsed |
| Dashboard Preview | New hierarchy controls hidden inside an expander in v1 | Always-visible Industry intelligence section, parent/child selectors, counted hierarchy branches and retained Unclassified originals; original chart denominators unchanged |
| Knowledge Graph | Company/industry/report links | Same graph and candidates; clarify company metadata versus article topics; consistent source/topic/model context |
| News Explorer | Compact original list/detail | Same articles and lookup; authored text-topic context, Unclassified and not-applicable query/model history |
| Get FinScope | Launcher command within the setup sequence in v1 | Prominent, single copyable Windows launcher command and two-process UI/worker architecture illustration; concise setup and qualified manual platform instructions; `/tree/local` retained |

The topic overlay is a small authored illustration, not US-BUSINESS-1 ground truth
or a fabricated classifier result. Seven records have literal supporting phrases;
17 remain Unclassified despite known company metadata. No original title, summary,
sentiment, article ID, candidate membership or word-frequency input is changed.
All seven word scopes (whole sample and each company) have a golden count/match
digest regression. Topic filters narrow their labelled list only; the charts keep
their dashboard denominator, and the website does not claim full local runtime
or cross-page filter behavior.

## Audit and visible revision

The user correctly observed that the first preparation was visually close to the
old public site. It mostly changed prose: Home retained its hero illustration,
Dashboard hid its only new selectors/table inside a closed expander, and Graph
kept identical SVG structure with added context below. Its tracked diff was eight
files / 258 insertions / 27 deletions, plus the new 55-line content module and
97-line sync record. The full per-file audit and original patch were preserved
locally before revision; the prepared v1 archive is not overwritten.

Visible revision v2 changes the four requested surfaces above, extending the
existing tokens/components rather than replacing the premium theme. Industry
parent counts partition the current authored originals; children sum to their
parent, and Unclassified remains explicit. Local workflow/launcher diagrams are
static illustrations, not operational public controls. Graph geometry and
candidate memberships remain preserved.

The isolated comparison will pair committed public baseline `f2fade9` with the
modified v2 snapshot. Preview-only sidebar build identifiers distinguish them;
those identifiers contain no credentials or private paths. A harmless snapshot
fingerprint and entrypoint hashes identify the exact source being reviewed.

## Verification and release status

**Application source released:** `e565645e153c2a0afa9ec2c18ba6419b5dc7f69c`, pushed
normally to main after explicit user acceptance. Exact-push
[regression CI](https://github.com/DVDWK812/Finscope/actions/runs/41633144517)
passes both Streamlit jobs;
[showcase isolation CI](https://github.com/DVDWK812/Finscope/actions/runs/41633144638)
passes with showcase-only dependencies and provider/model/database guards.
All eleven committed paths were checked against the intended list; the five
unrelated edits, 23 protected files and local refs remain preserved.

The approved feature scope is closed; subsequent code work is maintenance only
(critical bug fixes/security updates), plus finishing release verification.
This documentation-only closeout retains the application files of the SHA above;
its own final-HEAD CI is recorded in the release receipt/delivery.

**Hosted acceptance received, 3 November:** after the push the user explicitly
confirmed that all six pages on https://finscope-dvdwk812.streamlit.app/ load with
Home's capability cards/architecture, the Guide worker workflow, Dashboard's
explicitly illustrative hierarchy, Get FinScope's launcher/UI-worker diagram,
and working Graph/Explorer. This is user-reported manual browser verification,
separate from localhost acceptance and CI. The public taxonomy is authored demo
data, not real-news classification or model output.

No matching FinScope Edge window was available in the permitted inventory and
no Browser/Chrome control tool was exposed; no browser input/alternate channel
bypass was attempted. Independent agent screenshots, a per-device hosted audit
and a server-network forensic audit are not claimed. Public isolation is supported
by the static entry/import boundary and guarded acceptance/CI. The feature exception
is closed and the showcase is maintenance only: critical bugs/security updates.

**Visible v2 approved for commit and push, 3 November 2026 Sydney.** The user
explicitly accepted the localhost revision. This is release approval, not a claim
of agent-operated browser testing, supplied per-size screenshots, three-human
usability evidence or hosted deployment acceptance. The approved public source
matches the guarded/tested v2 snapshot; review-only wrappers are not published.

**V1 offline evidence retained; not released.** In an isolated export of committed
main plus the explicit sync paths: **241 tests passed**, including **28 showcase
tests** with provider/model/database guards; Python syntax passed for 47 files;
all seven existing no-network CLI previews passed. The original fixture, graph
visuals and theme match committed main (allowing checkout line endings); all word
frequency/match scopes retain their exact baseline digest. Relative documentation
links and whitespace checks passed for that preparation. Only tests and existing CLI `--dry-run`
previews were executed; no product service, live collection or inference started.

**V2 offline checks:** 243 full regression tests, including 30 showcase/isolation
tests, pass; syntax checks and seven existing no-network CLI previews pass. The
original fixture and graph renderer match main, and every original headline
frequency/match scope retains its baseline. Theme tokens are retained and the
component CSS is extended for the new visible presentation.

Two localhost-only public snapshots are prepared: previous public commit
`f2fade9` at port 8598 (`baseline-f2fade9-06cd6b198b`) and modified v2 at port 8597
(`visible-v2-b117e6c346`). Each sidebar displays its harmless review identifier.
All core files are hash-checked; the snapshot entrypoint only appends that static
caption. Guarded AppTests run all six exact snapshot pages and verify their build
caption. Both health endpoints return 200/ok. These are functional/source/liveness
checks, not browser screenshots or visual acceptance.

Agent-operated desktop/tablet/mobile screenshots remain unavailable. User localhost
acceptance, exact application CI and separate manual hosted acceptance are recorded
above; final documentation-HEAD CI is recorded in the release receipt/delivery.
The isolated comparison and manual checklist were the authorized fallback. The
earlier prepared snapshot, patches and test receipts remain archived unchanged.
The Edge showcase window was found after the user opened it, but Computer Use
stopped because it could not establish the browser URL with sufficient confidence.
No further browser actions were attempted in that turn; no screenshots or hosted
success are claimed. This tooling block is not evidence of an application failure.

Following user acceptance: push only the explicit showcase paths to main,
verify both exact-push workflows and all six actual hosted pages, record the final
SHA/links/findings, then return to maintenance-only status. The feature scope is
closed; remaining work is release verification or critical fixes. Existing deployment URL
and admin access take priority. Main's five unrelated edits and 23 protected
evidence files are hash-checked; local is never edited, reset, merged or pushed.
No provider/model/database/credential operation is performed by this sync.
