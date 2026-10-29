"""Acceptance boundaries for a public preview without the local product runtime."""
import builtins
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from finscope.showcase_data import END, START, examples, graph, graph_overview, select, word_cloud_terms


ROOT = Path(__file__).resolve().parents[1]


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
        pages = list(app.radio(key="showcase_page").options)
        self.assertEqual(len(pages), 6)
        for page in pages:
            app.radio(key="showcase_page").set_value(page).run()
            self.assertFalse(app.exception, page)
            self.assertFalse(app.get("file_uploader"))
            self.assertFalse(any("API key" in item.label for item in app.text_input))
            self.assertFalse(any("Prepare" in item.label or "Fetch news" in item.label
                                 or "Run real AI" in item.label for item in app.button))

    def test_landing_calls_to_action_and_local_installation(self):
        app = self.app()
        next(b for b in app.button if b.label == "How it works").click().run()
        self.assertEqual(app.radio(key="showcase_page").value, "User Guide")
        self.assertEqual(len(app.subheader), 4)
        app.radio(key="showcase_page").set_value("Get FinScope").run()
        content = "\n".join(code.value for code in app.code)
        self.assertIn("requirements-local.txt", content)
        self.assertIn("streamlit run streamlit_app.py", content)
        self.assertIn("--server.address localhost --server.port 8501", content)
        self.assertNotIn("-r deploy/requirements.txt", content)

    def test_dashboard_filters_raw_counts_and_reset(self):
        app = self.app()
        app.radio(key="showcase_page").set_value("Dashboard Preview").run()
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
        app.radio(key="showcase_page").set_value("News Explorer").run()
        app.text_input[0].set_value("no such fictional company").run()
        self.assertTrue(any("No fictional examples" in info.value for info in app.info))
        app.radio(key="showcase_page").set_value("Knowledge Graph").run()
        for company in ("Aster Circuits", "Maple Commerce"):
            app.selectbox(key="graph_company").set_value(company).run()
            self.assertFalse(app.exception)
            chosen = app.selectbox(key="graph_article").value
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


class FictionalDataTests(unittest.TestCase):
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
        app.radio(key="showcase_page").set_value("Knowledge Graph").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Headline word cloud" in h.value for h in app.subheader))
        app.radio(key="graph_perspective").set_value("Industry network").run()
        self.assertFalse(app.exception)
        app.radio(key="graph_cloud_scope").set_value("Selected company").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("authored fictional headlines" in c.value for c in app.caption))
