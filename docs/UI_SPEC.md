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

## Tests and remaining work
`python -m unittest discover -s tests -v` checks the offline adapter, filters, sector/event aggregation and edge cases. The new UI-data tests use only Python standard library. Actual Streamlit browser/runtime smoke testing and user feedback remain outstanding.

Before live connection: approve source rights, define accepted text lengths/headline-only limits, implement ingestion/storage, replace synthetic event IDs with a tested event-clustering system, validate sector sentiment labels and test with at least three target users.
