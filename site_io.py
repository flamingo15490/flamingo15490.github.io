"""Write generated files with workspace guards when available, standalone otherwise."""
from pathlib import Path
from hashlib import sha256
import sys, os
SITE=Path(__file__).resolve().parent
WORKSPACE=next((p for p in SITE.parents if (p/'management_common.py').is_file()),None)
if WORKSPACE:
    sys.path.insert(0,str(WORKSPACE))
    from management_common import guarded_write,file_digest

def write(relative,data):
    path=(SITE/relative).resolve()
    path.relative_to(SITE)
    raw=data.encode('utf-8') if isinstance(data,str) else data
    before=path.read_bytes() if path.is_file() else None
    if before==raw:return
    if WORKSPACE:
        guarded_write(WORKSPACE,path.relative_to(WORKSPACE).as_posix(),raw,file_digest(path),'coordinator')
    else:
        expected=sha256(before).hexdigest() if before is not None else None
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_name(path.name+'.tmp')
        temp.write_bytes(raw)
        current=path.read_bytes() if path.is_file() else None
        if (sha256(current).hexdigest() if current is not None else None)!=expected:
            temp.unlink();raise RuntimeError('File changed concurrently: '+relative)
        os.replace(temp,path)
