"""Streamlit runtime regressions using synthetic fixtures and blocked HTTP transport."""
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
ANCHOR = date(2026, 10, 24)


def render_view(page, event_view=True, filters=None):
    """Render the same page functions used by navigation, without private AppTest APIs."""
    from datetime import date
    from finscope.ui_data import SyntheticNewsRepository, filter_articles, unique_events
    from streamlit_app import overview, trends, explorer, status

    rows = filter_articles(SyntheticNewsRepository(date(2026, 10, 24)).list_articles(), **(filters or {}))
    shown = unique_events(rows) if event_view else rows
    if page == "overview":
        overview(rows, shown, event_view)
    elif page == "trends":
        trends(shown, event_view, date(2026, 10, 20), date(2026, 10, 24))
    elif page == "explorer":
        explorer(rows, shown)
    else:
        status()


class StreamlitRuntimeTests(unittest.TestCase):
    def setUp(self):
        transport = patch("requests.sessions.Session.request", side_effect=AssertionError("UI attempted HTTP"))
        self.http = transport.start()
        self.addCleanup(transport.stop)
        self.addCleanup(lambda: self.http.assert_not_called())

    def app(self):
        app = AppTest.from_file(str(APP), default_timeout=10)
        app.session_state["demo_anchor"] = ANCHOR
        app.run()
        self.assertFalse(app.exception)
        return app

    def view(self, page, event_view=True, filters=None):
        app = AppTest.from_function(render_view, args=(page, event_view, filters), default_timeout=10).run()
        self.assertFalse(app.exception)
        return app

    def test_main_starts_synthetic_with_expected_counts(self):
        app = self.app()
        self.assertIn("SYNTHETIC DEMO DATA", app.warning[0].value)
        self.assertEqual([m.value for m in app.metric], ["12", "10", "3", "40.0%"])

    def test_counting_toggle_changes_share_but_preserves_raw_and_unique_counts(self):
        app = self.app().toggle[0].set_value(False).run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["12", "10", "3", "50.0%"])
        self.assertEqual(int(app.dataframe[0].value.to_numpy().sum()), 14)

    def test_date_sector_source_and_sentiment_filters_intersect(self):
        app = self.app()
        app.date_input[0].set_value((date(2026, 10, 22), ANCHOR))
        app.multiselect(key="sector").set_value(["Healthcare", "Technology"])
        app.multiselect(key="source").set_value(["Demo Wire C"])
        app.multiselect(key="sentiment").set_value(["Positive"])
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["1", "1", "1", "100.0%"])

    def test_empty_result_and_reset(self):
        app = self.app()
        app.multiselect(key="sector").set_value(["Healthcare"])
        app.multiselect(key="sentiment").set_value(["Negative"])
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["0", "0", "0", "—"])
        self.assertIn("No records match", app.info[0].value)
        self.assertEqual(len(app.dataframe), 0)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["12", "10", "3", "40.0%"])
        self.assertEqual(app.multiselect(key="sentiment").value, [])
        app.toggle[0].set_value(False).run()
        self.assertEqual([m.value for m in app.metric], ["12", "10", "3", "50.0%"])

    def test_incomplete_date_range_has_guidance_and_no_results(self):
        app = self.app().date_input[0].set_value((ANCHOR,)).run()
        self.assertFalse(app.exception)
        self.assertIn("Select both", app.info[0].value)
        self.assertEqual(app.metric[0].value, "0")

    def test_all_pages_handle_empty_results(self):
        for page in ("overview", "trends", "explorer"):
            with self.subTest(page=page):
                app = self.view(page, filters={"sectors": ["Healthcare"], "sentiments": ["Negative"]})
                self.assertIn("No records match", app.info[0].value)

    def test_trends_totals_follow_counting_mode(self):
        for event_view, expected in ((True, 10), (False, 12)):
            with self.subTest(event_view=event_view):
                app = self.view("trends", event_view)
                self.assertEqual(int(app.dataframe[0].value.to_numpy().sum()), expected)
                self.assertEqual(len(app.dataframe[0].value), 5)

    def test_explorer_event_selection_exposes_multisector_source_reports(self):
        app = self.view("explorer")
        self.assertEqual(len(app.dataframe[0].value), 10)
        app.selectbox[0].set_value("a08").run()
        self.assertFalse(app.exception)
        linked = app.dataframe[1].value
        self.assertEqual(set(linked["Article ID"]), {"a08", "a09"})
        self.assertTrue(all("Healthcare" in tags and "Technology" in tags for tags in linked["Sector(s)"]))
        self.assertTrue(any("Source reports for this event in the current filter: 2" in m.value for m in app.markdown))

    def test_explorer_source_filter_uses_remaining_representative(self):
        app = self.view("explorer", filters={"sources": ["Demo Wire C"]})
        self.assertIn("a09", set(app.dataframe[0].value["Article ID"]))
        app.selectbox[0].set_value("a09").run()
        self.assertFalse(app.exception)
        self.assertEqual(list(app.dataframe[1].value["Article ID"]), ["a09"])

    def test_system_status_preserves_no_go(self):
        app = self.view("status")
        self.assertIn("Phase 2: NO-GO", app.info[0].value)
        states = app.dataframe[0].value.set_index("Component")["State"]
        self.assertEqual(states["News API"], "Not connected")
        self.assertEqual(states["FinBERT"], "Not connected")
        self.assertEqual(states["Embedding deduplication"], "Synthetic event IDs")

    def test_live_fixture_is_rejected_before_display(self):
        from dataclasses import replace
        from finscope.ui_data import SyntheticNewsRepository

        rows = SyntheticNewsRepository(ANCHOR).list_articles()
        rows[0] = replace(rows[0], synthetic=False)
        with patch("finscope.ui_data.SyntheticNewsRepository.list_articles", return_value=rows):
            app = self.app()
        self.assertIn("Live data is disabled", app.error[0].value)
        self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
