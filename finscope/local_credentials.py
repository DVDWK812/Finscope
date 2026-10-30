"""Project .env plus optional Windows per-user Credential Manager. No SQLite keys."""
import os

PROVIDERS=('marketaux','newsdata','finnhub','openai')


def vault_key(provider,value=None):
    if provider not in PROVIDERS:raise ValueError('Unsupported credential provider')
    if os.name!='nt':return ''
    import ctypes as c
    from ctypes import wintypes as w
    class Credential(c.Structure):
        _fields_=[('Flags',w.DWORD),('Type',w.DWORD),('TargetName',w.LPWSTR),('Comment',w.LPWSTR),
                  ('LastWritten',w.FILETIME),('CredentialBlobSize',w.DWORD),('CredentialBlob',c.POINTER(c.c_ubyte)),
                  ('Persist',w.DWORD),('AttributeCount',w.DWORD),('Attributes',c.c_void_p),('TargetAlias',w.LPWSTR),('UserName',w.LPWSTR)]
    api=c.WinDLL('Advapi32',use_last_error=True);target='FinScope local / '+provider
    api.CredReadW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.POINTER(c.POINTER(Credential))];api.CredReadW.restype=w.BOOL
    api.CredWriteW.argtypes=[c.POINTER(Credential),w.DWORD];api.CredWriteW.restype=w.BOOL
    api.CredFree.argtypes=[c.c_void_p]
    if value is not None:
        if not isinstance(value,str) or not value.strip() or len(value)>500:raise ValueError('Invalid credential')
        blob=(c.c_ubyte*len(value.encode('utf-16-le'))).from_buffer_copy(value.encode('utf-16-le'))
        entry=Credential();entry.Type=1;entry.TargetName=target;entry.UserName=provider;entry.Persist=2
        entry.CredentialBlobSize=len(blob);entry.CredentialBlob=c.cast(blob,c.POINTER(c.c_ubyte))
        if not api.CredWriteW(c.byref(entry),0):raise ValueError('Windows credential storage failed; existing .env remains usable')
        return ''
    pointer=c.POINTER(Credential)()
    if not api.CredReadW(target,1,0,c.byref(pointer)):return ''
    try:return c.string_at(pointer.contents.CredentialBlob,pointer.contents.CredentialBlobSize).decode('utf-16-le')
    finally:api.CredFree(pointer)


def credential(provider):
    from .api_sources import local_credentials,ENV_KEYS
    env='OPENAI_API_KEY' if provider=='openai' else ENV_KEYS[provider]
    return vault_key(provider) or local_credentials().get(env,'')
