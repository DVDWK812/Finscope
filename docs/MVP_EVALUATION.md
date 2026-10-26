# Approved-text MVP evaluation — 26 October 2026 UTC

Actual CPU inference, not mocks. The reproducible inputs and numeric outputs are in `evaluation/authored_demo_v1.json` and `evaluation/authored_demo_results_20261026.json`. No API/publisher text, API reports or credentials were loaded. Labels were assigned before this run by Codex while authoring fictional examples. One example repeats the prior acceptance smoke text. These are provisional convenience labels, **not independent human annotation or a held-out benchmark**.

## Models and method

- FinBERT: `ProsusAI/finbert`, revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`; weight licence CC BY-NC-SA 4.0 (noncommercial attribution to ProsusAI / MIH AI B.V.). [Pinned model card](https://huggingface.co/ProsusAI/finbert/blob/0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031/README.md). Do not substitute the repository software licence for the weight licence.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0. [Pinned model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md). Official attention-mask mean pooling and L2 normalization, 384 dimensions; maximum 256 tokens including special tokens. FinBERT maximum 512. Oversized inputs are rejected, never silently truncated.
- Local safetensors only; all files hash-verified, remote code disabled, CPU one thread, no inference-time download or mock fallback. Runtime: torch 2.14.1+cpu, transformers 5.20.2, huggingface-hub 2.3.0, safetensors 0.8.0, tokenizers 0.23.3. RSS probe psutil 7.2.2.
- Twelve fictional texts: four positive, four negative, four neutral. Three intended same-event pairs and 63 different-event pairs; all 66 unordered pairs evaluated. Nine intended events. Simple keyword sector references cover Technology, Healthcare, Energy, Financials, Materials and Unclassified; multi-label arithmetic is separately regression-tested.
- Cosine threshold **0.80** was declared before running this evaluation, not tuned to these outputs. Candidate groups use a representative within 72 hours and retain all raw rows. Results depend on arrival order and representative choice; same-time ties use stored article IDs. No independent entity/date/event verification exists.

## Observed results

Actual run completed **2026-10-26T12:34:25.738586+00:00**, Windows 11 CPU.

| Measurement | Observed |
|---|---|
| Sentiment agreement with provisional labels | 12/12; accuracy 1.00, macro-F1 1.00 |
| Confusion matrix (actual rows; positive, negative, neutral columns) | positive [4,0,0]; negative [0,4,0]; neutral [0,0,4] |
| Keyword sector exact-set agreement | 12/12 (mostly single-label examples; not a general sector accuracy claim) |
| Pairwise cosine candidates | TP 3, FP 1, FN 0, TN 62; precision .75, recall 1.00, F1 .8571 |
| Pairwise membership in final groups | TP 3, FP 2, FN 0, TN 61; precision .60, recall 1.00, F1 .75 |
| Raw rows / candidate groups / authored events | 12 / 8 / 9 |
| Process-cold model load, prepared local files | 9.2155 seconds, excludes download/install |
| Per-record combined warm FinBERT+embedding inference | 54.79–67.46 ms; median 61.13 ms; excludes queue, token preflight and DB save |
| Whole-process RSS before / after load / after work | 27.52 / 835.86 / 867.04 MiB; snapshots, **not peak memory** |

The important error: p1 (Aster revenue/profit rise) and n3 (Aster revenue decline/loss) have cosine **.852358**, despite opposite outcomes and different authored events. Group membership also links p2 to n3, even though their direct cosine is only **.684459**. A shared representative implies within-group relationships that were not individually verified. Never present cosine as confirmed identity, deduplication correctness, or sentiment consensus. Raw view remains available; the default candidate-group view can hide a contradictory raw label. The app explains its earliest-report representative policy. No threshold change was made after seeing the errors.

Three simultaneous programmatic workspaces each saved exactly their own one actual-model record. End-to-end wall times including the shared model lock were 67.11, 132.65 and 197.63 ms; model portions 61.77, 60.47 and 60.29 ms. This verifies a bounded local concurrency path, **not three human sessions or a hosting load test**. Missing rights, >2,000 characters and a 302-token embedding probe were all rejected; zero extra FinBERT forward batches and no extra row were observed. The generic CLI preview remains deliberately unconfigured; it does not represent this explicit evaluation.

## Public deployment evidence

[FinScope](https://finscope-dvdwk812.streamlit.app/) was deployed from main commit `06dd670d4423d75b941b6e761c2eea1e629927cc`, Python 3.12.15, `deploy/streamlit_app.py`. Build logs show start 12:32:42 UTC and server start 12:34:19.752 UTC (97.752 seconds). The uv resolver could not resolve requests from the CPU index; the host's standard pip fallback succeeded. The host replaced pyarrow 26 with 24 under its own compatibility safeguard. These were actual build observations, not application failures.

Pinned model preparation completed through the explicit setup control. The hosted synthetic chipmaker form produced Positive: positive **.9536037445**, negative **.0196152162**, neutral **.0267810058**, combined inference **143 ms**; Technology evidence `chipmaker`; Overview 1 raw row / 1 candidate group / 1 source. The initial hosted model-load/download time and peak RSS were not instrumented, so are unknown. Later instrumentation reports measured process-cold model load and current RSS separately in System Status. Free-host wakeup, restart endurance, sustained concurrency and three-human feedback remain pending. The local browser first showed Unclassified before the chipmaker keyword correction; the corrected hosted record is Technology. Original evidence was preserved.

## Interpretation and next evidence

The acceptance path works. The sample is tiny, simple, authored with known expected tones and shares entities/templates. The 66 pairs are dependent and highly imbalanced; no confidence interval or population claim is justified. Scores are not calibrated correctness probabilities. Text sentiment is not market direction, sector impact or investment advice. Human reviewers must independently label a broader approved set, especially mixed tone, negation, unfamiliar sectors, cross-company similar reports and same-company contradictory events. Keep original labels/results immutable; version any expanded dataset. Production event deduplication is **not validated**.

Rerun only on authored text with explicitly prepared assets:

```powershell
.venv-ai/Scripts/python.exe -m finscope.demo_evaluation --run-actual-models --output reports/authored_demo_evaluation_NEW_TIMESTAMP.json
```

Public hosting of approved demo input does not clear Marketaux/GDELT/NewsData/Finnhub source rights or production gates. No news-provider request was made.
