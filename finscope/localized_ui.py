"""Explicit Streamlit presentation adapter; stable widget values stay internal."""
import functools
import hashlib
import inspect
from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar,copy_context
import streamlit as native
from .i18n import tr,display,Verbatim
from .ui_preferences import theme,language

INPUTS={'selectbox','multiselect','radio','checkbox','date_input','number_input','text_input','text_area','file_uploader'}
LABELS=INPUTS|{'button','form_submit_button','link_button','download_button','expander','title','header','subheader','caption','info','warning','error','success','spinner','metric'}
_key_counts=ContextVar('ui_key_counts',default=None)
_in_form=ContextVar('ui_in_form',default=False)


def reset_keys():_key_counts.set({})


def widget_key(method,label):
    frame=inspect.currentframe().f_back.f_back
    source=getattr(label,'source',str(label))
    identity=frame.f_code.co_filename+'|'+str(frame.f_lineno)+'|'+method+'|'+source
    counts=_key_counts.get()
    if counts is None:reset_keys();counts=_key_counts.get()
    index=counts.get(identity,0);counts[identity]=index+1
    return 'ui_'+hashlib.sha256((identity+'|'+str(index)).encode()).hexdigest()[:18]


class LocalizedUI:
    raw=native
    def __getattr__(self,name):
        attr=getattr(native,name)
        if name=='form':
            @contextmanager
            def form(*args,**kwargs):
                with attr(*args,**kwargs) as container:
                    token=_in_form.set(True)
                    try:yield container
                    finally:_in_form.reset(token)
            return form
        if name not in LABELS|{'write','text','markdown','tabs','dataframe','vega_lite_chart'}:return attr
        @functools.wraps(attr)
        def call(*args,**kwargs):
            args=list(args)
            if name in INPUTS|{'button','download_button'} and args and not kwargs.get('key'):
                kwargs['key']=widget_key(name,args[0])
            canonical=kwargs.get('key') if name in INPUTS-{'file_uploader'} else None
            if canonical:
                # React controls retain their previous formatted text with an
                # unchanged widget ID. Remount the translated presentation only;
                # routing, callbacks and persisted filter values use canonical IDs.
                mirrors=native.session_state.setdefault('_ui_mirrors',{})
                prior=mirrors.get(canonical)
                locale=language()
                presentation=canonical if locale=='en' else canonical+'__'+locale
                if prior and prior[0]!=locale:
                    # A returning frontend widget can revive its old value.
                    # The last active presentation (updated by callbacks) wins.
                    native.session_state[canonical]=deepcopy(prior[1])
                    if presentation!=canonical:native.session_state[presentation]=deepcopy(prior[1])
                elif canonical in native.session_state and presentation!=canonical:
                    current=native.session_state[canonical]
                    if presentation not in native.session_state or not prior or prior[1]!=current:
                        native.session_state[presentation]=deepcopy(current)
                kwargs['key']=presentation
                callback=kwargs.get('on_change');callback_args=kwargs.pop('args',());callback_kwargs=kwargs.pop('kwargs',{})
                def changed():
                    if presentation!=canonical:native.session_state[canonical]=native.session_state[presentation]
                    mirrors[canonical]=(locale,deepcopy(native.session_state[presentation]))
                    if callback:callback(*callback_args,**callback_kwargs)
                if callback or not _in_form.get():kwargs['on_change']=changed
            if name in INPUTS and kwargs.get('key') in native.session_state:
                # A restored keyed value is authoritative. Avoid simultaneously
                # specifying a second default (Streamlit emits a warning).
                for default in ('value','default','index'):kwargs.pop(default,None)
            if name in LABELS and args:args[0]=tr(args[0])
            if name in {'write','markdown'}:args=[tr(v) if isinstance(v,str) else v for v in args]
            # Original text, source/model payloads and quoted evidence are verbatim.
            if name=='text':args=[v if isinstance(v,Verbatim) else tr(v) for v in args]
            for key in ('help','placeholder'):
                if key in kwargs:kwargs[key]=tr(kwargs[key])
            if name in {'selectbox','multiselect','radio'}:
                formatter=kwargs.get('format_func',lambda v:v)
                # Capture this render's locale: testing and widget serialization
                # can call the formatter outside the script's context.
                context=copy_context()
                kwargs['format_func']=lambda value:context.run(lambda:display(formatter(value)))
                if name in {'selectbox','multiselect'} and 'placeholder' not in kwargs:
                    kwargs['placeholder']=tr('Choose an option' if name=='selectbox' else 'Choose options')
            if name=='tabs' and args:args[0]=[tr(v) for v in args[0]]
            if name=='metric' and 'help' in kwargs:kwargs['help']=tr(kwargs['help'])
            if name=='vega_lite_chart':
                from .product_theme import plot
                kwargs.pop('theme',None);return plot(*args,**kwargs)
            if name=='dataframe' and args:
                import pandas as pd
                import json
                frame=args[0].data if hasattr(args[0],'data') and hasattr(args[0],'set_properties') else args[0]
                if not isinstance(frame,pd.DataFrame):frame=pd.DataFrame(frame)
                if isinstance(frame,pd.DataFrame):
                    frame=frame.copy()
                    for column in frame.columns:
                        if column in {'Industry','Sector','Sentiment','Label','Tone'}:frame[column]=frame[column].map(display)
                    frame=frame.rename(columns=lambda c:display(c))
                    from .chart_interactions import interactive_chart
                    values=json.loads(frame.to_json(orient='split',date_format='iso'))
                    return interactive_chart('data_table',{'headers':list(frame.columns),'rows':values['data']},
                        key=kwargs.get('key') or widget_key(name,'data_table'))
            result=attr(*args,**kwargs)
            if canonical:
                if kwargs['key']!=canonical:native.session_state[canonical]=result
                native.session_state['_ui_mirrors'][canonical]=(language(),deepcopy(result))
            return result
        return call


st=LocalizedUI()
