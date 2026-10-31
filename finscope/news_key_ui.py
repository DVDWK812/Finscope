"""One compact news-key editor within the existing source settings panel."""
from .localized_ui import st
from .i18n import t,tr,Verbatim
from .news_keys import NewsKeyRegistry,NewsKeyError,LEGACY
STATUS={'untested':'Untested','ok':'Last request succeeded','failed':'Last request failed','invalid':'Authentication rejected','pending':'Request outcome pending'}
ERRORS={'authentication':'Authentication failed (401); verify this key or choose a backup.',
        'permission_or_subscription':'Permission/subscription restriction (403); this does not establish an invalid key.',
        'rate_limit':'Source/account rate limit (429); changing keys does not bypass the hold.',
        'provider_error':'Provider failure; source-level holds remain active.',
        'transport_or_response_error':'Transport/response error; no automatic retry.'}


def clear_input(key):
    for name in (key,key+'__en',key+'__zh-CN'):st.session_state.pop(name,None)
    st.session_state.get('_ui_mirrors',{}).pop(key,None)


def render(store,provider):
    registry=NewsKeyRegistry(store);prefix='news_keys_'+provider
    try:rows=registry.rows(provider);configured=registry.configured(provider)
    except NewsKeyError as error:st.error(str(error));return
    st.caption('Key configured' if configured else 'No enabled primary key; this source is not configured.')
    st.caption('Keys share the source/account budget and all provider holds. Backups are never tried automatically.')
    for row in rows:
        left,right=st.columns([4,1])
        with left:
            role=tr('Primary key') if row['is_primary'] else tr('Backup key')
            state=tr('Disabled') if not row['enabled'] else tr(STATUS[row['last_status']])
            st.write(Verbatim(str(tr(row['name'])) if row['slot_id']==LEGACY else row['name']),Verbatim(' · '+str(role)+' · '+str(state)))
            st.caption(t('Last used: {time}',time=row['last_used_at'] or str(tr('Never used'))))
            if row['last_error']:st.warning(tr(ERRORS[row['last_error']]))
            if row['deletion_pending']:st.error('News key deletion is pending; resolve it before editing')
        with right:
            if st.button('Manage key',key=prefix+'_manage_'+row['slot_id']):
                st.session_state[prefix+'_selected']=row['slot_id']
                st.session_state.pop('_news_key_editor',None)
                clear_input('news_key_delete_'+provider+'_'+row['slot_id'])
    def open_editor(mode,slot=None):
        clear_input('settings_secret_'+provider)
        clear_input(prefix+'_new_name');clear_input(prefix+'_new_primary')
        st.session_state[prefix+'_new_primary']=not configured
        st.session_state['_news_key_editor']={'provider':provider,'mode':mode,'slot':slot}
    if st.button('Add news key',key='settings_secret_'+provider+'_edit'):
        open_editor('add')
    def perform(action):
        try:
            action();st.session_state[prefix+'_notice']='News key configuration saved; no request was made.'
            st.session_state.pop(prefix+'_error',None)
            clear_input('settings_secret_'+provider)
            clear_input(prefix+'_new_name');clear_input(prefix+'_new_primary')
            st.session_state.pop('_news_key_editor',None)
        except ValueError as error:
            st.session_state[prefix+'_error']=str(error) if isinstance(error,NewsKeyError) else 'News key save failed; previous keys are unchanged'
    selected=st.session_state.get(prefix+'_selected')
    row=next((r for r in rows if r['slot_id']==selected),None)
    if row:
        with st.container(border=True):
            st.write(Verbatim(str(tr(row['name'])) if selected==LEGACY else row['name']))
            if st.button('Make primary',key=prefix+'_primary_'+selected,disabled=not row['enabled'] or row['is_primary'] or row['last_status']=='invalid' or bool(row['deletion_pending'])):
                perform(lambda:registry.promote(provider,selected));st.rerun()
            if st.button('Disable key' if row['enabled'] else 'Enable key',key=prefix+'_enabled_'+selected,disabled=bool(row['deletion_pending'])):
                perform(lambda:registry.enable(provider,selected,not bool(row['enabled'])));st.rerun()
            if selected==LEGACY:
                st.caption('The existing credential and .env are preserved. Add a managed replacement or explicitly copy the existing key.')
                if st.button('Add managed replacement',key=prefix+'_replace_legacy'):open_editor('add')
                copy=st.checkbox('Keep the original and create a managed primary copy',key=prefix+'_copy_confirm')
                if st.button('Copy existing key',key=prefix+'_copy',disabled=not copy):
                    perform(lambda:registry.add(provider,str(tr('Copied existing key')),registry.legacy_key(provider),primary=True))
                    clear_input(prefix+'_copy_confirm');st.rerun()
            else:
                if st.button('Replace key',key=prefix+'_replace_'+selected,disabled=bool(row['deletion_pending'])):open_editor('replace',selected)
                confirmation='news_key_delete_'+provider+'_'+selected
                confirm=st.checkbox('I confirm deletion of this managed key',key=confirmation)
                if st.button('Delete key',key=prefix+'_delete_'+selected,disabled=not confirm):
                    perform(lambda:registry.delete(provider,selected,confirmed=True))
                    clear_input(confirmation);st.rerun()
    editor=st.session_state.get('_news_key_editor',{})
    if editor.get('provider')==provider:
        with st.container(border=True):
            adding=editor['mode']=='add'
            name=st.text_input('Key display name',key=prefix+'_new_name',max_chars=40) if adding else ''
            secret_key='settings_secret_'+provider
            st.text_input('API key',type='password',key=secret_key,max_chars=500)
            primary=st.checkbox('Use as primary after saving',value=not configured,key=prefix+'_new_primary') if adding else False
            def persist():
                secret=st.session_state.get(secret_key,'')
                perform(lambda:registry.add(provider,st.session_state.get(prefix+'_new_name',''),secret,primary=st.session_state.get(prefix+'_new_primary',False))
                        if adding else registry.replace(provider,editor['slot'],secret))
            st.button('Save key securely',key=secret_key+'_save',on_click=persist,disabled=not st.session_state.get(secret_key) or adding and not name.strip())
            if st.button('Cancel key edit',key=prefix+'_cancel'):
                clear_input(secret_key);st.session_state.pop('_news_key_editor',None);st.rerun()
    if st.session_state.get(prefix+'_error'):st.error(st.session_state[prefix+'_error'])
    if st.session_state.get(prefix+'_notice'):st.success(st.session_state[prefix+'_notice'])
