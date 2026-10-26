from dataclasses import replace
from datetime import date
from types import SimpleNamespace
import unittest
from streamlit.testing.v1 import AppTest

from finscope.ui_data import SyntheticNewsRepository, candidate_tone_conflicts, unique_events


def render_originals(filtered=False):
    import streamlit as st
    from streamlit_app import explorer
    from finscope.ui_data import SyntheticNewsRepository, unique_events
    from dataclasses import replace
    from datetime import date
    from types import SimpleNamespace
    first=SyntheticNewsRepository(date(2026,10,27)).list_articles()[0]
    second=replace(first,article_id="contradictory",sentiment="Negative",title="Synthetic opposite outcome")
    rows=[first,second]
    st.session_state["data_mode"]="Approved-text AI demo"
    st.session_state["approved_metadata"]={row.article_id:SimpleNamespace(article=row,scores={},sector_evidence={},
        permission_reference="Authored fixture",sector_rule_version="test",similarity=.85,
        model_revision="fixture",embedding_revision="fixture") for row in rows}
    selected=rows[:1] if filtered else rows
    explorer(selected,unique_events(selected))


class GroupingSafetyTests(unittest.TestCase):
    def test_opposite_tone_flags_same_candidate_only_and_is_order_independent(self):
        first=SyntheticNewsRepository(date(2026,10,27)).list_articles()[0]
        opposite=replace(first,article_id="b",sentiment="Negative")
        self.assertEqual(set(candidate_tone_conflicts([first,opposite])),{first.event_id})
        self.assertEqual(set(candidate_tone_conflicts([opposite,first])),{first.event_id})
        self.assertFalse(candidate_tone_conflicts([first,replace(opposite,event_id="different-event")]))
        self.assertFalse(candidate_tone_conflicts([first,replace(opposite,sentiment="Neutral")]))

    def test_candidate_summary_does_not_remove_originals_from_explorer(self):
        app=AppTest.from_function(render_originals).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),2)
        self.assertEqual(len(app.dataframe[1].value),2)
        self.assertTrue(any("Potential contradictory financial outcomes" in x.value for x in app.warning))
        self.assertEqual(len(app.selectbox[0].options),2)

    def test_group_details_reveal_opposing_record_outside_current_filter(self):
        app=AppTest.from_function(render_originals,args=(True,)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),1)
        self.assertEqual(len(app.dataframe[1].value),2)
        self.assertTrue(any("positive AND negative" in x.value for x in app.warning))
