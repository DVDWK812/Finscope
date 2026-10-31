"""Two independent allowlisted UI preferences; no pipeline or credential state."""
from contextlib import closing
from contextvars import ContextVar
import json

ALLOWED={'ui_theme':('dark','light'),'ui_language':('en','zh-CN')}
_theme=ContextVar('finscope_ui_theme',default='dark')
_language=ContextVar('finscope_ui_language',default='en')


def theme():return _theme.get()
def language():return _language.get()


def activate(values):
    if any(values.get(k,opts[0]) not in opts for k,opts in ALLOWED.items()):raise ValueError('Invalid UI preference')
    _theme.set(values.get('ui_theme','dark'));_language.set(values.get('ui_language','en'))


def load(store):
    result={k:v[0] for k,v in ALLOWED.items()}
    with closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_settings'").fetchone():return result
        for name,payload in db.execute("SELECT name,payload FROM product_settings WHERE name IN ('ui_theme','ui_language')"):
            try:value=json.loads(payload)
            except (ValueError,TypeError):continue
            if value in ALLOWED[name]:result[name]=value
    return result


def save(store,name,value):
    if name not in ALLOWED or value not in ALLOWED[name]:raise ValueError('Invalid UI preference')
    from .task_queue import TaskQueue
    TaskQueue(store)  # Existing backed-up schema migration, only when required.
    with closing(store.connect()) as db:
        db.execute('INSERT OR REPLACE INTO product_settings VALUES (?,?)',(name,json.dumps(value)));db.commit()


def bootstrap(store):
    from .localized_ui import reset_keys
    reset_keys();values=load(store);activate(values);return values


def toggle(store):
    save(store,'ui_theme','light' if load(store)['ui_theme']=='dark' else 'dark')


def toolbar(store):
    import streamlit as st
    from .i18n import t
    with st.container(key='ui_topbar'):
        st.button('☀' if theme()=='dark' else '☾',key='ui_theme_toggle',
                  help=t('Switch to light theme' if theme()=='dark' else 'Switch to dark theme'),on_click=toggle,args=(store,))


def language_settings(store,prefix='ui'):
    import streamlit as st
    from .i18n import t
    st.subheader('Language / 语言')
    st.session_state.setdefault(prefix+'_language_choice',language())
    selected=st.selectbox(t('Language'),ALLOWED['ui_language'],key=prefix+'_language_choice',
                          format_func=lambda value:'English (en)' if value=='en' else '简体中文 (zh-CN)')
    if st.button(t('Save language'),key=prefix+'_language_save'):
        save(store,'ui_language',selected);st.rerun()
