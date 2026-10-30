"""Shared public-showcase design tokens and escaped presentation primitives."""
from html import escape


TOKENS = {
    "background": "#0b1220", "surface": "#111d2e", "raised": "#17263a",
    "border": "#2c3b50", "text": "#e7edf6", "muted": "#adbbce",
    "accent": "#70d6c0", "accent_surface": "#183d3b", "button": "#27685e",
    "positive": "#70d6b4", "neutral": "#bcc9db", "negative": "#f5a09a",
    "industry": "#dfc38b", "candidate": "#c8b5ed", "source": "#e6b0a9",
    "radius": "14px", "space": "16px", "font": "Inter, ui-sans-serif, system-ui, sans-serif",
}
SENTIMENT_COLORS = {name: TOKENS[name.lower()] for name in ("Positive", "Neutral", "Negative")}
NAV_ITEMS = (
    ("Home", "home", "home"), ("User Guide", "guide", "menu_book"),
    ("Dashboard Preview", "dashboard", "dashboard"),
    ("Knowledge Graph", "graph", "hub"), ("News Explorer", "explorer", "article"),
    ("Get FinScope", "install", "download"),
)
NAV_KEYS = {page: "nav_" + key for page, key, _ in NAV_ITEMS}


def badge(text="Demo Data / Illustrative Preview"):
    return '<span class="fs-badge"><span aria-hidden="true">●</span> ' + escape(text) + '</span>'


def brand():
    return ('<div class="fs-brand"><span class="fs-brand-mark" aria-hidden="true">F</span>'
            '<div><strong>FinScope</strong><small>NEWS INTELLIGENCE</small></div></div>')


def eyebrow(text):
    return '<div class="fs-eyebrow">' + escape(text) + '</div>'


def line_icon(name):
    paths = {
        "sources": '<path d="M5 5h14v14H5zM8 9h8M8 12h8M8 15h5"/>',
        "model": '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
        "analyze": '<path d="M4 18V6m0 12h16M8 14l4-5 4 3 4-6"/>',
        "inspect": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 10h6M10 7v6"/>',
    }
    return ('<span class="fs-line-icon" aria-hidden="true"><svg viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
            'stroke-linejoin="round">' + paths[name] + '</svg></span>')


def dashboard_preview(records):
    """Landing illustration computed from the same authored sample as the demo."""
    records = list(records)
    total = len(records)
    industries = list(dict.fromkeys(r.sector for r in records))
    positive = sum(r.sentiment == "Positive" for r in records)
    metrics = (("Original reports", total), ("Industries", len(industries)),
               ("Positive labels", f"{positive / total:.0%}" if total else "—"))
    kpis = ''.join(f'<div><small>{escape(label)}</small><strong>{value}</strong></div>' for label, value in metrics)
    bars = []
    for sector in industries:
        sample = [r for r in records if r.sector == sector]
        counts = {tone: sum(r.sentiment == tone for r in sample) for tone in SENTIMENT_COLORS}
        accessible = escape(sector + ': ' + ', '.join(f'{n} {tone}' for tone, n in counts.items()), quote=True)
        segments = ''.join(f'<i style="width:{n / len(sample) * 100:.2f}%;background:{SENTIMENT_COLORS[tone]}"></i>'
                           for tone, n in counts.items() if n)
        bars.append(f'<div class="fs-mini-row"><span>{escape(sector)}</span><div class="fs-mini-bar" role="img" aria-label="{accessible}">{segments}</div><small>{len(sample)}</small></div>')
    legend = ''.join(f'<span><i style="background:{color}"></i>{tone}</span>' for tone, color in SENTIMENT_COLORS.items())
    return ('<section class="fs-demo-window" aria-label="Illustrative dashboard from authored sample">'
            '<div class="fs-demo-toolbar"><span>WORKSPACE OVERVIEW</span><span class="fs-demo-dot">ILLUSTRATIVE</span></div>'
            f'<div class="fs-mini-kpis" data-report-count="{total}" data-positive-count="{positive}">{kpis}</div>'
            '<h3>Sector sentiment</h3><p>Preset labels across the authored sample</p>'
            + ''.join(bars) + f'<div class="fs-mini-legend">{legend}</div>'
            '<div class="fs-demo-foot">Authored fictional records · Counts reflect originals</div></section>')


def theme_css():
    variables = ";".join(f"--fs-{name.replace('_', '-')}: {value}" for name, value in TOKENS.items())
    return '<style>:root{' + variables + r''' }
    [data-testid="stAppViewContainer"]{background:var(--fs-background);color:var(--fs-text);}
    [data-testid="stHeader"]{background:var(--fs-background);}
    [data-testid="stSidebar"]{background:var(--fs-surface);border-right:1px solid var(--fs-border);
      width:232px!important;min-width:232px!important;max-width:232px!important;}
    [data-testid="stMainBlockContainer"]{max-width:1280px;padding:2.5rem 2rem 3.5rem;}
    h1,h2,h3{color:var(--fs-text)!important;letter-spacing:-.035em;}
    h1{font-size:clamp(1.8rem,3vw,2.65rem)!important;line-height:1.15!important;font-weight:650!important;}
    h2{font-size:1.35rem!important;}h3{font-size:1.1rem!important;}
    p,li,label{line-height:1.55;}
    [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:var(--fs-muted);}
    [data-testid="stWidgetLabel"] p{color:var(--fs-text);font-size:.82rem;}
    [data-testid="stCaptionContainer"] p{color:var(--fs-muted)!important;font-size:.8rem;}
    a{color:var(--fs-accent);text-underline-offset:3px;}
    button,a,summary{transition:background-color .16s,border-color .16s,color .16s;}
    button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--fs-accent)!important;outline-offset:3px;}
    .stButton button,.stLinkButton a{min-height:44px;border-radius:9px;}
    .st-key-fs_nav{gap:.2rem!important;}
    .st-key-fs_nav button{justify-content:flex-start;border:1px solid transparent;background:transparent;
      color:var(--fs-muted);min-height:44px;padding:.65rem .75rem;}
    .st-key-fs_nav button p{font-size:.85rem;white-space:normal;}
    .st-key-fs_nav button > div{justify-content:flex-start;}
    .st-key-fs_nav button:hover{background:var(--fs-raised);border-color:var(--fs-border);color:var(--fs-text);}
    .st-key-fs_nav button[kind="primary"]{background:var(--fs-accent-surface);border-color:#37665f;color:var(--fs-accent);}
    .st-key-fs_nav button[kind="primary"] p{color:var(--fs-accent);font-weight:600;}
    .fs-brand{display:flex;gap:11px;align-items:center;margin:.25rem 0 2rem;}
    .fs-brand-mark{display:grid;place-items:center;width:35px;height:38px;border:1px solid #4c8c80;
      border-radius:9px;background:var(--fs-accent-surface);color:var(--fs-accent);font-size:23px;font-weight:700;}
    .fs-brand strong{display:block;color:var(--fs-text);font-size:1.2rem;letter-spacing:-.04em;}
    .fs-brand small{display:block;font-size:.54rem;letter-spacing:.16em;color:var(--fs-muted);margin-top:2px;}
    .fs-eyebrow{font-size:.66rem;font-weight:650;letter-spacing:.14em;color:var(--fs-muted);text-transform:uppercase;}
    .fs-badge{display:inline-flex;align-items:center;gap:6px;font-size:.68rem;line-height:1.4;
      border:1px solid #3d625c;border-radius:6px;padding:5px 8px;color:#b0e5d9;background:#132d2c;}
    .fs-badge span{font-size:7px;color:var(--fs-accent);}
    .fs-header-meta{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:.45rem;}
    .st-key-fs_page_header{padding-bottom:1rem;border-bottom:1px solid var(--fs-border);margin-bottom:1rem;}
    .st-key-fs_page_header h1{padding-top:.2rem;padding-bottom:.4rem;}
    .st-key-fs_page_header p{max-width:760px;font-size:.94rem;}
    [data-testid="stMetric"]{background:var(--fs-surface);border:1px solid var(--fs-border);
      padding:1.05rem 1.2rem;border-radius:var(--fs-radius);min-height:112px;}
    [data-testid="stMetricLabel"] p{color:var(--fs-muted);font-size:.76rem;}
    [data-testid="stMetricValue"]{color:var(--fs-text);font-size:1.8rem;font-weight:600;}
    .st-key-fs_map,.st-key-fs_graph_detail,.st-key-fs_cloud,.st-key-fs_explorer_detail{
      background:var(--fs-surface);border:1px solid var(--fs-border);border-radius:var(--fs-radius);padding:1.15rem;}
    .st-key-fs_cloud{border-top:2px solid #478d80;margin-top:1rem;}
    .st-key-fs_graph_detail .story{background:transparent;border:0;padding:0;}
    .story{padding:1.15rem;background:var(--fs-surface);border:1px solid var(--fs-border);border-radius:var(--fs-radius);}
    .story h3{line-height:1.35;margin:.5rem 0 .65rem;}
    .story-meta{font-size:.74rem;color:var(--fs-muted);}
    .tone{font-size:.72rem;font-weight:600;display:inline-flex;align-items:center;border:1px solid var(--fs-border);
      border-radius:5px;padding:3px 7px;}
    .positive{color:var(--fs-positive);}.neutral{color:var(--fs-neutral);}.negative{color:var(--fs-negative);}
    .fs-footer{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding:1rem 0;
      border-top:1px solid var(--fs-border);color:var(--fs-muted);font-size:.72rem;margin-top:2rem;}
    .st-key-fs_home_hero{padding:1.5rem 0 1rem;}
    .fs-hero h1{font-size:clamp(2.6rem,4.1vw,4rem)!important;line-height:1.06!important;letter-spacing:-.055em;margin:.65rem 0 1.3rem;}
    .fs-hero h1 .fs-hero-accent{color:var(--fs-accent);}
    .fs-hero p{font-size:1.05rem;line-height:1.65;max-width:440px;margin-bottom:1.2rem;}
    .fs-demo-window{border:1px solid #3b5066;border-radius:16px;background:var(--fs-surface);padding:1.25rem;}
    .fs-demo-toolbar{display:flex;justify-content:space-between;gap:10px;font-size:.58rem;letter-spacing:.12em;color:var(--fs-muted);padding-bottom:1.1rem;border-bottom:1px solid var(--fs-border);}
    .fs-demo-dot{color:var(--fs-accent);}
    .fs-mini-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:1rem 0;}
    .fs-mini-kpis small{display:block;color:var(--fs-muted);font-size:.65rem;}
    .fs-mini-kpis strong{display:block;color:var(--fs-text);font-size:1.7rem;font-weight:600;letter-spacing:-.03em;}
    .fs-demo-window h3{font-size:.9rem!important;margin:.5rem 0 .1rem;}
    .fs-demo-window p{font-size:.68rem!important;margin:0 0 1.1rem;}
    .fs-mini-row{display:grid;grid-template-columns:88px 1fr 16px;gap:10px;align-items:center;margin:13px 0;font-size:.7rem;color:var(--fs-muted);}
    .fs-mini-bar{display:flex;height:9px;gap:2px;overflow:hidden;border-radius:3px;}
    .fs-mini-bar i{display:block;height:9px;}
    .fs-mini-row small{text-align:right;}
    .fs-mini-legend{display:flex;flex-wrap:wrap;gap:12px;font-size:.62rem;color:var(--fs-muted);margin:1.2rem 0;}
    .fs-mini-legend span{display:inline-flex;align-items:center;gap:5px;}
    .fs-mini-legend i{display:inline-block;width:6px;height:6px;border-radius:50%;}
    .fs-demo-foot{padding-top:.9rem;border-top:1px solid var(--fs-border);font-size:.62rem;color:var(--fs-muted);}
    .fs-line-icon{display:inline-flex;width:34px;height:34px;align-items:center;justify-content:center;color:var(--fs-accent);border:1px solid #365950;border-radius:8px;background:#142d2d;}
    .fs-line-icon svg{width:21px;height:21px;}
    .fs-feature{border:1px solid var(--fs-border);border-radius:var(--fs-radius);background:var(--fs-surface);padding:1.3rem;min-height:185px;}
    .fs-feature h3{font-size:1rem!important;margin:.85rem 0 .5rem;}
    .fs-feature p{font-size:.84rem;line-height:1.6;margin:0;}
    .st-key-fs_step_1,.st-key-fs_step_2,.st-key-fs_step_3,.st-key-fs_step_4{
      border:1px solid var(--fs-border);border-radius:var(--fs-radius);background:var(--fs-surface);padding:1.3rem;min-height:240px;}
    .st-key-fs_chart_sector,.st-key-fs_chart_mix,.st-key-fs_chart_time,.st-key-fs_chart_heatmap{
      border:1px solid var(--fs-border);border-radius:var(--fs-radius);background:var(--fs-surface);padding:1.1rem;}
    .st-key-fs_explorer_detail .story{padding:0;border:0;background:transparent;}
    .fs-capability{padding:1.3rem;border:1px solid var(--fs-border);border-radius:var(--fs-radius);background:var(--fs-surface);}
    .fs-capability ul{padding-left:1.2rem;margin-bottom:0;}.fs-capability li{margin:.45rem 0;font-size:.87rem;}
    #vg-tooltip-element.vg-tooltip{background:var(--fs-raised);color:var(--fs-text);border:1px solid var(--fs-border);border-radius:8px;}
    @media(max-width:1050px){
      .st-key-fs_home_hero [data-testid="stHorizontalBlock"],.st-key-fs_explorer_layout [data-testid="stHorizontalBlock"],.st-key-fs_dashboard_charts [data-testid="stHorizontalBlock"]{flex-direction:column;}
      .st-key-fs_home_hero [data-testid="stColumn"],.st-key-fs_explorer_layout [data-testid="stColumn"],.st-key-fs_dashboard_charts [data-testid="stColumn"]{width:100%;flex:1 1 100%;}
      .st-key-fs_hero_ctas [data-testid="stHorizontalBlock"]{flex-direction:row;}
      .st-key-fs_hero_ctas [data-testid="stColumn"]{width:auto;flex:1 1 45%;}
    }
    @media(max-width:700px){
      [data-testid="stMainBlockContainer"]{padding:3.5rem 1rem 2rem;}
      .st-key-fs_map,.st-key-fs_graph_detail,.st-key-fs_cloud,.st-key-fs_explorer_detail{padding:.8rem;}
      .fs-header-meta{align-items:flex-start;}.fs-badge{font-size:.63rem;}
      .st-key-fs_kpis [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.65rem;}
      .st-key-fs_kpis [data-testid="stColumn"]{min-width:140px;flex:1 1 45%;}
      [data-testid="stMetric"]{min-height:100px;padding:.8rem;}
      .fs-hero h1{font-size:2.65rem!important;}.fs-feature{min-height:0;}
      .st-key-fs_step_1,.st-key-fs_step_2,.st-key-fs_step_3,.st-key-fs_step_4{min-height:0;}
      .fs-demo-window{padding:1rem;}.fs-mini-row{grid-template-columns:75px 1fr 14px;gap:8px;}
    }
    @media(prefers-reduced-motion:reduce){button,a,summary{transition:none;}}
    </style>'''
