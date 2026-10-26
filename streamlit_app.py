"""Approved-text AI demo plus the retained illustrative fixture tour."""
from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import asdict
import json
import os
from pathlib import Path
from uuid import uuid4

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


def approved_mode():
    return st.session_state.get("data_mode") == "Approved-text AI demo"


@st.cache_resource(show_spinner=False)
def cached_pipeline():
    from finscope.demo_runtime import load_pipeline
    return load_pipeline()


def approved_workspace():
    from finscope.demo_pipeline import ApprovedDemoRepository, ApprovedSubmission
    from finscope.model_assets import assets_present, prepare_models
    workspace=st.session_state.setdefault("workspace_id",uuid4().hex)
    repository=ApprovedDemoRepository(Path(os.environ.get("FINSCOPE_DEMO_DB_PATH","reports/approved_demo.sqlite3")))
    st.info("Noncommercial research demo · Real FinBERT + MiniLM inference on your approved text. "
            "No news API is connected. Similarity groups are candidates, not verified events.")
    available=all(assets_present(kind) for kind in ("finbert","minilm"))
    if not available:
        st.warning("Demo models need one-time preparation before inference.")
        acknowledge=st.checkbox("Use FinBERT under CC BY-NC-SA 4.0 and MiniLM under Apache-2.0 for this noncommercial demo")
        if st.button("Prepare demo models",disabled=not acknowledge):
            try:
                with st.spinner("Preparing verified model files; this can take a minute…"):
                    prepare_models(acknowledge_licenses=True)
                st.rerun()
            except Exception:
                st.error("Model preparation failed. No input was sent to an inference service. Check System Status or retry preparation later.")
    with st.expander("Analyze approved financial text",expanded=True):
        with st.form("approved_text_form"):
            title=st.text_input("Title",value="Synthetic chipmaker earnings update",max_chars=160)
            text=st.text_area("Financial news text",value="Fictional chipmaker Aster reported a 20 percent rise in revenue and record quarterly profits.",height=120,max_chars=2000)
            origin=st.selectbox("Text provenance",["Synthetic text I authored","My own or explicitly licensed text"])
            source=st.text_input("Source / author",value="User-authored demo",max_chars=100)
            permission=st.text_input("Permission reference",value="Authored by me for this noncommercial demo",max_chars=300)
            url=st.text_input("Original source URL (licensed text only; optional)",max_chars=1000)
            time_kind=st.selectbox("Timestamp meaning",["submitted","published","first_seen"])
            supplied_date=st.date_input("Record date (UTC)",value=datetime.now(timezone.utc).date())
            supplied_time=st.time_input("Record time (UTC)",value=datetime.now(timezone.utc).time().replace(second=0,microsecond=0,tzinfo=None))
            rights=st.checkbox("I have the rights to process and store this text in the demo for up to 24 hours; it contains no private information.")
            st.caption("Up to 2,000 characters; actual model limits are checked without truncation. "
                       "Records belong to this browser session; export before leaving. No URL is fetched.")
            submitted=st.form_submit_button("Run real AI analysis",disabled=not available,type="primary")
        if submitted:
            try:
                timestamp=(datetime.now(timezone.utc) if time_kind=="submitted" else
                           datetime.combine(supplied_date,supplied_time,tzinfo=timezone.utc))
                submission=ApprovedSubmission(text,title,source,timestamp,time_kind,
                              "synthetic" if origin.startswith("Synthetic") else "licensed",permission,rights,url or None)
                submission.validate()  # Rights/size/metadata fail before model loading.
                with st.spinner("Running local FinBERT and sentence embeddings…"):
                    record=cached_pipeline().submit(submission,repository,workspace)
                st.session_state["last_result_id"]=record.article.article_id
                saved_dates=[r.article.timestamp.date() for r in repository.list_records(workspace)]
                st.session_state["date_range"]=(min(saved_dates),max(saved_dates))
                st.success(f"Saved actual model result: {record.article.sentiment} · {record.inference_ms:.0f} ms")
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error("Analysis could not complete. No mock prediction was substituted. Check model readiness in System Status.")
    records=repository.list_records(workspace)
    st.session_state["approved_metadata"]={r.article.article_id:r for r in records}
    last=next((r for r in records if r.article.article_id==st.session_state.get("last_result_id")),None)
    if last:
        st.subheader(f"Latest actual inference: {last.article.sentiment}")
        st.dataframe(pd.DataFrame([last.scores]),hide_index=True,width="stretch")
        st.caption("Model probabilities are not calibrated accuracy or investment advice. "
                   f"Sector evidence: {last.sector_evidence}")
    if records:
        exported=[{"article":{**asdict(r.article),"timestamp":r.article.timestamp.isoformat()},
                   "origin":r.origin,"scores":r.scores,"sector_evidence":r.sector_evidence,
                   "finbert_revision":r.model_revision,"embedding_revision":r.embedding_revision,
                   "permission_reference":r.permission_reference,"sector_rule_version":r.sector_rule_version,
                   "group_status":"candidate_unverified","nearest_cosine":r.similarity} for r in records]
        st.download_button("Export this workspace",json.dumps(exported,indent=2),"finscope-approved-demo.json","application/json")
    return [r.article for r in records]


def record_table(rows: list[ArticleRecord]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Article ID": a.article_id, ("Candidate group ID" if approved_mode() else "Event ID"): a.event_id,
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
        ("Candidate event groups" if approved_mode() else "Unique events", metrics["unique_events"]),
        ("Sources", metrics["sources"]),
        ("Positive label share", positive_share),
    ]):
        col.metric(label, value)
    unit = ("Candidate groups" if approved_mode() else "Unique events") if event_view else "Raw articles"
    st.caption(f"Positive share: positive labels / {len(shown)} displayed {unit.lower()}. "
               + ("Actual model labels on approved demo inputs; candidate grouping is unverified." if approved_mode()
                  else "Invented labels; no market or sector-impact inference."))
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
    st.line_chart(table, color=SENTIMENT_COLORS, x_label="UTC record date" if approved_mode() else "UTC publication date",
                  y_label=("Candidate groups" if approved_mode() else "Unique events") if event_view else "Raw articles", height=320)
    st.dataframe(table, width="stretch")
    st.caption(("Supplied/submitted record dates in UTC; see each record's timestamp meaning. " if approved_mode() else "Synthetic publication dates in UTC; missing days have zero demo records. ")+
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
        st.markdown("**Approved record details**" if approved_mode() else "**Synthetic record details**")
        st.write(detail.title)
        st.write(detail.summary)
        st.caption(f"Article {detail.article_id} · Event {detail.event_id} · {detail.source}")
        st.caption(f"{detail.timestamp.astimezone(timezone.utc).isoformat()} "
                   f"({detail.timestamp_kind}) · {', '.join(detail.sectors)} · {detail.sentiment}")
        if approved_mode():
            metadata=st.session_state.get("approved_metadata",{}).get(detail.article_id)
            if metadata:
                st.write(metadata.scores)
                st.caption(f"Sector rules matched: {metadata.sector_evidence}")
                st.caption(f"Permission reference: {metadata.permission_reference} · Rules {metadata.sector_rule_version}")
                st.caption(f"Nearest representative cosine: {metadata.similarity}; candidate grouping only, no confirmed event identity.")
                st.caption(f"FinBERT {metadata.model_revision} · MiniLM {metadata.embedding_revision}")
            if detail.url:st.link_button("Original source",detail.url)
    linked = [a for a in selected if a.event_id == detail.event_id]
    st.markdown(f"**{'Reports in this candidate group' if approved_mode() else 'Source reports for this event'} in the current filter: {len(linked)}**")
    st.dataframe(record_table(linked), width="stretch", hide_index=True)
    if approved_mode():
        st.caption("Raw reports and candidate groups are different counts. Groups use cosine ≥0.80 within 72 hours; event identity is unverified. "
                   "The earliest matching report supplies the displayed label, not a sentiment consensus.")
        return
    st.caption("Reports excluded by filters are not listed. Demo event IDs are predefined; "
               "grouping is not embedding inference or sentiment consensus. "
               "Synthetic records have no publisher links or model confidence scores.")


def status() -> None:
    st.subheader("System Status")
    if approved_mode():
        st.info("Approved-input MVP · News-provider production approval remains NO-GO. "
                "FinBERT/MiniLM run on synthetic or user-approved licensed text only.")
        st.write({"news_apis":"Not connected","models":"Pinned local CPU backends; no mock fallback",
                  "grouping":"Candidate similarity groups, not confirmed events","storage":"Session-scoped SQLite; 24-hour retention; free-host restarts may clear storage",
                  "limits":"2,000 characters; FinBERT 512 tokens; MiniLM 256; 100 records per workspace"})
        st.markdown("FinBERT: CC BY-NC-SA 4.0 · MiniLM: Apache-2.0. No production data-source approval is claimed.")
        return
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
    st.set_page_config(page_title="FinScope | Financial Text Intelligence", page_icon="📈", layout="wide")
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
    st.sidebar.radio("Data workspace",["Approved-text AI demo","Illustrative fixture tour"],key="data_mode")
    if st.session_state.get("active_data_mode")!=st.session_state["data_mode"]:
        for key in ("date_range","sector","source","sentiment","inspected_article"):
            st.session_state.pop(key,None)
        st.session_state["active_data_mode"]=st.session_state["data_mode"]
    st.title("FinScope")
    st.caption("Financial text intelligence · Sentiment, sectors and candidate event groups")
    if approved_mode():
        articles=approved_workspace()
    else:
        repository: NewsRepository = SyntheticNewsRepository(anchor)
        articles = repository.list_articles()
    if not approved_mode() and (not articles or any(not a.synthetic for a in articles)):
        st.error("This prototype requires nonempty synthetic fixtures. Live data is disabled.")
        st.stop()
    all_dates = sorted(a.timestamp.astimezone(timezone.utc).date() for a in articles) or [datetime.now(timezone.utc).date()]
    st.session_state.setdefault("date_range", (all_dates[0], all_dates[-1]))
    st.session_state.setdefault("event_view", True)
    if not approved_mode():st.warning("SYNTHETIC DEMO DATA — all headlines, dates, sources and sentiment labels are invented. "
               "Live APIs, FinBERT and embeddings are not connected. Phase 2 remains NO-GO.", icon="⚠️")
    with st.sidebar:
        st.header("Filter records")
        st.caption("Dates use UTC · source and timestamp meanings stay attached")
        dates = st.date_input("Date range (UTC)",
                              min_value=all_dates[0], max_value=all_dates[-1],
                              format="YYYY-MM-DD", key="date_range")
        sectors = st.multiselect("Sector", SECTORS, placeholder="All sectors", key="sector")
        sources = st.multiselect("Source", sorted({a.source for a in articles}),
                                 placeholder="All sources", key="source")
        sentiments = st.multiselect("Text sentiment", SENTIMENTS,
                                    placeholder="All sentiments", key="sentiment")
        event_view = st.toggle("Count candidate groups" if approved_mode() else "Count unique events", key="event_view",
                               help="Filters apply first. Each event uses its earliest matching report; "
                                    "its sentiment is not a consensus estimate.")
        st.button("Reset filters", on_click=reset_filters,
                  args=(all_dates[0], all_dates[-1]), width="stretch")
        st.divider()
        st.caption("Live-provider approval pending · Text sentiment is not industry impact." if approved_mode()
                   else "Phase 2: NO-GO · Headline sentiment is not industry impact.")
    complete_dates = len(dates) == 2
    if complete_dates:
        selected = filter_articles(articles, start=dates[0], end=dates[1],
                                   sectors=sectors, sources=sources, sentiments=sentiments)
    else:
        selected = []
        st.info("Select both start and end dates to display results.")
    shown = unique_events(selected) if event_view else selected
    group_label="candidate groups" if approved_mode() else "unique events"
    st.caption(f"View: {group_label if event_view else 'Raw articles'} · "
               f"{len(selected)} raw articles · {len(unique_events(selected))} {group_label} · "
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
