"""Concise visual views over the same filtered raw originals."""
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
import math

import pandas as pd
import streamlit as st

from .local_analytics import (Filters, daily_counts, evidence_graph, heatmap_cells,
                            model_key, overview_counts, sector_counts, select_articles,
                            default_result_model, result_models, graph_view, graph_members, cell_members)
from .ui_data import SECTORS, SENTIMENTS

from .product_theme import COLORS,plot


def keep_valid_selection(key, choices):
    if key in st.session_state and st.session_state[key] not in choices:
        del st.session_state[key]


FILTER_KEYS = ('local_dates','local_sectors','local_search','local_sources','local_sentiments',
               'local_unknown_dates','local_result_model')


def remember_filter(key):
    st.session_state.setdefault('filter_preferences',{})[key] = st.session_state[key]


def restore_filters():
    for key,value in st.session_state.get('filter_preferences',{}).items():
        if key in FILTER_KEYS and key not in st.session_state:
            st.session_state[key]=value


def publication_label(item):
    if item.timestamp_kind == 'published' and item.timestamp:
        stamp=datetime.fromisoformat(item.timestamp).astimezone(timezone.utc)
        return 'Published '+stamp.strftime('%d %b %Y, %H:%M UTC')
    if item.timestamp_kind == 'published' and item.publication_date:
        return 'Published '+item.publication_date+' (date only)'
    return 'Publication date unknown'


def shared_filters(news, analyses, *, for_analysis=False, analysis_model=None, sector_options=None,model_choices=None,model_widget_key='local_result_model'):
    restore_filters()
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
            remember_filter('local_dates')
        st.button("Include all saved publication dates", on_click=widen_dates, key="widen_local_dates")
    hidden_unknown = [n for n in news if not n.published_day and n.article_id in st.session_state.get('new_news_ids', [])]
    if hidden_unknown and not st.session_state.get('local_unknown_dates',True):
        st.info(f"{len(hidden_unknown)} new records have unknown publication dates and are outside the current range.")
        def include_unknown():
            st.session_state['local_unknown_dates']=True
            remember_filter('local_unknown_dates')
        st.button('Include unknown publication dates',on_click=include_unknown)
    left, middle, right = st.columns([2, 2, 2])
    with left:
        selected = st.date_input("Publication date range (UTC)", value=(start,end), key="local_dates",on_change=remember_filter,args=('local_dates',),
                                 help='Exact timestamps use UTC; date-only records keep their original calendar day. Unknown publication dates stay separate.')
    with middle:
        options=sector_options or SECTORS
        if sector_options is not None and any(s not in options for s in st.session_state.get('local_sectors',[])):
            st.session_state['local_sectors']=[s for s in st.session_state['local_sectors'] if s in options]
        sectors = st.multiselect("Sectors", options, key="local_sectors", placeholder="All sectors",on_change=remember_filter,args=('local_sectors',))
    with right:
        search = st.text_input("Search news", key="local_search", placeholder="Headlines, summaries or source",on_change=remember_filter,args=('local_search',))
    with st.expander("More filters", expanded=False):
        a, b = st.columns(2)
        with a:
            sources = st.multiselect("Sources", sorted({n.source for n in news}), key="local_sources",on_change=remember_filter,args=('local_sources',))
        with b:
            sentiments = [] if for_analysis else st.multiselect("Sentiment", SENTIMENTS, key="local_sentiments",on_change=remember_filter,args=('local_sentiments',))
        unknown = st.checkbox("Include unknown publication dates (separate from daily charts)", value=True, key="local_unknown_dates",on_change=remember_filter,args=('local_unknown_dates',))
    if for_analysis:
        models = (analysis_model,) if analysis_model else ()
    else:
        choices = list(model_choices) if model_choices is not None else result_models(analyses)
        default = default_result_model(analyses)
        if default not in choices:
            choices.insert(0, default)
        if st.session_state.get("local_result_model") not in choices:
            st.session_state["local_result_model"] = default
        def model_label(value):
            parts=value.split(' · ')
            name=' · '.join(parts[:2])
            return name+' · '+parts[-1][:8] if sum(v.startswith(name+' · ') for v in choices)>1 else name
        if model_widget_key!='local_result_model':
            if st.session_state.get(model_widget_key) not in choices:st.session_state[model_widget_key]=st.session_state['local_result_model']
            def remember_product_model():
                st.session_state['local_result_model']=st.session_state[model_widget_key];remember_filter('local_result_model')
            current=st.selectbox('Results model',choices,key=model_widget_key,format_func=model_label,on_change=remember_product_model)
            st.session_state['local_result_model']=current
            st.caption('Current results: '+' · '.join(current.split(' · ')[:2]))
        else:
            current = st.selectbox("Results model", choices, key="local_result_model",format_func=model_label,
                                  on_change=remember_filter,args=('local_result_model',))
        models = (current,)
    undated = sum(not n.published_day for n in news)
    if undated:
        st.caption(f"Library: {undated} originals have no publication date; excluded from daily charts.")
    # Streamlit removes widget keys on pages where they are not rendered. Keep
    # defaults too, so adding data cannot silently widen the previous window.
    for key in FILTER_KEYS:
        if key in st.session_state:remember_filter(key)
    if len(selected) != 2:
        st.info("Select both start and end dates.")
        return [], {}, start, end
    selected_news, results = select_articles(news, analyses, Filters(selected[0], selected[1], tuple(sectors), tuple(sources),
                          tuple(sentiments), tuple(models), search, unknown, "published", False))
    return selected_news, results, selected[0], selected[1]


def distribution_chart(results):
    rows,angle=[],0
    total=max(1,len(results))
    for sentiment in SENTIMENTS:
        count=sum(a.label==sentiment for a in results.values())
        end=angle+count/total*2*math.pi
        if count:
            rows.append({'Sentiment':sentiment,'Articles':count,'Start':angle,'End':end})
        angle=end
    plot({"data": {"values": rows}, "mark": {"type": "arc", "innerRadius": 65},
        "encoding": {"theta": {"field": "End", "type": "quantitative", "scale":None},"theta2":{"field":"Start"},
                     "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS[:3]}},
                     "tooltip": [{"field": "Sentiment"}, {"field": "Articles", "type": "quantitative"}]},
        "height": 260}, width="stretch")


def sector_chart(news, results):
    table=display_sector_counts(news,results)
    rows=[{'Sector':r['Sector'],'Sentiment':label,'Articles':r[label]} for r in table for label in (*SENTIMENTS,'Not analyzed')]
    upper=max(1,max((sum(r[label] for label in (*SENTIMENTS,'Not analyzed')) for r in table),default=0))
    st.vega_lite_chart({'data':{'values':rows},'mark':'bar','encoding':{
        'x':{'field':'Sector','type':'ordinal','sort':list(SECTORS)},
        'y':{'field':'Articles','type':'quantitative','title':'Local articles','scale':{'domain':[0,upper]}},
        'color':{'field':'Sentiment','type':'nominal','scale':{'domain':[*SENTIMENTS,'Not analyzed'],'range':COLORS}},
        'tooltip':[{'field':'Sector'},{'field':'Sentiment'},{'field':'Articles','type':'quantitative'}]},'height':300},width='stretch')
    st.caption("Multi-sector articles count once per assigned sector; sector totals can exceed the raw article total.")


def display_sector_counts(news, results):
    selected=st.session_state.get('local_sectors',[])
    return [r for r in sector_counts(news,results) if not selected or r['Sector'] in selected]


def source_chart(news):
    from collections import Counter
    counts=Counter(n.source for n in news)
    st.vega_lite_chart({'data':{'values':[{'Source':k,'Articles':v} for k,v in counts.items()]},'mark':{'type':'bar','color':COLORS[0]},
        'encoding':{'x':{'field':'Articles','type':'quantitative','title':'Local articles','scale':{'domain':[0,max(counts.values(),default=1)]}},
        'y':{'field':'Source','type':'nominal','sort':'-x'},'tooltip':[{'field':'Source'},{'field':'Articles','type':'quantitative'}]},'height':260},width='stretch')


def timeline_chart(news, results, start, end):
    table=daily_counts(news,results,start,end,date_basis='published')
    rows=[{'Date':r['Date'],'Sentiment':label,'Articles':r[label]} for r in table for label in (*SENTIMENTS,'Not analyzed')]
    upper=max(1,max((r['Articles'] for r in rows),default=0))
    # Retain the existing date-only daily buckets and thin labels, not data.
    # A discrete domain also stays finite during the host's empty-data render.
    days=[r['Date'] for r in table]
    ticks=days[::max(1,math.ceil(len(days)/6))]
    if days and days[-1] not in ticks:ticks.append(days[-1])
    plot({'data':{'values':rows},'mark':{'type':'line','point':True},'encoding':{
        'x':{'field':'Date','type':'ordinal','scale':{'domain':days},'title':'Publication date (UTC)','axis':{'values':ticks,'labelExpr':'substring(datum.label,5)' if start.year==end.year else 'datum.label','labelOverlap':'greedy','labelAngle':0}},
        'y':{'field':'Articles','type':'quantitative','title':'Local articles','scale':{'domain':[0,upper]},'axis':{'tickMinStep':1}},
        'color':{'field':'Sentiment','type':'nominal','scale':{'domain':[*SENTIMENTS,'Not analyzed'],'range':COLORS}},
        'tooltip':[{'field':'Date'},{'field':'Sentiment'},{'field':'Articles','type':'quantitative'}]},'height':320},width='stretch')


def heatmap(news, results, start, end, store, *, sectors_override=None,background=False):
    st.subheader("Date × sector")
    metric = st.radio("Heatmap measure", ["Article volume", "Sentiment balance"], horizontal=True)
    try:
        cells = heatmap_cells(news, results, start, end, sectors=st.session_state.get('local_sectors') or sectors_override or SECTORS, date_basis="published")
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
        related_articles(records,results,store,context='heatmap',background=background)
    undated=[n for n in news if not n.published_day]
    if undated:
        with st.expander(f"Unknown publication date: {len(undated)} originals"):
            related_articles(undated,results,store,context='heatmap_unknown',background=background)


def related_articles(news, results, store, *, context,background=False):
    if background:
        from .pipeline_ui import article_list
        from .product_storage import ProductStorage
        from .taxonomy import load_taxonomy
        catalog=load_taxonomy(st.session_state.get('product_taxonomy','US-BUSINESS-1'))
        article_list(news,results,store,ProductStorage(store).classifications(catalog['id']),catalog,context)
        return
    if not news:
        st.info("No local articles in this selection.")
        return
    by_id={n.article_id:n for n in news}
    keep_valid_selection(context+'_related',by_id)
    key=st.selectbox("Related articles",list(by_id),format_func=lambda key:by_id[key].title,
                     key=context+'_related')
    article_details(by_id[key],results.get(key),store,context=context,background=background)


def article_details(item, result, store, *, context="explorer",background=False,content_renderer=None):
    st.subheader(item.title)
    st.caption(f"{item.source} · {publication_label(item)}")
    if item.provider=='authored_synthetic':
        st.caption('Synthetic development text')
    st.write(f"**{result.label if result else 'Not analyzed'}** · {', '.join(item.sectors)}"+
             (f" · {result.family}" if result else ''))
    if item.provider in {"rba_rss","rba_html","abs_html","accc_rss","nist_rss"}:
        try:
            origin=json.loads(item.provenance)
            st.caption(origin.get("attribution","Reserve Bank of Australia")+' · '+origin.get('derivative_attribution','AI analysis is derived; no RBA endorsement.'))
        except (ValueError,TypeError):
            pass
    if content_renderer:
        content_renderer(item)
    elif item.summary:
        st.text(item.summary)
    st.caption('Permitted body saved locally; analysis excerpt coverage is retained in result provenance.' if item.body else "Headline + supplied summary; not full article text." if item.summary else "Headline only; no summary or full article supplied.")
    if item.url:
        st.link_button("Open original article", item.url)
    if not result and not background:
        from .product_ui import next_step
        next_step('Analyze news →','Analyze',context+'_'+item.article_id+'_next')
    with st.expander("Provenance, permissions and analysis history"):
        if result:
            st.caption(f"{result.model_id} · Revision: {result.revision} · Analyzed: {result.analyzed_at}")
            if result.probabilities is not None:
                st.dataframe(pd.DataFrame([result.probabilities]),hide_index=True,width='stretch')
            if result.rationale:
                st.text('Model-generated rationale: '+result.rationale)
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
        if background:
            from .pipeline_ui import reanalyze
            reanalyze(item,store,prefix)
        else:
            manual_reanalysis(item,store,prefix)
    if result and result.candidate_id:
        show_candidate(item,result,store)


def manual_reanalysis(item,store,prefix):
        from .model_ui import controls,execute
        from .model_providers import ModelError
        settings=controls(prefix,store=store)
        if st.button("Reanalyze this article",key=prefix+"_reanalyze",disabled=not settings.ready or not item.rights.analyze):
            try:
                with st.spinner("Running the selected model on this original…"):
                    execute(item,store,settings)
                st.rerun()
            except ModelError as error:
                st.error(str(error))
            except Exception:
                st.error("Reanalysis failed. No fake output was substituted; previous versions remain saved.")


def show_candidate(item,result,store):
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
    allowed=st.session_state.get('local_sectors',[])
    sectors=sorted({s for n in news for s in n.sectors if not allowed or s in allowed})
    left,right=st.columns([2,1])
    with left:
        keep_valid_selection('graph_sector',sectors)
        focus=st.selectbox("Graph sector",sectors,key='graph_sector')
    with right:
        expanded=st.checkbox("Expand graph",key='graph_expand')
    with st.expander("Graph layers"):
        sources=st.checkbox("Show source nodes",key='graph_sources')
        similar=st.checkbox("Show unverified similarity groups",key='graph_similar')
        st.caption("Entities are literal text matches; themes and similarity groups are unverified, with no causal claims or model calls.")
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
        related_articles(records,results,store,context='graph_node')
        with st.expander('Relationship evidence'):
            for evidence in [e for e in full['edges'] if e['from']==selected or e['to']==selected]:
                st.text(evidence['relationship']+" · "+evidence['evidence'])
    by_id = {n.article_id: n for n in focused}
    keep_valid_selection('local_graph_article',by_id)
    with st.expander('Accessible article selector'):
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
    ordered = sorted(news, key=lambda n: (n.published_day, n.article_id), reverse=True)
    keep_valid_selection('local_inspected_article',[n.article_id for n in ordered])
    st.dataframe(pd.DataFrame([{"Title": n.title,
        "Published": publication_label(n), "Source": n.source, "Sector": ", ".join(n.sectors),
        "Sentiment": results[n.article_id].label if n.article_id in results else "Not analyzed",
        "Model": results[n.article_id].family if n.article_id in results else "—", "Original URL": n.url} for n in ordered]),
        hide_index=True, width="stretch", column_config={"Original URL": st.column_config.LinkColumn(display_text='Open original')})
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
    synthetic=sum(n.provider=='authored_synthetic' for n in news)
    if synthetic:
        st.caption(f'{synthetic} synthetic development originals included in this local selection')
    counts = overview_counts(news, results)
    for col, (label, value) in zip(st.columns(4), [("Original articles", counts["raw_articles"]), ("Analyzed articles", counts["analyzed"]),
                  ("Sources", counts["sources"]), ("Pending analysis", counts["unanalysed"])]):
        col.metric(label, value)
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
            source_chart(news)
        sector_chart(news, results)
    with sectors:
        st.subheader("Sector sentiment")
        sector_chart(news, results)
        st.dataframe(pd.DataFrame(display_sector_counts(news, results)), hide_index=True, width="stretch")
    with trends:
        st.subheader("Daily sentiment")
        try:
            timeline_chart(news,results,start,end)
            st.caption("Publication dates only; zero means no matching local records, not full market coverage.")
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
