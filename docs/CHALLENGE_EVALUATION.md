# Provisional user-adjudicated challenge evaluation

Actual local CPU inference, 29 October 2026 Sydney. This is an approved-input demonstration evaluation with **unverified reviewer independence**, not certified independent-human accuracy or production validation.

## Reference and run integrity

The user supplied two completed submissions from different people and then explicitly confirmed five worksheet decisions: B17 Neutral (spelling correction), B18 Negative, opposed outcomes P08 Yes / P09 No / P10 Yes. All other normalized matching labels were retained. Mixed and uncertain sentiment spellings share the rubric combined bucket. Original submissions, verbatim rationales, amendment history and worksheet are preserved in ignored local storage; no private names or attestations are published.

The user instructed proceeding after adjudication. A **provisional user-adjudicated reference was locked before any prediction**, rather than claiming the original independent-label gate was satisfied. Reviewer code/completion/independence fields, original-reviewer confirmation of the later B18 amendment and adjudicator header remain PENDING. No person's signature, completion time or independence was invented. The stored freeze time is a software evidence timestamp, not human completion. Human provenance remains incomplete and must not be silently upgraded after results are known.

- Packet canonical SHA-256 (CRLF normalized to LF): `fc1a6b98dfa167f38b4d5fa62bda9cc5052c4204f03783f869ba384dca1b9f4e`.
- Locked reference SHA-256: `d0467a36e1f2f198703078480dcfc5033f2a7e8a4c4ba2e3ba202c6a3a5c1327`.
- Actual report SHA-256: `02189f34760f3b62c252eba38a526aeb2bd27a236321d80fc8c1077755d5b0eb`.
- Reference frozen UTC: `2026-10-28T16:25:16.854680+00:00`.
- Single actual execution UTC: `2026-10-28T16:26:06.952388+00:00` to `2026-10-28T16:26:42.056724+00:00`, exit 0.
- Evidence folder: `reports/labels/adjudication/round_d1372a73ae/` (ignored): frozen reference, intent/completion marker, complete actual JSON, CLI log and original submissions. The source WeChat files are unchanged.

No API/provider/RBA calls, model downloads, repeats, model/rule/threshold tuning or Streamlit changes. The pinned inference/persistence/sector code and manifests match the pre-evaluation main source. A new offline arithmetic helper scores uncertainty/failure coverage; it does not affect predictions. Model assets were hash-verified by the existing local-only loaders. Existing protected provider evidence/cooldowns still match their six baseline hashes.

## Frozen method and scope

FinBERT revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`; MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Existing keyword-v1 sectors, cosine **0.80**, 72-hour window and representative-only grouping are unchanged. Both model licences remain as documented in [AI evidence](AI_PROTOTYPE.md). Runtime: torch 2.14.1+cpu, transformers 5.20.2, huggingface-hub 2.3.0, safetensors 0.8.0, tokenizers 0.23.3.

All 18 CC0 fictional texts were submitted once in packet order in an isolated temporary repository, with the same evaluation submission timestamp. This deliberately keeps every pair eligible for the 72-hour test; it does not validate publication times or real reporting-period extraction. Original UUID tie ordering and order-dependent representative selection are unchanged. Every case output, all three probabilities, all 12 selected cosines and group membership are saved locally. No sector ground truth was provided, so no sector accuracy is claimed.

## Sentiment results

**12/16 correct (75.0% accuracy), macro-F1 0.730159**, covering **16/18 (88.9%)** texts. Reference counts: Positive 8, Negative 4, Neutral 4, Mixed/uncertain 2. B02 and B07 were predicted and retained but excluded from three-class metrics because FinBERT has no combined mixed/uncertain class. All 18 inferences succeeded; no error exclusions.

| Reference / predicted | Positive | Negative | Neutral |
|---|---:|---:|---:|
| Positive | 6 | 2 | 0 |
| Negative | 0 | 4 | 0 |
| Neutral | 0 | 2 | 2 |

Four scorable disagreements: B01 (narrowed losses), B10 (resolved dispute/withdrawn shutdown warning), B08 (unchanged outlook expressed with negation), B16 (unchanged results) were all predicted Negative. These observed failures limit the simple authored pilot's earlier 12/12 result; no rule or model was changed to correct them. B18's final Negative label is preserved as supplied, alongside its original mixed-label disagreement and later user amendment; its rationale is not independent factual validation.

| Case | Provisional reference | Actual prediction | Positive | Negative | Neutral |
|---|---|---|---:|---:|---:|
| B01 | positive | negative | 0.425851 | 0.552862 | 0.021287 |
| B02 | mixed/uncertain | positive | 0.752950 | 0.229641 | 0.017408 |
| B03 | neutral | neutral | 0.014432 | 0.056090 | 0.929478 |
| B04 | positive | positive | 0.946254 | 0.016918 | 0.036827 |
| B05 | positive | positive | 0.952611 | 0.019733 | 0.027657 |
| B06 | negative | negative | 0.007009 | 0.975922 | 0.017069 |
| B07 | mixed/uncertain | negative | 0.018529 | 0.966934 | 0.014537 |
| B08 | neutral | negative | 0.029193 | 0.888288 | 0.082518 |
| B09 | negative | negative | 0.012223 | 0.972466 | 0.015312 |
| B10 | positive | negative | 0.014565 | 0.952163 | 0.033272 |
| B11 | positive | positive | 0.934904 | 0.013184 | 0.051912 |
| B12 | positive | positive | 0.893510 | 0.009671 | 0.096819 |
| B13 | positive | positive | 0.930335 | 0.012904 | 0.056761 |
| B14 | positive | positive | 0.948086 | 0.034630 | 0.017284 |
| B15 | negative | negative | 0.008342 | 0.973429 | 0.018229 |
| B16 | neutral | negative | 0.013175 | 0.970475 | 0.016350 |
| B17 | neutral | neutral | 0.027996 | 0.108945 | 0.863059 |
| B18 | negative | negative | 0.016151 | 0.971901 | 0.011948 |

## Selected-pair event results

Only the **12 preselected challenge pairs** were examined. P07 and P12 have Uncertain event identity and are reported but excluded from binary event metrics. There are **10 scorable pairs: 2 same-event / 8 different-event**. Unannotated pairs among the possible 153 are never treated as negatives.

| Decision | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pair cosine candidate | 2 | 1 | 0 | 7 | 0.666667 | 1.000000 | 0.800000 |
| Final pipeline group membership | 2 | 0 | 0 | 8 | 1.000000 | 1.000000 | 1.000000 |

**The 10-pair group score is not validated deduplication.** P02 (different Celadon reporting quarters) exceeds the cosine threshold at 0.813457, but remained in separate final groups in this run because of representative selection. P07 (opposed Tern loss estimates/outlook) has uncertain identity, cosine 0.962896 and **did share a candidate group**; its opposing Positive/Negative predictions trigger the existing review warning. Excluding uncertain identity from accuracy does not erase this safety concern. Raw result: **18 original records / 15 unverified candidate groups**. The existing raw-default UI and preserved originals remain necessary.

| Pair | Texts | Reference event | Opposed outcomes (user reference) | Cosine | Semantic candidate | Same final group | Opposing model tone |
|---|---|---|---|---:|---|---|---|
| P01 | B04/B05 | same-event | no | 0.856826 | True | True | False |
| P02 | B04/B06 | different-event | yes | 0.813457 | True | False | True |
| P03 | B05/B06 | different-event | yes | 0.718234 | False | False | True |
| P04 | B11/B12 | same-event | no | 0.916332 | True | True | False |
| P05 | B11/B13 | different-event | no | 0.695718 | False | False | False |
| P06 | B12/B13 | different-event | no | 0.579405 | False | False | False |
| P07 | B14/B15 | uncertain | yes | 0.962896 | True | True | True |
| P08 | B01/B02 | different-event | yes | 0.717313 | False | False | True |
| P09 | B02/B03 | different-event | no | 0.562239 | False | False | False |
| P10 | B07/B08 | different-event | yes | 0.647867 | False | False | False |
| P11 | B09/B10 | different-event | uncertain | 0.489775 | False | False | False |
| P12 | B16/B18 | uncertain | uncertain | 0.794311 | False | False | False |

Opposed-outcome annotations and opposing model tone are separate constructs, not event identity or verified factual contradictions. For example, P10 is user-adjudicated opposed but both predictions were Negative, so the tone flag missed it. No validated contradiction-detector claim or automatic record hiding follows from these judgments.

## Timing and limitations

Observed prepared-file model load including integrity checks: **32.111 s**. Combined per-record inference median **115.445 ms**, range **99.71–156.96 ms**. Current process RSS at the end **857.23 MiB**, not peak. Exactly **18 FinBERT forward batches** and 18 embedding calls through the real pipeline. This is a local measurement, not new public-host, concurrency, cold-start SLA or human-usability evidence.

Small, intentionally difficult, dependent, fictional examples with unverified independence cannot estimate broad financial-news accuracy, calibration or prevalence. Two event positives and selected pairs are especially fragile. There was no tuning on these labels. **This packet is now evaluated and no longer an untouched holdout**; any tuning requires a separate development set and a fresh, independently labeled holdout. Later provenance updates must preserve the original incomplete status and prediction time.

Limited approved-input course demonstration remains GO with visible limitations. Production live-provider integration, confirmed-event deduplication and independent-human validation remain **NO-GO / incomplete**. Three actual usability records, human provenance, rehearsal and user-confirmed assessment deadline remain outstanding; no Moodle access or submission occurred.
