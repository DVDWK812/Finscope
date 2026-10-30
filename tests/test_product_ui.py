from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from streamlit.proto.TextInput_pb2 import TextInput

from finscope.local_news import LocalNewsStore
from test_local_news import item, pipeline

APP = Path(__file__).resolve().parents[1]/"streamlit_app.py"


def render_import_outcome():
    import streamlit as st
    from finscope.product_ui import preview_news
    st.session_state["fetch_outcome"]={"provider":"Local RBA import","status":"ok","outcome":"records",
                                     "http_status":None,"records":1,"network_attempted":False}
    preview_news(None)


class ProductUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name)/"local.sqlite3"
        for mocker in [patch.dict("os.environ", {"FINSCOPE_LOCAL_DB": str(self.db)}),
                       patch("requests.sessions.Session.request", side_effect=AssertionError("UI must be offline")),
                       patch("finscope.model_assets.assets_present", return_value=True),
                       patch("streamlit_app.cached_pipeline", return_value=pipeline())]:
            mocker.start(); self.addCleanup(mocker.stop)

    def app(self, page=None):
        if page:
            LocalNewsStore(self.db).set_setting("guide_completed", True)
        app = AppTest.from_file(str(APP), default_timeout=15)
        # These retained assertions exercise the explicitly accessible advanced
        # manual workspace. The default worker UI has independent workflow tests.
        app.session_state['advanced_manual_ui']=True
        if page:
            app.session_state["workspace_page"] = page
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_first_visit_guide_and_persistent_returning_user(self):
        app = self.app()
        self.assertEqual(app.button[0].label, "Get Started")
        self.assertEqual(len(app.subheader), 4)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(LocalNewsStore(self.db).setting("guide_completed"))
        returning = self.app()
        self.assertEqual(returning.title[0].value, "News intelligence")
        self.assertFalse(any(b.label == "Get Started" for b in returning.button))

    def test_three_masked_provider_connectors_and_pause(self):
        app = self.app("Add news")
        for provider in ("Marketaux", "Finnhub", "NewsData.io"):
            app.selectbox(key="api_provider").set_value(provider).run()
            self.assertFalse(app.exception)
            key = {"Marketaux":"marketaux", "Finnhub":"finnhub", "NewsData.io":"newsdata"}[provider]
            self.assertEqual(app.text_input(key="key_"+key).proto.type, TextInput.PASSWORD)
            fetch = next(b for b in app.button if b.label == "Fetch news")
            self.assertEqual(fetch.disabled, provider == "NewsData.io")

    def test_default_finbert_pipeline_save_and_returning_library(self):
        store = LocalNewsStore(self.db)
        original = item(); store.save_news(original)
        app = self.app("Analyze")
        self.assertEqual(app.selectbox(key="analysis_model").value, "Local FinBERT")
        app.multiselect(key="analysis_articles").set_value([original.article_id]).run()
        next(b for b in app.button if b.label == "Run real AI analysis").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(store.latest_analyses()[original.article_id].label, "Positive")
        app.radio(key="workspace_page").set_value("Dashboard").run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric][:2], ["1", "1"])

    def test_no_credentials_in_local_export_and_separate_browser_widgets(self):
        first = self.app("Add news")
        first.text_input(key="key_marketaux").set_value("PRIVATE-UNIT-SECRET").run()
        second = self.app("Add news")
        self.assertEqual(second.text_input(key="key_marketaux").value, "")
        self.assertNotIn("PRIVATE-UNIT-SECRET", str(LocalNewsStore(self.db).export()))

    def test_shared_filters_heatmap_graph_and_drilldown_render_together(self):
        store = LocalNewsStore(self.db)
        first, second = item(), item(source="Second authored source")
        store.save_news(first); store.save_news(second)
        from finscope.local_news import analyze_finbert
        analyze_finbert(first,store,pipeline()); analyze_finbert(second,store,pipeline())
        app = self.app("Dashboard")
        self.assertEqual([t.label for t in app.tabs], ["Overview", "Sector sentiment", "Trends", "Heatmap", "Evidence graph", "News Explorer"])
        app.multiselect(key="local_sources").set_value([first.source]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value,"1")
        self.assertEqual(app.selectbox(key="local_inspected_article").value,first.article_id)
        self.assertTrue(any(first.title==h.value for h in app.subheader))
        app.selectbox(key="local_graph_article").set_value(first.article_id).run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(sum(first.title==h.value for h in app.subheader),2)

    def test_optional_model_modes_do_not_connect_on_page_load(self):
        store=LocalNewsStore(self.db);store.save_news(item())
        app=self.app("Analyze")
        app.selectbox(key="analysis_model").set_value("Local Ollama").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label=="List installed Ollama models" for b in app.button))
        self.assertTrue(next(b for b in app.button if b.label=="Run real AI analysis").disabled)
        app.selectbox(key="analysis_model").set_value("OpenAI API").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="analysis_openai_key").proto.type,TextInput.PASSWORD)
        self.assertFalse(app.checkbox(key="analysis_send_consent").value)
        self.assertTrue(next(b for b in app.button if b.label=="Run real AI analysis").disabled)

    def test_local_collector_selection_is_explicit_and_does_not_fetch(self):
        app=self.app("Add news")
        app.selectbox(key="api_provider").set_value("Local Collector").run()
        self.assertFalse(app.exception)
        self.assertTrue(next(b for b in app.button if b.label=="Collect RBA news").disabled)
        self.assertTrue(any("fixed" in c.value for c in app.caption))

    def test_local_import_does_not_imply_an_unobserved_http_attempt(self):
        app=AppTest.from_function(render_import_outcome).run()
        self.assertFalse(app.exception)
        self.assertIn("HTTP not requested",app.success[0].value)


if __name__ == "__main__": unittest.main()
