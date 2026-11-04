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
- **Primary evaluation:** pinned FinBERT versus a fixed financial sentiment lexicon
  baseline on exactly the same new texts and human sentiment labels. Choose an
  appropriately licensed financial lexicon (proposed: Loughran–McDonald positive/
  negative lists; [official source](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)), record its exact release/hash and permitted use before obtaining
  or running it. No lexicon file is supplied or downloaded by this plan.
- Use identical source title plus actual nonempty summary, joined by one newline;
  normalize Unicode NFC and whitespace only. No generated summary, article-page
  text, translation or input-dependent extra context. Preserve the exact input hash.
  Predeclare exclusions: non-English/unknown language, empty or unreadable text,
  unavailable rights, and input over FinBERT's fixed 512-token limit. Do not silently
  truncate. Report exclusions for both methods on the same paired comparison set.
- Fixed lexicon rule proposed for approval and freezing: case-insensitive alphabetic
  word tokens, count positive (P) and negative (N) list occurrences (include only
  positive-valued category flags, excluding removed entries), no stemming,
  negation handling or intensifiers; score (P-N)/(P+N) when P+N>0. Positive if P>N,
  Negative if N>P, otherwise Neutral (including no matched words). Report no-match
  coverage separately. These rules/zero threshold must be frozen before labels are
  inspected; any later refinement belongs to another evaluation.
- FinBERT uses the pinned manifest/revision and highest-probability label, with a
  documented deterministic tie rule matching the pinned implementation. No tuning,
  thresholds or model changes on the held-out packet. Human labels describe textual
  financial tone, not price forecasts. Mixed/uncertain and not-applicable labels are
  retained and excluded from the primary three-class score by a rule fixed before
  predictions; publish their counts and both methods' outputs separately if permitted.
- Primary metrics: paired sample count, class distribution, each method's confusion
  matrix, accuracy and macro-F1; paired accuracy/F1 differences with a prespecified
  paired bootstrap (e.g. 2,000 resamples, seed 20261104) and small-sample caveats.
  Report raw two-reviewer agreement before adjudication, coverage and all exclusions.
  Freeze protocol, packet/input hashes, reviewer originals, adjudication, lexicon
  hash/rules, model manifest, preprocessing/scoring code and exact commit before
  inference; store predictions separately and do not revise references after seeing
  them. Independence and annotation completion remain unverified until attested.
- **Optional separate evaluation:** industry dictionary versus MiniLM/local LLM
  topic classification on independently specified industry labels. Report parent/
  child multi-label metrics, unknown reasons and support separately; do not mix
  industry labels into the primary sentiment comparison or treat this optional
  comparison as already run.
- Record cold process startup, uncached inference, warm stage inference, persistent
  cache hits, peak RAM/VRAM, failures and pauses separately. Cold process does not
  imply cold OS file cache. No price forecast or causal market-impact claim.

## Empty independent annotation form

Status: step 4 is a plan only, not completed evaluation. Industry columns below are
optional and separate; leaving them blank does not exclude primary sentiment labels.

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
