"""Public, synthetic-only product storytelling. Independent of the local runtime."""
from datetime import timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from .showcase_data import (END, START, SECTORS, SENTIMENTS, article_label,
                            candidate_groups, examples, graph, graph_overview, select, word_cloud_terms)
from .showcase_visuals import graph_layout, relationship_markup, visible_graph, word_cloud_markup
from .showcase_theme import TOKENS, NAV_ITEMS, NAV_KEYS, SENTIMENT_COLORS, badge, brand, dashboard_preview, eyebrow, line_icon, theme_css

REPOSITORY = "https://github.com/DVDWK812/Finscope"
PAGES = ("Home", "User Guide", "Dashboard Preview", "Knowledge Graph", "News Explorer", "Get FinScope")
COLORS = [SENTIMENT_COLORS[name] for name in SENTIMENTS]
DEMO_LABEL = "Demo Data / Illustrative Preview"

STYLE = theme_css()


def go(page):
    st.session_state["showcase_page"] = page


def heading(title, description):
    with st.container(key="fs_page_header"):
        st.markdown('<div class="fs-header-meta">' + eyebrow("PRODUCT SHOWCASE") + badge() + '</div>', unsafe_allow_html=True)
        st.title(title)
        st.write(description)


def plot(spec, **_options):
    spec = {**spec, "background": TOKENS["surface"], "config": {
        "font": "system-ui", "view": {"stroke": None},
        "axis": {"labelColor": TOKENS["muted"], "titleColor": TOKENS["muted"],
                 "labelFontSize": 11, "titleFontSize": 11, "labelPadding": 8,
                 "gridColor": TOKENS["border"], "gridOpacity": .45, "domain": False, "ticks": False},
        "legend": {"labelColor": TOKENS["muted"], "title": None, "orient": "bottom",
                   "direction": "horizontal", "labelFontSize": 11, "symbolType": "circle",
                   "columnPadding": 14, "symbolSize": 65}}}
    st.vega_lite_chart(spec, width="stretch", theme=None)


def home():
    st.markdown('<div class="fs-header-meta">' + eyebrow("LOCAL-FIRST FINANCIAL INTELLIGENCE") + badge() + '</div>', unsafe_allow_html=True)
    with st.container(key="fs_home_hero"):
        intro, preview = st.columns([1.05, 1], gap="large")
        with intro:
            st.markdown('<section class="fs-hero"><h1>Financial news.<br><span class="fs-hero-accent">A clearer perspective.</span></h1>'
                        '<p>A local workspace for financial news, sentiment and source-level inspection. '
                        'Move from individual headlines to the context behind them.</p></section>', unsafe_allow_html=True)
            with st.container(key="fs_hero_ctas"):
                demo, install = st.columns(2)
                demo.button("Explore Demo", key="hero_demo", icon=":material/arrow_forward:", type="primary", on_click=go, args=("Dashboard Preview",), width="stretch")
                install.button("Get FinScope", key="hero_install", icon=":material/download:", on_click=go, args=("Get FinScope",), width="stretch")
            st.button("How it works", key="hero_guide", type="tertiary", icon=":material/menu_book:", on_click=go, args=("User Guide",))
            st.caption("Explore authored examples here. Run the complete product on your computer.")
        with preview:
            st.markdown(dashboard_preview(examples()), unsafe_allow_html=True)
    st.subheader("From individual reports to an inspectable picture")
    cards = (("sources", "Keep the original", "Start with source reports. Preserve their wording, dates and provenance."),
             ("analyze", "See the context", "Read sentiment, industry and time patterns without treating tone as a forecast."),
             ("inspect", "Inspect the evidence", "Explore potential topic links and return to the reports behind every view."))
    for column, (icon, title, text) in zip(st.columns(3), cards):
        with column:
            st.markdown('<article class="fs-feature">' + line_icon(icon) + f'<h3>{title}</h3><p>{text}</p></article>', unsafe_allow_html=True)


def guide():
    heading("How FinScope works", "Four steps from approved text to an inspectable local workspace.")
    steps = (("sources", "Choose a news source", "Use a supported connector or approved text in the local app. Credentials stay on your computer."),
             ("model", "Choose an AI model", "Pinned FinBERT and MiniLM are the defaults. Prepare model assets explicitly before analysis."),
             ("analyze", "Fetch and analyze", "Preview originals, confirm quota and usage rights, then opt in to storage and analysis."),
             ("inspect", "Explore and inspect", "Read sector and time views, open original reports and review potential relationships as unverified."))
    for offset in (0, 2):
        columns = st.columns(2)
        for column, index in zip(columns, (offset, offset + 1)):
            icon, title, text = steps[index]
            with column:
                with st.container(key=f"fs_step_{index + 1}"):
                    st.markdown(line_icon(icon) + eyebrow(f"STEP {index + 1:02}"), unsafe_allow_html=True)
                    st.subheader(title)
                    st.write(text)
    st.button("Try the illustrative dashboard", key="guide_demo", icon=":material/arrow_forward:", type="primary", on_click=go, args=("Dashboard Preview",))


def reset_filters():
    # Explicit assignments send changed widget values back to the browser.
    # Removing keys resets server defaults but can leave old client filter chips.
    st.session_state["preview_sectors"] = []
    st.session_state["preview_sentiments"] = []
    st.session_state["preview_dates"] = (START, END)


def preview_filters():
    with st.expander("Filter sample", expanded=False):
        a, b, c = st.columns([1.2, 1, 1])
        with a:
            dates = st.date_input("Example dates", value=(START, END), min_value=START, max_value=END, format="DD/MM/YYYY", key="preview_dates")
        with b:
            sectors = st.multiselect("Industry", SECTORS, key="preview_sectors", placeholder="All industries")
        with c:
            sentiments = st.multiselect("Illustrative sentiment", SENTIMENTS, key="preview_sentiments", placeholder="All labels")
        st.button("Reset preview", icon=":material/restart_alt:", on_click=reset_filters)
    if len(dates) != 2:
        st.info("Choose a start and end date to explore the fictional sample.")
        return [], START, END
    st.caption(f'{dates[0]:%d %b} – {dates[1]:%d %b %Y} · {", ".join(sectors) or "All industries"} · {", ".join(sentiments) or "All sentiments"}')
    return select(examples(), dates[0], dates[1], sectors, sentiments), dates[0], dates[1]


def sector_plot(rows):
    data = [{"Industry": sector, "Sentiment": label,
             "Reports": sum(r.sector == sector and r.sentiment == label for r in rows)}
            for sector in SECTORS for label in SENTIMENTS]
    plot({"data": {"values": data}, "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {"y": {"field": "Industry", "type": "nominal", "sort": list(SECTORS), "title": None},
                     "x": {"field": "Reports", "type": "quantitative", "title": "Fictional reports", "axis": {"tickMinStep": 1}},
                     "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS}},
                     "tooltip": [{"field": "Industry"}, {"field": "Sentiment"}, {"field": "Reports"}]},
        "height": 265}, width="stretch")


def time_rows(rows, start, end):
    data = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        for label in SENTIMENTS:
            data.append({"Date": day.isoformat(), "Sentiment": label,
                         "Reports": sum(r.day == day and r.sentiment == label for r in rows)})
    return data


def dashboard():
    heading("A dashboard, in perspective", "Explore sentiment and coverage across a fixed authored sample.")
    rows, start, end = preview_filters()
    if not rows:
        st.info("No fictional records match these filters. Reset the preview or choose a wider selection.")
        return
    counts = [sum(r.sentiment == label for r in rows) for label in SENTIMENTS]
    with st.container(key="fs_kpis"):
        for column, label, value in zip(st.columns(4),
                ("Fictional reports", "Positive label share", "Industries", "Example days"),
                (len(rows), f"{counts[0] / len(rows):.0%}", len({r.sector for r in rows}), (end - start).days + 1)):
            column.metric(label, value)
    with st.container(key="fs_dashboard_charts"):
        a, b = st.columns([1.5, 1])
        with a:
            with st.container(key="fs_chart_sector"):
                st.subheader("Sector sentiment distribution")
                st.caption("Original reports by industry and preset tone")
                sector_plot(rows)
        with b:
            with st.container(key="fs_chart_mix"):
                st.subheader("Illustrative sentiment mix")
                st.caption(f"{len(rows)} original reports in this selection")
                plot({"data": {"values": [{"Sentiment": label, "Reports": value} for label, value in zip(SENTIMENTS, counts)]},
                    "mark": {"type": "arc", "innerRadius": 66, "padAngle": .025, "cornerRadius": 3},
                    "encoding": {"theta": {"field": "Reports", "type": "quantitative"},
                                 "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS}},
                                 "tooltip": [{"field": "Sentiment"}, {"field": "Reports"}]}, "height": 265})
    with st.container(key="fs_chart_time"):
        st.subheader("Financial news trends — fictional sample")
        st.caption("Daily report counts · No price or market-return series")
        plot({"data": {"values": time_rows(rows, start, end)},
            "mark": {"type": "line", "point": {"filled": True, "size": 32}, "strokeWidth": 2},
            "encoding": {"x": {"field": "Date", "type": "temporal", "title": None, "axis": {"format": "%d %b", "tickCount": 6, "labelOverlap": "greedy"}},
                         "y": {"field": "Reports", "type": "quantitative", "title": "Reports", "axis": {"tickMinStep": 1}},
                         "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS}},
                         "tooltip": [{"field": "Date", "type": "temporal", "format": "%d %b %Y"}, {"field": "Sentiment"}, {"field": "Reports"}]}, "height": 220})
    with st.container(key="fs_chart_heatmap"):
        st.subheader("Industry sentiment heatmap")
        st.caption("October 2026 · Day of the month")
        cells = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            for sector in SECTORS:
                sample = [r for r in rows if r.day == day and r.sector == sector]
                cells.append({"Date": day.isoformat(), "Industry": sector, "Reports": len(sample),
                              "Balance": sum({"Positive": 1, "Neutral": 0, "Negative": -1}[r.sentiment] for r in sample) / len(sample) if sample else None})
        plot({"data": {"values": cells}, "mark": {"type": "rect", "cornerRadius": 2, "stroke": TOKENS["surface"], "strokeWidth": 2},
            "encoding": {"x": {"field": "Date", "type": "ordinal", "title": None, "axis": {"labelAngle": 0, "labelFontSize": 10, "labelExpr": "substring(datum.label,8,10)"}},
                         "y": {"field": "Industry", "type": "nominal", "title": None, "sort": list(SECTORS)},
                         "color": {"condition": {"test": "datum.Reports == 0", "value": TOKENS["raised"]}, "field": "Balance", "type": "quantitative",
                                   "scale": {"domain": [-1, 0, 1], "range": [COLORS[2], "#61758c", COLORS[0]]}, "legend": {"title": "Label balance", "gradientLength": 150}},
                         "tooltip": [{"field": "Date"}, {"field": "Industry"}, {"field": "Reports"}, {"field": "Balance", "format": ".2f"}]}, "height": 235})
        st.caption("Balance = (positive − negative labels) / reports. Empty cells have no authored record; they do not measure market coverage.")


def story(row, details=False):
    if row is None:
        st.info("Select a headline to inspect its evidence.")
        return
    st.markdown(f'<div class="story"><div class="story-meta">FICTIONAL · {row.day:%d %b %Y} · {escape(row.source)}</div>'
                f'<h3>{escape(article_label(row))}</h3><span class="tone {row.sentiment.lower()}">{row.sentiment} · illustrative label</span></div>', unsafe_allow_html=True)
    if details:
        st.write("Complete headline: " + row.title)
        st.write(row.summary)
        st.caption(f"{row.company} · {row.sector}")
        group = next((g for g in candidate_groups(examples()) if row.article_id in g["article_ids"]), None)
        if group:
            st.caption(f'Unverified candidate: {group["label"]}. {group["basis"]}')
        st.caption("Fictional sample only. No publisher URL exists; no original-article link is fabricated.")
        with st.expander("Technical details", expanded=False):
            st.write({"Article ID": row.article_id, "Candidate reference": row.candidate or "None"})


def explorer_picker_changed(widget_key):
    st.session_state["explorer_article"] = st.session_state[widget_key]
    # A native dataframe selection is read-only. Remount to clear an old row's
    # highlight when the accessible alternative picker selects another report.
    st.session_state["explorer_table_revision"] = st.session_state.get("explorer_table_revision", 0) + 1


def article_selector(label, rows, key):
    by_id = {r.article_id: r for r in rows}
    if st.session_state.get(key) not in by_id:
        st.session_state.pop(key, None)
    ids = list(by_id)
    widget_key = key + "__" + "_".join(ids)
    selected = st.session_state.get(key)
    if widget_key not in st.session_state:
        st.session_state[widget_key] = selected if selected in ids else ids[0]
    chosen = st.selectbox(label, ids, key=widget_key, index=None,
                          format_func=lambda ident: article_label(by_id[ident]),
                          on_change=explorer_picker_changed if key == "explorer_article" else None,
                          args=(widget_key,) if key == "explorer_article" else None)
    st.session_state[key] = chosen
    return by_id.get(chosen)


def render_relationship_graph(data, include_sources=False, mobile_zoom=1.0):
    visible = visible_graph(data, include_sources)
    markup = relationship_markup(visible, mobile_zoom=mobile_zoom)
    _, canvas_height, _, _ = graph_layout(visible)
    components.html('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'
                    f'<style>body{{margin:0;background:{TOKENS["surface"]};color:{TOKENS["text"]};}}</style></head><body>'
                    + markup + '</body></html>', height=int(canvas_height * mobile_zoom) + 56, scrolling=False)


def headline_cloud(records):
    terms = word_cloud_terms(records)
    if not terms:
        st.info("No headline terms are available for this illustrative selection.")
        return
    st.html(word_cloud_markup(terms))
    options = [item["term"] for item in terms]
    if st.session_state.get("graph_cloud_word") not in options:
        st.session_state.pop("graph_cloud_word", None)
    term = st.selectbox("Select a word", options, key="graph_cloud_word")
    selected = next(item for item in terms if item["term"] == term)
    matches = [row for row in records if row.article_id in selected["article_ids"]]
    st.caption(f'{len(matches)} fictional headline(s) contain “{term}”. Counts are once per headline.')
    st.dataframe([{"Headline": article_label(r), "Complete headline": r.title, "Company": r.company,
                   "Industry": r.sector, "Sentiment": r.sentiment, "Fictional source": r.source}
                  for r in matches], hide_index=True, width="stretch")
    with st.expander("Technical details: word matches", expanded=False):
        st.dataframe([{"Article ID": r.article_id, "Headline": article_label(r)} for r in matches],
                     hide_index=True, width="stretch")
    story(article_selector("Open a matching fictional article", matches, "graph_cloud_article"), details=True)


def knowledge_graph():
    heading("Explore the news connections", "Follow the context from industry to company, headline and potential related coverage.")
    all_rows = examples()
    with st.container(key="fs_graph_controls"):
        a, b = st.columns([1.2, 1.4])
        with a:
            perspective = st.radio("Graph perspective", ("Company focus", "Industry network"), horizontal=True, key="graph_perspective")
        with b:
            company = st.selectbox("Fictional company", sorted({r.company for r in all_rows}), key="graph_company")
    rows = [r for r in all_rows if r.company == company]
    groups = candidate_groups(rows)
    with st.container(key="fs_kpis"):
        columns = st.columns(4 if perspective == "Company focus" else 3)
        if perspective == "Company focus":
            for col, label, value in zip(columns, ("Fictional reports", "Unverified topic groups", "Illustrative sources", "Positive / Negative"),
                    (len(rows), len(groups), len({r.source for r in rows}),
                     f'{sum(r.sentiment == "Positive" for r in rows)} / {sum(r.sentiment == "Negative" for r in rows)}')):
                col.metric(label, value)
        else:
            for col, label, value in zip(columns, ("Fictional companies", "Illustrated sectors", "Illustrative source reports"),
                                         (len({r.company for r in all_rows}), len(SECTORS), len(all_rows))):
                col.metric(label, value)
    with st.container(key="fs_map"):
        title, options = st.columns([3, 1])
        title.subheader("Industry → Company → Articles" if perspective == "Company focus" else "Industry → Company → Source")
        with options:
            with st.popover("Map options", icon=":material/tune:"):
                include_sources = st.checkbox("Show fictional sources", value=False,
                    key="graph_company_sources" if perspective == "Company focus" else "graph_network_sources")
                zoom = st.slider("Mobile map zoom", min_value=1.0, max_value=1.5, value=1.0, step=.25, key="graph_mobile_zoom")
                st.caption("Desktop fits the panel. On small screens, pan the map or enlarge its text.")
        data = graph(all_rows, company) if perspective == "Company focus" else graph_overview(all_rows)
        render_relationship_graph(data, include_sources=include_sources, mobile_zoom=zoom)
        st.caption("Dashed links are unverified topic candidates, not confirmed shared events. On mobile, pan left for company context or right for related coverage.")
    if perspective == "Company focus":
        with st.container(key="fs_graph_detail"):
            st.markdown(eyebrow("ARTICLE INSPECTION"), unsafe_allow_html=True)
            picker, detail = st.columns([1, 2])
            with picker:
                chosen = article_selector("Inspect an illustrative article", rows, "graph_article")
                st.caption(f"{len(rows)} original fictional reports · {company}")
            with detail:
                story(chosen, details=True)
        with st.expander("Potentially related reports", expanded=False):
            if groups:
                st.dataframe([{"Topic": g["label"], "Reports": len(g["article_ids"]),
                               "Headlines": " / ".join(g["headlines"]), "Status": "Unverified candidate",
                               "Relationship basis": g["basis"]} for g in groups], hide_index=True, width="stretch")
            else:
                st.info("These fictional reports remain separate. No multi-report candidate topic is shown.")
    else:
        with st.expander("Industry coverage details", expanded=False):
            st.dataframe([{"Company": name, "Sector": next(r.sector for r in all_rows if r.company == name),
                           **{tone: sum(r.company == name and r.sentiment == tone for r in all_rows) for tone in SENTIMENTS}}
                          for name in sorted({r.company for r in all_rows})], hide_index=True, width="stretch")
    with st.container(key="fs_cloud"):
        st.subheader("Headline word cloud")
        scope = st.radio("Text scope", ("All fictional headlines", "Selected company"), horizontal=True, key="graph_cloud_scope")
        cloud_rows = all_rows if scope == "All fictional headlines" else rows
        st.caption(f"{len(cloud_rows)} authored fictional headlines · Each word counts once per headline. Generic words and company names excluded.")
        headline_cloud(cloud_rows)


def explorer():
    heading("Stay close to the original", "Browse the authored sample and inspect one report at a time.")
    a, b = st.columns([2, 1])
    with a:
        query = st.text_input("Search fictional examples", placeholder="Industry, company or headline", max_chars=120)
    with b:
        industry = st.selectbox("Example industry", ("All industries", *SECTORS))
    rows = sorted(select(examples(), sectors=() if industry == "All industries" else (industry,), search=query),
                  key=lambda r: (r.day, r.article_id), reverse=True)
    st.caption(f"{len(rows)} fictional originals · preset labels · no publisher content or URLs")
    if not rows:
        st.info("No fictional examples match. Try a different search or industry.")
        return
    ids = tuple(r.article_id for r in rows)
    with st.container(key="fs_explorer_layout"):
        listing, detail = st.columns([1.4, 1], gap="large")
        with listing:
            st.subheader("Original reports")
            st.caption("Select a row, or use the headline picker in the detail panel.")
            revision = st.session_state.get("explorer_table_revision", 0)
            listing_data = pd.DataFrame([{"Headline": article_label(r), "Sentiment": r.sentiment,
                                          "Published": r.day} for r in rows])
            styled = listing_data.style.map(lambda tone: f"color:{SENTIMENT_COLORS[tone]};font-weight:600", subset=["Sentiment"])
            event = st.dataframe(styled,
                                 key=f"explorer_rows_{revision}__" + "_".join(ids), hide_index=True, width="stretch", height=350,
                                 on_select="rerun", selection_mode="single-row",
                                 column_config={"Headline": st.column_config.TextColumn(width="medium"),
                                                "Sentiment": st.column_config.TextColumn("Tone", width="small"),
                                                "Published": st.column_config.DateColumn(format="DD MMM", width="small")})
            indices = tuple(i for i in event.selection.rows if isinstance(i, int) and 0 <= i < len(rows))
            token = (ids, revision, indices)
            if token != st.session_state.get("explorer_list_token"):
                st.session_state["explorer_list_token"] = token
                if indices:
                    chosen_id = rows[indices[0]].article_id
                    st.session_state["explorer_article"] = chosen_id
                    st.session_state["explorer_article__" + "_".join(ids)] = chosen_id
        with detail:
            with st.container(key="fs_explorer_detail"):
                st.markdown(eyebrow("ARTICLE INSPECTION"), unsafe_allow_html=True)
                chosen = article_selector("Inspect a headline", rows, "explorer_article")
                story(chosen, details=True)


def get_finscope():
    heading("Make FinScope your local workspace", "A personal research application on localhost. Your sources and saved results stay in your local workspace.")
    st.link_button("Get the source on GitHub", REPOSITORY, icon=":material/open_in_new:", type="primary")
    st.subheader("Install and start")
    st.caption("Python 3.11+ · Run these commands on your own computer · Explicit model preparation")
    windows, unix = st.tabs(["Windows · PowerShell", "macOS / Linux"])
    for tab, python, executable in ((windows, "python", ".venv-ai/Scripts/python.exe"),
                                   (unix, "python3", ".venv-ai/bin/python")):
        with tab:
            st.markdown(eyebrow("01 / GET THE LOCAL PRODUCT"), unsafe_allow_html=True)
            st.code("git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git\ncd Finscope", language="bash", wrap_lines=True)
            st.markdown(eyebrow("02 / CREATE THE ENVIRONMENT"), unsafe_allow_html=True)
            st.code(f"{python} -m venv .venv-ai\n{executable} -m pip install -r requirements-local.txt", language="bash", wrap_lines=True)
            st.markdown(eyebrow("03 / PREPARE MODELS AND START"), unsafe_allow_html=True)
            st.code(f"{executable} -m finscope.model_assets --prepare --acknowledge-model-licenses\n{executable} -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="bash", wrap_lines=True)
    st.caption("Open http://localhost:8501 after launch. Model licences and publisher-content permissions are separate.")
    available, planned = st.columns(2)
    with available:
        st.markdown('<section class="fs-capability">' + eyebrow("AVAILABLE IN THE LOCAL PRODUCT")
                    + '<h3>Your personal news workspace</h3><ul><li>Provider fetch and preview connectors</li>'
                    '<li>Pinned local FinBERT + MiniLM</li><li>Persistent SQLite and original links</li>'
                    '<li>Sector/time analytics, heatmap and evidence graph</li><li>Fixed RBA collector CLIs</li></ul></section>', unsafe_allow_html=True)
    with planned:
        st.markdown('<section class="fs-capability">' + eyebrow("OPTIONAL INTEGRATIONS / IN DEVELOPMENT")
                    + '<h3>Additional ways to connect</h3><ul><li>Local Ollama model selection</li>'
                    '<li>Explicitly consented external LLM APIs</li><li>RBA collector controls in the app</li></ul>'
                    '<p>Separate local-product work; availability is not demonstrated by this preview.</p></section>', unsafe_allow_html=True)
    with st.expander("Provider keys, quotas and permissions", expanded=False):
        st.write("Configure provider keys only in the local app's masked fields or project .env. Confirm quota and input rights before fetching, retaining or analyzing text. NewsData's existing pause remains in force; external model calls require explicit transmission consent.")


def main():
    st.set_page_config(page_title="FinScope | Product Showcase", page_icon="◈", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)
    page = st.session_state.get("showcase_page", "Home")
    with st.sidebar:
        st.markdown(brand(), unsafe_allow_html=True)
        st.markdown(eyebrow("PRODUCT TOUR"), unsafe_allow_html=True)
        with st.container(key="fs_nav"):
            for name, _, icon in NAV_ITEMS:
                st.button(name, key=NAV_KEYS[name], icon=":material/" + icon + ":", width="stretch",
                          type="primary" if page == name else "secondary", on_click=go, args=(name,),
                          help="Current page" if page == name else "Open " + name)
        st.caption("Viewing: " + page)
        st.divider()
        st.markdown(badge("Fictional examples"), unsafe_allow_html=True)
        st.caption("The complete product runs locally.")
        st.link_button("Source on GitHub", REPOSITORY, icon=":material/open_in_new:", width="stretch")
    {"Home": home, "User Guide": guide, "Dashboard Preview": dashboard,
     "Knowledge Graph": knowledge_graph, "News Explorer": explorer, "Get FinScope": get_finscope}[page]()
    st.markdown('<div class="fs-footer"><span>FinScope · Financial news in context</span><span>Authored examples · Local-first product</span></div>', unsafe_allow_html=True)
    with st.expander("About FinScope"):
        st.write("A noncommercial financial-text research product. This showcase uses authored fictional data and preset labels; it performs no news collection or AI inference. Local sentiment is text tone, not a price forecast. Similarity suggests candidates, not verified event deduplication or contradiction detection.")
        st.caption("Local model weights: ProsusAI FinBERT, CC BY-NC-SA 4.0; sentence-transformers MiniLM, Apache-2.0. Publisher-content permissions are separate. Software and detailed evidence are available in the repository.")


if __name__ == "__main__":
    main()
