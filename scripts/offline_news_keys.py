"""Isolated real-browser acceptance: no user data, real vault, worker or HTTP.

FINSCOPE_TESTING=1 FINSCOPE_TEST_UI_PORT=8512 python -m streamlit run
scripts/offline_news_keys.py --server.address 127.0.0.1 --server.port 8512
"""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from finscope import test_safety
from finscope.local_news import LocalNewsStore,LocalIngestionService,ContentRights,FetchBlocked
from finscope.api_sources import HTTPResponse
from finscope.local_worker import Worker
from finscope.task_queue import TaskQueue
from finscope.ui_preferences import save
from finscope.news_keys import NewsKeyRegistry

if not test_safety.active() or os.environ.get('FINSCOPE_TEST_UI_PORT') not in ('8512','8513','8514'):
    raise RuntimeError('This acceptance fixture requires inherited credential/data isolation')
store=LocalNewsStore(os.environ['FINSCOPE_LOCAL_DB']);queue=TaskQueue(store)
if not queue.config():
    day=datetime.now(timezone.utc).date().isoformat()
    queue.configure(dict(sources=['marketaux','finnhub','newsdata'],model='Local FinBERT',model_id='',taxonomy='US-BUSINESS-1',limit=3,
      source_permissions={p:dict(preview=True,retain=True,analyze=True,external=False,reference='Authored offline acceptance permission; no real news') for p in ('marketaux','finnhub','newsdata')},
      budgets={p:dict(utc_day=day,remaining=3,topic='technology',symbol='NVDA' if p=='finnhub' else '') for p in ('marketaux','finnhub','newsdata')}))
    store.set_setting('guide_completed',True);save(store,'ui_language','en')
st.set_page_config(page_title='FinScope — isolated offline key acceptance',layout='wide')
st.warning('OFFLINE ACCEPTANCE · temporary database + in-memory fake credentials · no user keys, model inference or real news requests')
st.session_state.setdefault('product_page','Settings')
from streamlit_app import main
with patch('streamlit.set_page_config'):main()

with st.expander('Offline worker credential-selection check',expanded=True):
    st.caption('Fixture-only controls. Each explicit check advances a synthetic clock by 61 seconds; production holds are never touched.')
    source=st.selectbox('Offline check source',['marketaux','finnhub','newsdata'],key='offline_check_source')
    if st.button('Run offline fetch check',key='offline_fetch'):
        selected=queue.config();identity,fresh=queue.submit();snapshot=queue.get(identity)['snapshot']
        clock=st.session_state.get('_fixture_clock',datetime.now(timezone.utc))+timedelta(seconds=61)
        st.session_state['_fixture_clock']=clock
        def transport(url,params,headers,timeout):
            st.session_state['_mock_dispatches']=st.session_state.get('_mock_dispatches',0)+1
            return HTTPResponse([] if source=='finnhub' else {'data':[]},200,{})
        service=LocalIngestionService(store,clock=lambda:clock,transport=transport,
            cooldown_path=store.path.parent/'offline_holds.json',study_path=store.path.parent/'offline_study.sqlite3')
        try:
            with patch('finscope.local_worker.LocalIngestionService',return_value=service):
                Worker(store).fetch(source,snapshot,lambda:None)
            queue.update(identity,status='completed',stage='offline fixture')
            with closing(store.connect()) as db:
                actual=db.execute('SELECT slot_id FROM news_request_keys WHERE provider=? ORDER BY rowid DESC LIMIT 1',(source,)).fetchone()[0]
            st.session_state['_offline_result']={'provider':source,'selected_slot':actual,
                'snapshot_matched':actual==snapshot['news_key_slots'][source]['slot_id'],'simulated_dispatches':st.session_state.get('_mock_dispatches',0)}
        except (FetchBlocked,ValueError) as error:
            queue.update(identity,status='blocked',stage='offline fixture',error=str(error))
            st.session_state['_offline_result']={'provider':source,'blocked':str(error),'simulated_dispatches':st.session_state.get('_mock_dispatches',0)}
    if st.session_state.get('_offline_result'):st.json(st.session_state['_offline_result'])
    with closing(store.connect()) as db:
        data={'database':str(store.path),'temporary':True,'fake_credentials':True,
          'slots':db.execute('SELECT provider,slot_id,name,enabled FROM news_key_slots WHERE deleted_at IS NULL').fetchall()
              if db.execute("SELECT 1 FROM sqlite_master WHERE name='news_key_slots'").fetchone() else [],
          'requests':db.execute('SELECT provider,status FROM local_requests').fetchall()}
    Path('.test-results/p15_sandbox_state.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
