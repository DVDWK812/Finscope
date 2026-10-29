# Final delivery freeze — 29 October 2026 Sydney

The user froze the delivery scope on 29 October. Models, revisions, keyword rules, cosine 0.80, 72-hour policy, grouping algorithm and raw-default application behavior remain unchanged. Work is limited to delivery documentation/templates and verification with offline mocks or approved authored development examples.

## Evidence preservation

The consumed challenge is never rerun through models, app, CLI or rehearsal and is never used for tuning. [The original evaluation report](CHALLENGE_EVALUATION.md), packet, locked reference, original human submissions/rationales, amendments and actual outputs remain preserved. Earlier blind-labeling instructions are archival. No private annotation records are published or staged. Later human attestations must be appended with actual dates, retaining original incomplete provenance and prediction timestamps; no backdating or retrospective claim of independent review.

| Existing frozen artifact | Recorded SHA-256 |
|---|---|
| Packet, CRLF normalized to LF | `fc1a6b98dfa167f38b4d5fa62bda9cc5052c4204f03783f869ba384dca1b9f4e` |
| Locked provisional reference | `d0467a36e1f2f198703078480dcfc5033f2a7e8a4c4ba2e3ba202c6a3a5c1327` |
| Actual single-run report | `02189f34760f3b62c252eba38a526aeb2bd27a236321d80fc8c1077755d5b0eb` |

A local pre-change hash manifest covers **155 existing evidence files**, including all files then present under ignored `reports/`, the entire `evaluation/` tree and `docs/CHALLENGE_EVALUATION.md`. The manifest and private evidence stay under ignored `reports/delivery_freeze/`; only counts and verified aggregate outcomes belong in public documentation. Hash checks read bytes only; they do not execute evaluation scripts or rescore/recompute predictions.

## Release statements and materials

The [team-reference synopsis](REPORT_SYNOPSIS.md), [script](DEMO_SCRIPT.md) and [operator checklist/cue cards](DEMO_CHECKLIST.md) use **12/16 scorable sentiment agreement (75%), macro-F1 0.730159, two mixed/uncertain references excluded, pairwise cosine precision 0.666667**. P02 exposes reporting-period false matching; P07 exposes uncertain identity/opposed-outcome grouping. Reviewer independence and completion attestations remain **unverified**. Raw articles remain the default. Neither event deduplication nor contradiction detection is validated.

[The eight-task protocol](USER_TESTING.md) and [blank three-human evidence template](USABILITY_EVIDENCE_TEMPLATE.md) are prepared. A/B/C actual human records, participant confirmations, approved anonymized findings, rehearsal and team contribution signoff remain pending. Agent-operated smoke checks are engineering evidence only. Do not publish completed private records.

## Final verification

Verified on 29 October Sydney (28 October UTC), from clean/fast-forwarded main `62646b2`. The hosted smoke used authored p1/p2/n3 only, never the challenge packet.

| Check | Observed outcome |
|---|---|
| Full offline regression | **182 tests passed**, 4.700 s; mocks/invented arithmetic examples, no challenge inference |
| `python -m finscope.benchmark --dry-run` | Passed, exit 0; zero provider requests |
| Evidence integrity | All **155** pre-existing protected files byte-for-byte unchanged; three published frozen hashes match |
| Delivery document links / whitespace | Relative links resolve; `git diff --check` passed |
| Hosted startup/setup | Initial “app in the oven” resolved to the approved-input app; missing assets required the existing explicit preparation control, which completed. No hosting-account action or reboot |
| Hosted rights gate | Missing rights rejected; workspace remained at zero saved rows |
| Hosted actual authored inference | p1 Positive **170 ms**; p2 Positive **128 ms**; n3 Negative **119 ms**, combined inference times displayed by the app |
| Hosted defaults and views | Raw initially; 3 raw originals / 1 unverified candidate after submissions. Candidate opt-in retained originals; Reset restored raw. Trends showed 2 Positive / 0 Neutral / 1 Negative. Overview, Explorer, Trends and System Status rendered |
| Filtered candidate safety | Positive filter showed 2 matching originals / 1 chart representative; candidate details retained all 3 originals, including Negative outside the filter. Global/detail opposing-tone warnings remained review flags |
| Actual hosted JSON export | Downloaded during Positive filtering and candidate-summary mode; parsed locally: **3 distinct originals**, both tones, source/submitted timestamp meaning/synthetic provenance/permission reference/three scores/pinned model revisions retained |
| Fresh-session smoke | A second tab loaded with **0 originals** while the first retained **3**; no second-tab inference. These are two agent-operated tabs, not independent profiles, people or a security-isolation guarantee |
| Hosted resources | Prepared-file cold model load **6.944 s**; current process RSS after three inferences **880.2 MiB**, not peak/install/download time, load guarantee or SLA |

The actual p1 scores were positive 0.9536037445068359, negative 0.019615216180682182, neutral 0.026781005784869194. n3 Negative probability was 0.9752560257911682 and its nearest representative cosine 0.8523579498784285. These are repeat engineering probes on the old development examples, not new accuracy or challenge results. The current public UI does not attest its exact deployed Git SHA; that SHA is **unverified**. Hosting hibernation, endurance and peak memory remain unverified. Earlier two-session isolation evidence remains dated in HOSTING_VERIFICATION.md.

Local logs, authored export, screenshot and smoke summary remain ignored in `reports/delivery_freeze/`. Remote main SHA and its push-triggered GitHub Actions jobs are checked after pushing; exact-head results remain local and are reported at handover so this commit does not claim its own future CI result. No private annotation records enter the release.

No Moodle access, coursework submission, provider/RBA calls, new source research, production-source approval or unrelated external-account action is authorized by this freeze. The official deadline remains user-confirmed; both historical conflicting values remain unverified. Codex assisted with the audit, templates/report/demo edits and software/host verification; no human evidence or signatures were generated.
