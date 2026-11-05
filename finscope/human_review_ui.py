"""Folded local industry selection; never dispatches a model or task."""
from .human_review import HumanReviews
from .i18n import Verbatim, node_name, t, tr
from .localized_ui import st


UNCLASSIFIED = None  # Distinct from every taxonomy node ID.


def render(item, store, catalog, automated, context):
    reviews = HumanReviews(store)
    try:
        history = reviews.history(item, catalog['id'])
    except ValueError:
        with st.expander('Review Industry Classification', expanded=False):
            st.info('Review blocked: current text and classification-use permissions are required.')
        return
    active = reviews.active(item, catalog['id'])
    nodes = {n['id']: n for n in catalog['nodes']}
    with st.expander('Review Industry Classification', expanded=False):
        st.caption('Local user review / Manual selection. Automatic results stay unchanged.')
        st.write('Automated classification')
        st.write(Verbatim(' · '.join(node_name(nodes[l['id']]) for l in automated.get('labels', []) if l['id'] in nodes)) or tr('Unclassified'))
        if automated.get('status') == 'failed':
            st.warning('Classification failed before a valid result was saved.')
        with st.expander('Automatic classification and original evidence', expanded=False):
            st.json(automated)
        if active:
            st.caption(t('Reviewed by Local user review · {utc}', utc=active['created_utc']))
        # Scope drafts to this article, text, taxonomy and saved event.
        key = 'human_review_'+context+'_'+item.article_id+'_'+item.content_version+'_'+catalog['id']+'_'+(history[-1]['id'] if history else 'new')
        default = ([UNCLASSIFIED] if active['status']=='unclassified' else active['industry_ids']) if active else []
        ids = st.multiselect('Select industries', [*nodes, UNCLASSIFIED], default=default,
                            format_func=lambda k:tr('Unclassified') if k is UNCLASSIFIED else Verbatim(node_name(nodes[k])),
                            key=key+'_industries', help='Selecting a subindustry also includes its parent.')
        note = st.text_area('Note (optional)', value=active.get('note', '') if active else '',
                            key=key+'_note', max_chars=500)
        unknown = UNCLASSIFIED in ids
        conflict = unknown and len(ids) != 1
        if conflict:
            st.info('Choose industries or Unclassified.')
        if st.button('Save human review', key=key+'_save', disabled=not ids or conflict):
            try:
                reviews.save(item, catalog['id'], [] if unknown else ids, unclassified=unknown, note=note)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop('_library_snapshot', None)
                st.rerun()
        if active and st.button('Restore automated classification', key=key+'_revoke'):
            try:
                reviews.save(item, catalog['id'], [], revoke=True)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop('_library_snapshot', None)
                st.rerun()
        if history:
            with st.expander('Human review history', expanded=False):
                st.caption('Revoked and superseded reviews are historical only. Notes and evidence from older text versions are hidden.')
                st.json(history)
