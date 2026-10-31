"""Visible, isolated readiness acceptance. Never use real credentials or data."""
from contextlib import closing
from datetime import datetime,timezone
import json,os
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from finscope import test_safety
from finscope.local_news import LocalNewsStore,LocalIngestionService
from finscope.news_keys import NewsKeyRegistry
from finscope.task_queue import TaskQueue
from finscope.ui_preferences import save
from finscope.api_sources import HTTPResponse

if not test_safety.active() or os.environ.get('FINSCOPE_TEST_UI_PORT')!='8512':
    raise RuntimeError('This fixture requires inherited temporary-data and credential isolation')
store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);queue=TaskQueue(store);registry=NewsKeyRegistry(store)
if not queue.config():
    providers=['marketaux','newsdata','finnhub'];day=datetime.now(timezone.utc).date().isoformat()
    queue.configure(dict(sources=providers,model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',limit=3,
      source_permissions={p:dict(preview=True,retain=True,analyze=True,external=False,reference='Authored offline fixture permission') for p in providers},
      budgets={p:dict(utc_day=day,remaining=3,topic='technology',symbol='NVDA' if p=='finnhub' else '') for p in providers}))
    for provider in providers:
        for name in ('Primary','Backup A','Backup B'):
            registry.add(provider,name,'AUTHORED-FAKE-'+provider+'-'+name,primary=name=='Primary')
    store.set_setting('guide_completed',True);save(store,'ui_language','en')
st.set_page_config(page_title='FinScope — OFFLINE source readiness acceptance',layout='wide')
st.warning('OFFLINE ACCEPTANCE · temporary SQLite + in-memory FAKE keys · injected responses only · no real news/model requests')
st.session_state.setdefault('product_page','Settings')
def transport(url,*args):
    st.session_state['_injected_calls']=st.session_state.get('_injected_calls',0)+1
    return HTTPResponse([] if 'finnhub.io' in url else {'data':[]},200,{})
def service(*args,**kwargs):
    return LocalIngestionService(store,transport=transport,study_path=store.path.parent/'study.sqlite3',cooldown_path=store.path.parent/'holds.json')
import finscope.news_source_ui,finscope.news_readiness
from streamlit_app import main
with patch('streamlit.set_page_config'),patch('finscope.news_source_ui.LocalIngestionService',side_effect=service),patch('finscope.news_readiness.LocalIngestionService',side_effect=service):
    main()
with st.expander('Offline acceptance controls',expanded=True):
    with closing(store.connect()) as db:injected=db.execute('SELECT count(*) FROM news_request_keys').fetchone()[0]
    st.caption('Injected provider dispatches: '+str(injected)+' · real requests: 0')
    if st.button('Simulate rejected NewsData primary (fake metadata only)'):
        with closing(store.connect()) as db:
            db.execute("UPDATE news_key_slots SET last_status='invalid' WHERE provider='newsdata' AND slot_id=(SELECT primary_slot FROM news_key_policies WHERE provider='newsdata')");db.commit()
        st.rerun()
    with closing(store.connect()) as db:
        output={'temporary':True,'fake_credentials':True,'database':str(store.path),'injected_calls':injected,
          'slots':db.execute('SELECT provider,name,slot_id,last_status FROM news_key_slots WHERE deleted_at IS NULL').fetchall(),
          'requests':db.execute('SELECT provider,status FROM local_requests').fetchall(),
          'tasks':db.execute('SELECT count(*) FROM product_tasks').fetchone()[0]}
    Path('.test-results/p16_browser_state.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
