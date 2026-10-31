"""Read-only selection/evidence helpers; never fetches, classifies or infers."""
import re
from html import escape

# Same normalization patterns as the existing document-frequency extractor.
ALIASES={'large language model':r'large language models?|\bLLMs?\b|大语言模型',
         'artificial intelligence':r'artificial intelligence|\bAI\b|人工智能',
         'semiconductor':r'semiconductors?|chipmakers?|半导体',
         'cybersecurity':r'cybersecurity|cyber security|网络安全',
         'interest rate':r'interest rates?|利率','oil storage':r'oil storage|油气储存'}


def article_selection(ids,current,clicked=None):
    return clicked if clicked in ids else current if current in ids else next(iter(ids),None)


def keyword_snippets(item,term):
    if not item.rights.preview:return []
    pattern=ALIASES.get(term,re.escape(term) if re.search(r'[\u4e00-\u9fff]',term) else r'(?<![\w-])'+re.escape(term)+r'(?![\w-])')
    for field in ('body','summary','title'):
        text=getattr(item,field)
        matches=list(re.finditer(pattern,text,re.I))
        if not matches:continue
        result=[]
        for match in matches[:2]:
            start=max(0,match.start()-90);end=min(len(text),match.end()+130)
            html=escape(text[start:match.start()])+'<mark>'+escape(match.group())+'</mark>'+escape(text[match.end():end])
            result.append({'field':field,'start':match.start(),'end':match.end(),'match':match.group(),
                           'html':('…' if start else '')+html+('…' if end<len(text) else '')})
        return result
    return []


def article_rows(news,results):
    return [{'id':n.article_id,'title':n.title,'source':n.source,'published':n.published_day or 'Publication date unknown',
             'tone':results[n.article_id].label if n.article_id in results else 'Not analyzed'} for n in news]
