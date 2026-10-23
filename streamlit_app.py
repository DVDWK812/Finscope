"""FinScope demonstration UI. Run: streamlit run streamlit_app.py.

Only synthetic examples are loaded. No API requests or model inference occur.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from finscope.ui_data import (
    SENTIMENTS,
    SECTORS,
    SyntheticNewsRepository,
    daily_sentiment_counts,
    filter_articles,
    headline_metrics,
    sector_sentiment_counts,
    unique_events,
)

st.set_page_config(page_title="FinScope | Financial News Intelligence", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.7rem; max-width: 1280px;}
    [data-testid="stMetric"] {padding: 1rem; border: 1px solid rgba(128,128,128,.22); border-radius: .75rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

ALL = SyntheticNewsRepository().list_articles()

st.title("FinScope")
st.caption("Sector-level financial news intelligence · Exploratory UI prototype")
st.warning(
    "SYNTHETIC DEMO DATA — all displayed headlines, dates, sources and sentiment labels "
    "are invented for UI testing. Live news ingestion and AI inference are not connected. "
    "No trading or sector-impact conclusions should be drawn.",
    icon="⚠️",
)

with st.sidebar:
    st.header("Explore news")
    st.caption("Data mode: Synthetic fixtures · Offline")
    all_dates = sorted(a.timestamp.date() for a in ALL)
    dates = st.date_input("Date range (UTC)", value=(all_dates[0], all_dates[-1]),
                          min_value=all_dates[0], max_value=all_dates[-1])
    sectors = st.multiselect("Sector", SECTORS, placeholder="All sectors")
    sources = st.multiselect("Source", sorted({a.source for a in ALL}), placeholder="All sources")
    sentiments = st.multiselect("Text sentiment", SENTIMENTS, placeholder="All sentiments")
    event_view = st.toggle("Count unique events", value=True,
                           help="Groups records by demo event ID after filtering. Representative sentiment is not a consensus estimate.")
    st.divider()
    st.caption("Phase 1: data provider feasibility unresolved. Headline sentiment is not industry impact.")

if len(dates) == 2:
    selected = filter_articles(ALL, start=dates[0], end=dates[1],
                               sectors=sectors, sources=sources, sentiments=sentiments)
else:
    selected = []
    st.info("Select both start and end dates to display results.")
shown = unique_events(selected) if event_view else selected


def overview() -> None:
    st.subheader("Market overview")
    metrics = headline_metrics(selected, shown)
    cards = st.columns(4)
    for col, (label, value) in zip(cards, [
        ("Raw articles", metrics["raw_articles"]),
        ("Unique events", metrics["unique_events"]),
        ("Sources", metrics["sources"]),
        ("Positive text sentiment", f'{metrics["positive_share"]:.1f}%'),
    ]):
        col.metric(label, value)
    st.caption("Positive share uses the selected article/event view. It is not a prediction of asset returns.")
    st.subheader("Sentiment by sector")
    table = pd.DataFrame(sector_sentiment_counts(shown)).set_index("Sector")
    st.bar_chart(table, stack=True, x_label="Sector", y_label="Number of records")
    st.dataframe(table, use_container_width=True)
    st.caption("Multi-sector items count once within each relevant sector; sector totals may exceed the displayed record count.")


def trends() -> None:
    st.subheader("News sentiment over time")
    if not shown:
        st.info("No records match the current filters.")
        return
    table = pd.DataFrame(daily_sentiment_counts(shown)).set_index("Date")
    st.line_chart(table, x_label="UTC date", y_label="Number of records")
    st.dataframe(table, use_container_width=True)
    st.caption("The demo uses synthetic publication dates. Real GDELT first-seen dates must be labeled separately.")


def explorer() -> None:
    st.subheader("News explorer")
    if not shown:
        st.info("No records match the current filters.")
        return
    ordered = sorted(shown, key=lambda a: (a.timestamp, a.article_id), reverse=True)
    st.dataframe(pd.DataFrame([{
        "UTC date": a.timestamp.date().isoformat(), "Title": a.title,
        "Sector(s)": ", ".join(a.sectors), "Text sentiment": a.sentiment,
        "Source": a.source, "Event ID": a.event_id,
    } for a in ordered]), use_container_width=True, hide_index=True)
    options = {f"{a.title} · {a.source} [{a.article_id}]": a for a in ordered}
    detail = options[st.selectbox("Inspect a record", list(options))]
    st.subheader(detail.title)
    st.write(detail.summary)
    st.caption(
        f"{detail.source} · {detail.timestamp.isoformat()} ({detail.timestamp_kind}) · "
        f"{', '.join(detail.sectors)} · {detail.sentiment} · event {detail.event_id}"
    )
    linked = [a for a in selected if a.event_id == detail.event_id]
    st.write(f"Related reports in current filter: {len(linked)}")
    st.caption("Synthetic records have no external publisher links or model confidence scores.")


def status() -> None:
    st.subheader("Data & model status")
    st.info("The current app is an offline interface prototype. No financial-news provider is approved for live UI display.")
    st.table(pd.DataFrame([
        {"Component": "News API", "State": "Not connected", "Next gate": "Availability, usable text and public-use permissions"},
        {"Component": "FinBERT", "State": "Not connected", "Next gate": "Labeled evaluation and model integration"},
        {"Component": "Sector classification", "State": "Synthetic labels", "Next gate": "Evaluate multi-label mapping"},
        {"Component": "Embedding deduplication", "State": "Synthetic event IDs", "Next gate": "Evaluate event matching precision/recall"},
        {"Component": "Timestamps", "State": "Synthetic publication time", "Next gate": "Separate real publication vs first-seen"},
    ]))
    st.caption("No user API keys are requested or persisted by this prototype.")

nav = st.navigation([
    st.Page(overview, title="Overview", icon=":material/dashboard:"),
    st.Page(trends, title="Trends", icon=":material/show_chart:"),
    st.Page(explorer, title="News Explorer", icon=":material/article:"),
    st.Page(status, title="System Status", icon=":material/info:"),
])
nav.run()
