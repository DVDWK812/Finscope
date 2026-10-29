"""Public, synthetic-only product storytelling. Independent of the local runtime."""
from datetime import timedelta

import streamlit as st

from .showcase_data import END, START, SECTORS, SENTIMENTS, examples, graph, select

REPOSITORY = "https://github.com/DVDWK812/Finscope"
PAGES = ("Home", "User Guide", "Dashboard Preview", "Knowledge Graph", "News Explorer", "Get FinScope")
COLORS = ["#4de0b3", "#9caec8", "#ff8f87"]
DEMO_LABEL = "Demo Data / Illustrative Preview"

STYLE = """
<style>
[data-testid="stAppViewContainer"] {background:#0c1423;color:#e9f0fb;}
[data-testid="stHeader"] {background:rgba(12,20,35,.94);}
[data-testid="stSidebar"] {background:#101d30;border-right:1px solid #26364e;}
.block-container {max-width:1260px;padding-top:2.5rem;padding-bottom:3rem;}
h1,h2,h3,[data-testid="stSidebar"] h2 {color:#f4f7fc!important;letter-spacing:-.035em;}
p,li,label {line-height:1.6;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li {color:#c3cfe1;}
[data-testid="stWidgetLabel"] p,[data-testid="stSidebar"] label p {color:#dbe5f4;}
a {color:#60e5bc!important;}
.eyebrow {color:#60e5bc;font-size:.76rem;font-weight:700;letter-spacing:.17em;margin-bottom:.9rem;}
.hero {padding:1.6rem 0 1rem;max-width:900px;}
.hero h1 {font-size:clamp(2.5rem,5.7vw,4.8rem);line-height:1.06;margin:0 0 1.3rem;}
.hero p {color:#b9c7db;font-size:1.12rem;max-width:720px;}
.accent {color:#60e5bc;}
.preview-label {display:inline-block;border:1px solid #34594f;background:#132d2a;color:#8ceacb;
 padding:.35rem .8rem;border-radius:100px;font-size:.78rem;letter-spacing:.015em;margin:.5rem 0 1.1rem;}
.feature {border-top:2px solid #3a766c;background:#132238;border-radius:0 0 14px 14px;padding:1.4rem;min-height:170px;}
.feature h3 {font-size:1.1rem;margin:.2rem 0 .7rem;}
.feature p {font-size:.95rem;color:#bbc8dc;}
.step {color:#60e5bc;font-size:1.5rem;font-weight:700;}
.story {padding:1.1rem 0;border-bottom:1px solid #29394f;}
.story h3 {font-size:1.12rem;line-height:1.4;margin:.3rem 0 .5rem;}
.story-meta {font-size:.8rem;color:#a6bad2;}
.tone {font-size:.8rem;font-weight:650;}
.positive {color:#60e5bc;}.negative {color:#ff9b93;}.neutral {color:#b8c7dc;}
[data-testid="stMetric"] {background:#132238;border:1px solid #2a3c54;padding:1rem;border-radius:12px;}
[data-testid="stMetricLabel"] p {color:#b8c7dc;}
[data-testid="stMetricValue"] {color:#f1f6fd;}
[data-testid="stCaptionContainer"] {color:#a9b9cf;}
[data-testid="stCaptionContainer"] p {color:#aebed3!important;}
.stButton button,.stLinkButton a {background:#172b43;border:1px solid #3a526d;color:#e9f4ff!important;}
.stButton button p,.stLinkButton a p {color:#e9f4ff!important;}
.stButton button[kind="primary"],.stLinkButton a[kind="primary"] {background:#147760;border-color:#26977c;}
@media(max-width:768px){.block-container{padding:1.4rem 1rem 2rem;}.feature{min-height:0;margin-bottom:.7rem;}
 [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}[data-testid="stColumn"]{min-width:180px;flex:1 1 45%;}}
</style>
"""


def go(page):
    st.session_state["showcase_page"] = page


def heading(title, description):
    st.title(title)
    st.write(description)
    st.markdown(f'<div class="preview-label">{DEMO_LABEL}</div>', unsafe_allow_html=True)


def plot(spec, **_options):
    spec = {**spec, "background": "transparent", "config": {
        "view": {"stroke": None},
        "axis": {"labelColor": "#b9c9de", "titleColor": "#c8d8eb", "gridColor": "#27374e", "domainColor": "#3a4e68"},
        "legend": {"labelColor": "#c8d8eb", "titleColor": "#d9e5f4"}}}
    st.vega_lite_chart(spec, width="stretch", theme=None)


def home():
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
    st.title("How FinScope works")
    st.write("Four steps in the full local product. This website illustrates the workflow; it does not fetch or analyze news.")
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
    st.markdown(f'<div class="story"><div class="story-meta">FICTIONAL · {row.day:%d %b %Y} · {row.source}</div>'
                f'<h3>{row.title}</h3><span class="tone {row.sentiment.lower()}">{row.sentiment} · illustrative label</span></div>', unsafe_allow_html=True)
    if details:
        st.write(row.summary)
        st.caption(f"{row.article_id} · {row.company} · {row.sector} · Illustrative candidate {row.candidate}")
        st.caption("Fictional sample only. No publisher URL exists; no original-article link is fabricated.")


def knowledge_graph():
    heading("Follow the connections", "An illustrative graph linking fictional companies, industries, articles, sources and candidate events.")
    company = st.selectbox("Fictional company", sorted({r.company for r in examples()}), key="graph_company")
    data = graph(examples(), company)
    plot({"layer": [
        {"data": {"values": data["edges"]}, "mark": {"type": "rule", "color": "#476079", "opacity": .65},
         "encoding": {"x": {"field": "x", "type": "quantitative", "axis": None, "scale": {"domain": [0, 100]}},
                      "y": {"field": "y", "type": "quantitative", "axis": None, "scale": {"domain": [0, 100]}},
                      "x2": {"field": "x2"}, "y2": {"field": "y2"}, "tooltip": [{"field": "relationship"}, {"field": "article_id"}]}},
        {"data": {"values": data["nodes"]}, "mark": {"type": "circle", "size": 700, "opacity": 1, "stroke": "#101d30", "strokeWidth": 2},
         "encoding": {"x": {"field": "x", "type": "quantitative", "axis": None}, "y": {"field": "y", "type": "quantitative", "axis": None},
                      "color": {"field": "kind", "type": "nominal", "title": "Entity type", "legend": {"orient": "bottom", "columns": 2}, "scale": {"range": ["#60e5bc", "#9dbfff", "#e9c776", "#d4adff", "#f69e9e"]}},
                      "tooltip": [{"field": "name"}, {"field": "kind"}]}},
        {"data": {"values": data["nodes"]}, "mark": {"type": "text", "dy": -22, "color": "#d6e2f2", "fontSize": 11, "limit": 130},
         "encoding": {"x": {"field": "x", "type": "quantitative", "axis": None}, "y": {"field": "y", "type": "quantitative", "axis": None}, "text": {"field": "name"}}}],
        "height": 430, "resolve": {"scale": {"color": "independent"}}}, width="stretch")
    st.caption("Every relationship is authored for this preview. Candidate membership does not establish event identity, factual contradiction or a real financial relationship.")
    rows = [r for r in examples() if r.company == company]
    chosen = st.selectbox("Inspect an illustrative article", [r.article_id for r in rows], key="graph_article")
    story(next(r for r in rows if r.article_id == chosen), details=True)


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
    st.title("Make FinScope your local workspace")
    st.write("The complete application runs on your computer at http://localhost:8501. This public website remains an illustrative showcase.")
    st.link_button("Get the source on GitHub ↗", REPOSITORY, type="primary")
    st.subheader("Install and start")
    st.caption("Python 3.11+ · allow disk space for explicitly prepared model assets · noncommercial model use")
    windows, unix = st.tabs(["Windows · PowerShell", "macOS / Linux"])
    with windows:
        st.code("git clone https://github.com/DVDWK812/Finscope.git\ncd Finscope\npython -m venv .venv-ai\n.venv-ai/Scripts/python.exe -m pip install -r requirements-local.txt\n.venv-ai/Scripts/python.exe -m finscope.model_assets --prepare --acknowledge-model-licenses\n.venv-ai/Scripts/python.exe -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="powershell")
    with unix:
        st.code("git clone https://github.com/DVDWK812/Finscope.git\ncd Finscope\npython3 -m venv .venv-ai\n.venv-ai/bin/python -m pip install -r requirements-local.txt\n.venv-ai/bin/python -m finscope.model_assets --prepare --acknowledge-model-licenses\n.venv-ai/bin/python -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="bash")
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
    with st.sidebar:
        st.markdown("## ◈ FinScope")
        st.caption("News. Sentiment. Context.")
        page = st.radio("Explore FinScope", PAGES, key="showcase_page", label_visibility="collapsed")
        st.divider()
        st.caption("Public showcase\n\nThe full product runs locally.")
        st.link_button("GitHub ↗", REPOSITORY, width="stretch")
    {"Home": home, "User Guide": guide, "Dashboard Preview": dashboard,
     "Knowledge Graph": knowledge_graph, "News Explorer": explorer, "Get FinScope": get_finscope}[page]()
    st.divider()
    with st.expander("About FinScope"):
        st.write("A noncommercial financial-text research product. This showcase uses authored fictional data and preset labels; it performs no news collection or AI inference. Local sentiment is text tone, not a price forecast. Similarity suggests candidates, not verified event deduplication or contradiction detection.")
        st.caption("Local model weights: ProsusAI FinBERT, CC BY-NC-SA 4.0; sentence-transformers MiniLM, Apache-2.0. Publisher-content permissions are separate. Software and detailed evidence are available in the repository.")


if __name__ == "__main__":
    main()
