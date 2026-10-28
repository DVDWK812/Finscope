# Three-person public MVP test protocol

Status: **prepared, not executed by three humans**. Programmatic three-workspace concurrency is separately reported in MVP_EVALUATION.md. Use [the public app](https://finscope-dvdwk812.streamlit.app/), one independent browser session/person, no private text, no copied provider stories. Do not send invitations automatically. Record participant codes A/B/C only, date/UTC, browser/device and deployed commit (ask maintainer if unknown).

| Actual human participant | Completed feedback | Evidence/status |
|---|---|---|
| A | No | Pending actual person, time and observations |
| B | No | Pending actual person, time and observations |
| C | No | Pending actual person, time and observations |

Use only the authored development examples for usability tasks. **The challenge packet is consumed and frozen: never enter B01–B18 into the app, CLI, models or rehearsal, and never tune on it.** Its existing [evaluation](CHALLENGE_EVALUATION.md) is retained with reviewer independence and completion attestations unverified. The earlier independent-labeling protocol is historical; it is not authorization to repeat evaluation. A/B/C are participant codes, not claims that three people have participated.

Copy the [blank three-human evidence template](USABILITY_EVIDENCE_TEMPLATE.md) into ignored `reports/usability/` before collecting feedback. Keep completed participant records, screenshots, consent and raw comments local/private; publish only explicitly approved, anonymized aggregate findings. The blank template may be public. Do not replace or amend original annotation files with usability observations. A maintainer-operated hosted smoke check does not fill any participant slot.

## Tasks (about 10 minutes per person)

1. Explain what data is permitted and whether a news API is connected. Without checking rights, submit the default fictional text. Expect rejection and zero saved records.
2. Confirm rights and run the default synthetic text. Record the actual label, three scores, visible sector evidence, latency and raw/group counts. Do not substitute the reference score for a newly observed value.
3. Verify raw counts are the initial default. Submit its p2 paraphrase from `evaluation/authored_demo_v1.json` under a distinct title/source. Opt into unverified-candidate summaries, then open Explorer: both originals must still be listed. Reset filters must return to raw counts. A semantic candidate is not confirmed event identity.
4. Submit n3 (contradictory Aster result). Inspect all raw labels and grouping. If positive/negative labels coexist in a candidate, expect a potential contradictory-outcome warning, including after a sentiment filter excludes one member. Candidate details must still show the opposing original outside the filter. State whether the wording distinguishes a review flag from confirmed factual contradiction. Keep any unexpected result as evidence, not a reason to edit labels afterwards.
5. Submit a synthetic bank/software sentence and an unrelated meeting sentence. Explain multiple sector labels and Unclassified. Inspect original source, timestamp meaning, permission reference and model revisions in News Explorer.
6. Open Trends. Change sentiment/source/sector/date filters and reset. Confirm trends/Overview/Explorer agree for the selected raw/group basis; multi-sector totals may exceed raw counts. Published, first-seen and submitted are distinct.
7. Export your workspace while a filter and candidate-summary mode are active. Open the JSON and verify every original remains present, including the opposing record excluded by the filter; inspect source, timestamp kind, scores, permission and revision fields. Open a separate browser session: expect no other participant's saved text to appear. Export only your own approved records; do not commit private participant data. Refresh/session reset and free-host storage are deliberately temporary. Do not reboot the shared app during human testing; the maintainer records authorized restart evidence separately.
8. Open System Status and report observed resource/load fields or unavailable. Note host sleep/wakeup, any model preparation prompt, exceptions, slow operations and accessibility/mobile problems. Do not repeatedly click inference while it is running.

## Feedback record (one per participant)

Use the detailed template linked above to record each task as pass/fail/partial/not attempted, its actual UTC/time/assistance, observed behavior and evidence reference. Record participant confirmation only when that human supplies it; a software timestamp or maintainer statement is not their attestation.

| Field | Observed value |
|---|---|
| Participant code / UTC / deployed SHA / device | Pending |
| Task completion (1–8), assistance needed, time | Pending |
| Actual inference label/scores/latency and counts | Pending |
| Source/time/sector/group explanation understood? | Pending |
| Workspace isolation/export result | Pending |
| Error or confusing wording; reproducible steps | Pending |
| Ease of use 1–5 and one improvement | Pending |

The maintainer consolidates blockers by severity and fixes data leakage, false success, crashes and inaccessible inference first. Re-run affected regression tests and one real approved-text browser acceptance after each fix; record exact CI commit. Do not claim the three-person requirement is met until all three actual feedback records exist. Independent label review must be recorded separately from usability feedback.
