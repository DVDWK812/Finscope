"""Mutually exclusive query scopes; publisher filters are not licence evidence."""
MEDIA_DOMAINS={'Reuters':'reuters.com','Bloomberg':'bloomberg.com','CNBC':'cnbc.com',
              'WSJ':'wsj.com','Financial Times':'ft.com','Yahoo Finance':'finance.yahoo.com'}
MODES=('全部财经新闻','指定媒体新闻','指定公司新闻')

def scope(mode,media=(),strategy='latest'):
    if mode not in ('all','media','company'):raise ValueError('Choose one news acquisition mode')
    if mode=='media':
        if not media or any(m not in MEDIA_DOMAINS for m in media):raise ValueError('Select at least one of the six supported media')
        if strategy!='latest':raise ValueError('Specified media currently supports Latest news only')
        return sorted({MEDIA_DOMAINS[m] for m in media})
    if media:raise ValueError('Media filters cannot be mixed with all-news or company mode')
    if mode=='company' and strategy!='latest':raise ValueError('Company tracking uses its existing query strategy')
    return []
