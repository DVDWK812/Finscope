from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from finscope.demo_pipeline import DemoPipeline


def render_approved_status():
    import streamlit as st
    from streamlit_app import status
    st.session_state["data_mode"]="Approved-text AI demo"
    st.session_state["model_load_seconds"]=9.2  # Fixture for displaying measured runtime metadata.
    status()


class ApprovedAppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);(root/"model.safetensors").write_bytes(b"fixture, never loaded")
        class Encoder:
            revision="unit-vector-v1"
            def tokenize(self,texts):return {},[10]*len(texts)
            def encode(self,texts):return [[1.,0.] for _ in texts]
        class Sentiment:
            def predict(self,records):return [SimpleNamespace(label="positive",positive=.8,negative=.1,neutral=.1,revision="unit-finbert-v1")]
        engine=DemoPipeline(Sentiment(),Encoder())
        patches=[patch.dict("os.environ",{"FINSCOPE_DEMO_DB_PATH":str(root/"demo.sqlite3")}),
                 patch("finscope.model_assets.assets_present",return_value=True),
                 patch("finscope.demo_runtime.load_pipeline",return_value=engine),
                 patch("requests.sessions.Session.request",side_effect=AssertionError("No news/model HTTP in unit tests"))]
        for item in patches:item.start();self.addCleanup(item.stop)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=15).run()

    def test_approved_text_to_saved_result_and_overview_uses_the_pipeline(self):
        self.assertFalse(self.app.exception)
        self.app.checkbox[0].set_value(True)
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.metric[0].value,"1")
        self.assertEqual(self.app.metric[1].value,"1")
        self.assertTrue(any("Latest actual inference: Positive" in h.value for h in self.app.subheader))
        self.assertTrue(any("Technology" in caption.value for caption in self.app.caption))

    def test_unapproved_text_does_not_create_an_analysis_record(self):
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Confirm your right" in error.value for error in self.app.error))
        self.assertEqual(self.app.metric[0].value,"0")

    def test_raw_default_and_reset_survive_candidate_opt_in(self):
        self.assertFalse(self.app.toggle[0].value)
        self.app.toggle[0].set_value(True).run()
        self.assertTrue(self.app.toggle[0].value)
        reset=next(button for button in self.app.button if button.label=="Reset filters")
        reset.click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.toggle[0].value)

    def test_status_reports_load_and_group_limits_without_loading_a_model(self):
        with patch("finscope.demo_runtime.load_pipeline",side_effect=AssertionError("Status must not load models")):
            app=AppTest.from_function(render_approved_status).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("NO-GO" in info.value for info in app.info))
        self.assertTrue(any("0.60" in warning.value for warning in app.warning))
        self.assertEqual(app.metric[0].value,"9.2")


if __name__=="__main__":unittest.main()
