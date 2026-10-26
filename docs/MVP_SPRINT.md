# MVP delivery sprint

Deadline: 31 October 2026 Australia/Sydney. Main only, small tested commits, exact-commit PUSH CI. Kickoff and working public vertical slice: 26 October. The remaining five calendar days are 27–31 October; these are planned activities, not execution claims.

| Date | Critical deliverable | Current evidence |
|---|---|---|
| 26 Oct kickoff | Submit approved text → actual FinBERT + MiniLM → SQLite → Overview/Trends/Explorer; begin public deployment | Working locally and on Community Cloud; see evaluation |
| 27 Oct | Review provisional evaluation labels, add difficult approved examples without tuning on the test set | 12-text authored pilot completed; independent review pending |
| 28 Oct | Three people independently exercise public application and export evidence | Protocol ready; no human results invented |
| 29 Oct | Fix observed blockers, repeat affected tests and public inference; test host wake/restart | Pending actual feedback/host observations |
| 30 Oct | Finalize report, README, limitations and 5–7 minute rehearsal | Drafts ready; team signoff pending |
| 31 Oct | Demonstration, final evidence/export, submission | Pending |

## Reused architecture

Streamlit approved input → provenance/size/time checks → cached local pinned FinBERT and MiniLM → keyword sector evidence + cosine candidate grouping → session-scoped SQLite repository → filtered Overview/Trends/Explorer/export. The existing fixture repository remains a separate labelled tour. Provider adapters, guarded sampler, reservation ledger and cooldowns are outside this path. No URL is fetched. No API key is needed by the public app.

The SQLite store is disposable, isolated by random browser-session workspace IDs, capped at 100 rows/workspace and 1,000 total. An app access purges records older than 24 hours; this is not a background timed-deletion guarantee or a durable authenticated account system. A refresh can start a new workspace; export before leaving. Free-host redeploy/reboot can clear the database and model cache. Do not submit sensitive material. Shared model execution is serialized; no autoscaling/SLA claim.

## Scope control and release gates

- **GO: limited noncommercial approved-input demonstration.** Actual inference and persisted results are observed. Inputs require processing/storage rights; synthetic default and authored evaluation avoid publisher restrictions.
- **Pending before assessed delivery:** three-human usability results, independent labels, host wake/restart and resource observations, rehearsal/report/course-code/team disclosure signoff.
- **NO-GO: production live-provider integration.** Multi-day financial relevance/useful permitted descriptions, publication timestamp accuracy/scope, source diversity/history/quota, public display/retention/inference/derived-output rights and independent model/event quality remain unresolved. Marketaux remains a conditional preferred financial metadata candidate, GDELT provisional. One-shot evidence remains unchanged and its deleted task is never recreated.

Defer live ingestion, further API research, authenticated accounts, background workers, crawler/full text, training/fine-tuning, sophisticated sector models, event-identity claims and extra infrastructure. Add only changes needed for the demonstrable approved-text product and observed blockers.
