"""Concise visual views over the same filtered raw originals."""
from dataclasses import asdict
from datetime import date, datetime, timezone
import json

import pandas as pd
import streamlit as st

from .local_analytics import (Filters, daily_counts, evidence_graph, heatmap_cells,
                            model_key, overview_counts, sector_counts, select_articles,
                            default_result_model, result_models, graph_view, graph_members, cell_members)
from .ui_data import SECTORS, SENTIMENTS

COLORS = ["#16856b", "#8b97a8", "#dc6b72", "#d9dee6"]


def keep_valid_selection(key, choices):
    if key in st.session_state and st.session_state[key] not in choices:
        del st.session_state[key]


def shared_filters(news, analyses, *, for_analysis=False, analysis_model=None):
    dates = sorted(date.fromisoformat(n.published_day) for n in news if n.published_day)
    start, end = (dates[0], dates[-1]) if dates else (datetime.now(timezone.utc).date(),)*2
    old_range = st.session_state.get("local_dates", (start, end))
    outside = [n for n in news if n.published_day and len(old_range) == 2
               and not old_range[0] <= date.fromisoformat(n.published_day) <= old_range[1]]
    if outside:
        new_ids = set(st.session_state.get("new_news_ids", []))
        new_count = sum(n.article_id in new_ids for n in outside)
        st.info(f"{new_count} new records outside the current date range." if new_count else
                f"{len(outside)} saved records outside the current date range.")
        def widen_dates():
            st.session_state["local_dates"] = (start, end)
        st.button("Include all saved publication dates", on_click=widen_dates, key="widen_local_dates")
    left, middle, right = st.columns([2, 2, 2])
    with left:
        selected = st.date_input("Publication date range (UTC)", value=(start, end), key="local_dates")
    with middle:
        sectors = st.multiselect("Sectors", SECTORS, key="local_sectors", placeholder="All sectors")
    with right:
        search = st.text_input("Search news", key="local_search", placeholder="Headlines, summaries or source")
    with st.expander("More filters", expanded=False):
        a, b = st.columns(2)
        with a:
            sources = st.multiselect("Sources", sorted({n.source for n in news}), key="local_sources")
        with b:
            sentiments = [] if for_analysis else st.multiselect("Sentiment", SENTIMENTS, key="local_sentiments")
        unknown = st.checkbox("Include unknown publication dates (separate from daily charts)", value=True, key="local_unknown_dates")
    if for_analysis:
        models = (analysis_model,) if analysis_model else ()
    else:
        choices = result_models(analyses)
        default = default_result_model(analyses)
        if default not in choices:
            choices.insert(0, default)
        if st.session_state.get("local_result_model") not in choices:
            st.session_state["local_result_model"] = default
        current = st.selectbox("Results model", choices, key="local_result_model",
                              format_func=lambda value: " · ".join(value.split(" · ")[:2]))
        models = (current,)
    undated = sum(not n.published_day for n in news)
    if undated:
        st.caption(f"{undated} originals have no publication date; first-seen/submission dates are not publication dates.")
    if len(selected) != 2:
        st.info("Select both start and end dates.")
        return [], {}, start, end
    selected_news, results = select_articles(news, analyses, Filters(selected[0], selected[1], tuple(sectors), tuple(sources),
                          tuple(sentiments), tuple(models), search, unknown, "published", False))
    return selected_news, results, selected[0], selected[1]


def distribution_chart(results):
    rows = [{"Sentiment": sentiment, "Articles": sum(a.label == sentiment for a in results.values())} for sentiment in SENTIMENTS]
    st.vega_lite_chart({"data": {"values": rows}, "mark": {"type": "arc", "innerRadius": 65},
        "encoding": {"theta": {"field": "Articles", "type": "quantitative"},
                     "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS[:3]}},
                     "tooltip": [{"field": "Sentiment"}, {"field": "Articles", "type": "quantitative"}]},
        "height": 260}, width="stretch")


def sector_chart(news, results):
    table = pd.DataFrame(sector_counts(news, results)).set_index("Sector")
    st.bar_chart(table, color=COLORS, stack=True, height=300, x_label="Keyword sector", y_label="Raw articles")
    st.caption("Multi-sector articles count once per assigned sector; sector totals can exceed the raw article total.")


def heatmap(news, results, start, end, store):
    st.subheader("Date × sector")
    metric = st.radio("Heatmap measure", ["Article volume", "Sentiment balance"], horizontal=True)
    try:
        cells = heatmap_cells(news, results, start, end, date_basis="published")
    except ValueError as error:
        st.info(str(error)); return
    from .chart_interactions import interactive_chart, chart_scope
    data={"cells":cells,"metric":metric,"model":st.session_state.get("local_result_model"),"articles":[n.article_id for n in news]}
    scope=chart_scope('heatmap',data)
    if st.session_state.get('heatmap_scope') != scope:
        st.session_state['heatmap_selected']=None
        st.session_state['heatmap_scope']=scope
    clicked=interactive_chart('heatmap',data,key='local_heatmap',selected=st.session_state.get('heatmap_selected'))
    if clicked:
        st.session_state['heatmap_selected']=clicked
    st.caption("Click a cell for local articles; balance = (positive − negative) / analyzed, with low samples flagged.")
    selected=st.session_state.get('heatmap_selected')
    if selected:
        day,sector=selected.split('|',1)
        records=cell_members(news,{'Date':day,'Sector':sector})
        st.subheader(f"{sector} · {day}")
        st.caption(f"{len(records)} local originals · {sum(n.article_id in results for n in records)} analyzed")
        related_articles(records,results,store,context='heatmap')
    undated=[n for n in news if not n.published_day]
    if undated:
        with st.expander(f"Unknown publication date: {len(undated)} originals"):
            related_articles(undated,results,store,context='heatmap_unknown')


def related_articles(news, results, store, *, context):
    if not news:
        st.info("No local articles in this selection.")
        return
    by_id={n.article_id:n for n in news}
    keep_valid_selection(context+'_related',by_id)
    key=st.selectbox("Related articles",list(by_id),format_func=lambda key:by_id[key].title,
                     key=context+'_related')
    article_details(by_id[key],results.get(key),store,context=context)


def article_details(item, result, store, *, context="explorer"):
    st.subheader(item.title)
    st.caption(f"{item.source} · {item.provider} · {item.timestamp or item.publication_date or 'Unknown date'} ({item.timestamp_kind})")
    if item.provider in {"rba_rss","rba_html"}:
        try:
            st.caption(json.loads(item.provenance).get("attribution","Reserve Bank of Australia")+" · AI analysis is derived; no RBA endorsement.")
        except (ValueError,TypeError):
            pass
    st.text(item.summary or "No summary supplied. Analysis can use a permitted headline only.")
    st.caption("Text available: headline + supplied summary; this is not full publisher text.")
    if item.url:
        st.link_button("Open original article", item.url)
    if result:
        st.write(f"**{result.label}** · {result.family} · {result.model_id}")
        if result.probabilities is not None:
            st.dataframe(pd.DataFrame([result.probabilities]), hide_index=True, width="stretch")
        if result.rationale:
            st.text("Model-generated rationale: "+result.rationale)
        st.caption(f"Revision: {result.revision} · Analyzed: {result.analyzed_at}")
    else:
        st.info("Not analyzed. Select this original on the Analyze page after confirming its permissions.")
    with st.expander("Provenance, permissions and analysis history"):
        st.write({"article_id": item.article_id, "fetched_at": item.fetched_at,
                  "timestamp_meaning": item.timestamp_kind, "publication_date_only": item.publication_date,
                  "provenance": item.provenance, "permissions": asdict(item.rights)})
        if result:
            st.write({"output_provenance":result.provenance})
        history = [a for a in store.list_analyses() if a.article_id == item.article_id]
        if history:
            st.dataframe(pd.DataFrame([{"Model": model_key(a), "Label": a.label, "Analyzed": a.analyzed_at,
                                        "Result ID": a.analysis_id} for a in history]), hide_index=True, width="stretch")
    prefix=context+"_"+item.article_id
    with st.expander("Update usage permissions",expanded=False):
        from dataclasses import replace
        reference=st.text_input("Permission reference",value=item.rights.reference,max_chars=300,key=prefix+"_rights_ref")
        nlp=st.checkbox("Permission includes local NLP",value=item.rights.analyze,key=prefix+"_rights_nlp")
        external=st.checkbox("Permission includes external LLM transmission",value=item.rights.external,key=prefix+"_rights_external")
        st.caption("Record your actual permission. This does not grant publisher rights. Previous permission attestations remain in local history.")
        if st.button("Save updated permissions",key=prefix+"_rights_save"):
            try:
                store.update_rights(item.article_id,replace(item.rights,reference=reference,analyze=nlp,external=external))
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    with st.expander("Reanalyze this original",expanded=False):
        from .model_ui import controls,execute
        from .model_providers import ModelError
        settings=controls(prefix)
        if st.button("Reanalyze this article",key=prefix+"_reanalyze",disabled=not settings.ready or not item.rights.analyze):
            try:
                with st.spinner("Running the selected model on this original…"):
                    execute(item,store,settings)
                st.rerun()
            except ModelError as error:
                st.error(str(error))
            except Exception:
                st.error("Reanalysis failed. No fake output was substituted; previous versions remain saved.")
    if result and result.candidate_id:
        latest = {a.article_id:a for a in store.list_analyses() if a.family==result.family
                  and a.model_id==result.model_id and a.revision==result.revision
                  and a.embedding_revision==result.embedding_revision}
        members = [n for n in store.list_news() if n.article_id in latest and latest[n.article_id].candidate_id == result.candidate_id]
        if len(members) > 1:
            with st.expander(f"Unverified candidate: {len(members)} preserved originals (including outside filters)"):
                st.caption("Semantic similarity is not confirmed event identity or factual contradiction detection.")
                for n in members:
                    st.write(f"{n.title} · {n.source} · {latest[n.article_id].label}")


def graph(news, results, store):
    st.subheader("Evidence relationships")
    sectors=sorted({s for n in news for s in n.sectors})
    left,right=st.columns([2,1])
    with left:
        keep_valid_selection('graph_sector',sectors)
        focus=st.selectbox("Graph sector",sectors,key='graph_sector')
    with right:
        expanded=st.checkbox("Expand graph",key='graph_expand')
    with st.expander("Graph layers"):
        sources=st.checkbox("Show source nodes",key='graph_sources')
        similar=st.checkbox("Show unverified similarity groups",key='graph_similar')
    data,full,focused=graph_view(news,results,sector=focus,article_limit=30 if expanded else 8,
                              node_limit=120 if expanded else 40,show_sources=sources,show_similar=similar)
    st.caption(f"Showing {len(data['nodes'])}/{len(full['nodes'])} nodes · {sum(n['kind']=='Article' for n in data['nodes'])}/{len(focused)} articles in {focus}.")
    from .chart_interactions import interactive_chart, chart_scope
    data['model']=st.session_state.get('local_result_model')
    scope=chart_scope('graph',data)
    if st.session_state.get('graph_scope') != scope:
        st.session_state['graph_selected']=None
        st.session_state['graph_scope']=scope
    clicked=interactive_chart('graph',data,key='local_evidence_graph',selected=st.session_state.get('graph_selected'))
    if clicked:
        st.session_state['graph_selected']=clicked
    selected=st.session_state.get('graph_selected')
    if selected:
        node=next(n for n in data['nodes'] if n['id']==selected)
        records=[n for n in focused if n.article_id in graph_members(full,selected)]
        st.subheader(node['kind']+": "+node['label'])
        st.caption(f"{len(records)} related originals in the current filters")
        for evidence in [e for e in full['edges'] if e['from']==selected or e['to']==selected][:12]:
            st.caption(evidence['relationship']+" · "+evidence['evidence'])
        related_articles(records,results,store,context='graph_node')
    by_id = {n.article_id: n for n in focused}
    keep_valid_selection('local_graph_article',by_id)
    accessible_id = st.selectbox("Graph article reference", list(by_id), index=None,
                     format_func=lambda key: by_id[key].title+" · "+by_id[key].source,
                     key="local_graph_article", placeholder="Choose an original article")
    selected_id = accessible_id
    if selected_id in by_id:
        article_details(by_id[selected_id], results.get(selected_id), store,context="graph")
    with st.expander("Inspect graph evidence"):
        st.dataframe(pd.DataFrame([{k: e[k] for k in ("article_id", "relationship", "evidence")} for e in data["edges"]]),
                     hide_index=True, width="stretch")


def explorer(news, results, store):
    ordered = sorted(news, key=lambda n: (n.record_date, n.article_id), reverse=True)
    keep_valid_selection('local_inspected_article',[n.article_id for n in ordered])
    st.dataframe(pd.DataFrame([{"Article ID": n.article_id, "Title": n.title,
        "Date": n.timestamp or n.publication_date or "Unknown", "Source": n.source, "Sector": ", ".join(n.sectors),
        "Sentiment": results[n.article_id].label if n.article_id in results else "Not analyzed",
        "Model": results[n.article_id].family if n.article_id in results else "—", "Original URL": n.url} for n in ordered]),
        hide_index=True, width="stretch", column_config={"Original URL": st.column_config.LinkColumn()})
    record_id = st.selectbox("Inspect an article", [n.article_id for n in ordered], key="local_inspected_article",
                  format_func=lambda key: next(n.title+" · "+n.source for n in ordered if n.article_id == key))
    if record_id:
        article_details(next(n for n in ordered if n.article_id == record_id), results.get(record_id), store)


def dashboard(store):
    st.title("News intelligence")
    st.caption("Your local news library")
    all_news, analyses = store.list_news(), store.list_analyses()
    if not all_news:
        for col, label in zip(st.columns(4), ["Saved originals", "Analyzed articles", "Sources", "Pending analysis"]):
            col.metric(label, 0)
        st.info("Your library is ready. Choose Add news to fetch a source or save approved text.")
        return
    news, results, start, end = shared_filters(all_news, analyses)
    counts = overview_counts(news, results)
    for col, (label, value) in zip(st.columns(4), [("Original articles", counts["raw_articles"]), ("Analyzed articles", counts["analyzed"]),
                  ("Sources", counts["sources"]), ("Pending analysis", counts["unanalysed"])]):
        col.metric(label, value)
    st.caption(f"All views use the same {len(news)} filtered originals. Multi-sector assignments can contribute to multiple sector cells. Candidate groups never replace raw counts.")
    if not news:
        st.info("No articles match these filters. Widen the date range or clear filters.")
        return
    overview, sectors, trends, matrix, network, articles = st.tabs(["Overview", "Sector sentiment", "Trends", "Heatmap", "Evidence graph", "News Explorer"])
    with overview:
        left, right = st.columns(2)
        with left:
            st.subheader("Sentiment distribution")
            if results:
                distribution_chart(results)
            else:
                st.info("Run analysis to see sentiment distribution.")
        with right:
            st.subheader("Articles by source")
            counts_by_source = pd.Series([n.source for n in news]).value_counts().rename("Raw articles")
            st.bar_chart(counts_by_source, horizontal=True, color="#16856b", height=260)
        sector_chart(news, results)
    with sectors:
        st.subheader("Sector sentiment")
        sector_chart(news, results)
        st.dataframe(pd.DataFrame(sector_counts(news, results)), hide_index=True, width="stretch")
    with trends:
        st.subheader("Daily sentiment")
        try:
            table = pd.DataFrame(daily_counts(news, results, start, end,date_basis="published")).set_index("Date")
            st.line_chart(table, color=COLORS, height=320, y_label="Raw articles")
            st.caption("Zero means no matching records in your local library. Published, first-seen, submitted and date-only meanings remain attached to originals; this is not exhaustive market coverage.")
        except ValueError as error:
            st.info(str(error))
    with matrix:
        heatmap(news, results, start, end,store)
    with network:
        graph(news, results, store)
    with articles:
        explorer(news, results, store)
    with st.expander("Export and local storage"):
        st.caption("Export includes every permitted saved original and all analysis versions, including those excluded by these filters. API keys are excluded.")
        st.download_button("Export local library", json.dumps(store.export(), indent=2), "finscope-local.json", "application/json")
