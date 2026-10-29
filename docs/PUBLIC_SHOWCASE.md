# Local product and public showcase — 29 October 2026 Sydney

The user's latest architecture instruction separates two entrypoints. The localhost product remains primary and retains its actual provider/model/storage/analytics path. The public URL remains https://finscope-dvdwk812.streamlit.app/ and presents only a synthetic product tour. Earlier hosted inference evidence remains historical; it is not the new website's function.

| Surface | Entry / requirements | Behavior |
|---|---|---|
| Full local product | `streamlit_app.py` / `requirements-local.txt` | Local source preview, permitted actual FinBERT/MiniLM, persistent SQLite, raw originals, source links and analytics |
| Public showcase | `deploy/streamlit_app.py` / `deploy/requirements.txt` | Home, four-step User Guide, synthetic Dashboard/Knowledge Graph/News Explorer and Get FinScope; no functional AI/news input |

`finscope.showcase` imports Streamlit and the standard-library-only `showcase_data` fixtures. It does not import `streamlit_app`, product UI, providers, collectors, model assets/runtime or database modules. The deployment requirements explicitly contain Streamlit and pandas only; neither the local requirements nor PyTorch/Transformers/Ollama are included. The Docker recipe remains a full local-runtime recipe, not a showcase image, and has not been newly built here.

## Public content and boundaries

- 24 authored fictional reports, fictional entities/sources and preset labels. No challenge text, private annotation, publisher story or fabricated publisher URL. Dashboard/graph/explorer carry **Demo Data / Illustrative Preview** labels. Filters change only the fixed sample.
- Sector distribution, sentiment mix, date trends, volume/share indicators and industry heatmap use raw example counts. Missing cells remain missing, not observed neutral market data.
- Graph edges link fictional company/industry/article/source/unverified-candidate nodes. They do not assert financial causation, verified event identity or contradiction detection. Article references resolve only to the sample cards.
- Setup commands target the full local requirements and root entrypoint on localhost:8501. Available local capabilities are separated from optional Ollama/external-model/in-app-collector work still being developed elsewhere. No key input, uploads, fetch/inference controls or user-news database exist on the public site.
- A concise About expander preserves model attribution/weight terms and candidate/sentiment limitations. Evaluation tables, logs, raw benchmark/debug output and extended licence discussions stay in repository evidence, outside the main public interface.

## Verification

Seven acceptance/data tests exercise every public page, navigation, filter counts/reset, graph/article identity, fictional-data boundaries and setup commands while provider HTTP, SQLite connections and local/model-runtime imports are blocked. A separate CI workflow installs only the showcase requirements before running those tests. The existing local/legacy test suite remains required; its tests are not weakened.

Concurrent uncommitted local-product work is expressly excluded from this task. The first whole-workspace baseline had 213 tests with one pre-existing unknown-publication-time expectation failure while those files were being edited. Showcase integration is therefore also checked against an isolated export of committed main plus the exact showcase paths, without copying the other chat's work, private `.env`, news database or models. This is a test snapshot, not a branch/worktree or a replacement checkout.

Verified before the feature commit: **220 tests passed** (213 existing + seven showcase tests) in the isolated committed-main candidate, plus the benchmark dry run. Local showcase browser checks verified landing→guide→dashboard navigation, 24 example originals, Technology filtering to four, graph rendering/references, explorer search to four Aster cards and local setup commands. Phone-width (390 px) Explorer had document width 390 px, with no horizontal overflow; desktop graph rendered at 1280 px. These are agent engineering checks, not human usability.

The unchanged pinned local pipeline also completed one real approved authored p1 smoke with HTTP blocked: Positive 0.9536037445068359 / Negative 0.01961519755423069 / Neutral 0.02678101323544979, **54.85 ms** combined inference, **5.939 s** prepared-file load, one saved synthetic record in a separate ignored test SQLite file. This is local runtime preservation evidence, not public inference or new accuracy. An initial harness used an invalid workspace ID and was rejected before inference; the corrected UUID harness passed. No production behavior/test was relaxed.

## Actual deployment check and compatibility repair

After feature commit `fc065c3e801314cbdf762c6c542fdce073a1010b` was pushed to origin/main, the unchanged public URL opened as **FinScope | Product Showcase** without a preparation prompt. Actual browser navigation verified Home, User Guide, Dashboard Preview, Knowledge Graph, News Explorer and Get FinScope. The hosted dashboard started with **24 fictional originals**; Technology filtering showed **4**, with **50% preset Positive labels**. Graph/card disclosures remained fictional; the Explorer supplied no publisher URLs. Setup used `requirements-local.txt` and the root localhost:8501 command. No credentials, article upload, fetch or inference control was presented. These are agent-operated preview checks, not live financial results or human usability.

The showcase-only workflow [40854256012](https://github.com/DVDWK812/Finscope/actions/runs/40854256012) passed using only public requirements. Initial matrix [40854256048](https://github.com/DVDWK812/Finscope/actions/runs/40854256048) failed on Streamlit 1.50 because the new test used the newer `AppTest.file_uploader` convenience property; the newer job was cancelled after its test/preview steps passed. Retained the failure honestly and repaired the test to use the public `app.get("file_uploader")` query. The no-upload assertion, all existing tests, supported versions and runtime boundaries remain unchanged. The repaired candidate's **220 tests pass**. Exact repair-commit PUSH CI is verified at handover; its final SHA/results stay in ignored local evidence to avoid a claim about this commit's future CI.

No provider requests, challenge inference/tuning, private-record publication, Moodle access or submission occurred in this split. The three members still own the academic report; only the concise synopsis is maintained. Uncommitted local-product changes remain owned elsewhere and excluded, rather than silently incorporated into this release.
