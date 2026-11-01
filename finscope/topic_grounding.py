"""Conservative safeguards against company-only and valuation-only topic labels.

These reject known forms of unsupported reasoning, not semantic paraphrases.
MiniLM/LLM still propose and judge activities without a literal catalog match.
"""
import re
from .taxonomy import load_taxonomy

VERSION='company-and-financial-commentary-grounding-2'
GENERIC=set(('a an the and or of to in on for with by from as at it its this that these those what who how '
 'has have had is are was were be been being do does did done doing over under last next year years quarter quarterly '
 'week weeks month months day days all more less most than then now could would should might may will can '
 'stock stocks share shares price prices market markets value valuation valuations capitalisation capitalization '
 'earnings p e pe times trade trades trading buy buys buying sell sells cheap cheaper cheapest looks look '
 'investor investors investment investments investing return returns performance performed history record growth '
 'lost loss losses gains gain risen rose fell falling decline declining higher lower bottom top best worst '
 'billion million trillion percent percentage stat stats ignore hard worth huge great potential soon move '
 'company companies business businesses model models likely publicly public listed ipo '
 'deal deals contract contracts partnership partnerships agreement agreements signed signing').split())
FINANCIAL_ACTIVITIES=(r'brokerage|brokers?|underwriting|fund manag|asset manag|assets? under management|investment bank|'
 r'stock exchange|exchange operator|payment process|merchant payment|card network|lending|deposits?|'
 r'insurance (?:polic|premium|underwriting)|credit card issuer|bank loan|savings account|mortgage originat|'
 r'portfolio manag|securities underwrit|fund inflows|banking services|'
 r'(?:blockchain|digital|cross.border|merchant|consumer|everyday) payments')


def guard(labels,text):
    domain={'ai','tech','gpu','ev'}
    for node in load_taxonomy()['nodes']:
        for phrase in [node['name_en'],*node['includes'],*node['synonyms']]:
            domain.update(w.lower() for w in re.findall(r'[A-Za-z]+',phrase) if w.lower() not in GENERIC)
    accepted=[];rejected=[]
    for label in labels:
        quotes=[e.get('model_quote',e['quote']) for e in label['evidence']]
        quote=' '.join(quotes)
        proper={w.lower() for w in re.findall(r'\b[A-Z][A-Za-z0-9&.-]*\b',quote) if w.lower() not in domain}
        words={w.lower() for w in re.findall(r'[A-Za-z]+',quote)}
        residual=words-GENERIC-proper
        reason=''
        if not residual:reason='Quote contains only company/name or investment-performance language, not a business activity'
        elif label['id'].startswith('financials') and not re.search(FINANCIAL_ACTIVITIES,text,re.I):
            reason='Financial-market commentary or issuer financing is not evidence of a financial-services provider activity in this catalog'
        if reason:rejected.append(dict(id=label['id'],reason=reason,evidence=label['evidence']))
        else:accepted.append(label)
    return accepted,rejected
