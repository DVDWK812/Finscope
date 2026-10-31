"""Sole Windows credential adapter. Deletion is restricted to owned news UUIDs."""
import ctypes as c
from ctypes import wintypes as w
import os
from .credential_store import validate_provider, validate_secret, validate_slot
from .test_safety import forbid_system_credentials


class Credential(c.Structure):
    _fields_ = [('Flags', w.DWORD), ('Type', w.DWORD), ('TargetName', w.LPWSTR), ('Comment', w.LPWSTR),
                ('LastWritten', w.FILETIME), ('CredentialBlobSize', w.DWORD), ('CredentialBlob', c.POINTER(c.c_ubyte)),
                ('Persist', w.DWORD), ('AttributeCount', w.DWORD), ('Attributes', c.c_void_p),
                ('TargetAlias', w.LPWSTR), ('UserName', w.LPWSTR)]


def target_name(provider,slot_id=None):
    validate_provider(provider)
    if slot_id is not None: validate_slot(provider,slot_id)
    return 'FinScope local / '+provider+('/slots/'+slot_id if slot_id is not None else '')


class Win32CredentialBindings:
    """Marshalling logic; regression tests provide mock APIs, never a DLL."""
    def __init__(self, api, *, last_error=lambda:0):
        self.api = api
        self.last_error = last_error
        api.CredReadW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.POINTER(c.POINTER(Credential))]
        api.CredReadW.restype = w.BOOL
        api.CredWriteW.argtypes = [c.POINTER(Credential), w.DWORD]
        api.CredWriteW.restype = w.BOOL
        api.CredFree.argtypes = [c.c_void_p]
        api.CredFree.restype = None

    def read(self, provider, slot_id=None):
        validate_provider(provider)
        target=target_name(provider,slot_id)
        pointer = c.POINTER(Credential)()
        try:
            found = self.api.CredReadW(target, 1, 0, c.byref(pointer))
        except Exception:
            raise ValueError('Windows credential read failed') from None
        if not found:
            if slot_id is not None and self.last_error()!=1168:
                raise ValueError('News credential could not be read; no request was made')
            return ''
        try:
            if not pointer or not 0 <= pointer.contents.CredentialBlobSize <= 4096:
                raise ValueError
            return c.string_at(pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize).decode('utf-16-le')
        except (UnicodeError, ValueError):
            raise ValueError('Windows credential read failed') from None
        finally:
            self.api.CredFree(pointer)

    def write(self, provider, value, slot_id=None):
        validate_provider(provider); validate_secret(value)
        target=target_name(provider,slot_id)
        blob = (c.c_ubyte * len(value.encode('utf-16-le'))).from_buffer_copy(value.encode('utf-16-le'))
        entry = Credential(); entry.Type = 1; entry.TargetName = target
        entry.UserName = provider; entry.Persist = 2
        entry.CredentialBlobSize = len(blob); entry.CredentialBlob = c.cast(blob, c.POINTER(c.c_ubyte))
        try:
            saved = self.api.CredWriteW(c.byref(entry), 0)
        except Exception:
            raise ValueError('Windows credential storage failed; existing .env remains usable') from None
        if not saved:
            raise ValueError('Windows credential storage failed; existing .env remains usable')

    def delete_slot(self,provider,slot_id,*,confirmed=False):
        validate_slot(provider,slot_id)
        if confirmed is not True: raise ValueError('Confirm deletion of this news key')
        self.api.CredDeleteW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD]
        self.api.CredDeleteW.restype=w.BOOL
        try:
            if not self.api.CredDeleteW(target_name(provider,slot_id),1,0) and self.last_error()!=1168:
                raise ValueError
        except Exception:
            raise ValueError('News key deletion failed; configuration remains disabled for review') from None


class WindowsCredentialStore:
    def _bindings(self):
        forbid_system_credentials()  # Before platform checks or DLL/API access.
        if os.name != 'nt':
            return None
        return Win32CredentialBindings(c.WinDLL('Advapi32', use_last_error=True),last_error=c.get_last_error)

    def read(self, provider):
        validate_provider(provider)
        bindings = self._bindings()
        return bindings.read(provider) if bindings else ''

    def write(self, provider, value):
        validate_provider(provider); validate_secret(value)
        bindings = self._bindings()
        if bindings:
            bindings.write(provider, value)

    def read_slot(self,provider,slot_id):
        validate_slot(provider,slot_id)
        bindings=self._bindings()
        return bindings.read(provider,slot_id) if bindings else ''

    def write_slot(self,provider,slot_id,value):
        validate_slot(provider,slot_id);validate_secret(value)
        bindings=self._bindings()
        if not bindings: raise ValueError('Protected news key storage requires Windows Credential Manager')
        bindings.write(provider,value,slot_id)

    def delete_slot(self,provider,slot_id,*,confirmed=False):
        validate_slot(provider,slot_id)
        if confirmed is not True: raise ValueError('Confirm deletion of this news key')
        bindings=self._bindings()
        if not bindings: raise ValueError('Protected news key storage requires Windows Credential Manager')
        bindings.delete_slot(provider,slot_id,confirmed=True)
