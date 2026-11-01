"""RAM-only reader display buffer; never an archive or an NLP input.

Windows named mappings let the existing worker and Streamlit share approved
display fields. Closing the last process releases the mapping. Other platforms
support same-process previews only; they do not silently write a disk cache.
"""
import hashlib,json,mmap,os,struct

SIZE=2_000_000
HEADER=40
_owners={}
_readers={}
_local={}

def key(store,source):return 'FinScope-RSS-'+hashlib.sha256((str(store.path.resolve())+'|'+source).encode()).hexdigest()[:32]

def publish(store,source,rows,expires_at):
    rows=list(rows)
    while True:
        payload=json.dumps({'expires_at':expires_at,'rows':rows},ensure_ascii=False).encode()
        if len(payload)<=SIZE-HEADER:break
        if not rows:return
        rows.pop()
    name=key(store,source)
    if os.name!='nt':_local[name]=payload;return
    memory=_owners.get(name)
    if memory is None:memory=mmap.mmap(-1,SIZE,tagname=name)
    keep=any('title' in r or 'summary' in r for r in rows)
    if keep:_owners[name]=memory
    if not keep:memory.seek(0);memory.write(b'\0'*SIZE)
    memory.seek(0);memory.write(b'\0'*HEADER);memory.write(payload)
    memory.seek(0);memory.write(struct.pack('!Q',len(payload))+hashlib.sha256(payload).digest())
    if not keep:_owners.pop(name,None);memory.close()

def read(store,source,now,*,allow_expired=False):
    name=key(store,source)
    if os.name!='nt':payload=_local.get(name,b'')
    else:
        memory=_readers.get(name) or mmap.mmap(-1,SIZE,tagname=name);keep=False
        try:
            memory.seek(0)
            header=memory.read(HEADER);length=struct.unpack('!Q',header[:8])[0]
            if not 0<length<=SIZE-HEADER:return []
            payload=memory.read(length)
            if hashlib.sha256(payload).digest()!=header[8:]:return []
            data=json.loads(payload)
            if (allow_expired or data.get('expires_at','')>now) and any('title' in r or 'summary' in r for r in data.get('rows',[])):
                _readers[name]=memory;keep=True
        except (ValueError,TypeError):return []
        finally:
            if not keep:_readers.pop(name,None);memory.close()
    try:data=json.loads(payload)
    except (ValueError,TypeError):return []
    if not allow_expired and data.get('expires_at','')<=now:return []
    return data.get('rows',[])
