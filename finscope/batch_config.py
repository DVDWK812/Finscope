"""Credential-free initial bounded scope, shared by the UI and CLI."""
from .sec_sources import DEFAULT_OPTIONS

DEFAULT=dict(sources=['sec_submissions','sec_press','nist_rss','abs_archive'],model='Local FinBERT',model_id='',
    taxonomy='US-BUSINESS-1',classifier_llm=False,limit=120,budgets={},source_permissions={},sec_options=DEFAULT_OPTIONS)


def finbert_cache_key():
    from .model_assets import manifest
    from .text_processing import VERSION
    m=manifest('finbert')
    return '|'.join(('Local FinBERT',m['model_id'],m['revision'],VERSION,'sentiment-v1'))
