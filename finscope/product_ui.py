"""Local-first FinScope product UI. Explicit fetch, save and analysis actions."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from .api_sources import ENV_KEYS, TOPICS, local_credentials
from .local_news import (Analysis, ContentRights, FetchBlocked, LocalIngestionService,
                         LocalNewsStore, NewsItem, SOURCE_NOTES, SOURCE_OPTIONS,
                         analyze_finbert, utcnow)


def local_store():
    return LocalNewsStore(os.environ.get("FINSCOPE_LOCAL_DB", "reports/finscope_local.sqlite3"))


def welcome(store):
    st.caption("WELCOME TO FINSCOPE")
    st.title("Your news. A clearer financial picture.")
    st.write("Fetch financial news, analyze its tone and explore the original evidence — on your computer.")
    steps = [("01", "Choose a news source", "Connect your API key or use the fixed RBA collector."),
             ("02", "Choose an AI model", "Start with local FinBERT; other model options are optional."),
             ("03", "Fetch and analyze", "Preview the text, confirm its permitted use, then run analysis."),
             ("04", "Explore the evidence", "Filter sectors and dates, compare trends and open original articles.")]
    for col, (number, title, text) in zip(st.columns(4), steps):
        with col, st.container(border=True):
            st.caption(number)
            st.subheader(title)
            st.write(text)
    st.caption("Runs on localhost · News and results stay in local SQLite · External LLM calls require a separate consent action")
    if st.button("Get Started", type="primary"):
        store.set_setting("guide_completed", True)
        st.session_state["show_guide"] = False
        st.session_state["workspace_page"] = "Add news"
        st.rerun()


def permission_editor(prefix, *, preview=True):
    """An attestation records a user's rights, never grants publisher rights."""
    with st.expander("Content permissions", expanded=False):
        st.caption("API access does not establish retention, NLP or third-party transmission rights. "
                   "Supply your licence/permission reference; leave unverified uses off.")
        reference = st.text_input("Licence / permission reference", key=prefix+"_reference", max_chars=300)
        retain = st.checkbox("My permission covers local storage of this text", key=prefix+"_retain")
        analyze = st.checkbox("My permission covers local NLP processing", key=prefix+"_analyze")
        external = st.checkbox("My permission covers sending this text to an external LLM", key=prefix+"_external")
    return ContentRights(preview, retain, analyze, external, reference)


def api_source(store):
    label = st.selectbox("News source", list(SOURCE_OPTIONS), key="api_provider")
    provider = SOURCE_OPTIONS[label]
    st.caption(SOURCE_NOTES[provider])
    if provider == "local":
        collector_ui(store)
        return
    with st.form("fetch_news"):
        left, right = st.columns(2)
        with left:
            key = st.text_input(f"{label} API key", type="password", key="key_"+provider, max_chars=500)
            use_env = st.checkbox("Use project .env when the key field is empty", value=True)
            topic = st.selectbox("News topic", list(TOPICS))
        with right:
            symbol = st.text_input("Company ticker", value="NVDA", max_chars=15).strip().upper() if provider == "finnhub" else None
            days = st.number_input("Lookback days (account access may be narrower)", min_value=1, max_value=30, value=2,
                                   disabled=provider == "newsdata")
            remaining = st.number_input("Confirmed available request budget", min_value=0, max_value=10000, value=0)
        preview = st.checkbox("I may access and preview these records locally for my personal noncommercial use")
        quota = st.checkbox("I confirm this request budget is currently available on my account")
        st.caption("One request, at most 3 preview records. Local safety cap: 3 requests/provider/UTC day; 60-second spacing. "
                   "No retries, pagination or publisher-page requests. Keys remain in memory for this browser session.")
        fetch = st.form_submit_button("Fetch news", type="primary", disabled=provider == "newsdata")
    if fetch:
        try:
            if not preview or not quota:
                raise FetchBlocked("Confirm local preview permission and current quota before Fetch")
            credential = key or (local_credentials().get(ENV_KEYS[provider]) if use_env else None)
            rights = ContentRights(preview=True, reference=f"Personal account preview attestation; {label} terms; downstream uses unverified")
            result, items = LocalIngestionService(store).fetch(provider, topic, api_key=credential,
                            rights=rights, remaining=int(remaining), days=int(days), symbol=symbol, explicit=True)
            st.session_state["news_preview"] = items
            st.session_state["fetch_outcome"] = {
                "provider": label, "status": result.status, "outcome": result.outcome,
                "http_status": result.http_status, "records": len(items), "query_utc": utcnow().isoformat(),
            }
        except (ValueError, OSError):
            # Show only our safe reason codes, never low-level SQL/requests errors.
            st.error("Fetch blocked: check preview permission, credentials, quota and the local request holds.")
            # Reasons from FetchBlocked are fixed service-authored strings.
            import sys
            error = sys.exception()
            if isinstance(error, FetchBlocked):
                st.caption(str(error))
        except Exception:
            st.error("Fetch could not complete. The request may have consumed quota; inspect the local request ledger before trying again.")
    preview_news(store)


def preview_news(store):
    outcome = st.session_state.get("fetch_outcome")
    if outcome:
        message = (f"{outcome['provider']} · {outcome['status']} / {outcome['outcome']} · "
                   f"HTTP {outcome['http_status'] or 'unobserved'} · {outcome['records']} records")
        (st.success if outcome["status"] == "ok" else st.warning)(message)
    items = st.session_state.get("news_preview", [])
    if not items:
        return
    st.subheader("News preview")
    st.caption("Fetched successfully does not mean approved for analysis or storage. Only returned headlines/summaries are available; full publisher text was not fetched.")
    st.dataframe(pd.DataFrame([{"Title": n.title, "Source": n.source,
                    "Publication time": n.timestamp or n.publication_date or "Unknown",
                    "Time meaning": n.timestamp_kind, "Summary": n.summary or "Unavailable",
                    "Original URL": n.url} for n in items]), hide_index=True, width="stretch",
                    column_config={"Original URL": st.column_config.LinkColumn()})
    rights = permission_editor("preview")
    if st.button("Save permitted preview to local library"):
        try:
            rights.require("retain")
            for item in items:
                store.save_news(replace(item, rights=rights))
            st.success(f"Saved {len(items)} originals locally. Choose Analyze to continue.")
        except ValueError as error:
            st.error(str(error))


def authored_text(store):
    with st.form("authored_news"):
        title = st.text_input("Title", value="Synthetic chipmaker earnings update", max_chars=160)
        text = st.text_area("Financial text", value="Fictional chipmaker Aster reported a 20 percent rise in revenue and record quarterly profits.", max_chars=1800)
        source = st.text_input("Source / author", value="User-authored development text", max_chars=100)
        origin = st.selectbox("Text origin", ["Synthetic text I authored", "My own or explicitly licensed text"])
        url = st.text_input("Original URL (optional for licensed text)", max_chars=1000)
        reference = st.text_input("Permission reference", value="Authored by me for local noncommercial analysis", max_chars=300)
        kind = st.selectbox("Timestamp meaning", ["submitted", "published", "first_seen"])
        day = st.date_input("Record date (UTC)", value=utcnow().date())
        clock = st.time_input("Record time (UTC)", value=utcnow().time().replace(second=0, microsecond=0, tzinfo=None))
        rights = st.checkbox("I hold local display, storage and NLP rights for this non-private text")
        save = st.form_submit_button("Save approved text", type="primary")
    if save:
        try:
            from .api_sources import Article
            from .demo_pipeline import ApprovedSubmission
            stamp = utcnow() if kind == "submitted" else datetime.combine(day, clock, tzinfo=timezone.utc)
            synthetic = origin.startswith("Synthetic")
            ApprovedSubmission(title+"\n"+text, title, source, stamp, kind,
                "synthetic" if synthetic else "licensed", reference, rights, url or None).validate()
            item = NewsItem.from_article(Article("authored_synthetic" if synthetic else "authored_licensed",
                         title, url, source, text, stamp.isoformat(), kind),
                         ContentRights(True, rights, rights, False, reference))
            store.save_news(item)
            st.success("Original saved locally. Choose Analyze to run the model.")
        except ValueError as error:
            st.error(str(error))


def collector_ui(store):
    st.info("Fixed RBA RSS/HTML collection and permitted local import will be connected in milestone 3.")


def add_news(store):
    st.title("Add news")
    st.write("Connect a source and preview the originals before analysis.")
    api, text = st.tabs(["News connectors", "Approved text"])
    with api:
        api_source(store)
    with text:
        authored_text(store)


def prepare_finbert():
    from .model_assets import assets_present, prepare_models
    ready = all(assets_present(kind) for kind in ("finbert", "minilm"))
    if not ready:
        st.info("Prepare the pinned local model files once before analysis.")
        accepted = st.checkbox("Accept FinBERT CC BY-NC-SA 4.0 and MiniLM Apache-2.0 for noncommercial use")
        if st.button("Prepare local models", disabled=not accepted):
            try:
                with st.spinner("Preparing and verifying pinned model files…"):
                    prepare_models(acknowledge_licenses=True)
                st.rerun()
            except Exception:
                st.error("Model preparation failed. No prediction was substituted.")
    return ready


def analyze(store):
    st.title("Analyze news")
    st.write("Run local FinBERT on permitted headlines and available summaries. Originals are preserved.")
    items = store.list_news()
    if not items:
        st.info("Add news or approved text to your local library first.")
        return
    st.selectbox("Analysis model", ["Local FinBERT"], key="analysis_model")
    ready = prepare_finbert()
    eligible = [n for n in items if n.rights.analyze and n.rights.retain and n.timestamp]
    if len(eligible) != len(items):
        st.caption(f"{len(items)-len(eligible)} records are restricted or lack an exact timestamp. Their original metadata remains available.")
    selected = st.multiselect("Articles to analyze", [n.article_id for n in eligible],
                 format_func=lambda key: next(n.title for n in eligible if n.article_id == key), key="analysis_articles")
    if st.button("Run real AI analysis", type="primary", disabled=not selected or not ready):
        from streamlit_app import cached_pipeline
        successful, failed = 0, 0
        with st.spinner("Running pinned local FinBERT and MiniLM…"):
            for item in eligible:
                if item.article_id not in selected:
                    continue
                try:
                    analyze_finbert(item, store, cached_pipeline())
                    successful += 1
                except Exception:
                    failed += 1
        if successful:
            st.success(f"Saved {successful} actual analyses to local SQLite. Open Dashboard to explore.")
        if failed:
            st.error(f"{failed} analyses failed. No fake prediction was substituted; previous results and originals remain intact.")


def dashboard(store):
    st.title("News intelligence")
    news, latest = store.list_news(), store.latest_analyses()
    st.caption("Local library · Raw original articles · Latest selected model result per article")
    for col, (label, value) in zip(st.columns(4), [("Saved originals", len(news)), ("Analyzed articles", len(latest)),
                      ("Sources", len({n.source for n in news})), ("Pending analysis", len(news)-len(latest))]):
        col.metric(label, value)
    if not news:
        st.info("Your library is ready. Choose Add news to fetch a source or save approved text.")
        return
    counts = pd.DataFrame([{"Sector": sector, "Sentiment": latest[n.article_id].label, "Articles": 1}
                    for n in news if n.article_id in latest for sector in n.sectors])
    if not counts.empty:
        st.bar_chart(counts.pivot_table(index="Sector", columns="Sentiment", values="Articles", aggfunc="sum", fill_value=0), stack=True)
    st.dataframe(pd.DataFrame([{"Title": n.title, "Sector": ", ".join(n.sectors), "Source": n.source,
                   "Time": n.timestamp or n.publication_date or "Unknown", "Sentiment": latest[n.article_id].label if n.article_id in latest else "Not analyzed",
                   "Original URL": n.url} for n in news]), hide_index=True, width="stretch",
                   column_config={"Original URL": st.column_config.LinkColumn()})
    st.download_button("Export local library", json.dumps(store.export(), indent=2), "finscope-local.json", "application/json")


def about():
    st.title("About / Methodology")
    with st.expander("Models and limitations"):
        st.write("Pinned local ProsusAI FinBERT supplies Positive / Neutral / Negative probabilities. "
                 "MiniLM cosine ≥0.80 within 72 hours produces unverified candidate groups. "
                 "Keyword sectors may be incomplete. No event deduplication, contradiction detection or return forecasting is validated.")
        st.write("Frozen challenge: 12/16 scorable sentiment agreement (75%), macro-F1 0.730159; two mixed/uncertain exclusions. "
                 "Selected-pair cosine precision 0.666667. Reviewer independence/completion remain unverified. The consumed packet is never rerun.")
    with st.expander("Licences and storage"):
        st.write("FinBERT: CC BY-NC-SA 4.0, ProsusAI / MIH AI B.V. MiniLM: Apache-2.0. "
                 "Model licences do not grant publisher-content rights. News and analysis persist in your local SQLite library. "
                 "API keys stay in .env or browser-session memory and are never saved to the library/export.")
        st.markdown("[Marketaux terms](https://www.marketaux.com/tos) · [NewsData.io terms](https://newsdata.io/terms) · [Finnhub terms](https://finnhub.io/terms-of-service)")
    with st.expander("Development and evidence"):
        st.write("AI-assisted engineering; team members write the final academic report. See docs/REPORT_SYNOPSIS.md and the preserved evaluation evidence. "
                 "Automated/browser checks do not substitute for three-human usability evidence.")


def main():
    st.set_page_config(page_title="FinScope | Local News Intelligence", page_icon="📈", layout="wide")
    st.markdown("""<style>
    .block-container {max-width:1400px; padding-top:2rem;}
    [data-testid="stMetric"] {background:#f4f8f7; border:1px solid #dce7e3; border-radius:12px; padding:1rem;}
    [data-testid="stSidebar"] {border-right:1px solid #e2e8e6;}
    h1 {letter-spacing:-.035em;}
    @media(max-width:768px){.block-container{padding-left:1rem;padding-right:1rem;}}
    </style>""", unsafe_allow_html=True)
    store = local_store()
    if st.session_state.get("show_guide", not store.setting("guide_completed", False)):
        welcome(store)
        return
    with st.sidebar:
        st.title("FinScope")
        st.caption("LOCAL NEWS INTELLIGENCE")
        page = st.radio("Workspace", ["Dashboard", "Add news", "Analyze", "About / Methodology"], key="workspace_page")
        st.divider()
        st.caption("Local SQLite · Your original records persist")
        if st.button("User Guide"):
            st.session_state["show_guide"] = True
            st.rerun()
    {"Dashboard": dashboard, "Add news": add_news, "Analyze": analyze}.get(page, lambda _store: about())(store)

