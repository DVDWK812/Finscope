# UI prototype — Synthetic demonstration only

## Objective
Develop the interactive financial-news interface in parallel with Phase 1 source evaluation without claiming that a production news API, FinBERT model or event classifier is ready.

## Run locally
From the repository root, install `requirements.txt`, then run `streamlit run streamlit_app.py`. There are no API keys, database prerequisites or network requests. The app runs against synthetic fixtures only.

## Pages
- Overview: raw articles versus unique event counts, source count, selected positive-text share and sector-by-sentiment chart/table.
- Trends: daily sentiment counts using the selected time range and article/event view.
- News Explorer: filtered headlines, source, sector labels, event ID and drill-down details.
- System Status: explicitly unconnected sources/models and remaining production gates.

## Shared data contract
`finscope/ui_data.py` defines `ArticleRecord` and `NewsRepository`. Each record has an article ID, event ID, title, source, zero-or-more optional summary text, one or more sector labels, Positive/Neutral/Negative *text* sentiment, timezone-aware timestamp, explicit `published` vs `first_seen` semantics, and a `synthetic` flag. Its synthetic fixtures have no external news URLs.

The eventual approved adapter should satisfy this contract, but is intentionally absent. API ingestion and inference must not be performed on page load, and real news must not be enabled until public-display/storage/derived-output rights and input quality are resolved.

## Counting semantics
- Filters apply before counting or grouping.
- Raw-article count is the number of filtered source reports; unique-event count is distinct `event_id` within the filter.
- The event toggle chooses the deterministic earliest `(timestamp, article_id)` representative in a filtered group for *UI demonstration only*. This is **not** embedding clustering, model consensus or a validated sentiment aggregation policy.
- An item tagged with two sectors contributes to both sector totals, so the sum of sector totals can exceed the record count.
- The positive-text share is not a return prediction, bullish-sector probability or target-specific sector impact.
- Real GDELT `first_seen` times cannot be presented as publisher publication times.

The chart axes, shared result caption and positive-label denominator name the active counting view. Sources are counted from filtered raw reports, including reports collapsed by event grouping. Sector charts retain all labels on matching items (sector selection uses OR); Healthcare + Technology therefore matches a multi-sector article once before grouping, but contributes to both sector totals. Daily trends fill zero-count days across the selected UTC date range. Empty results show an unavailable positive share rather than implying an observed 0%.

Filters persist across all four pages. Reset explicitly updates browser widget values; it also restores the complete fixture date range and event mode. Relative fixture dates are fixed per browser session to avoid a midnight reset. Explorer exposes article IDs and all source reports for the selected event within the current filters, including reports collapsed from event view. A runtime guard rejects non-synthetic records.

## Tests and remaining work
After installing requirements, `python -m unittest discover -s tests -v` checks the offline adapter and Streamlit runtime. Streamlit AppTest covers filters, reset, incomplete dates, empty pages, event drill-down, counting modes and the synthetic-only guard with HTTP transport blocked. UI-data tests also cover UTC date boundaries, gap filling and multi-sector aggregation. CI tests both minimum Streamlit 1.50.0 and the current permitted release on Python 3.11.

On 24 October 2026, all 66 tests and benchmark dry runs passed locally on Python 3.12.3 with Streamlit 1.50.0 and 1.66.1 / pandas 2.3.3. Browser smoke checks exercised navigation, retained date/sector filters, negative-label empty results, reset followed by another interaction, multi-sector event reports, and raw/event switching. Phone/tablet layout checks showed wrapped metric cards and no document-width overflow. Ignored local screenshots under `reports/ui_*_synthetic.jpg` are demonstration evidence only. This is not a target-user usability study or an exhaustive browser/device certification.

Run with the project virtual environment, for example `.venv/Scripts/python.exe -m streamlit run streamlit_app.py` in PowerShell. Restart Streamlit after dependency or imported-helper signature changes; reload the browser afterward. The repository theme keeps sentiment colors and spacing consistent, and disables Streamlit usage statistics for this offline prototype. No live-provider connectivity is tested by these UI checks.

Runtime API references: [Streamlit dataframe width](https://docs.streamlit.io/develop/api-reference/data/st.dataframe), [native chart options](https://docs.streamlit.io/develop/api-reference/charts/st.bar_chart), [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).

Before live connection: approve source rights, define accepted text lengths/headline-only limits, implement ingestion/storage, replace synthetic event IDs with a tested event-clustering system, validate sector sentiment labels and test with at least three target users.
