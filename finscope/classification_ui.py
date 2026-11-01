"""Independent topic controls in the existing advanced batch panel."""
from contextlib import closing
from collections import Counter
from .localized_ui import st
from .i18n import Verbatim


def controls(q,active):
    from .classification_scheme import selected,configure,cache_key
    from .model_providers import LMStudioProvider
    from .lmstudio_runtime import start_service,load_model,model_operation
    current=selected(q.store)
    with st.expander('Industry classification · US-BUSINESS-1',expanded=False):
        st.caption('Rules + independent MiniLM recall + local semantic activity decisions. FinBERT remains the sentiment model. Classification-only tasks never collect news or reanalyze sentiment.')
        if current:st.caption(Verbatim(current['version']+' · '+current['model_key']+' · '+cache_key(current)[-12:]))
        left,right=st.columns(2)
        with left:
            if st.button('Inspect local classifier models'):
                try:st.session_state['topic_model_inventory']=LMStudioProvider().inventory()
                except ValueError as e:st.info(str(e))
        with right:
            if st.button('Start local classifier service',disabled=active):
                try:st.session_state['topic_model_inventory']=start_service(q.store,explicit=True)['models']
                except ValueError as e:st.info(str(e))
        models=st.session_state.get('topic_model_inventory',{})
        if models:
            names=list(models)
            model=st.selectbox('Local industry classifier model',names,index=names.index(current['model_key']) if current and current['model_key'] in names else 0)
            a,b=st.columns(2)
            with a:
                if st.button('Load selected classifier locally',disabled=active):
                    try:
                        model_operation(q.store,lambda:load_model(LMStudioProvider().inventory()[model],explicit=True,context_length=4096,gpu_offload='1'))
                        st.session_state['topic_model_inventory']=LMStudioProvider().inventory();st.rerun()
                    except ValueError as e:st.info(str(e))
            with b:
                if st.button('Use this classification scheme',disabled=active):
                    try:configure(q.store,model);st.rerun()
                    except ValueError as e:st.info(str(e))
        if st.button('Reclassify retained media only',disabled=active or not current):
            try:q.submit_reclassify(confirmed=True);st.rerun()
            except ValueError as e:st.info(str(e))
        if current:
            from .product_storage import ProductStorage
            from .media_use import scope_of
            data=ProductStorage(q.store);items=[n for n in data.news() if scope_of(n)]
            classes=data.classifications('US-BUSINESS-1')
            reasons=Counter(classes.get(n.article_id,{}).get('unclassified_reason') or ('classified' if classes.get(n.article_id,{}).get('labels') else 'not_run') for n in items)
            st.write(dict(reasons))
            from .expiring_media import partition
            part=partition(q.store)
            if part:
                with closing(part.connect()) as db:
                    rows=db.execute('SELECT stage,status,count(*) FROM product_classifier_calls GROUP BY stage,status').fetchall()
                st.caption('Local model dispatches (separate from FinBERT): '+str(sum(n for _,_,n in rows)))
        st.caption('Model outputs, quotes and diagnosis reviews stay in the expiring text partition. Prior classifier versions remain until the original expiry. No accuracy claim without independent human reference labels.')
