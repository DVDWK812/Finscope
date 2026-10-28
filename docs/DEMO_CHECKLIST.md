# Final demonstration operator checklist

Use with [the 6:15 A/B/C script](DEMO_SCRIPT.md), [final report](FINAL_REPORT.md) and [freeze verification](DELIVERY_FREEZE.md). Speaking roles remain placeholders; rehearsal, member signoff and three-human testing are pending until observed.

## Before presenting

- Record UTC, public URL, verified main SHA and its push-triggered CI result. Note the last hosted smoke date separately; a repository SHA alone does not prove which code the host is running.
- Open only the public approved-input app and public report/checklist. Hide account panels, terminals, `.env`, private annotations and local reports. No Moodle access, upload or submission.
- Prepare a fresh session and the existing CC0 authored p1/p2/n3 texts below. Do not open or run the consumed B01–B18 challenge in the app or CLI.
- Confirm the rights gate and explicit preparation status. If assets are missing, explain the setup step and record its outcome; do not silently substitute fixtures for real inference. Do not manage/reboot the hosting account during the demonstration.
- Verify raw articles are the initial default. Check all four pages and an approved synthetic-only export. Retain a clearly dated authored-text screenshot/export locally for fallback; never use private reviewer records as presentation material.
- Rehearse all three substantive roles against a timer (target 6:15, permitted user target 5–7 minutes). Record actual duration and assistance privately; names/signatures remain team-owned.

## Approved live-input cue cards

These are development examples from [authored-demo-v1](../evaluation/authored_demo_v1.json), dedicated CC0-1.0. Source: `Authored delivery demo`; permission reference: `authored-demo-v1 / CC0-1.0`; provenance: synthetic. Use distinct titles for each record, no publisher URL, and submitted UTC semantics. Read freshly observed outputs; the authored reference labels are not guaranteed live results.

| Cue | Text |
|---|---|
| p1 — fictional growth | Fictional chipmaker Aster reported a 20 percent rise in revenue and record quarterly profits. |
| p2 — fictional paraphrase | Aster, a fictional semiconductor company, announced record quarterly profit as revenue increased by 20 percent. |
| n3 — fictional opposing outcome | Fictional chipmaker Aster reported a 20 percent decline in revenue and a large quarterly loss. |

After p1, show actual scores/sector evidence and saved raw count. After p2, opt into unverified-candidate summaries and confirm both originals remain in Explorer. After n3, inspect any opposing-tone warning, filter Positive and verify the opposing original remains in candidate details. Export with the filter active and verify all originals. Reset returns to raw articles. A different live result is an observation to record, never a reason to retune on challenge examples.

## Frozen evaluation cue card

**12/16 scorable sentiment agreement (75%); macro-F1 0.730159; two mixed/uncertain references excluded (B02/B07), all 18 outputs retained. Pairwise cosine precision 0.666667 on ten scorable selected pairs.** P02 crosses reporting quarters at 0.813457; P07 has uncertain identity/opposed outcomes and groups at 0.962896. P07/P12 event uncertainty is excluded explicitly. The selected final-group score does not validate deduplication. Opposing model tone does not validate contradiction detection. **Reviewer independence and completion attestations remain unverified.** Display the existing public results table only; no challenge rerun.

## Fallback and human handover

- If the host is loading/asleep/unavailable, state the observed condition and time. Use a labelled local run or a dated authored-text capture. A fallback is not evidence of hosted success; no live provider calls or mock “real” outputs.
- Show the blank [three-human template](USABILITY_EVIDENCE_TEMPLATE.md) while actual A/B/C feedback is pending. Use an explicitly approved anonymized aggregate only after the three private records exist. Agent smoke sessions do not fill these slots.
- Read current load/RSS fields with their scope: prepared-file model load, combined inference latency and current RSS are separate; peak memory, endurance and SLA remain unverified.
- Close with the approved-input demonstration scope and remaining human checks: provenance attestations, actual usability, rehearsal and contribution signoff. The user confirms the official deadline; 31 October is the internal target.
