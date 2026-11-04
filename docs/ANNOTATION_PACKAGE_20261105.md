# New sentiment annotation package — partial, not evaluated

Prepared 5 November 2026 Sydney, local only. Existing frozen evaluation and the
2 November handoff are separate historical evidence. No news requests, production
inference, labels or retention changes were made.

## Actual deliverable

Private ignored directory: `reports/annotation_package_20261105/` (the existing
reports junction resolves to the shared local runtime directory, not public Git).
Contains `records.json`, `manifest.json`, `INSTRUCTIONS.md`, `reviewer_A.xlsx`,
`reviewer_B.xlsx`, `adjudication.xlsx`, and custodian-only `lexicon/`.
The three workbooks contain actual text/IDs/source information. Human labels,
participation, independence and completion timestamps are blank. Distribute only
each reviewer's own workbook plus instructions, not the lexicon or the other form.

**3 eligible title-only RBA records, 0 summaries; shortfall 57 against target 60.**
These are existing real collection records absent from the product news table and
not in the frozen challenge. Their original acquisition file is among preserved
evidence; it was read without alteration. Selection used provenance/history, not
model output. Their brief announcement wording and single publisher seriously limit
sentiment evaluation; reviewers may mark them unsuitable. No class distribution or
accuracy is asserted. They are not a new representative 60-item corpus.

Main DB exclusions: 5 authored development records, 148 already analyzed official
records, 113 SEC filing-index-only records. The 84 private finite media records are
not authorized for reviewer sharing and are excluded; no expiry was extended.
Existing duplicate receipt copies do not count as new samples.

RBA's [copyright notice](https://www.rba.gov.au/copyright/) sections 2/3 cover these
official textual headings under CC BY 4.0 with attribution. The package includes
source URLs, attribution and licence link; no logo, third-party data or full article
text. No RBA endorsement implied. No fresh article pages were requested.

## Fixed baseline and code

Actual official **Loughran–McDonald_MasterDictionary_1993-2025.csv**, official page
updated March 2026. Retrieved via the download linked from the
[authors' page](https://sraf.nd.edu/loughranmcdonald-master-dictionary/), which permits
free academic research use and requires commercial licensing separately. File is
kept locally, not redistributed in reviewer forms or Git.

- SHA-256: `e2d1328682bab7d2187684fb9f5420bb730401c9eefc00daf835edd203f4859d`
- 86,553 rows; 347 positive and 2,345 negative active entries (category flag > 0).
- Case-insensitive `[a-z]+` tokens; count occurrences, no stemming/negation or
  intensifier rules. P>N positive; N>P negative; tie/no match neutral. Record
  `(P-N)/(P+N)` (zero for no match) and separate match coverage. These are fixed
  experimental rules, not changes to production sentiment.

`finscope.paired_sentiment_evaluation` implements lexicon validation/scoring, paired
prediction with an explicitly supplied local backend, and comparison of previously
authorized predictions. It never loads/downloads a model, reads production DB or
contacts a provider. Future runner integration must supply the existing pinned
backend and unchanged resource/lifetime checks. No formal inference executed.
Input tokenizer rejection occurs before both methods; errors are recorded without
replacement Neutral labels. No automatic retries. FinBERT tie order for this
experiment is positive, neutral, negative; highest probability otherwise.

Score CLI: `python -m finscope.paired_sentiment_evaluation locked_bundle.json --output new_results.json`.
Bundle fields: records (id/text/input_sha256), references (ID to lowercase label),
finbert/lexicon (ID to label/input_sha256 and matched for lexicon), lock
(separate_run_authorization, reference_sha256, rules_sha256). Reference hash is
SHA-256 of UTF-8 `json.dumps(references, sort_keys=True, ensure_ascii=False)`;
rules hash is the module bytes. Output cannot overwrite an existing file. This
format is not permission to run; the separate authorization remains required.

Three-class confusion matrices, accuracy, macro-F1 (all three classes, zero F1 for
zero class denominator), coverage, exclusions and failures are implemented. Paired
scores use identical successful IDs; report failures and each method's eligible-set
coverage alongside them. Empty paired sets yield null accuracy/F1, not zero accuracy.
Bootstrap confidence intervals and inter-reviewer statistics are not implemented
in this delivery; decide/lock any additional analysis before viewing predictions.

Experiment preprocessing uses the prior plan's NFC and per-field whitespace
normalization, title then actual summary joined with a newline. Product uses NFKC,
HTML cleaning, body preference and a 1,400-character lead span. Thus this is a
title/summary sentiment comparison, not full-product pipeline evaluation. Exclude
>512 tokens, unavailable rights, empty/non-English/unknown-language text for both
methods. Mixed-uncertain and Not-applicable human labels remain auditable exclusions.

## Next actions and unfinished status

Team: obtain 57 additional new English texts with reviewer-sharing and local
inference rights, or explicitly approve a smaller exploratory scope. No automatic
new collection is authorized. Two reviewers independently fill labels/rationales,
timestamps and attestations; adjudicator preserves originals and records decisions.
Then lock corpus, references, rules, dictionary/model hashes and exact code SHA,
and separately authorize formal predictions. Do not show predictions before labels.

Step 4 has an actual **partial annotation package and development-tested utilities**;
sampling, human reference lock and formal evaluation remain incomplete. Industry
comparison was not executed. Clean Windows, fresh dependency installation and first
real weight download remain pending under step 3.
