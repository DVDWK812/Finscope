"""Folded, explicitly confirmed local review; never dispatches a model or task."""
from html import escape
from .human_review import HumanReviews
from .i18n import Verbatim, node_name, t, tr
from .localized_ui import st


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
        st.caption('Local user review · not independent annotation or ground truth. Automatic model results remain unchanged.')
        st.write('Automated classification')
        st.write(Verbatim(' · '.join(node_name(nodes[l['id']]) for l in automated.get('labels', []) if l['id'] in nodes)) or tr('Unclassified'))
        if automated.get('status') == 'failed':
            st.warning('Classification failed before a valid result was saved.')
        with st.expander('Automatic classification and original evidence', expanded=False):
            st.json(automated)
        st.write('Human-reviewed classification')
        if active:
            st.caption(t('Reviewed by Local user review · {utc}', utc=active['created_utc']))
            st.write(Verbatim(' · '.join(node_name(nodes[l['id']]) for l in active['labels'])) or tr('Unclassified'))
            st.write(Verbatim(active['reason']))
            for label in active['labels']:
                if not label.get('derived_from'):
                    st.caption(Verbatim(node_name(nodes[label['id']])))
                    st.markdown('<div class="fs-news-copy">'+escape(label['evidence'][0]['quote'])+'</div>', unsafe_allow_html=True)
                    st.write(Verbatim(label['reason']))
        else:
            st.caption('No effective human review; using automated classification.')
        st.caption('Select business topics supported by the text, never by a company name or stock-price movement alone. Copy an exact excerpt for each label; parent industries are added automatically.')
        # Identity includes version, taxonomy and last event: confirmations never carry
        # across another article/version/scheme or survive a successful mutation.
        key = 'human_review_'+context+'_'+item.article_id+'_'+item.content_version+'_'+catalog['id']+'_'+(history[-1]['id'] if history else 'new')
        unknown = st.checkbox('Still Unclassified after review', key=key+'_unknown')
        ids = st.multiselect('Reviewed industries', list(nodes), format_func=lambda k:Verbatim(node_name(nodes[k])),
                            key=key+'_labels', disabled=unknown)
        entries = []
        if not unknown:
            for identity in ids:
                st.caption(Verbatim(node_name(nodes[identity])))
                quote = st.text_area('Exact original evidence', key=key+'_'+identity+'_quote', max_chars=2000)
                explanation = st.text_input('Why this evidence supports the industry', key=key+'_'+identity+'_why', max_chars=500)
                entries.append(dict(id=identity, quote=quote, reason=explanation))
        reason = st.text_area('Review reason', key=key+'_reason', max_chars=500)
        confirmed = st.checkbox('I confirm this review and that selected industries have business-topic evidence, not just company names or stock prices.', key=key+'_confirm')
        if st.button('Save human review', key=key+'_save', disabled=not confirmed):
            try:
                reviews.save(item, catalog['id'], entries, unclassified=unknown, reason=reason, confirmed=confirmed)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop('_library_snapshot', None)
                st.rerun()
        if active:
            revoke = st.checkbox('I confirm revoking this human review and restoring automated labels.', key=key+'_revoke_confirm')
            if st.button('Revoke human review', key=key+'_revoke', disabled=not revoke):
                try:
                    reviews.save(item, catalog['id'], [], confirmed=revoke, revoke=True)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop('_library_snapshot', None)
                    st.rerun()
        if history:
            with st.expander('Human review history', expanded=False):
                st.caption('Revoked and superseded reviews are historical only. Evidence from older text versions is hidden.')
                st.json(history)
