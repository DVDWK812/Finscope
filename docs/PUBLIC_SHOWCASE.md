# Local product and public showcase — 29 October 2026 Sydney

**31 October visual redesign:** Milestone A introduces shared dark tokens,
compact native-button navigation, consistent headers and a responsive graph with
integrated inspection. Existing fictional evidence and counting remain unchanged.
233 tests pass before release; see [design and responsive checks](SHOWCASE_REDESIGN.md).
Exact CI and actual hosted acceptance are verified separately after push.

## Human-readable relationship preview — 31 October 2026 Sydney

Article nodes, selectors, word-match lists and News Explorer now share 24 concise
authored headline labels. Full headlines, company/industry, preset sentiment,
publication date, fictional source and distinct summaries remain in hover/details.
Technical codes remain internal, available under collapsed Technical details;
they are not map labels or default article text. Sentiment is written out and
uses consistent colours. Company Focus defaults to Industry → Company → Articles,
with sources hidden until requested. Single-report candidate nodes are omitted.

Only reviewed topics with at least two reports create candidate nodes. Every
such node says **Unverified candidate**; related topics do not establish one event.

| Fictional topic | Internal articles | Review outcome |
|---|---|---|
| Laboratory Expansion Coverage | SYN-001, SYN-002 | Retained C-1-0: laboratory/facility theme; identity unknown |
| Research Updates | SYN-005, SYN-006 | Retained C-2-0: opening and calendar are distinct research announcements |
| Supply Agreement Reports | SYN-013, SYN-014 | Retained C-4-0: supply theme; same contract unconfirmed |
| Prior Harbor meeting/savings pairing | SYN-009, SYN-010 | Removed C-3-0 membership: company alone was insufficient |
| Prior Maple format/calendar pairing | SYN-021, SYN-022 | Removed C-6-0 membership: launch and routine calendar were insufficient |

Other singleton references remain internal without graph nodes. All 24 article
IDs, original titles, dates, companies, industries, sources and preset sentiments
are unchanged. One authored summary replaces its technical cross-reference with
plain language. Every word frequency and matching-ID set is identical to the
previous commit, for the full sample and each company; no counting method changed.

Before release, 231 offline tests, syntax checks and seven dry-run CLI previews
pass. Four added regressions cover readable labels/tooltips, stable references,
reviewed memberships/singletons and article lookup across all three surfaces.
Existing tests remain; isolation guards reject news HTTP, runtime/model imports
and database calls. The local desktop browser renders wrapped readable headlines
and an explicit unverified topic. Exact pushed-main CI and actual deployed
desktop/mobile checks follow push, with evidence/screenshots retained in ignored
`reports/showcase_readable_20261031/`. Agent checks are not human usability evidence.
No local-branch edit, frozen evaluation change or actual provider/model/database
operation is part of this showcase work.

## Graph / word-cloud verification — 30 October 2026 Sydney

Latest branch policy: **main = public showcase; local = full product**. This work fetched/fast-forwarded only main, preserved five unrelated modified files byte-for-byte, and never switched to, reset, merged or pushed local. Setup instructions now explicitly clone the local branch; those displayed commands were not executed.

Corrective commit `52696ebb1add36a546e26cba454f6e6442380178` passed exact PUSH [regression CI](https://github.com/DVDWK812/Finscope/actions/runs/40890750246) (both supported Streamlit jobs) and [showcase isolation CI](https://github.com/DVDWK812/Finscope/actions/runs/40890750229). Its committed-source baseline also passed 223 local tests and seven offline CLI previews. The public URL initially still served the older “Follow the connections” graph without the new perspective/cloud controls; green CI was not reported as deployment success.

Verified source improvements:

- Company focus retains original fictional IDs, titles, 24 distinct summaries, company/industry/source/tone and unverified candidate relationships. Every article node also carries these fields in its tooltip context. Both `from`/`to` and `from_id`/`to_id` edge schemas are preserved; aggregate links retain all supporting article IDs.
- Curved, directional links have understandable colour/dash legends; labels wrap at readable size. Industry network omits source nodes by default to reduce crossings, with an explicit source toggle. The bounded graph canvas can scroll horizontally on phones without widening the page; the article selector provides full details without requiring hover.
- Headline document frequencies still count each authored headline once per word, with exact matching IDs. Generic filler and fictional company names are excluded. Responsive wrapping replaces fixed cloud columns; at 390 px all 16 terms had **zero overlapping text boxes**. Both all-headline and selected-company scopes retain word-to-article drill-down, with stale selections cleared on scope/company changes.
- The browser caught that `st.html` stripped an initial SVG attempt; the final map uses a self-contained inline preview frame with no scripts/assets/network. Actual rendering was checked after that repair, rather than inferred from AppTest alone.
- Public source watching is enabled in main's lightweight configuration. The old inference-specific disabled watcher setting remains historical; local-branch configuration was not edited. Actual hosted acceptance is checked after push, including recovery from the initially stale runtime.

All existing tests remain. Four additional regressions cover node evidence/edge aliases, source visibility, exact frequency evidence and state transitions. The final isolated committed-main candidate passes **227 tests**; all seven offline previews pass. Unchanged isolation guards block provider HTTP, database connections and model/runtime imports while public pages are exercised. No news-provider requests, inference, model downloads, private annotation publication or Moodle action occurred. All 23 frozen challenge/annotation files retain their byte hashes. Exact final SHA/CI and deployed screenshots are recorded at handover and in ignored `reports/showcase_graph_20261030/`.

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


## Knowledge Graph / headline word cloud enhancement — 30 October 2026 Sydney

The public synthetic showcase now offers two complementary relation perspectives.
**Industry network** aggregates the 24 authored reports into fictional
industry → company → reporting-source links, with per-link report counts and a
small sector/company sentiment breakdown. **Company focus** uses deterministic
layered company → original article → candidate/source connections, with
article IDs, original dates, distinct authored illustrative context, potential
candidate membership and original-report detail. Hover tooltips expose the
relationship basis. Grouping remains unverified, with no real-world or causal
claim.

The Knowledge Graph page also includes a dependency-free, headline-derived
**word cloud**. Terms are lowercase English words from authored headlines;
generic filler and company names are excluded. Each report contributes no
more than one count to a term. The default cloud uses the 24 examples; a
selector switches to the chosen company's four headlines. Word size reflects
the actual fictional-example headline-document count, not LLM importance,
statistical significance or observed market frequency. An optional drill-down
lists the exact source examples for a selected word. No publisher content,
private labels, API keys, weights, requests or new deployment dependencies
are introduced. The previous historical synthetic-evidence boundary stands.

This enhancement does not alter or execute the full local app, frozen
sentiment/evaluation packets, provider adapters, inference or model assets.
The deployment and compatibility tests are validated separately after push.
