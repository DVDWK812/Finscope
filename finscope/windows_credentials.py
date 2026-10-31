"""Sole Windows Credential Manager adapter. No delete/enumerate/export API."""
import ctypes as c
from ctypes import wintypes as w
import os
from .credential_store import validate_provider, validate_secret
from .test_safety import forbid_system_credentials


class Credential(c.Structure):
    _fields_ = [('Flags', w.DWORD), ('Type', w.DWORD), ('TargetName', w.LPWSTR), ('Comment', w.LPWSTR),
                ('LastWritten', w.FILETIME), ('CredentialBlobSize', w.DWORD), ('CredentialBlob', c.POINTER(c.c_ubyte)),
                ('Persist', w.DWORD), ('AttributeCount', w.DWORD), ('Attributes', c.c_void_p),
                ('TargetAlias', w.LPWSTR), ('UserName', w.LPWSTR)]


class Win32CredentialBindings:
    """Marshalling logic; regression tests provide mock APIs, never a DLL."""
    def __init__(self, api):
        self.api = api
        api.CredReadW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.POINTER(c.POINTER(Credential))]
        api.CredReadW.restype = w.BOOL
        api.CredWriteW.argtypes = [c.POINTER(Credential), w.DWORD]
        api.CredWriteW.restype = w.BOOL
        api.CredFree.argtypes = [c.c_void_p]
        api.CredFree.restype = None

    def read(self, provider):
        validate_provider(provider)
        pointer = c.POINTER(Credential)()
        try:
            found = self.api.CredReadW('FinScope local / ' + provider, 1, 0, c.byref(pointer))
        except Exception:
            raise ValueError('Windows credential read failed') from None
        if not found:
            return ''
        try:
            if not pointer or not 0 <= pointer.contents.CredentialBlobSize <= 4096:
                raise ValueError
            return c.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize).decode('utf-16-le')
        except (UnicodeError, ValueError):
            raise ValueError('Windows credential read failed') from None
        finally:
            self.api.CredFree(pointer)

    def write(self, provider, value):
        validate_provider(provider); validate_secret(value)
        blob = (c.c_ubyte * len(value.encode('utf-16-le'))).from_buffer_copy(value.encode('utf-16-le'))
        entry = Credential(); entry.Type = 1; entry.TargetName = 'FinScope local / ' + provider
        entry.UserName = provider; entry.Persist = 2
        entry.CredentialBlobSize = len(blob); entry.CredentialBlob = c.cast(blob, c.POINTER(c.c_ubyte))
        try:
            saved = self.api.CredWriteW(c.byref(entry), 0)
        except Exception:
            raise ValueError('Windows credential storage failed; existing .env remains usable') from None
        if not saved:
            raise ValueError('Windows credential storage failed; existing .env remains usable')


class WindowsCredentialStore:
    def _bindings(self):
        forbid_system_credentials()  # Before platform checks or DLL/API access.
        if os.name != 'nt':
            return None
        return Win32CredentialBindings(c.WinDLL('Advapi32', use_last_error=True))

    def read(self, provider):
        validate_provider(provider)
        bindings = self._bindings()
        return bindings.read(provider) if bindings else ''

    def write(self, provider, value):
        validate_provider(provider); validate_secret(value)
        bindings = self._bindings()
        if bindings:
            bindings.write(provider, value)
