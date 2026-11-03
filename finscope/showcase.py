"""Public, synthetic-only product storytelling. Independent of the local runtime."""
from datetime import timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from .showcase_data import (END, START, SECTORS, SENTIMENTS, article_label,
                            candidate_groups, examples, graph, graph_overview, select, word_cloud_terms)
from .showcase_visuals import graph_layout, relationship_markup, visible_graph, word_cloud_markup
from .showcase_content import (LOCAL_REVIEW_SHA, LOCAL_REVIEW_DATE, GUIDE_STEPS, SOURCE_CARDS,
                               MODEL_CARDS, CAPABILITIES, ALL_PARENTS, ALL_CHILDREN,
                               topic_context, topic_select, topic_rollup)
from .showcase_preferences import preferences, t, localize_html, LANGUAGE, display_formatter
from .showcase_theme import (theme_tokens, sentiment_colors, NAV_ITEMS, NAV_KEYS, badge, brand,
                             dashboard_preview, eyebrow, theme_css,
                             capabilities_markup, workflow_markup, hierarchy_markup, launcher_architecture)

REPOSITORY = "https://github.com/DVDWK812/Finscope"
SHOWCASE_SOURCE = REPOSITORY + "/tree/main"
LOCAL_PRODUCT = REPOSITORY + "/tree/local"
PAGES = ("Home", "User Guide", "Dashboard Preview", "Knowledge Graph", "News Explorer", "Get FinScope")


def palette():
    return [sentiment_colors()[name] for name in SENTIMENTS]

def go(page):
    st.session_state["showcase_page"] = page


def sync_choice(display_key, state_key):
    st.session_state[state_key] = st.session_state[display_key]


def choice(kind, label, options, key, **kwargs):
    """Remount localized choices so the browser refreshes selected display text.

    Canonical English values still drive every filter; only the widget instance
    changes locale. Native comboboxes otherwise retain their old input text.
    """
    if LANGUAGE.get() == "en":
        return kind(label, options, key=key, **kwargs)
    display_key = key + "__display_zh"
    fallback = [] if kind is st.multiselect else options[0]
    st.session_state[display_key] = st.session_state.get(key, fallback)
    result = kind(label, options, key=display_key, on_change=sync_choice,
                  args=(display_key, key), **kwargs)
    st.session_state[key] = result
    return result


def heading(title, description):
    with st.container(key="fs_page_header"):
        st.markdown(localize_html('<div class="fs-header-meta">' + eyebrow("PRODUCT SHOWCASE") + badge() + '</div>'), unsafe_allow_html=True)
        st.title(t(title))
        st.write(t(description))


def plot(spec, **_options):
    def labels(value):
        if isinstance(value, dict):
            translated = {key: item if key == "field" else labels(item) for key, item in value.items()}
            if "field" in translated and "title" not in translated:
                translated["title"] = t(translated["field"])
            return translated
        if isinstance(value, list):
            return [labels(item) for item in value]
        return t(value) if isinstance(value, str) else value

    spec = labels(spec)
    spec = {**spec, "background": theme_tokens()["surface"], "config": {
        "font": "system-ui", "view": {"stroke": None},
        "axis": {"labelColor": theme_tokens()["muted"], "titleColor": theme_tokens()["muted"],
                 "labelFontSize": 11, "titleFontSize": 11, "labelPadding": 8,
                 "gridColor": theme_tokens()["border"], "gridOpacity": .45, "domain": False, "ticks": False},
        "legend": {"labelColor": theme_tokens()["muted"], "title": None, "orient": "bottom",
                   "direction": "horizontal", "labelFontSize": 11, "symbolType": "circle",
                   "columnPadding": 14, "symbolSize": 65}}}
    st.vega_lite_chart(spec, width="stretch", theme=None)


def data_table(data, **options):
    """Translate presentation values; leave records and selection IDs intact."""
    frame = pd.DataFrame(data).map(lambda value: t(value) if isinstance(value, str) else value)
    frame = frame.rename(columns=t)
    tokens = theme_tokens()
    styled = frame.style.set_properties(**{"background-color": tokens["surface"], "color": tokens["text"]})
    if t("Sentiment") in frame:
        colors = {t(tone): color for tone, color in sentiment_colors().items()}
        styled = styled.map(lambda tone: f"color:{colors.get(tone, tokens['text'])};font-weight:600",
                            subset=[t("Sentiment")])
    if "column_config" in options:
        options["column_config"] = {t(key): {**value, "label": t(value.get("label") or key)}
                                    for key, value in options["column_config"].items()}
    return st.dataframe(styled, **options)


def home():
    st.markdown(localize_html('<div class="fs-header-meta">' + eyebrow("LOCAL-FIRST FINANCIAL INTELLIGENCE") + badge() + '</div>'), unsafe_allow_html=True)
    with st.container(key="fs_home_hero"):
        intro, preview = st.columns([1.05, 1], gap="large")
        with intro:
            st.markdown(localize_html('<section class="fs-hero"><h1>Financial news.<br><span class="fs-hero-accent">A clearer perspective.</span></h1>'
                        '<p>Collect permitted financial text, classify its topics, analyze sentiment '
                        'and inspect originals in a persistent local workspace.</p></section>'), unsafe_allow_html=True)
            with st.container(key="fs_hero_ctas"):
                demo, install = st.columns(2)
                demo.button(t("Explore Demo"), key="hero_demo", icon=":material/arrow_forward:", type="primary", on_click=go, args=("Dashboard Preview",), width="stretch")
                install.button(t("Get FinScope"), key="hero_install", icon=":material/download:", on_click=go, args=("Get FinScope",), width="stretch")
            st.button(t("How it works"), key="hero_guide", type="tertiary", icon=":material/menu_book:", on_click=go, args=("User Guide",))
            st.caption(t("Explore authored examples here. Run the complete product on your computer."))
            st.caption(t("In the local app, Update & Analyze runs persistent worker tasks with saved progress and explicit resource pauses."))
        with preview:
            st.markdown(localize_html(workflow_markup(GUIDE_STEPS, compact=True)), unsafe_allow_html=True)
    st.subheader(t("Local Product Capabilities"))
    st.caption(t("Implemented in the separate local application. These cards describe capabilities; this website does not collect news, start workers or run models."))
    st.markdown(localize_html(capabilities_markup(CAPABILITIES)), unsafe_allow_html=True)
    st.caption(t("Local defaults and configured integrations have different evidence scopes. DeepSeek is an authored-text interface test; repeated-load stability remains unverified."))
    with st.expander(t("Illustrative sample overview · 24 fictional originals"), expanded=False):
        st.markdown(localize_html(dashboard_preview(examples())), unsafe_allow_html=True)


def guide():
    heading("How FinScope works", "Configure once, review the scope, then update and inspect locally.")
    st.subheader(t("The local workflow"))
    st.markdown(localize_html(workflow_markup(GUIDE_STEPS)), unsafe_allow_html=True)
    st.caption(t("Settings covers General, News sources and Analysis models. Saving settings does not fetch or infer; changing filters does not fetch. The diagram is illustrative, not an operational control."))
    st.button(t("Try the illustrative dashboard"), key="guide_demo", icon=":material/arrow_forward:", type="primary", on_click=go, args=("Dashboard Preview",))
    with st.expander(t("Sources, collection modes and permissions"), expanded=False):
        st.write(t("Broad Financial News is the default, without company or industry query filters. Selected media uses six publisher filters and Latest news only; Company Tracking uses a saved watchlist. These are collection scopes, not inferred article industries."))
        capability_cards(SOURCE_CARDS)
        st.caption(t("Batches are bounded. Failed or unknown requests do not automatically retry or rotate keys; dated budgets do not renew themselves. No arbitrary-site crawl, universal full text, exhaustive coverage or unrestricted publisher rights is promised."))
    with st.expander(t("Models, topics and provenance"), expanded=False):
        capability_cards(MODEL_CARDS, columns=3)
        st.write(t("DeepSeek has a controlled three-authored-text interface test; it is not the automatic real-news pipeline or an accuracy evaluation. A response alias is not a fixed weight revision."))
        st.caption(t("Repeated-load stability remains unverified: the later multi-round attempt was blocked by resource preflight before inference. Starting a local service or listing models is not loading a model."))
    with st.expander(t("Advanced collection and saved-record analysis"), expanded=False):
        st.write(t("In the local Settings workspace, advanced collect-only actions save permitted inputs without analysis. Saved-record offline analysis reuses retained text without fetching it again. Persistent tasks retain checkpoints; explicit continuation still respects expiry, permissions, model readiness and failed/unknown dispatch holds."))
        st.caption(t("Unknown account balance, Unclassified text and not-applicable analysis are distinct states. They are not zero quota, a company-industry guess or Neutral sentiment."))


def capability_cards(cards, columns=2):
    """Reuse the established card presentation; copy is escaped, never remote."""
    for offset in range(0, len(cards), columns):
        for column, (title, text) in zip(st.columns(columns), cards[offset:offset + columns]):
            with column:
                st.markdown(localize_html('<article class="fs-feature"><h3>' + escape(t(title)) + '</h3><p>'
                            + escape(t(text)) + '</p></article>'), unsafe_allow_html=True)


def reset_filters():
    # Explicit assignments send changed widget values back to the browser.
    # Removing keys resets server defaults but can leave old client filter chips.
    st.session_state["preview_sectors"] = []
    st.session_state["preview_sentiments"] = []
    st.session_state["preview_dates"] = (START, END)
    st.session_state["preview_topic_parent"] = ALL_PARENTS
    for key in list(st.session_state):
        if key.startswith("preview_topic_child__"):
            st.session_state[key] = ALL_CHILDREN


def preview_filters():
    with st.expander(t("Filter sample"), expanded=False):
        a, b, c = st.columns([1.2, 1, 1])
        with a:
            dates = st.date_input(t("Example dates"), value=(START, END), min_value=START, max_value=END, format="DD/MM/YYYY", key="preview_dates")
        with b:
            sectors = choice(st.multiselect, t("Industry"), SECTORS, key="preview_sectors", placeholder=t("All industries"), format_func=display_formatter())
        with c:
            sentiments = choice(st.multiselect, t("Illustrative sentiment"), SENTIMENTS, key="preview_sentiments", placeholder=t("All labels"), format_func=display_formatter())
        st.button(t("Reset preview"), icon=":material/restart_alt:", on_click=reset_filters)
    if len(dates) != 2:
        st.info(t("Choose a start and end date to explore the fictional sample."))
        return [], START, END
    st.caption(t('{v0} – {v1} · {v2} · {v3}', v0=format(dates[0], '%d %b'), v1=format(dates[1], '%d %b %Y'), v2=", ".join(t(s) for s in sectors) or t("All industries"), v3=", ".join(t(s) for s in sentiments) or t("All sentiments")))
    return select(examples(), dates[0], dates[1], sectors, sentiments), dates[0], dates[1]


def sector_plot(rows):
    data = [{"Industry": sector, "Sentiment": label,
             "Reports": sum(r.sector == sector and r.sentiment == label for r in rows)}
            for sector in SECTORS for label in SENTIMENTS]
    plot({"data": {"values": data}, "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {"y": {"field": "Industry", "type": "nominal", "sort": list(SECTORS), "title": None},
                     "x": {"field": "Reports", "type": "quantitative", "title": "Fictional reports", "axis": {"tickMinStep": 1}},
                     "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": palette()}},
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
        st.info(t("No fictional records match these filters. Reset the preview or choose a wider selection."))
        return
    counts = [sum(r.sentiment == label for r in rows) for label in SENTIMENTS]
    with st.container(key="fs_kpis"):
        for column, label, value in zip(st.columns(4),
                ("Fictional reports", "Positive label share", "Industries", "Example days"),
                (len(rows), f"{counts[0] / len(rows):.0%}", len({r.sector for r in rows}), (end - start).days + 1)):
            column.metric(t(label), value)
    industry_topic_preview(rows)
    with st.container(key="fs_dashboard_charts"):
        a, b = st.columns([1.5, 1])
        with a:
            with st.container(key="fs_chart_sector"):
                st.subheader(t("Sector sentiment distribution"))
                st.caption(t("Original reports by company industry and preset tone"))
                sector_plot(rows)
        with b:
            with st.container(key="fs_chart_mix"):
                st.subheader(t("Illustrative sentiment mix"))
                st.caption(t('{v0} original reports in this selection', v0=len(rows)))
                plot({"data": {"values": [{"Sentiment": label, "Reports": value} for label, value in zip(SENTIMENTS, counts)]},
                    "mark": {"type": "arc", "innerRadius": 66, "padAngle": .025, "cornerRadius": 3},
                    "encoding": {"theta": {"field": "Reports", "type": "quantitative"},
                                 "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": palette()}},
                                 "tooltip": [{"field": "Sentiment"}, {"field": "Reports"}]}, "height": 265})
    with st.container(key="fs_chart_time"):
        st.subheader(t("Financial news trends — fictional sample"))
        st.caption(t("Daily report counts · No price or market-return series"))
        plot({"data": {"values": time_rows(rows, start, end)},
            "mark": {"type": "line", "point": {"filled": True, "size": 32}, "strokeWidth": 2},
            "encoding": {"x": {"field": "Date", "type": "temporal", "title": None, "axis": {"format": "%d %b", "tickCount": 6, "labelOverlap": "greedy"}},
                         "y": {"field": "Reports", "type": "quantitative", "title": "Reports", "axis": {"tickMinStep": 1}},
                         "color": {"field": "Sentiment", "type": "nominal", "scale": {"domain": list(SENTIMENTS), "range": palette()}},
                         "tooltip": [{"field": "Date", "type": "temporal", "format": "%d %b %Y"}, {"field": "Sentiment"}, {"field": "Reports"}]}, "height": 220})
    with st.container(key="fs_chart_heatmap"):
        st.subheader(t("Industry sentiment heatmap"))
        st.caption(t("October 2026 · Day of the month"))
        cells = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            for sector in SECTORS:
                sample = [r for r in rows if r.day == day and r.sector == sector]
                cells.append({"Date": day.isoformat(), "Industry": sector, "Reports": len(sample),
                              "Balance": sum({"Positive": 1, "Neutral": 0, "Negative": -1}[r.sentiment] for r in sample) / len(sample) if sample else None})
        plot({"data": {"values": cells}, "mark": {"type": "rect", "cornerRadius": 2, "stroke": theme_tokens()["surface"], "strokeWidth": 2},
            "encoding": {"x": {"field": "Date", "type": "ordinal", "title": None, "axis": {"labelAngle": 0, "labelFontSize": 10, "labelExpr": "substring(datum.label,8,10)"}},
                         "y": {"field": "Industry", "type": "nominal", "title": None, "sort": list(SECTORS)},
                         "color": {"condition": {"test": "datum.Reports == 0", "value": theme_tokens()["raised"]}, "field": "Balance", "type": "quantitative",
                                   "scale": {"domain": [-1, 0, 1], "range": [palette()[2], "#61758c", palette()[0]]}, "legend": {"title": "Label balance", "gradientLength": 150}},
                         "tooltip": [{"field": "Date"}, {"field": "Industry"}, {"field": "Reports"}, {"field": "Balance", "format": ".2f"}]}, "height": 235})
        st.caption(t("Balance = (positive − negative labels) / reports. Empty cells have no authored record; they do not measure market coverage."))


def industry_topic_preview(rows):
    with st.container(key="fs_industry_topics"):
        st.subheader(t("Industry intelligence"))
        unclassified = sum(topic_context(r)["parent"] == "Unclassified" for r in rows)
        st.caption(t('{v0} authored topic labels · {v1} Unclassified · {v2} originals. This is an illustration, not model output; company industries remain separate.', v0=len(rows) - unclassified, v1=unclassified, v2=len(rows)))
        all_rows = examples()
        parents = [ALL_PARENTS, *sorted({topic_context(r)["parent"] for r in all_rows})]
        a, b = st.columns(2)
        with a:
            parent = choice(st.selectbox, t("Topic parent"), parents, key="preview_topic_parent", format_func=display_formatter())
        children = sorted({topic_context(r)["child"] for r in topic_select(all_rows, parent)
                           if topic_context(r)["child"] is not None})
        with b:
            child = choice(st.selectbox, t("Child topic"), [ALL_CHILDREN, *children], disabled=not children,
                                 key="preview_topic_child__" + parent, format_func=display_formatter())
        selected = topic_select(rows, parent, child)
        st.markdown(localize_html(hierarchy_markup(topic_rollup(rows), parent)), unsafe_allow_html=True)
        st.caption(t('{v0} topic-list originals / {v1} dashboard originals. Topic pickers narrow this list; the charts retain the dashboard selection.', v0=len(selected), v1=len(rows)))
        if selected:
            with st.expander(t('Inspect topic originals ({v0})', v0=len(selected)), expanded=False):
                data_table([{"Headline": article_label(r), "Company industry": r.sector,
                               "Text topic parent": topic_context(r)["parent"],
                               "Text topic child": topic_context(r)["child"] or "No child label"} for r in selected],
                             hide_index=True, width="stretch")
        else:
            st.info(t("No authored topic examples match this dashboard selection. Reset the preview or change the topic."))
        st.caption(t("Local shared filters: date / source / parent / child / model → Dashboard · Industries · Graph · Explorer. This website uses page-specific authored-sample filters; no collection query is sent."))


def story(row, details=False):
    if row is None:
        st.info(t("Select a headline to inspect its evidence."))
        return
    st.markdown(f'<div class="story"><div class="story-meta">{t("FICTIONAL")} · {row.day:%d %b %Y} · {escape(row.source)}</div>'
                f'<h3>{escape(article_label(row))}</h3><span class="tone {row.sentiment.lower()}">{t(row.sentiment)} · {t("illustrative label")}</span></div>', unsafe_allow_html=True)
    if details:
        st.write(t("Complete headline: {headline}", headline=row.title))
        st.write(row.summary)
        st.caption(t('{v0} · Company industry: {v1}', v0=row.company, v1=t(row.sector)))
        topic = topic_context(row)
        topic_label = (f'{t(topic["parent"])} / {t(topic["child"])} · {t("authored illustration")}'
                       if topic["child"] else t("Unclassified · separate from company metadata"))
        st.caption(t("Text topic: {topic}", topic=topic_label))
        group = next((g for g in candidate_groups(examples()) if row.article_id in g["article_ids"]), None)
        if group:
            st.caption(t('Unverified candidate: {v0}. {v1}', v0=t(group["label"]), v1=t(group["basis"])))
        st.caption(t("Fictional sample only. No publisher URL exists; no original-article link is fabricated."))
        with st.expander(t("Topic and model context"), expanded=False):
            basis = (t('authored illustration using the literal phrase “{evidence}”.', evidence=topic["evidence"])
                     if topic["evidence"] else t("no authored text-topic annotation; company metadata is not substituted."))
            st.write(t("Topic basis: {basis}", basis=basis))
            st.write(t("Collection cohort: Not applicable — authored example; no source query was sent."))
            st.write(t("Model history: Not applicable — no model runs in this showcase. The local product retains separate classification and sentiment versions, input evidence and source provenance."))
        with st.expander(t("Technical details"), expanded=False):
            st.write({t("Article ID"): row.article_id, t("Candidate reference"): row.candidate or t("None")})


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
    chosen = st.selectbox(t(label), ids, key=widget_key, index=None,
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
                    f'<style>body{{margin:0;background:{theme_tokens()["surface"]};color:{theme_tokens()["text"]};}}</style></head><body>'
                    + markup + '</body></html>', height=int(canvas_height * mobile_zoom) + 56, scrolling=False)


def headline_cloud(records):
    terms = word_cloud_terms(records)
    if not terms:
        st.info(t("No headline terms are available for this illustrative selection."))
        return
    st.html(word_cloud_markup(terms))
    options = [item["term"] for item in terms]
    if st.session_state.get("graph_cloud_word") not in options:
        st.session_state.pop("graph_cloud_word", None)
    term = st.selectbox(t("Select a word"), options, key="graph_cloud_word", format_func=display_formatter())
    selected = next(item for item in terms if item["term"] == term)
    matches = [row for row in records if row.article_id in selected["article_ids"]]
    st.caption(t('{v0} fictional headline(s) contain “{v1}”. Counts are once per headline.', v0=len(matches), v1=term))
    data_table([{"Headline": article_label(r), "Complete headline": r.title, "Company": r.company,
                   "Industry": r.sector, "Sentiment": r.sentiment, "Fictional source": r.source}
                  for r in matches], hide_index=True, width="stretch")
    with st.expander(t("Technical details: word matches"), expanded=False):
        data_table([{"Article ID": r.article_id, "Headline": article_label(r)} for r in matches],
                     hide_index=True, width="stretch")
    story(article_selector("Open a matching fictional article", matches, "graph_cloud_article"), details=True)


def knowledge_graph():
    heading("Explore the news connections", "Follow the context from industry to company, headline and potential related coverage.")
    all_rows = examples()
    with st.container(key="fs_graph_controls"):
        a, b = st.columns([1.2, 1.4])
        with a:
            perspective = st.radio(t("Graph perspective"), ("Company focus", "Industry network"), horizontal=True, key="graph_perspective", format_func=display_formatter())
        with b:
            company = st.selectbox(t("Fictional company"), sorted({r.company for r in all_rows}), key="graph_company", format_func=display_formatter())
    rows = [r for r in all_rows if r.company == company]
    groups = candidate_groups(rows)
    with st.container(key="fs_kpis"):
        columns = st.columns(4 if perspective == "Company focus" else 3)
        if perspective == "Company focus":
            for col, label, value in zip(columns, ("Fictional reports", "Unverified topic groups", "Illustrative sources", "Positive / Negative"),
                    (len(rows), len(groups), len({r.source for r in rows}),
                     f'{sum(r.sentiment == "Positive" for r in rows)} / {sum(r.sentiment == "Negative" for r in rows)}')):
                col.metric(t(label), value)
        else:
            for col, label, value in zip(columns, ("Fictional companies", "Illustrated sectors", "Illustrative source reports"),
                                         (len({r.company for r in all_rows}), len(SECTORS), len(all_rows))):
                col.metric(t(label), value)
    with st.container(key="fs_map"):
        title, options = st.columns([3, 1])
        title.subheader(t("Industry → Company → Articles" if perspective == "Company focus" else "Industry → Company → Source"))
        with options:
            with st.popover(t("Map options"), icon=":material/tune:"):
                include_sources = st.checkbox(t("Show fictional sources"), value=False,
                    key="graph_company_sources" if perspective == "Company focus" else "graph_network_sources")
                zoom = st.slider(t("Mobile map zoom"), min_value=1.0, max_value=1.5, value=1.0, step=.25, key="graph_mobile_zoom")
                st.caption(t("Desktop fits the panel. On small screens, pan the map or enlarge its text."))
        data = graph(all_rows, company) if perspective == "Company focus" else graph_overview(all_rows)
        render_relationship_graph(data, include_sources=include_sources, mobile_zoom=zoom)
        st.caption(t("Industry nodes show company metadata; article text topics are separate. Dashed links are unverified topic candidates, not confirmed shared events. On mobile, pan left for company context or right for related coverage."))
    if perspective == "Company focus":
        with st.container(key="fs_graph_detail"):
            st.markdown(localize_html(eyebrow("ARTICLE INSPECTION")), unsafe_allow_html=True)
            picker, detail = st.columns([1, 2])
            with picker:
                chosen = article_selector("Inspect an illustrative article", rows, "graph_article")
                st.caption(t('{v0} original fictional reports · {v1}', v0=len(rows), v1=company))
            with detail:
                story(chosen, details=True)
        with st.expander(t("Potentially related reports"), expanded=False):
            if groups:
                data_table([{"Topic": g["label"], "Reports": len(g["article_ids"]),
                               "Headlines": " / ".join(g["headlines"]), "Status": "Unverified candidate",
                               "Relationship basis": g["basis"]} for g in groups], hide_index=True, width="stretch")
            else:
                st.info(t("These fictional reports remain separate. No multi-report candidate topic is shown."))
    else:
        with st.expander(t("Industry coverage details"), expanded=False):
            data_table([{"Company": name, "Sector": next(r.sector for r in all_rows if r.company == name),
                           **{tone: sum(r.company == name and r.sentiment == tone for r in all_rows) for tone in SENTIMENTS}}
                          for name in sorted({r.company for r in all_rows})], hide_index=True, width="stretch")
    with st.container(key="fs_cloud"):
        st.subheader(t("Headline word cloud"))
        scope = st.radio(t("Text scope"), ("All fictional headlines", "Selected company"), horizontal=True, key="graph_cloud_scope", format_func=display_formatter())
        cloud_rows = all_rows if scope == "All fictional headlines" else rows
        st.caption(t('{v0} authored fictional headlines · Each word counts once per headline. Generic words and company names excluded.', v0=len(cloud_rows)))
        headline_cloud(cloud_rows)


def explorer():
    heading("Stay close to the original", "Browse the authored sample and inspect one report at a time.")
    a, b = st.columns([2, 1])
    with a:
        query = st.text_input(t("Search fictional examples"), placeholder=t("Industry, company or headline"), max_chars=120, key="explorer_search")
    with b:
        industry = choice(st.selectbox, t("Example industry"), ("All industries", *SECTORS), key="explorer_industry", format_func=display_formatter())
    rows = sorted(select(examples(), sectors=() if industry == "All industries" else (industry,), search=query),
                  key=lambda r: (r.day, r.article_id), reverse=True)
    st.caption(t('{v0} fictional originals · preset labels · no publisher content or URLs', v0=len(rows)))
    st.caption(t("Inspect source evidence and authored text-topic context below. The local product also retains model/input history; no inference or model history is produced here."))
    if not rows:
        st.info(t("No fictional examples match. Try a different search or industry."))
        return
    ids = tuple(r.article_id for r in rows)
    with st.container(key="fs_explorer_layout"):
        listing, detail = st.columns([1.4, 1], gap="large")
        with listing:
            st.subheader(t("Original reports"))
            st.caption(t("Select a row, or use the headline picker in the detail panel."))
            revision = st.session_state.get("explorer_table_revision", 0)
            listing_data = pd.DataFrame([{"Headline": article_label(r), "Sentiment": r.sentiment,
                                          "Published": r.day} for r in rows])
            event = data_table(listing_data,
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
                st.markdown(localize_html(eyebrow("ARTICLE INSPECTION")), unsafe_allow_html=True)
                chosen = article_selector("Inspect a headline", rows, "explorer_article")
                story(chosen, details=True)


def get_finscope():
    heading("Make FinScope your local workspace", "A personal research application on localhost. Your sources and saved results stay in your local workspace.")
    st.link_button(t("Get the local product on GitHub"), LOCAL_PRODUCT, icon=":material/open_in_new:", type="primary")
    st.caption(t("Download the functional application from the local branch. The separate main branch contains this public showcase."))
    with st.container(key="fs_launcher"):
        launcher, architecture = st.columns([1, 1.2], gap="large")
        with launcher:
            st.markdown(localize_html(eyebrow("WINDOWS · AFTER SETUP")), unsafe_allow_html=True)
            st.subheader(t("Start the complete local product"))
            st.code("./launch_local.ps1 -Port 8501", language="powershell", wrap_lines=True)
            st.caption(t("One launcher starts the UI and its worker. Direct Streamlit startup serves only the UI."))
        with architecture:
            st.markdown(localize_html(launcher_architecture()), unsafe_allow_html=True)
    st.subheader(t("Install and start"))
    st.caption(t("Python 3.11+ · Run these commands on your own computer · Explicit model preparation"))
    windows, unix = st.tabs(["Windows · PowerShell", "macOS / Linux"])
    for tab, python, executable in ((windows, "python", ".venv-ai/Scripts/python.exe"),
                                   (unix, "python3", ".venv-ai/bin/python")):
        with tab:
            st.markdown(localize_html(eyebrow("01 / GET THE LOCAL PRODUCT")), unsafe_allow_html=True)
            st.code("git clone --branch local --single-branch https://github.com/DVDWK812/Finscope.git\ncd Finscope", language="bash", wrap_lines=True)
            st.markdown(localize_html(eyebrow("02 / CREATE THE ENVIRONMENT")), unsafe_allow_html=True)
            st.code(f"{python} -m venv .venv-ai\n{executable} -m pip install -r requirements-local.txt", language="bash", wrap_lines=True)
            st.markdown(localize_html(eyebrow("03 / PREPARE MODELS AND START")), unsafe_allow_html=True)
            st.code(f"{executable} -m finscope.model_assets --prepare --acknowledge-model-licenses", language="bash", wrap_lines=True)
            if python == "python":
                st.caption(t("After setup, use the full Windows launcher shown above for daily work."))
            else:
                st.caption(t("Source-derived manual route; macOS/Linux runtime acceptance is pending. Run the worker and UI in two project-folder terminals. This is not the verified Windows launcher."))
                st.code(f"# Terminal 1: local worker\n{executable} -m finscope.local_worker", language="bash", wrap_lines=True)
                st.code(f"# Terminal 2: UI\n{executable} -m streamlit run streamlit_app.py --server.address localhost --server.port 8501", language="bash", wrap_lines=True)
    st.caption(t("Open http://localhost:8501 after launch. Model licences and publisher-content permissions are separate."))
    available, optional = st.columns(2)
    with available:
        st.markdown(localize_html('<section class="fs-capability">' + eyebrow("AVAILABLE IN THE LOCAL PRODUCT")
                    + '<h3>Your personal news workspace</h3><ul><li>Update &amp; Analyze with persistent worker tasks</li>'
                    '<li>Configured news APIs, reviewed fixed sources and approved imports</li>'
                    '<li>Pinned local FinBERT + MiniLM</li><li>Persistent SQLite and original links</li>'
                    '<li>Parent/child Industries, shared filters and model history</li>'
                    '<li>Dashboard, evidence graph and News Explorer</li></ul></section>'), unsafe_allow_html=True)
    with optional:
        st.markdown(localize_html('<section class="fs-capability">' + eyebrow("OPTIONAL LOCAL INTEGRATIONS")
                    + '<h3>Additional ways to connect</h3><ul><li>Local LM Studio</li><li>Local Ollama</li>'
                    '<li>External LLM API with explicit send consent</li></ul>'
                    '<p>Require configured services/accounts, permitted inputs and installed assets. DeepSeek is a separate authored-text interface test. None runs on this website.</p></section>'), unsafe_allow_html=True)
    with st.expander(t("Provider keys, quotas and permissions"), expanded=False):
        st.write(t("Configure provider keys only in the local Settings editor or ignored project .env. Confirm source scope, account allowance and current UTC-day application budget before fetching. Saving settings makes no request. NewsData's pause remains in force; external model calls require explicit transmission consent. Research confirmation is not publisher permission; finite retention does not grant redistribution rights."))
    with st.expander(t("Availability and remaining verification"), expanded=False):
        st.write(t("Local implementation is separate from what this website demonstrates. The Windows launcher and dated local workflows have acceptance evidence; other-platform startup, repeated-load stability and future larger batches are not established by this preview. Source reach, language, response fields, account plans and permissions limit coverage. See the local product documentation for current gates."))


def render():
    st.markdown(theme_css(), unsafe_allow_html=True)
    page = st.session_state.get("showcase_page", "Home")
    with st.sidebar:
        st.markdown(localize_html(eyebrow("PRODUCT TOUR")), unsafe_allow_html=True)
        with st.container(key="fs_nav"):
            for name, _, icon in NAV_ITEMS:
                st.button(t(name), key=NAV_KEYS[name], icon=":material/" + icon + ":", width="stretch",
                          type="primary" if page == name else "secondary", on_click=go, args=(name,))
        st.caption(t("Viewing: {page}", page=t(page)))
        st.divider()
        st.markdown(localize_html(badge("Fictional examples")), unsafe_allow_html=True)
        st.caption(t("The complete product runs locally."))
        st.link_button(t("Showcase source"), SHOWCASE_SOURCE, icon=":material/open_in_new:", width="stretch")
    {"Home": home, "User Guide": guide, "Dashboard Preview": dashboard,
     "Knowledge Graph": knowledge_graph, "News Explorer": explorer, "Get FinScope": get_finscope}[page]()
    st.markdown(localize_html('<div class="fs-footer"><span>FinScope · Financial news in context</span><span>Authored examples · Local-first product</span></div>'), unsafe_allow_html=True)
    with st.expander(t("About FinScope")):
        st.write(t("A noncommercial financial-text research product. This showcase uses authored fictional data and preset labels; it performs no news collection or AI inference. Local sentiment is text tone, not a price forecast. Similarity suggests candidates, not verified event deduplication or contradiction detection."))
        st.caption(t("Local model weights: ProsusAI FinBERT, CC BY-NC-SA 4.0; sentence-transformers MiniLM, Apache-2.0. Publisher-content permissions are separate. Software and detailed evidence are available in the repository."))
        st.caption(t('Local product information reviewed: {v0} / {v1}', v0=LOCAL_REVIEW_DATE, v1=LOCAL_REVIEW_SHA[:7]))


def main():
    st.set_page_config(page_title="FinScope | Product Showcase", page_icon="◈", layout="wide")
    with st.sidebar:
        brand_slot = st.empty()
        with st.container(key="fs_preferences"):
            language = st.selectbox("Language / 语言", ("en", "zh-CN"),
                                    format_func=lambda value: {"en": "English", "zh-CN": "简体中文"}[value],
                                    key="showcase_language")
            appearance = st.radio("Appearance / 外观", ("dark", "light"), horizontal=True,
                                  format_func=lambda value: {"dark": "Dark / 深色", "light": "Light / 浅色"}[value],
                                  key="showcase_appearance")
    with preferences(language, appearance):
        brand_slot.markdown(brand(), unsafe_allow_html=True)
        if LANGUAGE.get() == "zh-CN":
            st.caption(t("English fictional headlines and summaries are preserved. The word cloud counts the original English headlines."))
        render()


if __name__ == "__main__":
    main()
