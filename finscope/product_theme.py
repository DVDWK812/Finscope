"""Layout/tokens adapted read-only from showcase f7df641; no demo data import."""
TOKENS={'accent':'#70d6c0','industry':'#dfc38b','candidate':'#c8b5ed','radius':'14px','space':'16px'}


def css():
    return '''<style>
    [data-testid="stMainBlockContainer"]{max-width:1380px;padding:2rem 2rem 3rem}
    [data-testid="stSidebar"]{border-right:1px solid #dce6e2}
    [data-testid="stAppDeployButton"]{display:none}
    h1,h2,h3{letter-spacing:-.035em}h1{font-size:clamp(1.8rem,3vw,2.65rem)!important}
    [data-testid="stMetric"]{border:1px solid #dce6e2;border-radius:14px;padding:1rem;min-height:108px;background:#f3f8f6}
    .stButton button,.stLinkButton a{min-height:44px;border-radius:9px}
    button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid #27685e!important;outline-offset:3px}
    @media(max-width:640px){[data-testid="stMainBlockContainer"]{padding:1.2rem .8rem}}
    </style>'''
