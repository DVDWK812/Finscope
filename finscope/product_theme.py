"""Presentation adapted from read-only showcase_theme f2fade9; no demo data."""
from html import escape

# Canonical showcase palette, shared by local UI, plots and component arguments.
TOKENS={'background':'#0b1220','surface':'#111d2e','raised':'#17263a','border':'#2c3b50',
        'text':'#e7edf6','muted':'#adbbce','accent':'#70d6c0','accent_surface':'#183d3b','button':'#27685e',
        'positive':'#70d6b4','neutral':'#bcc9db','negative':'#f5a09a','industry':'#dfc38b',
        'candidate':'#c8b5ed','source':'#e6b0a9','radius':'14px','space':'16px',
        'font':'Inter, ui-sans-serif, system-ui, sans-serif'}
COLORS=[TOKENS[k] for k in ('positive','neutral','negative','industry')]


def brand():
    return ('<div class="fs-brand"><span aria-hidden="true">F</span><div><strong>FinScope</strong>'
            '<small>LOCAL NEWS INTELLIGENCE</small></div></div>')


def plot(spec,**options):
    import streamlit as st
    st.vega_lite_chart({**spec,'background':TOKENS['surface'],'config':{
        'font':'system-ui','view':{'stroke':None},
        'axis':{'labelColor':TOKENS['muted'],'titleColor':TOKENS['muted'],'labelFontSize':11,
                'gridColor':TOKENS['border'],'gridOpacity':.45,'domain':False,'ticks':False,'labelPadding':8},
        'legend':{'labelColor':TOKENS['muted'],'titleColor':TOKENS['muted'],'orient':'bottom',
                  'direction':'horizontal','labelFontSize':11,'symbolType':'circle'}}},theme=None,**options)


def status_markup(status,stage,counts):
    labels={'queued':'Queued','running':'In progress','completed':'Completed','partial_failed':'Completed with issues',
            'blocked':'Action needed','cancelled':'Stopped','interrupted':'Interrupted'}
    stages={'finished':'Finished','preflight':'Checking configuration','cancelled':'Stopped'}
    stage='Fetching '+stage[7:] if stage.startswith('fetch: ') else stages.get(stage,stage.replace('_',' ').capitalize())
    color=TOKENS['negative'] if status in {'blocked','interrupted'} else TOKENS['industry'] if status=='partial_failed' else TOKENS['accent']
    stats=''.join(f'<span><b>{int(counts.get(key,0))}</b> {label}</span>' for key,label in
                  [('new','new'),('classified','classified'),('analyzed','analyzed'),('failed','failed'),('skipped','skipped')])
    return f'<div class="fs-task"><span style="color:{color}">{escape(labels.get(status,status))}</span><span>{escape(stage)}</span><div>{stats}</div></div>'


def css():
    variables=';'.join('--fs-'+k.replace('_','-')+':'+v for k,v in TOKENS.items())
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
    .st-key-product_page [role="radiogroup"]{gap:5px;width:100%}.st-key-product_page label{display:flex!important;flex-direction:row!important;align-items:center;padding:.65rem .7rem;border:1px solid transparent;border-radius:9px;min-height:44px;gap:.6rem!important;width:100%}
    .st-key-product_page label:hover{background:var(--fs-raised)}.st-key-product_page label:has(input:checked){background:var(--fs-accent-surface);border-color:var(--fs-button)}
    .st-key-product_page label:has(input:checked) p{color:var(--fs-accent)!important;font-weight:600}
    .st-key-product_page label>div:first-child:not(:has([data-testid="stMarkdownContainer"])),.st-key-product_page label>div>div:not([data-testid="stMarkdownContainer"]){display:none}.st-key-product_page label:before{display:block;min-width:20px;color:var(--fs-accent);font-size:20px;line-height:1}
    .st-key-product_page label:has(input[value="0"]):before{content:'▦'}.st-key-product_page label:has(input[value="1"]):before{content:'▥'}.st-key-product_page label:has(input[value="2"]):before{content:'◎'}.st-key-product_page label:has(input[value="3"]):before{content:'▤'}.st-key-product_page label:has(input[value="4"]):before{content:'⚙'}
    .stButton button[kind="primary"] p{color:var(--fs-background)!important;font-weight:650}
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
    </style>'''
