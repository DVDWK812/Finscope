"""Public, synthetic-only product storytelling. Independent of the local runtime."""
from datetime import timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from .showcase_data import (END, START, SECTORS, SENTIMENTS, article_label,
                            candidate_groups, examples, graph, graph_overview, select, word_cloud_terms)
from .showcase_visuals import graph_layout, relationship_markup, visible_graph, word_cloud_markup
from .showcase_theme import TOKENS, NAV_ITEMS, NAV_KEYS, SENTIMENT_COLORS, badge, brand, eyebrow, theme_css

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
    spec = {**spec, "background": "transparent", "config": {
        "view": {"stroke": None},
        "axis": {"labelColor": "#b9c9de", "titleColor": "#c8d8eb", "gridColor": "#27374e", "domainColor": "#3a4e68"},
        "legend": {"labelColor": "#c8d8eb", "titleColor": "#d9e5f4"}}}
    st.vega_lite_chart(spec, width="stretch", theme=None)


def home():
    st.markdown(badge(), unsafe_allow_html=True)
    st.markdown('''<section class="hero"><div class="eyebrow">FINSCOPE · LOCAL FINANCIAL INTELLIGENCE</div>
        <h1>Financial news.<br><span class="accent">A clearer perspective.</span></h1>
        <p>Bring sources, sentiment and industry context into one local workspace.
        Explore the interface here. Run the full product on your own computer.</p></section>''', unsafe_allow_html=True)
    st.caption("Public product showcase · No live news, model inference or user-news storage on this website.")
    a, b, _ = st.columns([1.2, 1.2, 2.5])
    a.button("How it works", type="primary", on_click=go, args=("User Guide",), width="stretch")
    b.button("Get FinScope", on_click=go, args=("Get FinScope",), width="stretch")
    st.divider()
    st.subheader("From individual reports to an inspectable picture")
    cards = (("01", "Bring your sources", "Choose a supported news connector or approved text in the local product."),
             ("02", "See the context", "Explore text sentiment, industry tags, time trends and possible overlaps."),
             ("03", "Keep the original", "Return to source articles and inspect the evidence behind each local result."))
    for column, (number, title, text) in zip(st.columns(3), cards):
        with column:
            st.markdown(f'<div class="feature"><div class="step">{number}</div><h3>{title}</h3><p>{text}</p></div>', unsafe_allow_html=True)
    st.subheader("A preview you can explore")
    st.caption(DEMO_LABEL + " · Fictional entities and preset sentiment labels. Nothing below is collected or inferred.")
    rows = examples()
    a, b = st.columns([1.6, 1])
    with a:
        sector_plot(rows)
    with b:
        st.metric("Fictional reports", len(rows))
        st.metric("Illustrated industries", len(SECTORS))
        st.button("Explore dashboard preview", on_click=go, args=("Dashboard Preview",), width="stretch")
    st.link_button("View the project on GitHub ↗", REPOSITORY)


def guide():
    heading("How FinScope works", "Four steps from approved text to an inspectable local workspace.")
    steps = (("01", "Choose a news source", "In the local app, select a supported provider or add approved text. Enter credentials only on your computer. Existing quota and permission checks apply."),
             ("02", "Choose an AI model", "Start with pinned local FinBERT and sentence embeddings. Prepare model assets explicitly once. Optional model integrations are described under Get FinScope."),
             ("03", "Fetch and analyze", "Preview returned headlines and available summaries. Confirm storage and processing rights before saving or running local analysis."),
             ("04", "Explore and inspect", "Use sector and time filters, the heatmap and evidence graph. Inspect raw originals and follow their real source links in the local product."))
    for number, title, text in steps:
        with st.container(border=True):
            st.markdown(f'<div class="eyebrow">STEP {number}</div>', unsafe_allow_html=True)
            st.subheader(title)
            st.write(text)
    st.button("Try the illustrative dashboard", type="primary", on_click=go, args=("Dashboard Preview",))


def reset_filters():
    for key in ("preview_sectors", "preview_sentiments", "preview_dates"):
        st.session_state.pop(key, None)


def preview_filters():
    a, b, c = st.columns([1.2, 1, 1])
    with a:
        dates = st.date_input("Example dates", value=(START, END), min_value=START, max_value=END, key="preview_dates")
    with b:
        sectors = st.multiselect("Industry", SECTORS, key="preview_sectors", placeholder="All industries")
    with c:
        sentiments = st.multiselect("Illustrative sentiment", SENTIMENTS, key="preview_sentiments", placeholder="All labels")
    st.button("Reset preview", on_click=reset_filters)
    if len(dates) != 2:
        st.info("Choose a start and end date to explore the fictional sample.")
        return [], START, END
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
    heading("A dashboard, in perspective", "Explore a fixed fictional sample. Filters change the preview, not live data or model outputs.")
    rows, start, end = preview_filters()
    if not rows:
        st.info("No fictional records match these filters. Reset the preview or choose a wider selection.")
        return
    counts = [sum(r.sentiment == label for r in rows) for label in SENTIMENTS]
    for column, label, value in zip(st.columns(4),
            ("Fictional reports", "Positive label share", "Industries", "Example days"),
            (len(rows), f"{counts[0] / len(rows):.0%}", len({r.sector for r in rows}), (end - start).days + 1)):
        column.metric(label, value)
    a, b = st.columns([1.6, 1])
    with a:
        st.subheader("Sector sentiment distribution")
        sector_plot(rows)
    with b:
        st.subheader("Illustrative sentiment mix")
        plot({"data": {"values": [{"Sentiment": label, "Reports": value} for label, value in zip(SENTIMENTS, counts)]},
            "mark": {"type": "arc", "innerRadius": 65},
            "encoding": {"theta": {"field": "Reports", "type": "quantitative"},
                         "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS}},
                         "tooltip": [{"field": "Sentiment"}, {"field": "Reports"}]}, "height": 265}, width="stretch")
    st.subheader("Financial news trends — fictional sample")
    plot({"data": {"values": time_rows(rows, start, end)},
        "mark": {"type": "line", "point": True},
        "encoding": {"x": {"field": "Date", "type": "temporal", "title": "Example date"},
                     "y": {"field": "Reports", "type": "quantitative", "title": "Fictional reports", "axis": {"tickMinStep": 1}},
                     "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": COLORS}},
                     "tooltip": [{"field": "Date"}, {"field": "Sentiment"}, {"field": "Reports"}]}, "height": 220}, width="stretch")
    st.subheader("Industry sentiment heatmap")
    cells = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        for sector in SECTORS:
            sample = [r for r in rows if r.day == day and r.sector == sector]
            cells.append({"Date": day.isoformat(), "Industry": sector, "Reports": len(sample),
                          "Balance": sum({"Positive": 1, "Neutral": 0, "Negative": -1}[r.sentiment] for r in sample) / len(sample) if sample else None})
    plot({"data": {"values": cells}, "mark": {"type": "rect", "cornerRadius": 3},
        "encoding": {"x": {"field": "Date", "type": "ordinal", "title": None, "axis": {"labelAngle": -40}},
                     "y": {"field": "Industry", "type": "nominal", "title": None, "sort": list(SECTORS)},
                     "color": {"condition": {"test": "datum.Reports == 0", "value": "#24344b"}, "field": "Balance", "type": "quantitative", "scale": {"domain": [-1, 0, 1], "range": [COLORS[2], "#5b6d86", COLORS[0]]}},
                     "tooltip": [{"field": "Date"}, {"field": "Industry"}, {"field": "Reports"}, {"field": "Balance"}]}, "height": 235}, width="stretch")
    st.caption("Illustrative balance = (positive − negative labels) / sample reports. Empty cells mean no example record; this is not observed market coverage or an investment signal.")


def story(row, details=False):
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


def article_selector(label, rows, key):
    by_id = {r.article_id: r for r in rows}
    if st.session_state.get(key) not in by_id:
        st.session_state.pop(key, None)
    ids = list(by_id)
    widget_key = key + "__" + "_".join(ids)
    selected = st.session_state.get(key)
    chosen = st.selectbox(label, ids, key=widget_key, index=ids.index(selected) if selected in ids else 0,
                          format_func=lambda ident: article_label(by_id[ident]))
    st.session_state[key] = chosen
    return by_id[chosen]


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
    heading("Stay close to the original", "Browse fictional headlines to see the intended news-exploration experience. Real source links belong to the local product.")
    a, b = st.columns([2, 1])
    with a:
        query = st.text_input("Search fictional examples", placeholder="Try an industry, company or headline", max_chars=120)
    with b:
        industry = st.selectbox("Example industry", ("All industries", *SECTORS))
    rows = select(examples(), sectors=() if industry == "All industries" else (industry,), search=query)
    st.caption(f"{len(rows)} fictional originals · preset labels · no publisher content or URLs")
    if not rows:
        st.info("No fictional examples match. Try a different search or industry.")
    for row in sorted(rows, key=lambda r: (r.day, r.article_id), reverse=True):
        with st.container(border=True):
            story(row, details=True)


def get_finscope():
    heading("Make FinScope your local workspace", "Run the complete application on your computer. Explore the interface here.")
    st.link_button("Get the source on GitHub ↗", REPOSITORY, type="primary")
    st.subheader("Install and start")
    st.caption("Python 3.11+ · allow disk space for explicitly prepared model assets · noncommercial model use")
    windows, unix = st.tabs(["Windows · PowerShell", "macOS / Linux"])
    with windows:
        st.code("git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git\ncd Finscope\npython -m venv .venv-ai\n.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt\n.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses\n.venv-ai/Scripts/python.exe -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="powershell")
    with unix:
        st.code("git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git\ncd Finscope\npython3 -m venv .venv-ai\n.venv-ai/bin/python -m pip install -r requirements-local.txt\n.venv-ai/bin/python -m finscope.model_assets --prepare --acknowledge-model-licenses\n.venv-ai/bin/python -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="bash")
    a, b = st.columns(2)
    with a:
        st.subheader("Available in the local product")
        st.markdown("- Marketaux and Finnhub fetch/preview connectors\n- NewsData.io connector, with its existing manual pause\n- Pinned local FinBERT + MiniLM\n- Persistent local SQLite and original links\n- Sector/time analytics, heatmap and evidence graph\n- Fixed RBA RSS/HTML collectors via local CLI")
    with b:
        st.subheader("Optional integrations in development")
        st.markdown("- Local Ollama model selection\n- Explicitly consented external LLM APIs\n- RBA collector controls inside the application")
        st.caption("These integrations are separate local-product work. Their availability is not demonstrated by this public preview.")
    st.subheader("For API-based features")
    st.write("Supply your own provider key in the local app's masked fields or project .env. Confirm available quota and input rights before fetching, retaining or analyzing text. Optional external models require their own key, permission and explicit transmission consent. Never paste credentials into this website.")
    st.caption("The local product remains the primary application. No live fetch, model setup, API-key input or news database is part of the public showcase.")


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
