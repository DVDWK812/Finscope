"""Compact nonsecret key evidence, with one selected-key action menu."""
from .localized_ui import st
from .i18n import t,tr,Verbatim
from .news_keys import NewsKeyRegistry,NewsKeyError,LEGACY
from .news_readiness import key_metadata,check_local,LOCAL,API,storage_label


def clear_input(key):
    for name in (key,key+'__en',key+'__zh-CN'):st.session_state.pop(name,None)
    st.session_state.get('_ui_mirrors',{}).pop(key,None)


def render(store,provider):
    registry=NewsKeyRegistry(store);prefix='news_keys_'+provider
    info=key_metadata(store,provider);rows=info['rows'];configured=bool(info['primary'])
    st.caption('Keys share the source/account budget and all provider holds. Backups are never tried automatically.')
    for row in rows:
        name=tr(row['name']) if row['slot_id']==LEGACY else row['name']
        st.write(Verbatim(str(name)))
        st.caption(t('Key evidence',local=tr(storage_label(row)),api=tr(API[row['api_state']]),role=tr(row['role'])))
        st.caption(t('Key last use',time=row['last_used_at'] or tr('Never used'),result=tr({'untested':'Not tested','ok':'Last request succeeded','failed':'Last request failed','invalid':'Authentication rejected','pending':'Request outcome pending'}.get(row['last_status'],'Not tested'))))
        if row['checked_at']:st.caption(t('Local evidence time',time=row['checked_at'],basis=tr('Verified during save' if row['check_basis']=='save_readback' else 'Explicit local check')))
        if row['deletion_pending']:st.error('News key deletion is pending; resolve it before editing')
    def open_editor(mode,slot=None):
        clear_input('settings_secret_'+provider)
        clear_input(prefix+'_new_name');clear_input(prefix+'_new_primary')
        st.session_state[prefix+'_new_primary']=not configured
        st.session_state['_news_key_editor']={'provider':provider,'mode':mode,'slot':slot}
    def perform(action,notice='News key configuration saved; no request was made.'):
        try:
            action();st.session_state[prefix+'_notice']=notice
            st.session_state.pop(prefix+'_error',None)
            clear_input('settings_secret_'+provider);clear_input(prefix+'_new_name');clear_input(prefix+'_new_primary')
            st.session_state.pop('_news_key_editor',None)
        except ValueError as error:
            st.session_state[prefix+'_error']=str(error) if isinstance(error,NewsKeyError) else 'News key save failed; previous keys are unchanged'
    if st.button('Add news key',key='settings_secret_'+provider+'_edit'):open_editor('add')
    if rows:
        ids=[r['slot_id'] for r in rows];selected_key=prefix+'_selected'
        if st.session_state.get(selected_key) not in ids:
            clear_input(selected_key);st.session_state[selected_key]=info['primary']['slot_id'] if info['primary'] else ids[0]
        selected=st.selectbox('Select key',ids,key=selected_key,format_func=lambda slot:tr(next(r['name'] for r in rows if r['slot_id']==slot)) if slot==LEGACY else next(r['name'] for r in rows if r['slot_id']==slot))
        row=next(r for r in rows if r['slot_id']==selected)
        if st.button('Check local key',key=prefix+'_check_local'):
            state=check_local(store,provider,selected)
            st.session_state[prefix+'_notice']=t('Local check result',state=tr(LOCAL[state]));st.rerun()
        actions=['Choose key action','Make primary','Enable key' if not row['enabled'] else 'Disable key']
        actions+=['Copy existing key'] if selected==LEGACY else ['Replace key','Delete key']
        action_key=prefix+'_action_'+selected
        if st.session_state.get(action_key) not in actions:clear_input(action_key)
        def action_changed():
            for key in ('news_key_delete_'+provider+'_'+selected,prefix+'_availability_confirm_'+selected,prefix+'_copy_confirm'):clear_input(key)
        action=st.selectbox('Key action',actions,key=action_key,on_change=action_changed)
        if action=='Make primary':
            if st.button('Make primary',key=prefix+'_primary_'+selected,disabled=not row['enabled'] or row['is_primary'] or row['last_status']=='invalid' or bool(row['deletion_pending'])):
                perform(lambda:registry.promote(provider,selected));st.rerun()
        elif action in ('Disable key','Enable key'):
            confirm=st.checkbox('Confirm key availability change',key=prefix+'_availability_confirm_'+selected)
            if st.button(action,key=prefix+'_enabled_'+selected,disabled=not confirm or bool(row['deletion_pending'])):
                perform(lambda:registry.enable(provider,selected,not bool(row['enabled'])));clear_input(prefix+'_availability_confirm_'+selected);st.rerun()
        elif action=='Replace key':
            if st.button('Replace key',key=prefix+'_replace_'+selected,disabled=bool(row['deletion_pending'])):open_editor('replace',selected)
        elif action=='Delete key':
            confirmation='news_key_delete_'+provider+'_'+selected
            confirm=st.checkbox('I confirm deletion of this managed key',key=confirmation)
            if st.button('Delete key',key=prefix+'_delete_'+selected,disabled=not confirm):
                perform(lambda:registry.delete(provider,selected,confirmed=True));clear_input(confirmation);st.rerun()
        elif action=='Copy existing key':
            st.caption('The existing credential and .env are preserved. Add a managed replacement or explicitly copy the existing key.')
            copy=st.checkbox('Keep the original and create a managed primary copy',key=prefix+'_copy_confirm')
            if st.button('Copy existing key',key=prefix+'_copy',disabled=not copy):
                perform(lambda:registry.add(provider,str(tr('Copied existing key')),registry.legacy_key(provider),primary=True),'Key saved safely; not yet verified with the provider.')
                clear_input(prefix+'_copy_confirm');st.rerun()
    if not any(r['slot_id']==LEGACY for r in rows):
        with st.expander('Existing single-key configuration',expanded=False):
            st.caption('Original credentials are preserved and have not been inspected.')
            if st.button('Check existing key locally',key=prefix+'_check_legacy'):
                check_local(store,provider,LEGACY);st.rerun()
    editor=st.session_state.get('_news_key_editor',{})
    if editor.get('provider')==provider:
        with st.container(border=True):
            adding=editor['mode']=='add'
            name=st.text_input('Key display name',key=prefix+'_new_name',max_chars=40) if adding else ''
            secret_key='settings_secret_'+provider
            st.text_input('API key',type='password',key=secret_key,max_chars=500)
            if adding:st.checkbox('Use as primary after saving',value=not configured,key=prefix+'_new_primary')
            def persist():
                secret=st.session_state.get(secret_key,'')
                perform(lambda:registry.add(provider,st.session_state.get(prefix+'_new_name',''),secret,primary=st.session_state.get(prefix+'_new_primary',False))
                        if adding else registry.replace(provider,editor['slot'],secret),'Key saved safely; not yet verified with the provider.')
            st.button('Save key securely',key=secret_key+'_save',on_click=persist,disabled=not st.session_state.get(secret_key) or adding and not name.strip())
            if st.button('Cancel key edit',key=prefix+'_cancel'):
                clear_input(secret_key);st.session_state.pop('_news_key_editor',None);st.rerun()
    if st.session_state.get(prefix+'_error'):st.error(st.session_state[prefix+'_error'])
    if st.session_state.get(prefix+'_notice'):st.success(st.session_state[prefix+'_notice'])
