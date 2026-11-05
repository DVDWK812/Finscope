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


# Home/Guide authored copy reused read-only from main f23a2cc06aa3e14d139de25aefb6ac41c2fec817; no showcase data imports.
HOME_GUIDE_STEPS = (('sources', 'Settings', 'Choose sources, permissions, current budgets and analysis models.'), ('analyze', 'Update & Analyze', 'Submit one explicit local task from your saved configuration.'), ('model', 'Background Worker', 'Collect → classify → sentiment → save. Checkpoints retain progress.'), ('inspect', 'Dashboard', 'Inspect Industries, Graph and News Explorer with shared local filters.'))
HOME_CAPABILITIES = (('sources', 'News collection', 'Implemented', 'Broad financial news · Selected media · Company tracking', 'Configured sources, permitted fields and current budgets. NewsData remains paused.'), ('analyze', 'Background processing', 'Implemented', 'Persistent local tasks, separate from the UI', 'Saved stages, resource pauses and explicit continuation through the local worker.'), ('model', 'Model selection', 'Defaults + optional', 'FinBERT sentiment + MiniLM embeddings', 'LM Studio / Ollama: configured integrations. DeepSeek: limited authored-text interface test.'), ('inspect', 'Sector intelligence', 'Implemented', 'Parent / child topics and shared local filters', 'Originals, source evidence and model history. Company metadata stays separate from text topics.'))
HOME_SOURCE_CARDS = (('News APIs', 'Marketaux and Finnhub need configured accounts, source scope and a current budget. NewsData remains manually paused, including paid-content access.'), ('Official and regulatory sources', 'Reviewed ABS, NIST, RBA and SEC adapters have bounded routes and source-specific policies. SEC requires your actual contact identity. ACCC remains disabled.'), ('Local imports', 'Strict JSONL/CSV imports accept approved inputs with their provenance and rights. Finite private-research file imports remain restricted.'), ('Media-link discovery', 'Five fixed Bloomberg, CNBC, WSJ, FT and Yahoo feeds support separate link discovery. Opt-in monitoring needs a dated budget; link counts are not licensed-text or NLP counts.'))
HOME_MODEL_CARDS = (('Local defaults', 'Pinned FinBERT supplies sentiment; MiniLM supplies embeddings and topic-candidate recall. Sentiment is text tone, not a return forecast.'), ('Independent industry topics', 'The topic scheme and configured local classifier are separate from sentiment selection. Company metadata and collection cohorts do not establish a text topic; retrieval scores are not calibrated confidence.'), ('Configured alternatives', 'LM Studio and Ollama use installed local models and resource checks. Optional external API actions need permitted inputs and explicit send consent; their output provenance stays separate.'))
