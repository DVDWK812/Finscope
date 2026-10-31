"""Presentation adapted from read-only showcase_theme f2fade9; no demo data."""
from html import escape

# Canonical showcase palette, shared by local UI, plots and component arguments.
DARK={'background':'#0b1220','surface':'#111d2e','raised':'#17263a','border':'#2c3b50',
        'text':'#e7edf6','muted':'#adbbce','accent':'#70d6c0','accent_surface':'#183d3b','button':'#27685e',
        'positive':'#70d6b4','neutral':'#bcc9db','negative':'#f5a09a','industry':'#dfc38b',
        'candidate':'#c8b5ed','source':'#e6b0a9','radius':'14px','space':'16px',
        'font':'Inter, ui-sans-serif, system-ui, sans-serif'}
DARK.update(hover='#20354a',focus='#70d6c0',button_bg='#70d6c0',button_text='#0b1220',warning_bg='#514326',neutral_bg='#526079')
LIGHT={**DARK,'background':'#edf2ef','surface':'#f7faf7','raised':'#e1eae5','border':'#b9cbc2',
       'text':'#253a37','muted':'#536b65','accent':'#27685e','accent_surface':'#d6eae1',
       'positive':'#26745e','neutral':'#61718a','negative':'#a83f45','industry':'#85611d',
       'candidate':'#785598','source':'#97564f','hover':'#d3e2d9','focus':'#26745e',
       'button_bg':'#27685e','button_text':'#f7faf7','warning_bg':'#f3e7c9','neutral_bg':'#d1dbe4'}
TOKENS=DARK  # Compatibility default; renderers resolve palette() per session/run.


def palette():
    from .ui_preferences import theme
    return dict(LIGHT if theme()=='light' else DARK)


def colors():return [palette()[k] for k in ('positive','neutral','negative','industry')]


class _Colors:
    def __getitem__(self,key):return colors()[key]
    def __iter__(self):return iter(colors())
    def __len__(self):return 4
COLORS=_Colors()


def brand():
    from .i18n import t
    return ('<div class="fs-brand"><span aria-hidden="true">F</span><div><strong>FinScope</strong>'
            '<small>'+escape(t('LOCAL NEWS INTELLIGENCE'))+'</small></div></div>')


def plot(spec,**options):
    import streamlit as st
    from copy import deepcopy
    import json
    from .i18n import display,tr,industry_labels
    spec=deepcopy(spec)
    labels={v:str(display(v)) for v in [*industry_labels(),'Positive','Neutral','Negative','Not analyzed','Unclassified','Technology','Healthcare','Materials','Energy','Financials']}
    expression='('+json.dumps(labels,ensure_ascii=False)+')[datum.label] || datum.label'
    for channel,encoding in spec.get('encoding',{}).items():
        if not isinstance(encoding,dict):continue
        field=encoding.get('field')
        if encoding.get('title') is not None:encoding['title']=str(tr(encoding['title']))
        elif 'title' not in encoding and field and channel not in ('theta','theta2','color'):encoding['title']=str(tr(field))
        if field in ('Sector','Industry','Sentiment'):
            if channel in ('x','y'):encoding.setdefault('axis',{})['labelExpr']=expression
            if channel=='color':encoding.setdefault('legend',{}).update(labelExpr=expression,title=str(tr(field)))
        if channel=='tooltip' and isinstance(encoding,list):pass
    for item in spec.get('encoding',{}).get('tooltip',[]):
        if isinstance(item,dict):
            field=item.get('field','');item['title']=str(tr(item.get('title',field)))
            if field in ('Sector','Industry','Sentiment'):
                mapping=json.dumps(labels,ensure_ascii=False)
                target='__ui_'+field
                calculation=f'({mapping})[datum[{json.dumps(field)}]] || datum[{json.dumps(field)}]'
                spec.setdefault('transform',[]).append({'calculate':calculation,'as':target})
                item['field']=target
    tokens=palette()
    st.vega_lite_chart({**spec,'background':tokens['surface'],'config':{
        'font':'system-ui','view':{'stroke':None},
        'axis':{'labelColor':tokens['muted'],'titleColor':tokens['muted'],'labelFontSize':11,
                'gridColor':tokens['border'],'gridOpacity':.45,'domain':False,'ticks':False,'labelPadding':8},
        'legend':{'labelColor':tokens['muted'],'titleColor':tokens['muted'],'orient':'bottom',
                  'direction':'horizontal','labelFontSize':11,'symbolType':'circle'}}},theme=None,**options)


def status_markup(status,stage,counts):
    TOKENS=palette()
    from .i18n import t,tr
    labels={'queued':'Queued','running':'In progress','completed':'Completed','partial_failed':'Completed with issues',
            'blocked':'Action needed','cancelled':'Stopped','interrupted':'Interrupted'}
    stages={'finished':'Finished','preflight':'Checking configuration','cancelled':'Stopped'}
    stage=t('Fetching {source}',source=stage[7:]) if stage.startswith('fetch: ') else tr(stages.get(stage,stage.replace('_',' ').capitalize()))
    color=TOKENS['negative'] if status in {'blocked','interrupted'} else TOKENS['industry'] if status=='partial_failed' else TOKENS['accent']
    stats=''.join(f'<span><b>{int(counts.get(key,0))}</b> {t(label)}</span>' for key,label in
                  [('new','new'),('classified','classified'),('analyzed','analyzed'),('failed','failed'),('skipped','skipped')])
    return f'<div class="fs-task"><span style="color:{color}">{escape(tr(labels.get(status,status)))}</span><span>{escape(stage)}</span><div>{stats}</div></div>'


def css():
    from .ui_preferences import theme
    variables=';'.join('--fs-'+k.replace('_','-')+':'+v for k,v in palette().items())
    variables+=';color-scheme:'+theme()
    return '<style>:root{'+variables+'''}
    [data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:var(--fs-background);color:var(--fs-text)}
    [data-testid="stAppViewContainer"],[data-testid="stAppViewContainer"] p,button,input,label{font-family:var(--fs-font)!important}
    [data-testid="stMainBlockContainer"]{max-width:1380px;padding:2.4rem 2rem 3.5rem}
    [data-testid="stSidebar"]{background:var(--fs-surface);border-right:1px solid var(--fs-border);width:232px!important;min-width:232px!important;max-width:232px!important}
    [data-testid="stSidebar"][data-collapsed="true"],[data-testid="stSidebar"][aria-expanded="false"]{width:0!important;min-width:0!important;max-width:0!important;border:0}
    [data-testid="stAppDeployButton"]{display:none}
    h1,h2,h3{color:var(--fs-text)!important;letter-spacing:-.035em}h1{font-size:clamp(1.8rem,3vw,2.65rem)!important;line-height:1.15!important}h3{font-size:1.1rem!important}
    [data-testid="stMarkdownContainer"] p,[data-testid="stCaptionContainer"] p{color:var(--fs-muted)}
    [data-testid="stWidgetLabel"] p{color:var(--fs-text);font-size:.82rem}a{color:var(--fs-accent)}
    .fs-brand{display:flex;align-items:center;gap:11px;margin:.3rem 0 2rem}.fs-brand>span{display:grid;place-items:center;width:35px;height:38px;border-radius:9px;border:1px solid var(--fs-accent);background:var(--fs-accent-surface);color:var(--fs-accent);font-size:23px;font-weight:700}
    .fs-brand strong{display:block;font-size:1.2rem;letter-spacing:-.04em;color:var(--fs-text)}.fs-brand small{font-size:.52rem;letter-spacing:.13em;color:var(--fs-muted)}
    [class*="st-key-product_page"] [role="radiogroup"]{gap:5px;width:100%}[class*="st-key-product_page"] label{display:flex!important;flex-direction:row!important;align-items:center;padding:.65rem .7rem;border:1px solid transparent;border-radius:9px;min-height:44px;gap:.6rem!important;width:100%}
    [class*="st-key-product_page"] label:hover{background:var(--fs-raised)}[class*="st-key-product_page"] label:has(input:checked){background:var(--fs-accent-surface);border-color:var(--fs-button)}
    [class*="st-key-product_page"] label:has(input:checked) p{color:var(--fs-accent)!important;font-weight:600}
    [class*="st-key-product_page"] label>div:first-child:not(:has([data-testid="stMarkdownContainer"])),[class*="st-key-product_page"] label>div>div:not([data-testid="stMarkdownContainer"]){display:none}[class*="st-key-product_page"] label:before{display:block;min-width:20px;color:var(--fs-accent);font-size:20px;line-height:1}
    [class*="st-key-product_page"] label:has(input[value="0"]):before{content:'▦'}[class*="st-key-product_page"] label:has(input[value="1"]):before{content:'▥'}[class*="st-key-product_page"] label:has(input[value="2"]):before{content:'◎'}[class*="st-key-product_page"] label:has(input[value="3"]):before{content:'▤'}[class*="st-key-product_page"] label:has(input[value="4"]):before{content:'⚙'}
    .stButton button[kind="primary"]{background:var(--fs-button-bg)!important;border-color:var(--fs-button-bg)!important}.stButton button[kind="primary"] p{color:var(--fs-button-text)!important;font-weight:650}
    [data-testid="stMetric"]{border:1px solid var(--fs-border);border-radius:var(--fs-radius);padding:1rem 1.15rem;min-height:108px;background:var(--fs-surface)}
    [data-testid="stMetricLabel"] p{color:var(--fs-muted);font-size:.76rem}[data-testid="stMetricValue"]{color:var(--fs-text);font-size:1.8rem}
    .st-key-product_chart_sector,.st-key-product_chart_mix,.st-key-product_chart_time,.st-key-product_chart_heatmap,.st-key-product_map,.st-key-product_cloud,[class*="st-key-story_detail_"]{background:var(--fs-surface);border:1px solid var(--fs-border);border-radius:var(--fs-radius);padding:1.1rem}
    .st-key-product_cloud{border-top:2px solid var(--fs-button)}
    .fs-task{display:flex;align-items:center;flex-wrap:wrap;gap:.6rem 1rem;padding:.8rem 1rem;background:var(--fs-surface);border:1px solid var(--fs-border);border-radius:12px;font-size:.8rem;color:var(--fs-muted)}
    .fs-task>span:first-child{font-weight:650}.fs-task>div{display:flex;gap:1rem;flex-wrap:wrap;margin-left:auto}.fs-task b{color:var(--fs-text);font-size:.95rem}
    .fs-news-copy,.fs-match-excerpt{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.75;color:var(--fs-text);font-size:.93rem}
    .fs-match-excerpt{padding:.8rem;border-left:3px solid var(--fs-accent);background:var(--fs-raised);border-radius:6px}.fs-match-excerpt mark{background:var(--fs-accent-surface);color:var(--fs-accent);font-weight:650;padding:0 2px}
    .stButton button,.stLinkButton a{min-height:44px;border-radius:9px}
    button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--fs-accent)!important;outline-offset:3px}
    #vg-tooltip-element.vg-tooltip{background:var(--fs-raised);color:var(--fs-text);border:1px solid var(--fs-border)}
    @media(max-width:1050px){.st-key-product_dashboard_charts [data-testid="stHorizontalBlock"],[class*="st-key-story_layout_"] [data-testid="stHorizontalBlock"],.st-key-product_filters [data-testid="stHorizontalBlock"]{flex-direction:column}.st-key-product_dashboard_charts [data-testid="stColumn"],[class*="st-key-story_layout_"] [data-testid="stColumn"],.st-key-product_filters [data-testid="stColumn"]{width:100%;flex:1 1 100%}}
    @media(max-width:700px){[data-testid="stMainBlockContainer"]{padding:3.2rem .8rem 2rem}.st-key-product_kpis [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.6rem}.st-key-product_kpis [data-testid="stColumn"]{min-width:130px;flex:1 1 45%}[data-testid="stMetric"]{min-height:98px;padding:.8rem}.fs-task>div{margin-left:0}.st-key-product_map,.st-key-product_cloud{padding:.65rem}}
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
    .st-key-ui_topbar{position:sticky;top:3.2rem;align-self:flex-end;width:44px;z-index:50;margin-bottom:-2.8rem}.st-key-ui_topbar button{font-size:1.3rem;min-width:44px;min-height:44px}h1{padding-right:3.2rem!important}
    .stButton button,.stLinkButton a,[data-testid="stFormSubmitButton"] button{background:var(--fs-raised);color:var(--fs-text);border-color:var(--fs-border)}
    .stButton button:hover,.stLinkButton a:hover{background:var(--fs-hover);border-color:var(--fs-focus)}
    input,textarea,[contenteditable="true"],[role="combobox"]{color:var(--fs-text)!important;caret-color:var(--fs-focus)!important}
    [data-testid="stTextInput"]>div,[data-testid="stNumberInput"]>div,[data-testid="stTextArea"]>div,[data-testid="stSelectbox"]>div,[data-testid="stMultiSelect"]>div,[data-testid="stDateInput"]>div{background:var(--fs-raised)!important;color:var(--fs-text)!important;border-color:var(--fs-border)!important;border-radius:8px}
    [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,textarea,[role="combobox"]{background:var(--fs-raised)!important}
    [role="listbox"],[role="dialog"],[data-baseweb="popover"],[data-testid="stTooltipContent"]{background:var(--fs-surface)!important;color:var(--fs-text)!important;border-color:var(--fs-border)!important}
    [role="option"]{color:var(--fs-text)!important;background:var(--fs-surface)}[role="option"]:hover,[role="option"][aria-selected="true"]{background:var(--fs-accent-surface)!important}
    [data-testid="stExpander"]{background:var(--fs-surface);border-color:var(--fs-border)}[data-testid="stExpander"] summary{background:var(--fs-surface)!important;color:var(--fs-text)!important}
    [data-testid="stAlert"]{background:var(--fs-raised)!important;color:var(--fs-text)!important;border:1px solid var(--fs-border)}[data-testid="stAlert"] p{color:var(--fs-text)!important}
    [data-testid="stForm"],[data-testid="stJson"],[data-testid="stCode"]{background:var(--fs-surface);color:var(--fs-text);border-color:var(--fs-border)}
    [data-testid="stCheckbox"] label,[data-testid="stRadio"] label,[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label{color:var(--fs-text)!important}
    [data-testid="stSelectbox"] [role="group"],[data-testid="stMultiSelect"] [role="group"]{background:var(--fs-raised)!important;border-color:var(--fs-border)!important}
    [data-testid="stSelectbox"] button,[data-testid="stMultiSelect"] button,[data-testid="stNumberInput"] button{background:var(--fs-raised)!important;color:var(--fs-muted)!important;border-color:var(--fs-border)!important}
    [data-testid="stMultiSelect"] [data-tag]{background:var(--fs-accent-surface)!important;color:var(--fs-accent)!important}
    [data-testid="stMultiSelect"] [data-tag] button{background:transparent!important;color:var(--fs-accent)!important}
    [role="dialog"] button,[role="gridcell"],[role="columnheader"],[role="rowheader"],[data-rac][role="grid"]{color:var(--fs-text)!important;background:var(--fs-surface)!important}
    [role="gridcell"][aria-selected="true"],[role="gridcell"][data-selected]{background:var(--fs-accent-surface)!important;color:var(--fs-accent)!important}
    [data-testid="stCheckbox"] input{accent-color:var(--fs-accent)}
    input::placeholder,textarea::placeholder{color:var(--fs-muted)!important;opacity:.8}
    </style>'''
