# Blinded human labeling packet — NOT YET LABELED

Read [BLIND_READING_PACKET.md](BLIND_READING_PACKET.md) for the 18 texts (B01–B18) and pair lookup (P01–P12). It copies `blind_holdout_v1.json` verbatim in readable form. Text was authored by Codex; **no expected labels or model outputs are supplied**. This is a prepared packet for independent human annotation, not an independently labeled dataset yet. The previous 12-text authored pilot remains development/convenience evidence; its labels/results must not be relabeled as human ground truth.

## Freeze and independence

Frozen packet SHA-256 (UTF-8 with CRLF normalized to LF): `fc1a6b98dfa167f38b4d5fa62bda9cc5052c4204f03783f869ba384dca1b9f4e`. Checked 27 October 2026 Sydney: 18 unique case IDs, 12 valid pair IDs/references, no labels, all texts below the app's character limit. No inference was run on this packet.

All 18 cases are holdout. Current FinBERT/MiniLM revisions, keyword-v1 rules, cosine .80 and 72-hour candidate policy are frozen for this evaluation. Grouping display safety changes do not tune inference. Do not feed these texts into the app, CLI or model, inspect predictions, adjust prompts/rules/thresholds, or selectively remove difficult cases before labels are locked. Do not use this holdout to tune and then report performance on it. Any tuning requires a separate development set and an entirely fresh untouched holdout for the next evaluation.

Two actual human reviewers independently complete separate copies of the blank sheet below (HR1 and HR2). Do not share answers or consult model outputs. A third actual human adjudicates disagreements after both timestamped sheets are locked; preserve originals. Private names/signatures stay outside public Git unless members consent; reviewer codes suffice publicly. A reviewer attestation is supplied by that person, never by Codex. Programmatic sessions and AI-authored labels do not count as people.

## Rubric

- Sentiment means the stated company's financial text tone, not share-price direction, sector impact or personal investment advice. Choose positive, negative, neutral, or mixed/uncertain; briefly cite the textual reason. Do not infer missing forecasts, analyst expectations, periods or outcomes. Negated losses, a narrower loss, unchanged guidance and mixed revenue/profit signals require careful reading.
- Pair label: same-event, different-event, or uncertain. Consider named company, reporting period, specific action and compatible reported facts. Similar wording alone is insufficient. Opposite claims about the same company/period can be uncertain/conflicting reports rather than a confidently identical or distinct event. Record whether financial outcomes appear opposed: yes/no/uncertain, separately from event identity.
- Cases may reasonably be ambiguous. Never force an answer to make the model look correct. The three-class sentiment analysis must report mixed/uncertain exclusions and label coverage; do not silently discard them. Pair uncertainty is also reported separately.

## Blank individual review sheet (copy once per person)

Reviewer code: **PENDING** · UTC completed: **PENDING** · Dataset SHA-256: **PENDING**

Human attestation: **PENDING** — I labeled independently without seeing model predictions or the other reviewer's labels. This statement is not signed until I confirm it myself.

| Case | Human sentiment label | Text-based rationale |
|---|---|---|
| B01 | | |
| B02 | | |
| B03 | | |
| B04 | | |
| B05 | | |
| B06 | | |
| B07 | | |
| B08 | | |
| B09 | | |
| B10 | | |
| B11 | | |
| B12 | | |
| B13 | | |
| B14 | | |
| B15 | | |
| B16 | | |
| B17 | | |
| B18 | | |

| Pair | Same/different/uncertain event | Opposed financial outcomes? | Rationale |
|---|---|---|---|
| P01 | | | |
| P02 | | | |
| P03 | | | |
| P04 | | | |
| P05 | | | |
| P06 | | | |
| P07 | | | |
| P08 | | | |
| P09 | | | |
| P10 | | | |
| P11 | | | |
| P12 | | | |

## After actual labels arrive

Record both reviewers' agreement/uncertainty counts before adjudication. Lock the adjudicated label file with dataset/model/rule hashes, reviewer codes, timestamps and independence attestations. Only then run the frozen pipeline once and retain every output, error and exclusion. Report three-class accuracy/macro-F1/confusion, label coverage, preselected-pair precision/recall/F1 and false matches separately from final-group membership. State denominators; these 12 challenge pairs are deliberately selected, not all 153 pairs or a population prevalence estimate. Do not score unannotated pairs as negatives. Never assert model-label disagreement proves a financial factual contradiction.

Status at preparation: **0 independent human labels, 0 holdout model predictions, 0 adjudications.** Human work and independent quality results remain a delivery gate.
