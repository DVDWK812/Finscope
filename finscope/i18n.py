"""Local UI translation only. Never rewrites news, model IDs or persisted values."""
from functools import lru_cache
from pathlib import Path
import json
import re
from string import Formatter
from .ui_preferences import language


class Verbatim(str):pass


class UIString(str):
    def __new__(cls,value,source):
        obj=super().__new__(cls,value);obj.source=source;return obj


@lru_cache(maxsize=2)
def resources(locale):
    if locale not in ('en','zh-CN'):raise ValueError('Unsupported UI language')
    return json.loads((Path(__file__).with_name('locales')/(locale+'.json')).read_text(encoding='utf-8'))


def t(key,**values):
    template=resources(language()).get(key,resources('en').get(key,key))
    return UIString(template.format(**values) if values else template,key)


@lru_cache(maxsize=1)
def templates():
    result=[]
    for key in resources('en'):
        parts=list(Formatter().parse(key))
        if not any(field is not None for _,field,_,_ in parts):continue
        if sum(len(literal) for literal,_,_,_ in parts)<8:continue
        pattern='';fields=[]
        for literal,field,spec,_ in parts:
            pattern+=re.escape(literal)
            if field is not None:pattern+='(.*?)';fields.append((field,spec))
        result.append((len(key),re.compile('^'+pattern+'$',re.S),key,fields))
    return sorted(result,reverse=True,key=lambda row:row[0])


def tr(text):
    if not isinstance(text,str) or isinstance(text,(Verbatim,UIString)):return text
    if text in resources('en'):return t(text)
    if language()=='en':return text
    for _,pattern,key,fields in templates():
        match=pattern.match(text)
        if match:
            values={}
            for (field,spec),value in zip(fields,match.groups()):
                if spec:
                    try:value=float(value.replace(',',''))
                    except ValueError:pass
                values[field]=value
            try:return t(key,**values)
            except (ValueError,TypeError):continue
    return text


@lru_cache(maxsize=1)
def industry_labels():
    from .taxonomy import load_taxonomy,CATALOGS,node_label
    return {node_label(n):n for mode in CATALOGS for n in load_taxonomy(mode)['nodes']}


def node_name(node):return node['name_zh'] if language()=='zh-CN' else node['name_en']


def display(value):
    if not isinstance(value,str) or isinstance(value,Verbatim):return value
    if value in industry_labels():return node_name(industry_labels()[value])
    # Model identities/revisions after the UI family prefix stay byte-for-byte.
    for family in ('Local LM Studio','Local Ollama','External LLM'):
        if value.startswith(family+' · '):return str(t(family))+value[len(family):]
    return tr(value)


def component_labels():
    result={k:str(t(k)) for k in resources('en') if '{' not in k}
    result.update({key:node_name(node) for key,node in industry_labels().items()})
    return result
