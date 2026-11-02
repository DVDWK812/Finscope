"""Account evidence editor; reads SQLite metadata, never credential contents."""
from contextlib import closing
from datetime import datetime,timezone
import json
from .localized_ui import st
from .news_accounts import SHARED,view,attest,exists

def render(store,provider,slot):
    now=datetime.now(timezone.utc)
    with closing(store.connect()) as db:
        info=view(db,provider,slot,now)
        receipt=db.execute('SELECT observed_at,http_status,headers FROM news_usage_receipts WHERE provider=? ORDER BY observed_at DESC LIMIT 1',(provider,)).fetchone() if exists(db,'news_usage_receipts') else None
    st.caption('Provider: '+provider+' · Account: '+info['account_id']+' · Provider GETs today: '+str(info['provider_used']))
    data=info['attestation'];balance=info['remaining_after_local_requests']
    st.caption('Supplier live balance: Unknown (no probe). User-confirmed balance less subsequent local requests: '+('Unknown' if balance is None else str(balance)))
    if data:st.caption('Account application budget: '+str(data['day_budget'])+' · counted today: '+str(info['used'])+' · evidence UTC: '+data['observed_at'])
    if receipt:st.caption('Last provider usage receipt (not necessarily this account): '+receipt[0]+' · HTTP '+str(receipt[1])+' · '+json.dumps(json.loads(receipt[2])))
    if info['usage_limit_unresolved']:st.caption('HTTP 402 plan usage limit unresolved; another key does not provide extra allowance.')
    with st.expander('Subscription account and verified allowance',expanded=False):
        st.caption('Use the same alias for keys in the same subscription. Unassigned historical requests remain counted conservatively. Limits are not added per key. Increasing the application budget is allowed today after checking account allowance; it does not clear HTTP history or provider holds.')
        prefix='account_'+provider+'_'+slot
        with st.form(prefix):
            alias=st.text_input('Local account alias',value=info['account_id'],max_chars=23)
            independent=st.checkbox('I verified this named account has lawful independent allowance and its terms permit this use',value=False)
            known=st.checkbox('I checked the current remaining account requests',value=False)
            remaining=int(st.number_input('Current account requests remaining',0,10000000,0))
            budget=int(st.number_input('Account application total GET budget for today (UTC)',1,10000,data['day_budget'] if data else 1))
            reference=st.text_area('Nonsecret balance evidence and applicable account terms',max_chars=800)
            confirmed=st.checkbox('Confirm this account association and today’s allowance; not a provider permission grant',value=False)
            save=st.form_submit_button('Save account evidence without requesting news')
        if save:
            try:
                attest(store,provider,slot,alias,remaining=remaining if known else None,day_budget=budget,reference=reference,
                    independent_confirmed=independent,confirmed=confirmed)
                st.success('Account evidence saved; request history preserved. Confirm the batch application budget separately.');st.rerun()
            except ValueError as error:st.error(str(error))
