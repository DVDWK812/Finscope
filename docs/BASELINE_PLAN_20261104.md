# New baseline evaluation plan — NOT RUN

This is a prospective plan, not results or human annotations. The consumed frozen
challenge packet, labels, thresholds and evaluation remain untouched. Do not use it
for development, sampling, prompts or this new baseline. No evaluation is authorized
by creating this document; a separate approved packet and explicit run decision are
required.

## Protocol to lock before any inference

- Recruit reviewers and record actual participation/independence only after they
  attest. Have two reviewers label independently without seeing model output;
  adjudicate disagreements separately and preserve both original labels.
- Assemble a new, rights-reviewed packet of 60 distinct English title/summary
  records, with dated provenance, permitted fields and retention. This is a proposed
  sample size, not an obtained corpus. Do not include expired private media, old
  development examples or frozen challenge records. Use an approved held-out split;
  isolate articles from the same event/publisher family to reduce leakage.
- Record title-only versus title+summary, source type, input length and truncation
  policy. Include multi-industry and reasonably unclassified texts; do not force
  balanced coverage by relabeling records. Explicitly flag ambiguous sentiment and
  unsuitable text before scoring.
- Freeze packet SHA-256, taxonomy US-BUSINESS-1 definitions, model manifests,
  prompt/version, exact application SHA and score script before running. Keep
  publisher text and evidence quotes only in storage permitted by its policy.
- Compare the current high-precision dictionary baseline with MiniLM plus the
  selected local semantic model for industry labels. Evaluate pinned FinBERT
  sentiment independently. Do not equate an embedding score or model self-rating
  with calibrated confidence. Do not tune on held-out labels after results.
- Report sentiment confusion matrix, macro-F1, agreement and explicit exclusions;
  report hierarchical multi-label precision/recall/F1 separately at parent and
  child level, coverage, unknown reasons and evidence support. Report denominators
  and uncertainty; do not generalize from small convenience samples.
- Record cold process startup, uncached inference, warm stage inference, persistent
  cache hits, peak RAM/VRAM, failures and pauses separately. Cold process does not
  imply cold OS file cache. No price forecast or causal market-impact claim.

## Empty independent annotation form

Copy one blank row per approved record and reviewer into private, policy-compliant
storage. Do not populate this Git document with private article text or labels.
`parent_ids` and `child_ids` must be valid taxonomy IDs; a known parent can have an
unknown child. Sentiment options: Positive / Neutral / Negative / Mixed-uncertain /
Not-applicable. Record textual tone, not a predicted price move. Evidence quotes
must occur in the actual permitted input. Keep issuer industry separate from topic.

| record_id | packet_hash | reviewer_code | labeled_at | input_fields | sentiment | parent_ids | child_ids | evidence_reference | unknown_reason | issuer_industry_separate | ambiguity_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | | | | |

| record_id | adjudicator_code | adjudicated_at | final_sentiment | final_parent_ids | final_child_ids | decision_reason | original_labels_preserved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

Reviewer attestations (blank): participation ______; independent first pass ______;
conflicts/assistance ______; date ______. No genuine human labels exist in this form.
