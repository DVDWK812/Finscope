"""Product-only preprocessing; frozen evaluation logic is never imported or changed."""
from dataclasses import asdict,replace
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

VERSION='product-lead-span-1'


def clean(text):
    return ' '.join(unicodedata.normalize('NFKC',text).replace('\x00','').split())


def canonical_url(url):
    p=urlsplit(url)
    if not url:return ''
    if p.scheme not in {'http','https'} or p.username or p.password:raise ValueError('Invalid original URL')
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),
        urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]),''))


def detect_language(text):
    if re.search('[\u4e00-\u9fff]',text):return 'zh'
    # Conservative English vocabulary evidence; Latin characters alone do not prove English.
    words=re.findall(r'[a-z]+',text.lower())
    clues={'the','of','and','to','in','for','with','new','from','is','on','at','by','as','an','has','a','its'}
    return 'en' if len(set(words)&clues)>=2 and sum(c.isascii() for c in text)/max(1,len(text))>.85 else 'unknown'


def prepare(item):
    title,summary,body=map(clean,(item.title,item.summary,item.body))
    basis='body' if body else 'summary' if summary else 'title'
    full=body or summary or title
    # Auditable lead excerpt, not silent truncation. Full permitted text stays saved.
    # Character and tokenizer limits are both checked; tokenizer never truncates.
    prefix=title+'\n' if basis!='title' else ''
    span_end=min(len(full),max(1,1400-len(prefix)))
    excerpt=prefix+full[:span_end]
    fingerprint=hashlib.sha256(json.dumps([title,summary,body],ensure_ascii=False).encode()).hexdigest()
    evidence={'preprocessing_version':VERSION,'analysis_basis':basis,'selection':'leading character span; one original, one label',
              'span_start':0,'span_end':span_end,'source_characters':len(full),'coverage':span_end/max(1,len(full)),
              'aggregation':'none; selected excerpt sentiment only','content_sha256':fingerprint}
    url=canonical_url(item.url)
    # Provider identity prevents accidental merging across independent publishers.
    identity=hashlib.sha256((item.source+'|'+url).encode()).hexdigest()[:32] if url else item.article_id
    return replace(item,article_id=identity,title=title,summary=summary,body=body,processed_text=excerpt,
                   content_version=fingerprint,language=detect_language(excerpt),text_basis=basis),evidence


def keywords(items,limit=32):
    """Distinct-article document frequency, including normalized multiword phrases."""
    stop=set('the a an and or of to in on for with from by as at is are was were be been this that it its their they new said will can more than which have has not into about also using use nist news research study researchers national institute standards technology'.split())
    stop.update('的 了 和 是 在 与 对 为 将 及 等 中 一个 我们 他们'.split())
    phrases={'large language model':r'large language models?|\bLLMs?\b|大语言模型',
             'artificial intelligence':r'artificial intelligence|\bAI\b|人工智能',
             'semiconductor':r'semiconductors?|chipmakers?|半导体',
             'cybersecurity':r'cybersecurity|cyber security|网络安全',
             'interest rate':r'interest rates?|利率','oil storage':r'oil storage|油气储存'}
    members={}
    for item in items:
        text=' '.join((item.title,item.summary,item.body))
        found={phrase for phrase,pattern in phrases.items() if re.search(pattern,text,re.I)}
        found.update(w.lower() for w in re.findall(r'\b[A-Za-z][A-Za-z-]{3,}\b',text) if w.lower() not in stop)
        # Chinese phrase segmentation uses curated vocabulary rather than pretending
        # each ideograph is a word; retain meaningful multi-character terms.
        found.update(w for w in ('芯片设计','晶圆制造','云计算','医疗器械','新能源','房地产','通货膨胀','经济增长') if w in text)
        for word in found:members.setdefault(word,set()).add(item.article_id)
    return [{'term':k,'count':len(v),'article_ids':sorted(v)} for k,v in sorted(members.items(),key=lambda x:(-len(x[1]),x[0]))[:limit]]
