# FinScope MVP report — working draft, 26 October 2026 UTC

Course code: FINS5557 / INFS5557 **pending confirmation in Moodle**. Track A Tech Team, three members; names/contribution approvals and assessment-specific format pending. This draft records executed engineering evidence and separates pending human validation.

## Objective and delivered product

FinScope is a publicly hosted noncommercial financial-text sentiment demonstration. A user submits synthetic, self-authored or explicitly licensed input with a rights attestation. Actual FinBERT probabilities, keyword sector evidence and MiniLM similarity candidates are saved behind a repository interface and reflected in Streamlit Overview, Trends and News Explorer. [Public app](https://finscope-dvdwk812.streamlit.app/). This is an approved-input MVP, not an approved live-news feed, investment adviser or price predictor.

## Design

The existing API feasibility adapters, normalization, cooldowns and durable sampling reservations are preserved and disconnected. The application validates provenance, length, timestamp meaning and URL syntax; it never fetches submitted URLs. Pinned local safetensors models run with remote code/downloads disabled at inference. An explicit setup action prepares hash-verified official assets. FinBERT scores three text-tone labels. Explainable whole-word rules allow multiple sectors and Unclassified. MiniLM uses attention-mask mean pooling and normalized 384-dimensional vectors.

Cosine ≥.80 within 72 hours links to a representative candidate group; raw report IDs/source/time remain intact. Filters apply before selecting a displayed representative. Counts and trends distinguish raw rows from candidate groups and submitted/published/first-seen times. SQLite is a minimal session-scoped repository with bounded capacity, purge-on-access after 24 hours and JSON export. It is temporary free-host storage, not durable authenticated user storage. No private material should be submitted.

## Evidence and quality

See [MVP evaluation](MVP_EVALUATION.md) and committed authored inputs/numeric results. Actual Windows CPU inference agreed with all 12 provisional sentiment labels (4/class; macro-F1 1.00) and all 12 simple sector references. These Codex-authored convenience examples are not independent human labels or a held-out/general accuracy estimate. At the predeclared .80 threshold, semantic-pair precision/recall was .75/1.00; final group-membership precision/recall .60/1.00 across 66 dependent pairs (three true same-event pairs). An opposite-outcome Aster report falsely grouped with positive reports. Similarity is consequently presented as candidate evidence only.

Prepared-file cold model loading took 9.2155 seconds locally; combined per-record warm inference median 61.13 ms; whole-process RSS after work 867.04 MiB, not peak. Three programmatic concurrent workspaces each retained one own record; they are not three human tests. Rejected rights/character/token probes caused no additional FinBERT forwards or rows. Hosted real inference returned .9536037445 positive with Technology evidence, 143 ms combined inference and saved Overview count 1. Initial hosting build/server startup was 97.752 seconds from logs; initial hosted asset/model cold-load and peak memory were unmeasured.

The updated hosted runtime separately measured **6.226 seconds** process-cold model loading from prepared assets and **866.0 MiB current process RSS** after one actual inference (146 ms). A real paraphrase inference took 110 ms, preserving two raw rows in one candidate group; RSS then 868.8 MiB. Missing rights was rejected before loading/inference. Public sharing was enabled. This is a code-update/session-reset check, not an endurance test. Hosting does not require the local computer to stay on.

Offline CI tests use controlled fakes for model boundaries, not model-performance evidence. At this report's drafting milestone, 131 offline tests plus benchmark/sampler/interface/runner/backend dry runs passed. Exact PUSH CI [run 40324915794](https://github.com/DVDWK812/Finscope/actions/runs/40324915794) for `9c51840d95ca7c8c7bc25c0d1db34720f34a36cd` passed both Streamlit matrix jobs; final documentation-head CI is verified separately after push. The authored evaluation is explicit and outside no-network CI.

## Rights, limitations and decisions

FinBERT weight terms are CC BY-NC-SA 4.0, with ProsusAI / MIH AI B.V. attribution; MiniLM is Apache-2.0. No model weights are redistributed in Git. Model licences do not authorize third-party news processing/public redistribution. Marketaux remains conditionally preferred for financial metadata, with reliability/history/quota/useful descriptions/timestamp and public display/retention/inference/derived-output rights unresolved. GDELT remains provisional; its completed failed one-shot is not retried. NewsData's hold remains. No provider calls or restricted article content were added to this MVP.

GO for a limited approved-input course demonstration; **NO-GO for production live-provider integration and validated event deduplication**. Remaining delivery work is independent approved-text annotation, actual three-human feedback, host sleep/restart/resource endurance and final rehearsal/team signoff. Free hosting may sleep or reset data; current model memory leaves limited headroom and no load/SLA guarantee. Text sentiment alone says nothing about market reaction or industry impact.

## Assistance and team review

Codex assisted with repository audit, implementation, fictional evaluation text/provisional labels, tests, deployment operations and this draft. Reported model outputs came from actual CPU inference, distinct from unit mocks. Team members must inspect/understand the code, independently review labels and conclusions, record their own contributions/three-user observations, confirm Moodle's official course code and apply the course's AI disclosure requirements before submission. No human feedback or independent accuracy result is fabricated.
