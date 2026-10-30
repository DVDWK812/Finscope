"""Acceptance boundaries for a public preview without the local product runtime."""
import builtins
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from finscope.showcase_data import (END, START, article_label, candidate_groups,
                                   examples, graph, graph_overview, select, word_cloud_terms)


from finscope.showcase_theme import NAV_KEYS

ROOT = Path(__file__).resolve().parents[1]


def navigate(app, page):
    return app.button(key=NAV_KEYS[page]).click().run()


def article_widget(app, key):
    return next(widget for widget in app.selectbox if (widget.key or "").startswith(key + "__"))


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        original_import = builtins.__import__
        forbidden = ("torch", "transformers", "huggingface_hub", "finscope.api_sources",
                     "finscope.product_ui", "finscope.local_news", "finscope.model_assets",
                     "finscope.demo_runtime", "finscope.finbert_backend", "finscope.embedding_backend")

        def guarded_import(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
                raise AssertionError("Showcase attempted a local runtime import: " + name)
            return original_import(name, *args, **kwargs)

        for mocker in (
                patch("builtins.__import__", side_effect=guarded_import),
                patch("requests.sessions.Session.request", side_effect=AssertionError("Showcase attempted HTTP")),
                patch("urllib.request.urlopen", side_effect=AssertionError("Showcase attempted HTTP")),
                patch("sqlite3.connect", side_effect=AssertionError("Showcase attempted database access"))):
            mocker.start()
            self.addCleanup(mocker.stop)

    def app(self):
        app = AppTest.from_file(str(ROOT / "deploy/streamlit_app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def test_every_page_runs_without_providers_database_or_models(self):
        app = self.app()
        pages = list(NAV_KEYS)
        self.assertEqual({b.key for b in app.button if b.key in NAV_KEYS.values()}, set(NAV_KEYS.values()))
        self.assertFalse(any(r.key == "showcase_page" for r in app.radio))
        self.assertEqual(len(pages), 6)
        for page in pages:
            navigate(app, page)
            self.assertFalse(app.exception, page)
            self.assertFalse(app.get("file_uploader"))
            self.assertFalse(any("API key" in item.label for item in app.text_input))
            self.assertFalse(any("Prepare" in item.label or "Fetch news" in item.label
                                 or "Run real AI" in item.label for item in app.button))

    def test_landing_calls_to_action_and_local_installation(self):
        app = self.app()
        next(b for b in app.button if b.label == "How it works").click().run()
        self.assertEqual(app.session_state["showcase_page"], "User Guide")
        self.assertEqual(len(app.subheader), 4)
        navigate(app, "Get FinScope")
        content = "\n".join(code.value for code in app.code)
        self.assertIn("requirements-local.txt", content)
        self.assertIn("streamlit run streamlit_app.py", content)
        self.assertIn("--server.address localhost --server.port 8501", content)
        self.assertNotIn("-r deploy/requirements.txt", content)

    def test_dashboard_filters_raw_counts_and_reset(self):
        app = self.app()
        navigate(app, "Dashboard Preview")
        self.assertEqual(app.metric[0].value, "24")
        self.assertTrue(any("Demo Data / Illustrative Preview" in m.value for m in app.markdown))
        app.multiselect(key="preview_sectors").set_value(["Technology"]).run()
        self.assertEqual(app.metric[0].value, "4")
        app.multiselect(key="preview_sentiments").set_value(["Positive"]).run()
        self.assertEqual(app.metric[0].value, "2")
        next(b for b in app.button if b.label == "Reset preview").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "24")

    def test_explorer_and_graph_resolve_only_fictional_records(self):
        app = self.app()
        navigate(app, "News Explorer")
        app.text_input[0].set_value("no such fictional company").run()
        self.assertTrue(any("No fictional examples" in info.value for info in app.info))
        navigate(app, "Knowledge Graph")
        for company in ("Aster Circuits", "Maple Commerce"):
            app.selectbox(key="graph_company").set_value(company).run()
            self.assertFalse(app.exception)
            chosen = article_widget(app, "graph_article").value
            self.assertIn(chosen, {r.article_id for r in examples() if r.company == company})
            self.assertTrue(any("No publisher URL" in c.value for c in app.caption))

    def test_public_entrypoint_and_dependencies_stay_independent(self):
        entrypoint = (ROOT / "deploy/streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("from finscope.showcase import main", entrypoint)
        self.assertNotIn("from streamlit_app import", entrypoint)
        packages = [line.split(">=")[0] for line in (ROOT / "deploy/requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
        self.assertEqual(packages, ["streamlit", "pandas"])
        self.assertIn("requirements-finbert.txt", (ROOT / "requirements-local.txt").read_text())


    def test_cloud_drilldown_survives_scope_company_and_network_changes(self):
        app = self.app()
        navigate(app, "Knowledge Graph")
        app.selectbox(key="graph_cloud_word").set_value("research").run()
        self.assertFalse(app.exception)
        table = next(frame.value for frame in app.dataframe if "Article ID" in frame.value.columns)
        expected = next(t["article_ids"] for t in word_cloud_terms(examples()) if t["term"] == "research")
        self.assertEqual(set(table["Article ID"]), set(expected))
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        app.selectbox(key="graph_company").set_value("Maple Commerce").run()
        self.assertFalse(app.exception)
        valid = {r.article_id for r in examples() if r.company == "Maple Commerce"}
        self.assertIn(article_widget(app, "graph_cloud_article").value, valid)
        app.radio(key="graph_perspective").set_value("Industry network").run()
        app.checkbox(key="graph_network_sources").set_value(True).run()
        self.assertFalse(app.exception)
        app.radio(key="graph_perspective").set_value("Company focus").run()
        self.assertFalse(app.exception)

    def test_human_article_selection_resolves_stable_id_and_shared_display_label(self):
        rows = [r for r in examples() if r.company == "Cedar Therapeutics"]
        app = self.app()
        navigate(app, "Knowledge Graph")
        self.assertFalse(app.checkbox(key="graph_company_sources").value)
        app.selectbox(key="graph_company").set_value("Cedar Therapeutics").run()
        self.assertEqual(set(article_widget(app, "graph_article").options), {article_label(r) for r in rows})
        article_widget(app, "graph_article").set_value("SYN-007").run()
        chosen = next(r for r in rows if r.article_id == "SYN-007")
        content = "\n".join(m.value for m in app.markdown)
        self.assertIn(article_label(chosen), content)
        self.assertIn(chosen.title, content)
        self.assertIn(chosen.summary, content)
        self.assertTrue(app.expander)
        self.assertTrue(all(not e.proto.expanded for e in app.expander))
        app.selectbox(key="graph_cloud_word").set_value("research").run()
        self.assertNotIn("SYN-", " ".join(article_widget(app, "graph_cloud_article").options))
        article_widget(app, "graph_cloud_article").set_value("SYN-005").run()
        matches = next(d.value for d in app.dataframe if "Complete headline" in d.value.columns)
        self.assertEqual(set(matches["Headline"]), {article_label(r) for r in examples()
                                                  if r.article_id in ("SYN-002", "SYN-005", "SYN-006")})
        navigate(app, "News Explorer")
        app.text_input[0].set_value("Cedar Therapeutics").run()
        content = "\n".join(m.value for m in app.markdown)
        self.assertTrue(all(article_label(r) in content and r.title in content for r in rows))
        app.text_input[0].set_value(article_label(chosen)).run()
        self.assertTrue(any(chosen.summary in m.value for m in app.markdown))
        self.assertFalse(any(r.summary in m.value for r in rows if r != chosen for m in app.markdown))
        self.assertFalse(app.exception)

    def test_unrelated_company_reports_do_not_gain_candidate_clutter(self):
        app = self.app()
        navigate(app, "Knowledge Graph")
        for company in ("Harbor Ledger Bank", "Maple Commerce", "Copperleaf Minerals"):
            app.selectbox(key="graph_company").set_value(company).run()
            self.assertEqual(app.metric[1].value, "0")
            self.assertTrue(any("remain separate" in item.value for item in app.info))
            self.assertFalse(app.exception)


class FictionalDataTests(unittest.TestCase):
    def test_public_text_tokens_meet_normal_text_contrast(self):
        from finscope.showcase_theme import TOKENS

        def luminance(color):
            channels = [int(color[n:n+2], 16) / 255 for n in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))

        for foreground in ("text", "muted", "accent", "positive", "neutral", "negative"):
            for background in ("background", "surface", "raised"):
                a, b = sorted((luminance(TOKENS[foreground]), luminance(TOKENS[background])))
                self.assertGreaterEqual((b + .05) / (a + .05), 4.5, (foreground, background))
        a, b = sorted((luminance(TOKENS["text"]), luminance(TOKENS["button"])))
        self.assertGreaterEqual((b + .05) / (a + .05), 4.5)

    def test_responsive_graph_layout_retains_all_evidence_without_node_collisions(self):
        from finscope.showcase_visuals import graph_layout, visible_graph
        rows = examples()
        for company in {r.company for r in rows}:
            for sources in (True, False):
                data = visible_graph(graph(rows, company), sources)
                width, height, positions, sizes = graph_layout(data)
                self.assertEqual(set(positions), {n["id"] for n in data["nodes"]})
                boxes = []
                for ident, (x, y) in positions.items():
                    w, h = sizes[ident]
                    box = (x - w/2, y - h/2, x + w/2, y + h/2)
                    self.assertTrue(0 <= box[0] < box[2] <= width, ident)
                    self.assertTrue(0 <= box[1] < box[3] <= height, ident)
                    for other in boxes:
                        self.assertFalse(min(box[2], other[2]) > max(box[0], other[0])
                                         and min(box[3], other[3]) > max(box[1], other[1]))
                    boxes.append(box)

    def test_readable_labels_and_complete_tooltips_never_expose_technical_codes(self):
        from html.parser import HTMLParser
        from finscope.showcase_visuals import relationship_markup, visible_graph

        class SvgText(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tag = ""
                self.words = []

            def handle_starttag(self, tag, attrs):
                self.tag = tag

            def handle_data(self, data):
                if self.tag in ("text", "title"):
                    self.words.append(data)

            def handle_endtag(self, tag):
                self.tag = ""

        rows = examples()
        self.assertEqual([r.article_id for r in rows], [f"SYN-{n:03}" for n in range(1, 25)])
        self.assertEqual(len({article_label(r) for r in rows}), 24)
        self.assertTrue(all(8 < len(article_label(r)) <= 32 for r in rows))
        for company in {r.company for r in rows}:
            data = graph(rows, company)
            self.assertEqual(len({n["id"] for n in data["nodes"]}), len(data["nodes"]))
            parsed = SvgText()
            parsed.feed(relationship_markup(visible_graph(data, False)))
            self.assertNotRegex(" ".join(parsed.words), r"\b(?:SYN-\d+|C-\d+-\d+)\b")
            for row in (r for r in rows if r.company == company):
                node = next(n for n in data["nodes"] if n["id"] == row.article_id)
                self.assertEqual(node["label"], article_label(row))
                tooltip = next(w for w in parsed.words if row.title in w and row.summary in w)
                for field in (row.company, row.sector, row.sentiment, row.day.isoformat(), row.source):
                    self.assertIn(field, tooltip)
                self.assertIn(row.sentiment + " sentiment", parsed.words)

    def test_reviewed_candidate_topics_and_singleton_suppression(self):
        rows = examples()
        expected = {"C-1-0": {"SYN-001", "SYN-002"},
                    "C-2-0": {"SYN-005", "SYN-006"},
                    "C-4-0": {"SYN-013", "SYN-014"}}
        groups = candidate_groups(rows)
        self.assertEqual({g["id"]: set(g["article_ids"]) for g in groups}, expected)
        self.assertTrue(all(g["label"] and g["basis"] and len(g["article_ids"]) > 1 for g in groups))
        self.assertTrue(all(not r.candidate for r in rows if r.article_id in
                            ("SYN-009", "SYN-010", "SYN-021", "SYN-022")))
        for company in {r.company for r in rows}:
            data = graph(rows, company)
            for node in (n for n in data["nodes"] if n["kind"] == "Unverified candidate"):
                self.assertEqual(set(node["article_ids"]), expected[node["id"]])
                self.assertGreater(len([e for e in data["edges"] if e["to_id"] == node["id"]]), 1)
        self.assertFalse(candidate_groups([rows[0]]))
        self.assertFalse(any(n["kind"] == "Unverified candidate" for n in graph([rows[0]], rows[0].company)["nodes"]))
        research = next(t for t in word_cloud_terms(rows) if t["term"] == "research")
        self.assertEqual(research, {"term": "research", "count": 3,
                                    "article_ids": ("SYN-002", "SYN-005", "SYN-006")})

    def test_article_node_context_and_both_edge_schemas_are_preserved(self):
        records = examples()
        self.assertEqual(len({row.summary for row in records}), len(records))
        by_id = {row.article_id: row for row in records}
        for node in graph(records, "Aster Circuits")["nodes"]:
            if node["kind"] == "Article":
                row = by_id[node["article_id"]]
                self.assertEqual((node["title"], node["summary"], node["sentiment"], node["source"],
                                  node["company"], node["industry"], node["candidate"]),
                                 (row.title, row.summary, row.sentiment, row.source,
                                  row.company, row.sector, row.candidate))
        for data in (graph(records, "Aster Circuits"), graph_overview(records)):
            for edge in data["edges"]:
                self.assertEqual((edge["from"], edge["to"]), (edge["from_id"], edge["to_id"]))

    def test_source_visibility_keeps_article_and_candidate_relationships(self):
        from finscope.showcase_visuals import visible_graph
        original = graph(examples(), "Aster Circuits")
        reduced = visible_graph(original, False)
        self.assertFalse(any(n["kind"] == "Source" for n in reduced["nodes"]))
        self.assertEqual({n["id"] for n in reduced["nodes"] if n["kind"] == "Article"},
                         {n["id"] for n in original["nodes"] if n["kind"] == "Article"})
        ids = {n["id"] for n in reduced["nodes"]}
        self.assertTrue(all(e["from_id"] in ids and e["to_id"] in ids for e in reduced["edges"]))
        self.assertTrue(any("candidate" in e["relationship"].lower() for e in reduced["edges"]))
        self.assertEqual(visible_graph(original), original)

    def test_headline_frequency_is_document_frequency_with_exact_evidence(self):
        from dataclasses import replace
        rows = [replace(examples()[0], title="Research research: company news update"),
                replace(examples()[1], title="Research expands")]
        terms = {t["term"]: t for t in word_cloud_terms(rows)}
        self.assertEqual(terms["research"]["count"], 2)
        self.assertEqual(set(terms["research"]["article_ids"]), {r.article_id for r in rows})
        self.assertFalse({"company", "news", "update"} & set(terms))

    def test_fixture_identity_no_urls_and_filter_denominators(self):
        rows = examples()
        self.assertEqual(len({r.article_id for r in rows}), 24)
        self.assertTrue(all(r.synthetic and not hasattr(r, "url") for r in rows))
        selected = select(rows, START, END, ["Technology"], ["Positive"])
        self.assertEqual(len(selected), 2)
        self.assertEqual(select(rows, END, START), [])
        self.assertEqual(select(rows, START, END, search="nonexistent"), [])
        self.assertTrue(all(START <= r.day <= END for r in rows))

    def test_graph_edges_resolve_fictional_entities_and_keep_articles(self):
        rows = examples()
        data = graph(rows, "Aster Circuits")
        ids = {n["id"] for n in data["nodes"]}
        self.assertEqual({n["kind"] for n in data["nodes"]},
                         {"Company", "Industry", "Article", "Source", "Unverified candidate"})
        for edge in data["edges"]:
            self.assertIn(edge["from"], ids)
            self.assertIn(edge["to"], ids)
            self.assertIn(edge["article_id"], {r.article_id for r in rows})
        self.assertEqual(graph(rows, "Nonexistent"), {"nodes": [], "edges": []})


    def test_industry_network_aggregates_only_fixture_evidence(self):
        rows = examples()
        network = graph_overview(rows)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Company"]), 6)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Industry"]), 6)
        self.assertEqual(len([n for n in network["nodes"] if n["kind"] == "Source"]), 3)
        ids = {n["id"] for n in network["nodes"]}
        self.assertTrue(network["edges"])
        self.assertTrue(all(e["from_id"] in ids and e["to_id"] in ids
                            and e["count"] >= 1 for e in network["edges"]))
        source_edges = [e for e in network["edges"]
                        if e["relationship"] == "Fictional source reports on company"]
        self.assertEqual(sum(e["count"] for e in source_edges), 24)
        self.assertEqual(graph_overview([]), {"nodes": [], "edges": []})

    def test_word_cloud_counts_fixture_titles_not_filler_text(self):
        records = examples()
        terms = word_cloud_terms(records)
        self.assertTrue(terms)
        self.assertLessEqual(len(terms), 16)
        self.assertEqual(terms, word_cloud_terms(records))
        self.assertNotIn("fictional", {item["term"] for item in terms})
        self.assertNotIn("aster", {item["term"] for item in terms})
        self.assertTrue(all(item["count"] == len(item["article_ids"]) for item in terms))
        self.assertTrue(all(set(item["article_ids"]) <= {r.article_id for r in records}
                            for item in terms))
        self.assertEqual(word_cloud_terms(records, limit=0), [])
        company_rows = [r for r in records if r.company == "Aster Circuits"]
        small = word_cloud_terms(company_rows)
        self.assertTrue(small)
        self.assertTrue(all(item["count"] <= 4 for item in small))
        self.assertEqual(word_cloud_terms([], limit=16), [])

    def test_graph_word_cloud_and_perspective_controls_render(self):
        # This method runs as a data test but exercises the public AppTest entrypoint.
        app = AppTest.from_file(str(ROOT / "deploy/streamlit_app.py"), default_timeout=15).run()
        navigate(app, "Knowledge Graph")
        self.assertFalse(app.exception)
        self.assertTrue(any("Headline word cloud" in h.value for h in app.subheader))
        app.radio(key="graph_perspective").set_value("Industry network").run()
        self.assertFalse(app.exception)
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("authored fictional headlines" in c.value for c in app.caption))
