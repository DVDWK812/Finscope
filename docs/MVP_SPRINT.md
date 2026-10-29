# MVP delivery sprint

**Final delivery freeze, 29 October:** No further inference or tuning on the consumed challenge packet. Preserve all original evidence and incomplete reviewer provenance. Current deliverables are the [team-reference synopsis](REPORT_SYNOPSIS.md), [three-human evidence template](USABILITY_EVIDENCE_TEMPLATE.md), [demo checklist](DEMO_CHECKLIST.md) and [verification record](DELIVERY_FREEZE.md). Dated day-plan entries below are historical plans; none authorizes a challenge rerun or claims human participation.

**29 October update:** [Provisional user-adjudicated challenge](CHALLENGE_EVALUATION.md) executed once with the real frozen models: 18 outputs, 12/16 scorable sentiment matches, semantic-pair precision .667 on 10 scorable pairs. Reviewer independence/completion attestations remain unverified; no human usability feedback is implied. The original day-plan entries below are plans/historical status, not current proof that the packet is still unpredicted. The packet is now consumed; no tuning on it.

Internal delivery target: 31 October 2026 Australia/Sydney, distinct from unverified conflicting historical deadline values (ASSESSMENT_VERIFICATION.md). Earlier course notes identify FINS5557 Applied AI in Finance T3 2026. The user will confirm the deadline; further agent Moodle access/submission is prohibited. Main only, small tested commits, exact-commit PUSH CI. Kickoff/public vertical slice: 26 October. Planned work is not execution evidence.

| Date | Critical deliverable | Current evidence |
|---|---|---|
| 26 Oct kickoff | Submit approved text → actual FinBERT + MiniLM → SQLite → Overview/Trends/Explorer; begin public deployment | Working locally and on Community Cloud; see evaluation |
| 27 Oct | Raw-default/grouping-safety fix; freeze difficult blind annotation packet | 135 tests; 18 texts/12 pairs unpredicted, human labels pending; Moodle course verified, deadline conflict recorded |
| 28 Oct | Three people independently exercise public application and export evidence | Protocol ready; no human results invented |
| 29 Oct | Fix observed blockers, repeat affected tests and public inference; test host wake/restart | Pending actual feedback/host observations |
| 30 Oct | Finalize report, README, limitations and 5–7 minute rehearsal | Drafts ready; team signoff pending |
| 31 Oct | Internal demonstration, final evidence/export and delivery candidate | Pending; do not describe as the verified Moodle due date or submit to a closed dropbox |

## Reused architecture

Streamlit approved input → provenance/size/time checks → cached local pinned FinBERT and MiniLM → keyword sector evidence + cosine candidate grouping → session-scoped SQLite repository → filtered Overview/Trends/Explorer/export. The existing fixture repository remains a separate labelled tour. Provider adapters, guarded sampler, reservation ledger and cooldowns are outside this path. No URL is fetched. No API key is needed by the public app.

The SQLite store is disposable, isolated by random browser-session workspace IDs, capped at 100 rows/workspace and 1,000 total. An app access purges records older than 24 hours; this is not a background timed-deletion guarantee or a durable authenticated account system. A refresh can start a new workspace; export before leaving. Free-host redeploy/reboot can clear the database and model cache. Do not submit sensitive material. Shared model execution is serialized; no autoscaling/SLA claim.

## Scope control and release gates

- **GO: limited noncommercial approved-input demonstration.** Actual inference and persisted results are observed. Inputs require processing/storage rights; synthetic default and authored evaluation avoid publisher restrictions.
- **Pending human evidence:** three-human usability results, independent labels/adjudication and actual rehearsal. The 18-case packet has provisional user-adjudicated results; reviewer independence and completion attestations remain unverified. No three-human usability work is marked complete. Remaining hosting hibernation/endurance behavior is unknown. Individual names/contribution claims remain intentionally unassigned at the user's request. The user handles official deadline and submission decisions; no further agent Moodle access.
- **NO-GO: production live-provider integration.** Multi-day financial relevance/useful permitted descriptions, publication timestamp accuracy/scope, source diversity/history/quota, public display/retention/inference/derived-output rights and independent model/event quality remain unresolved. Marketaux remains a conditional preferred financial metadata candidate, GDELT provisional. One-shot evidence remains unchanged and its deleted task is never recreated.

Defer live ingestion, further API research, authenticated accounts, background workers, crawler/full text, training/fine-tuning, sophisticated sector models, event-identity claims and extra infrastructure. Add only changes needed for the demonstrable approved-text product and observed blockers.
