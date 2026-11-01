"""Advanced batch actions inside the existing product shell; no HTTP or model load."""
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict
import json
from .localized_ui import st
from .i18n import Verbatim
from .task_queue import ACTIVE,validate_config
from .sec_sources import DEFAULT_OPTIONS,WATCHLIST_LABELS,validate_options,validate_user_agent
from .batch_config import DEFAULT

SOURCE_LABELS={'sec_submissions':'SEC EDGAR company disclosures','sec_press':'SEC official press releases',
               'nist_rss':'NIST official news','abs_html':'ABS current official announcements',
               'abs_archive':'ABS bounded archive (at most three linked index pages; no bodies)'}


def saved_config(q):
    with closing(q.store.connect()) as db:
        row=db.execute("SELECT payload FROM product_settings WHERE name='batch_pipeline'").fetchone()
    return json.loads(row[0]) if row else None


def controls(q):
    task=q.get();active=bool(task and task['status'] in ACTIVE)
    with st.expander('Batch collection and offline analysis',expanded=False):
        st.caption('Collection and analysis are independent durable stages. Closing this tab does not stop the worker. No external LLM or API-key rotation.')
        from .media_batch_ui import controls as media_controls
        media_controls(q,active)
        from .classification_ui import controls as topic_controls
        topic_controls(q,active)
        st.divider()
        st.caption('Existing official-source batches and local imports')
        c=deepcopy(saved_config(q) or DEFAULT)
        c['sources']=st.multiselect('Reviewed batch sources',list(SOURCE_LABELS),default=c['sources'],format_func=lambda k:Verbatim(SOURCE_LABELS[k]),key='batch_sources')
        c['limit']=int(st.number_input('Maximum records per source',1,300,c['limit'],key='batch_limit'))
        c['taxonomy']=st.selectbox('Batch topic taxonomy',['US-BUSINESS-1','CSRC-JRT0020-2024'],index=['US-BUSINESS-1','CSRC-JRT0020-2024'].index(c['taxonomy']),key='batch_taxonomy')
        c['model']=st.selectbox('Batch local sentiment model',['Local FinBERT','Local LM Studio'],index=0 if c['model']=='Local FinBERT' else 1,key='batch_model')
        c['model_id']=st.text_input('Batch LM Studio model ID',value=c.get('model_id',''),disabled=c['model']=='Local FinBERT',key='batch_model_id') if c['model']=='Local LM Studio' else ''
        options=c.get('sec_options',DEFAULT_OPTIONS)
        st.caption('Initial watchlist: '+', '.join(WATCHLIST_LABELS.values())+'. Issuer SIC is stored separately from evidence-backed news topics.')
        cik_text=st.text_area('SEC watchlist CIKs (ten digits, comma separated)',value=','.join(options['ciks']),key='batch_ciks')
        options['ciks']=[v.strip() for v in cik_text.replace('\n',',').split(',') if v.strip()]
        options['forms']=st.multiselect('SEC filing forms',['8-K','8-K/A','6-K','6-K/A','10-K','10-Q'],default=options['forms'],key='batch_forms')
        left,right=st.columns(2)
        with left:
            options['per_company']=int(st.number_input('Filings per company',1,50,options['per_company'],key='batch_per_company'))
            options['document_limit']=int(st.number_input('Maximum current-report document requests',0,20,options['document_limit'],key='batch_documents'))
        with right:
            options['request_limit']=int(st.number_input('Total SEC HTTP request cap',1,40,options['request_limit'],key='batch_http_cap'))
            options['minimum_interval']=float(st.number_input('Minimum SEC request spacing (seconds)',1.,60.,float(options['minimum_interval']),step=.5,key='batch_interval'))
        c['sec_options']=options
        st.caption('10-K/10-Q are metadata only. Current-report sentiment uses an identified operating-event excerpt; missing narrative is not Neutral. No exhibits or external links are downloaded.')
        ua=st.text_input('SEC User-Agent with your actual contact email',type='password',key='batch_ua',max_chars=250)
        try:
            from .sec_sources import user_agent,access_problem
            user_agent(q.store);st.caption('SEC contact identity configured locally.')
            problem=access_problem(q.store)
            if problem:st.warning(problem)
        except ValueError:st.caption('SEC requests wait for a truthful contact identity. Other reviewed sources remain usable.')
        if st.button('Save batch settings',key='batch_save',disabled=active):
            try:
                validate_config({**c,'operation':'update'});validate_options(options)
                if ua:validate_user_agent(ua)
                with closing(q.store.connect()) as db:
                    db.execute("INSERT OR REPLACE INTO product_settings VALUES ('batch_pipeline',?)",(json.dumps(c),))
                    if ua:db.execute("INSERT OR REPLACE INTO product_settings VALUES ('sec_user_agent',?)",(json.dumps(ua),))
                    db.commit()
                st.success('Batch settings saved. Update & Analyze now chains collection and offline analysis for this scope.')
            except ValueError as error:st.error(str(error))
        ready=st.checkbox('I explicitly start this bounded batch using the reviewed source policies',key='batch_confirm')
        left,right=st.columns(2)
        with left:
            if st.button('Collect and save only',key='batch_collect',disabled=active or not ready):
                try:q.submit_batch('collect',c,confirmed=True);st.rerun()
                except ValueError as error:st.error(str(error))
        with right:
            if st.button('Analyze saved records offline',key='batch_analyze',disabled=active or not ready):
                try:q.submit_batch('analyze',c,confirmed=True);st.rerun()
                except ValueError as error:st.error(str(error))
        st.caption('Offline analysis reads at most 300 current originals, reuses text/model caches and never requests news. Store-only batches do not inspect or load models.')
        imports(q,active)


def imports(q,active):
    from .batch_records import read_import,TYPES
    from .source_policies import SourcePolicy,FIELDS,PURPOSES
    st.subheader('Import permitted local JSONL / CSV')
    st.caption('Required: title, source, url. Optional: id, summary, body, source_type, document_type, company, ticker, cik, publication_date, timestamp. Import makes no network request and is labelled as a local file, never an API response.')
    upload=st.file_uploader('Local news file',type=['jsonl','csv'],key='batch_import_file')
    basis=st.text_input('Actual import licence or legal basis',key='batch_import_basis')
    retention=st.text_input('Permitted local retention period',key='batch_import_retention')
    expiry=st.text_input('Permission expiry ISO timestamp (if applicable)',key='batch_import_expiry')
    attribution=st.text_input('Required source attribution',key='batch_import_attribution')
    text_fields=st.multiselect('Fields covered by this import permission',['title','summary','body'],default=['title'],key='batch_import_fields')
    nlp=st.checkbox('The import basis covers local classification and sentiment analysis',key='batch_import_nlp')
    confirm=st.checkbox('I confirm the file and its actual storage/use scope',key='batch_import_confirm')
    if st.button('Import and save locally',key='batch_import_submit',disabled=active or not upload or not confirm):
        try:
            policy=SourcePolicy('user-reviewed-local-import','1','local_import',basis,'','user confirmed at import',
                tuple([v for v in FIELDS if v not in {'title','summary','body'}]+text_fields),
                PURPOSES if nlp else ('preview','retain','local_display'),retention,attribution,
                'Independent FinScope analysis; original attribution retained','Only fields and uses covered by the supplied actual basis',expiry)
            items=read_import(upload.getvalue(),upload.name.rsplit('.',1)[-1].lower(),policy)
            q.submit_import(items,confirmed=True);st.rerun()
        except (ValueError,TypeError,KeyError):st.error('Import rejected: verify the schema and actual field/use/retention/attribution evidence.')
