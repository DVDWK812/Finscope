"""Shared credential facade: per-user store first, literal project .env second."""
from pathlib import Path
from .credential_store import PROVIDERS, validate_provider
from . import test_safety

ENV_KEYS = dict(zip(PROVIDERS, ('MARKETAUX_API_KEY', 'NEWSDATA_API_KEY', 'FINNHUB_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY')))


def credential_store():
    fake = test_safety.fake_credentials()
    if fake is not None:
        return fake
    from .windows_credentials import WindowsCredentialStore
    return WindowsCredentialStore()


def project_env_path():
    return (test_safety.case_directory() or Path(__file__).resolve().parents[1]) / '.env'


def environment_credentials(path=None, *, reader=None):
    path = project_env_path() if path is None else Path(path)
    test_safety.require_test_path(path)
    if reader is None:
        from dotenv import dotenv_values
        reader = dotenv_values
    return reader(path, interpolate=False)


def vault_key(provider, value=None):
    """Compatibility facade; no native system APIs are called here."""
    validate_provider(provider)
    store = credential_store()
    if value is not None:
        store.write(provider, value)
        return ''
    return store.read(provider)


def save_credential(provider, value):
    vault_key(provider, value)


def credential(provider, *, store=None):
    from .api_sources import local_credentials
    validate_provider(provider)
    if store is not None and provider in ('marketaux','finnhub','newsdata'):
        from .news_keys import NewsKeyRegistry,NewsKeyError
        from contextlib import closing
        with closing(store.connect()) as db:managed=db.execute("SELECT 1 FROM sqlite_master WHERE name='news_key_slots'").fetchone()
        if managed:
            try:return NewsKeyRegistry(store).resolve(provider)
            except NewsKeyError:return ''
    return vault_key(provider) or local_credentials().get(ENV_KEYS[provider], '')


def credential_state(provider, *, ui_key_present=False, use_env=True, read_env=None, env_path=None,store=None):
    validate_provider(provider)
    if store is not None and provider in ('marketaux','finnhub','newsdata') and use_env and not ui_key_present:
        from contextlib import closing
        with closing(store.connect()) as db:managed=db.execute("SELECT 1 FROM sqlite_master WHERE name='news_key_slots'").fetchone()
        if managed:
            from .news_keys import NewsKeyRegistry,LEGACY
            registry=NewsKeyRegistry(store);selection=registry.selection(provider)
            if selection is None or selection['slot_id']!=LEGACY:
                present=registry.configured(provider) if selection else False
                return {'present':present,'variable':ENV_KEYS[provider],'source':'Managed primary news key' if present else 'No enabled primary news key'}
    vault = bool(use_env and vault_key(provider))
    present = ui_key_present or vault or bool(use_env and (read_env or environment_credentials)().get(ENV_KEYS[provider]))
    return {'present': bool(present), 'variable': ENV_KEYS[provider],
            'source': 'Masked UI field (session only)' if ui_key_present else
            'Windows Credential Manager' if vault else
            str(env_path or project_env_path()) if present else 'Not configured in selected credential sources'}
