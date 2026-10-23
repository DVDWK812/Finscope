"""Synthetic-only FinScope UI. Run: python -m streamlit run streamlit_app.py."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from finscope.ui_data import (
    SENTIMENTS, SECTORS, ArticleRecord, NewsRepository, SyntheticNewsRepository,
    daily_sentiment_counts, filter_articles, headline_metrics,
    sector_sentiment_counts, unique_events,
)

# Keep this order aligned with SENTIMENTS in both charts.
SENTIMENT_COLORS = ["#16856b", "#64748b", "#c0474b"]
EMPTY_MESSAGE = "No records match the current filters. Widen the date range or reset filters."


def record_table(rows: list[ArticleRecord]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Article ID": a.article_id, "Event ID": a.event_id,
        "UTC date": a.timestamp.astimezone(timezone.utc).date().isoformat(),
        "Title": a.title, "Sector(s)": ", ".join(a.sectors),
        "Text sentiment": a.sentiment, "Source": a.source,
    } for a in rows])


def overview(selected: list[ArticleRecord], shown: list[ArticleRecord], event_view: bool) -> None:
    st.subheader("Overview")
    metrics = headline_metrics(selected, shown)
    cards = st.columns(4)
    positive_share = f'{metrics["positive_share"]:.1f}%' if shown else "—"
    for col, (label, value) in zip(cards, [
        ("Raw articles", metrics["raw_articles"]),
        ("Unique events", metrics["unique_events"]),
        ("Sources", metrics["sources"]),
        ("Positive label share", positive_share),
    ]):
        col.metric(label, value)
    unit = "Unique events" if event_view else "Raw articles"
    st.caption(f"Positive share: positive labels / {len(shown)} displayed {unit.lower()}. "
               "Invented labels; no market or sector-impact inference.")
    if not shown:
        st.info(EMPTY_MESSAGE)
        return
    st.subheader("Sentiment by sector")
    table = pd.DataFrame(sector_sentiment_counts(shown)).set_index("Sector")
    st.bar_chart(table, stack=True, color=SENTIMENT_COLORS,
                 x_label="Sector", y_label=unit, height=320)
    st.dataframe(table, width="stretch")
    st.caption("Each multi-sector item counts once in every assigned sector, so sector totals "
               "can exceed the displayed count. Selecting sectors matches any selected label; "
               "the table retains every label on matching items.")


def trends(shown: list[ArticleRecord], event_view: bool, start: date, end: date) -> None:
    st.subheader("Trends")
    if not shown:
        st.info(EMPTY_MESSAGE)
        return
    table = pd.DataFrame(daily_sentiment_counts(shown, start=start, end=end)).set_index("Date")
    # ISO date categories preserve daily ticks, including zero-count days.
    st.line_chart(table, color=SENTIMENT_COLORS, x_label="UTC publication date",
                  y_label="Unique events" if event_view else "Raw articles", height=320)
    st.dataframe(table, width="stretch")
    st.caption("Synthetic publication dates in UTC; missing days have zero demo records. "
               "Event dates use the earliest representative inside the current filter. "
               "Real first-seen dates require a separate label.")


def explorer(selected: list[ArticleRecord], shown: list[ArticleRecord]) -> None:
    st.subheader("News Explorer")
    if not shown:
        st.info(EMPTY_MESSAGE)
        return
    ordered = sorted(shown, key=lambda a: (a.timestamp, a.article_id), reverse=True)
    st.dataframe(record_table(ordered), width="stretch", hide_index=True,
                 column_config={"Title": st.column_config.TextColumn(width="large")})
    records = {a.article_id: a for a in ordered}
    record_id = st.selectbox(
        "Inspect a record", list(records), key="inspected_article",
        format_func=lambda key: f"{records[key].title} · {records[key].source} [{key}]",
    )
    detail = records[record_id]
    with st.container(border=True):
        st.markdown("**Synthetic record details**")
        st.write(detail.title)
        st.write(detail.summary)
        st.caption(f"Article {detail.article_id} · Event {detail.event_id} · {detail.source}")
        st.caption(f"{detail.timestamp.astimezone(timezone.utc).isoformat()} "
                   f"({detail.timestamp_kind}, synthetic) · {', '.join(detail.sectors)} · {detail.sentiment}")
    linked = [a for a in selected if a.event_id == detail.event_id]
    st.markdown(f"**Source reports for this event in the current filter: {len(linked)}**")
    st.dataframe(record_table(linked), width="stretch", hide_index=True)
    st.caption("Reports excluded by filters are not listed. Demo event IDs are predefined; "
               "grouping is not embedding inference or sentiment consensus. "
               "Synthetic records have no publisher links or model confidence scores.")


def status() -> None:
    st.subheader("System Status")
    st.info("Phase 2: NO-GO. This is an offline synthetic interface. "
            "No news provider is approved for live UI display.")
    st.dataframe(pd.DataFrame([
        {"Component": "News API", "State": "Not connected", "Next gate": "Availability, usable text and public-use permissions"},
        {"Component": "FinBERT", "State": "Not connected", "Next gate": "Labeled evaluation and model integration"},
        {"Component": "Sector classification", "State": "Synthetic labels", "Next gate": "Evaluate multi-label mapping"},
        {"Component": "Embedding deduplication", "State": "Synthetic event IDs", "Next gate": "Evaluate event matching precision/recall"},
        {"Component": "Timestamps", "State": "Synthetic publication time", "Next gate": "Separate real publication vs first-seen"},
    ]), width="stretch", hide_index=True)
    st.caption("No API keys are requested or persisted. Source feasibility and licensing gates "
               "remain open; synthetic UI tests cannot clear them.")


def reset_filters(start: date, end: date) -> None:
    # Explicit values also reset browser widgets; deleting keys can leave their
    # old frontend values alive and restore stale filters on the next interaction.
    st.session_state.update(date_range=(start, end), sector=[], source=[],
                            sentiment=[], event_view=True)
    st.session_state.pop("inspected_article", None)


def main() -> None:
    st.set_page_config(page_title="FinScope | Synthetic News Demo", page_icon="📈", layout="wide")
    st.markdown("""
        <style>
        .block-container {padding-top: 1.7rem; max-width: 1280px;}
        [data-testid="stMetric"] {padding: 1rem; border: 1px solid rgba(128,128,128,.22);
            border-radius: .75rem; height: 100%;}
        [data-testid="stMetricLabel"] p {white-space: normal;}
        @media (max-width: 768px) {
            .block-container {padding-left: 1rem; padding-right: 1rem;}
            [data-testid="stHorizontalBlock"] {flex-wrap: wrap; gap: .75rem;}
            [data-testid="stColumn"] {flex: 1 1 calc(50% - .75rem); min-width: 0;}
        }
        </style>
        """, unsafe_allow_html=True)
    # Freeze relative fixtures per session so midnight does not reset date widgets.
    anchor = st.session_state.setdefault("demo_anchor", datetime.now(timezone.utc).date())
    repository: NewsRepository = SyntheticNewsRepository(anchor)
    articles = repository.list_articles()
    if not articles or any(not a.synthetic for a in articles):
        st.error("This prototype requires nonempty synthetic fixtures. Live data is disabled.")
        st.stop()
    all_dates = sorted(a.timestamp.astimezone(timezone.utc).date() for a in articles)
    st.session_state.setdefault("date_range", (all_dates[0], all_dates[-1]))
    st.session_state.setdefault("event_view", True)
    st.title("FinScope")
    st.caption("Sector news exploration · Offline UI prototype")
    st.warning("SYNTHETIC DEMO DATA — all headlines, dates, sources and sentiment labels are invented. "
               "Live APIs, FinBERT and embeddings are not connected. Phase 2 remains NO-GO.", icon="⚠️")
    with st.sidebar:
        st.header("Filter demo news")
        st.caption("Synthetic fixtures · Offline · Dates use UTC")
        dates = st.date_input("Date range (UTC)",
                              min_value=all_dates[0], max_value=all_dates[-1],
                              format="YYYY-MM-DD", key="date_range")
        sectors = st.multiselect("Sector", SECTORS, placeholder="All sectors", key="sector")
        sources = st.multiselect("Source", sorted({a.source for a in articles}),
                                 placeholder="All sources", key="source")
        sentiments = st.multiselect("Text sentiment", SENTIMENTS,
                                    placeholder="All sentiments", key="sentiment")
        event_view = st.toggle("Count unique events", key="event_view",
                               help="Filters apply first. Each event uses its earliest matching report; "
                                    "its sentiment is not a consensus estimate.")
        st.button("Reset filters", on_click=reset_filters,
                  args=(all_dates[0], all_dates[-1]), width="stretch")
        st.divider()
        st.caption("Phase 2: NO-GO · Headline sentiment is not industry impact.")
    complete_dates = len(dates) == 2
    if complete_dates:
        selected = filter_articles(articles, start=dates[0], end=dates[1],
                                   sectors=sectors, sources=sources, sentiments=sentiments)
    else:
        selected = []
        st.info("Select both start and end dates to display results.")
    shown = unique_events(selected) if event_view else selected
    st.caption(f"View: {'Unique events' if event_view else 'Raw articles'} · "
               f"{len(selected)} raw articles · {len(unique_events(selected))} unique events · "
               f"{len(shown)} displayed")
    nav = st.navigation([
        st.Page(lambda: overview(selected, shown, event_view), title="Overview", url_path="overview",
                icon=":material/dashboard:", default=True),
        st.Page(lambda: trends(shown, event_view, dates[0], dates[1]) if complete_dates else None,
                title="Trends", url_path="trends", icon=":material/show_chart:"),
        st.Page(lambda: explorer(selected, shown), title="News Explorer", url_path="explorer",
                icon=":material/article:"),
        st.Page(status, title="System Status", url_path="status", icon=":material/info:"),
    ])
    nav.run()


if __name__ == "__main__":
    main()
