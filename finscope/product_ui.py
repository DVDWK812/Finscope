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


def next_step(label, page, key):
    def navigate():
        st.session_state["workspace_page"] = page
    st.button(label, key=key, on_click=navigate)


def saved_handoff(items):
    st.session_state["new_news_ids"] = [n.article_id for n in items]
    st.session_state["handoff_article_ids"] = [n.article_id for n in items]


def welcome(store):
    st.caption("WELCOME TO FINSCOPE")
    st.title("Your news. A clearer financial picture.")
    st.write("Fetch financial news, analyze its tone and explore the original evidence — on your computer.")
    steps = [("01", "Choose a news source", "Connect your API key or use the fixed RBA collector."),
             ("02", "Fetch and select news", "Preview actual records and confirm their permitted use."),
             ("03", "Choose a model and analyze", "Start with local FinBERT; no model API key is needed."),
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
    def clear_preview():
        for key in ("news_preview", "fetch_outcome", "preview_saved", "public_collection_report"):
            st.session_state.pop(key, None)
    label = st.selectbox("News source", list(SOURCE_OPTIONS), key="api_provider", on_change=clear_preview)
    provider = SOURCE_OPTIONS[label]
    st.caption(SOURCE_NOTES[provider])
    if provider == "local":
        collector_ui(store)
        return
    env_key = local_credentials().get(ENV_KEYS[provider])
    status = LocalIngestionService(store).source_status(provider, configured=bool(st.session_state.get("key_"+provider) or
                (env_key if st.session_state.get('env_'+provider,True) else None)))
    st.caption(f"{status.state} · {status.reason}")
    if status.last_attempt:
        with st.expander("Last source attempt"):
            st.caption(f"{status.last_attempt} · {status.last_outcome} · holds use UTC days")
    with st.form("fetch_news_"+provider):
        left, right = st.columns(2)
        with left:
            key = st.text_input(f"{label} API key", type="password", key="key_"+provider, max_chars=500)
            use_env = st.checkbox("Use project .env when the key field is empty", value=True, key="env_"+provider)
            topic = st.selectbox("News topic", list(TOPICS), key="topic_"+provider) if provider != "finnhub" else "technology"
        with right:
            symbol = st.text_input("Company ticker", value="NVDA", max_chars=15, key="ticker_finnhub").strip().upper() if provider == "finnhub" else None
            days = (2 if provider == 'newsdata' else st.number_input("Lookback days (account access may be narrower)",
                                   min_value=1, max_value=30, value=2))
            remaining = st.number_input("Confirmed available request budget", min_value=0, max_value=10000, value=0)
        preview = st.checkbox("I may access and preview these records locally for my personal noncommercial use")
        quota = st.checkbox("I confirm this request budget is currently available on my account")
        with st.expander('Request safeguards'):
            st.caption("One request, up to 3 records; 3 requests/provider/UTC day, 60-second spacing, existing holds preserved; no automatic retries or publisher-page requests.")
        fetch = st.form_submit_button("Fetch news", type="primary", disabled=status.blocked)
    if fetch:
        try:
            if not preview or not quota:
                raise FetchBlocked("Confirm local preview permission and current quota before Fetch")
            credential = key or (local_credentials().get(ENV_KEYS[provider]) if use_env else None)
            rights = ContentRights(preview=True, reference=f"Personal account preview attestation; {label} terms; downstream uses unverified")
            result, items = LocalIngestionService(store).fetch(provider, topic, api_key=credential,
                            rights=rights, remaining=int(remaining), days=int(days), symbol=symbol, explicit=True)
            st.session_state["news_preview"] = items
            st.session_state["preview_saved"] = False
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
        http = (str(outcome["http_status"]) if outcome["http_status"] is not None else
                "unobserved" if outcome.get("network_attempted",True) else "not requested")
        message = (f"{outcome['provider']} · {outcome['status']} / {outcome['outcome']} · "
                   f"HTTP {http} · {outcome['records']} records")
        (st.success if outcome["status"] == "ok" else st.warning)(message)
        if outcome["status"] == "failed":
            st.caption(f"Attempt: {outcome.get('query_utc', 'unknown time')}. Read the source status above for current holds; no automatic retry.")
    items = st.session_state.get("news_preview", [])
    if not items:
        return
    st.subheader("News preview")
    st.caption("Select headlines/summaries to keep; storage and NLP require the permissions below.")
    # Avoid the dataframe's built-in CSV download before retention is permitted.
    for n in items:
        with st.container(border=True):
            st.checkbox("Select this article", value=True, key="preview_select_"+n.article_id)
            st.text(n.title)
            st.caption(f"{n.source} · {n.timestamp or n.publication_date or 'Unknown time'} ({n.timestamp_kind})")
            st.text(n.summary or "Summary unavailable")
            if n.provider in {"rba_rss","rba_html","abs_html","accc_rss"}:
                try:
                    st.caption(json.loads(n.provenance).get("attribution","Reserve Bank of Australia"))
                except (ValueError,TypeError):
                    pass
            st.link_button("Open original article", n.url)
    def source_licensed(item):
        try:return item.rights.retain and json.loads(item.provenance).get('source_license_applied') is True
        except (ValueError,TypeError):return False
    licensed=all(source_licensed(item) for item in items)
    if licensed:
        st.caption('Registered CC BY 4.0 text: local storage and NLP permitted with saved attribution; external sending remains off.')
        rights=None
    else:
        rights=permission_editor("preview")
    if st.button("Save permitted preview to local library"):
        try:
            selected = [n for n in items if st.session_state.get("preview_select_"+n.article_id)]
            if not selected:
                raise ValueError("Select at least one preview article")
            prepared=[]
            for item in selected:
                granted=item.rights if source_licensed(item) else rights
                granted.require('retain')
                prepared.append(replace(item,rights=granted))
            for item in prepared:
                store.save_news(item)
            saved_handoff(selected)
            st.success(f"Saved {len(selected)} selected originals locally.")
            st.session_state["preview_saved"] = True
        except ValueError as error:
            st.error(str(error))
    if st.session_state.get("preview_saved"):
        next_step("Analyze selected news →", "Analyze", "preview_next")


def authored_text(store):
    st.caption('Development fixtures stay labelled synthetic; licensed text requires your permission reference.')
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
            saved_handoff([item])
            st.session_state["authored_saved"] = True
            st.success("Original saved locally.")
        except ValueError as error:
            st.error(str(error))
    if st.session_state.get("authored_saved"):
        next_step("Analyze saved text →", "Analyze", "authored_next")


def collector_ui(store):
    from .local_collectors import SOURCES, collect_rba, import_output
    def clear_fixed_preview():
        for key in ('news_preview','fetch_outcome','preview_saved','public_collection_report'):
            st.session_state.pop(key,None)
    source_id=st.radio("Fixed collector source",list(SOURCES),format_func=lambda key:SOURCES[key]["label"],key='fixed_source',on_change=clear_fixed_preview)
    config=SOURCES[source_id]
    if source_id in {'abs_html','accc_rss'}:
        licensed_collector_ui(store,source_id,config)
        return
    kind=config["kind"]
    st.caption("Fixed RBA central-bank feed/index only; not a general crawler or multi-sector news feed.")
    status=LocalIngestionService(store).source_status('rba',configured=True)
    st.caption(f'{status.state} · {status.reason}')
    preview=st.checkbox("I may preview these official RBA records locally",key="rba_preview_rights")
    rights=ContentRights(preview=preview,reference="Personal local RBA preview attestation; downstream rights unverified")
    if st.button("Collect RBA news",type="primary",disabled=not preview or status.blocked):
        try:
            items=collect_rba(LocalIngestionService(store),kind,rights,explicit=True)
            st.session_state["news_preview"]=items
            st.session_state["preview_saved"] = False
            st.session_state["fetch_outcome"]={"provider":"RBA "+kind,"status":"ok","outcome":"records" if items else "empty",
                        "http_status":200,"records":len(items),"query_utc":utcnow().isoformat()}
        except (ValueError,OSError):
            st.error("Collection blocked or failed. Check preview permission and local request holds; no retry was made.")
    with st.expander("Import existing RBA collector output",expanded=False):
        st.caption("Select an existing articles.json from the fixed local collector. Import is local and makes no requests; unknown dates stay unknown.")
        uploaded=st.file_uploader("RBA collector JSON",type=["json"],key="rba_import_json")
        if st.button("Preview imported records",disabled=uploaded is None or not preview):
            try:
                items=import_output(uploaded.getvalue(),rights)
                st.session_state["news_preview"]=items
                st.session_state["preview_saved"] = False
                st.session_state["fetch_outcome"]={"provider":"Local RBA import","status":"ok","outcome":"records",
                              "http_status":None,"records":len(items),"query_utc":utcnow().isoformat(),"network_attempted":False}
            except ValueError as error:
                st.error(str(error))
    preview_news(store)


def licensed_collector_ui(store,source_id,config):
    from .public_sources import collect_source
    service=LocalIngestionService(store)
    state=service.source_status(config['bucket'],configured=True)
    if not config.get('enabled'):
        st.warning('Unavailable · '+config['access_status'])
        st.link_button('Source licence and exclusions',config['terms_url'])
        return
    st.caption(f"{state.state} · {config['scope']}")
    if state.blocked:st.warning(state.reason)
    st.link_button('Source licence and exclusions',config['terms_url'])
    limit=st.number_input('Records to parse from one response',min_value=1,max_value=50,value=30,key=source_id+'_parse_limit',
        help='Record count is separate from HTTP budget: at most two GETs (robots + one fixed entry), no pagination/retry or linked article fetching.')
    if st.button('Fetch official news',type='primary',disabled=state.blocked):
        try:
            with st.spinner('Reading robots and one fixed source…'):
                items,report=collect_source(service,source_id,limit=int(limit),explicit=True)
            st.session_state['news_preview']=items
            st.session_state['preview_saved']=False
            st.session_state['public_collection_report']=report
            st.session_state['fetch_outcome']={'provider':config['label'],'status':'ok','outcome':'records',
                'http_status':200,'records':len(items),'query_utc':report['query_utc']}
            st.rerun()
        except (FetchBlocked,OSError) as error:
            st.error(str(error) if isinstance(error,FetchBlocked) else 'Local collection evidence could not be saved; inspect the request ledger before another attempt.')
    report=st.session_state.get('public_collection_report')
    if report:
        st.caption(f"{len(report['requests'])}/{report['http_request_budget']} HTTP requests · {report['records']} parsed records · {config['license']}")
    preview_news(store)


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
    st.write("Choose a model and run it on permitted headlines and available summaries. Originals are preserved.")
    items = store.list_news()
    if not items:
        st.info("Add news or approved text to your local library first.")
        next_step("Choose a news source →", "Add news", "analysis_empty_next")
        return
    from .model_ui import controls,execute
    from .model_providers import ModelError
    options=controls(store=store)
    if options.mode=="Local FinBERT" and not options.ready:
        options.ready=prepare_finbert()
    from .dashboard_ui import shared_filters
    analyses = store.list_analyses()
    current_model = options.result_key()
    items,results,_,_=shared_filters(items,analyses,for_analysis=True,analysis_model=current_model)
    queue=st.radio("Analysis queue",["Pending for selected model", "All permitted articles"],horizontal=True,key="analysis_queue")
    if queue == "Pending for selected model":
        items = [n for n in items if n.article_id not in results]
    eligible = [n for n in items if n.rights.analyze and n.rights.retain]
    if not eligible:
        st.info('No permitted pending news for this model.' if queue.startswith('Pending') else 'No permitted news matches these filters.')
    if len(eligible) != len(items):
        st.caption(f"{len(items)-len(eligible)} records have unverified local NLP/storage permission. Review permissions in News Explorer.")
    ids = [n.article_id for n in eligible]
    previous = st.session_state.get("analysis_articles", st.session_state.get("handoff_article_ids", []))
    st.session_state["analysis_articles"] = [key for key in previous if key in ids]
    def select_batch():
        st.session_state["analysis_articles"] = ids
    st.button("Select all pending" if queue.startswith("Pending") else "Select all shown", on_click=select_batch,disabled=not ids)
    selected = st.multiselect("Articles to analyze", ids,
                 format_func=lambda key: next(n.title for n in eligible if n.article_id == key), key="analysis_articles")
    if st.button("Run real AI analysis", type="primary", disabled=not selected or not options.ready):
        if options.mode=="OpenAI API" and len(selected)>10:
            st.error("Choose at most 10 originals for one external run.")
            return
        successful, failed = 0, 0
        reasons=set()
        with st.spinner("Running the selected model…"):
            for item in eligible:
                if item.article_id not in selected:
                    continue
                try:
                    execute(item,store,options)
                    successful += 1
                except (ModelError,ValueError) as error:
                    failed += 1
                    if isinstance(error,ModelError):
                        reasons.add(str(error))
                except Exception:
                    failed += 1
        if successful:
            st.success(f"Saved {successful} analyses locally.")
            st.session_state["analysis_completed_model"] = current_model
        if failed:
            st.error(f"{failed} analyses failed; previous results remain saved.")
            for reason in reasons:
                st.caption(reason)
            if not reasons:
                st.caption('The local model could not run; check model files/runtime in Settings / Help and use Prepare local models if needed.')
    if st.session_state.get("analysis_completed_model"):
        def view_results():
            st.session_state["workspace_page"] = "Dashboard"
            st.session_state["local_result_model"] = st.session_state["analysis_completed_model"]
        st.button("View sector results →", on_click=view_results, key="analysis_next")


def dashboard(store):
    from .dashboard_ui import dashboard as render_dashboard
    render_dashboard(store)


def about():
    st.title("Settings / Help")
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
    with st.expander('Local model setup'):
        st.code('.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt',language='powershell')
        prepare_finbert()


def main():
    st.set_page_config(page_title="FinScope | Local News Intelligence", page_icon="📈", layout="wide")
    st.markdown("""<style>
    .block-container {max-width:1400px; padding-top:2rem;}
    [data-testid="stAppDeployButton"] {display:none;}
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
        page = st.radio("Workspace", ["Dashboard", "Add news", "Analyze", "Settings / Help"], key="workspace_page")
        st.divider()
        st.caption("Local SQLite · Your original records persist")
        if st.button("User Guide"):
            st.session_state["show_guide"] = True
            st.rerun()
    {"Dashboard": dashboard, "Add news": add_news, "Analyze": analyze}.get(page, lambda _store: about())(store)

