"""Narrow an existing API preview before any durable write; never fetch news."""
from dataclasses import replace

from .local_news import ContentRights, NewsItem


def permitted_preview(item, rights, scope):
    if not isinstance(item, NewsItem) or item.provider not in {'marketaux', 'finnhub'}:
        raise ValueError('Select an existing Marketaux or Finnhub preview')
    item.rights.require('preview')
    if not isinstance(rights, ContentRights):
        raise ValueError('Supply article-specific storage and NLP permissions')
    for action in ('preview', 'retain', 'analyze'):
        rights.require(action)
    if scope not in {'title', 'title_summary'}:
        raise ValueError('Choose the permitted API text scope')
    if not item.title.strip():
        raise ValueError('The selected preview has no headline')
    # Never reuse body, preprocessing, sector labels or external consent from
    # the preview. Classification and preprocessing use only the selected fields.
    return replace(item, rights=replace(rights, external=False),
                   summary=item.summary if scope == 'title_summary' else '',
                   body='', processed_text='', content_version='', text_basis='',
                   sectors=(), language='unknown',
                   provenance='Retained API preview; permitted fields: ' + scope)
