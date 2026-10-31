"""Provider-scoped store contract and non-system test implementation."""
from threading import RLock

PROVIDERS = ('marketaux', 'newsdata', 'finnhub', 'openai', 'deepseek')


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
