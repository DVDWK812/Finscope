"""Provider-scoped store contract and non-system test implementation."""
from threading import RLock

PROVIDERS = ('marketaux', 'newsdata', 'finnhub', 'openai', 'deepseek')
NEWS_PROVIDERS = ('marketaux', 'finnhub', 'newsdata')


def validate_slot(provider, slot_id):
    from uuid import UUID
    if provider not in NEWS_PROVIDERS or not isinstance(slot_id,str):
        raise ValueError('Invalid news credential slot')
    try:
        if UUID(slot_id).hex != slot_id: raise ValueError
    except (ValueError,AttributeError):
        raise ValueError('Invalid news credential slot') from None


def validate_provider(provider):
    if provider not in PROVIDERS:
        raise ValueError('Unsupported credential provider')


def validate_secret(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError('Invalid credential')


class MemoryCredentialStore:
    """Private to a test case; no serialization or system access."""
    def __init__(self):
        self._values = {}
        self._lock = RLock()

    def read(self, provider):
        validate_provider(provider)
        with self._lock:
            return self._values.get(provider, '')

    def write(self, provider, value):
        validate_provider(provider); validate_secret(value)
        with self._lock:
            self._values[provider] = value

    def __repr__(self):
        return '<MemoryCredentialStore>'

    def read_slot(self, provider, slot_id):
        validate_slot(provider,slot_id)
        with self._lock: return self._values.get((provider,slot_id),'')

    def write_slot(self, provider, slot_id, value):
        validate_slot(provider,slot_id); validate_secret(value)
        with self._lock: self._values[provider,slot_id]=value

    def delete_slot(self, provider, slot_id, *, confirmed=False):
        validate_slot(provider,slot_id)
        if confirmed is not True: raise ValueError('Confirm deletion of this news key')
        with self._lock: self._values.pop((provider,slot_id),None)
