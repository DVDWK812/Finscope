"""Local, dependency-free chart component; selection is read-only server input."""
import hashlib
import json
from pathlib import Path

import streamlit.components.v1 as components
import streamlit as st

_chart = components.declare_component('finscope_evidence_chart', path=str(Path(__file__).with_name('chart_component')))


def chart_scope(kind, data):
    return hashlib.sha256(json.dumps([kind,data],sort_keys=True).encode()).hexdigest()[:20]


def selected_value(event, scope, valid_ids):
    # Ignore stale/forged events from a previous date/sector/model/render.
    if isinstance(event,dict) and event.get('scope')==scope and event.get('id') in valid_ids:
        return event['id']
    return None


def interactive_chart(kind, data, *, key, selected=None):
    from .product_theme import TOKENS
    scope=chart_scope(kind,data)
    event=_chart(kind=kind,data=data,scope=scope,selected=selected,palette=TOKENS,key=key,default=None)
    ids=({n['id'] for n in data['nodes']} if kind=='graph' else {c['id'] for c in data['rows']} if kind=='articles' else {c['term'] for c in data['terms']} if kind=='cloud' else {c['Date']+'|'+c['Sector'] for c in data['cells']})
    value=selected_value(event,scope,ids)
    marker=json.dumps(event,sort_keys=True)
    if value is not None and st.session_state.get(key+'_handled') != marker:
        st.session_state[key+'_handled']=marker
        return value
    return None
