"""Explicit demo-model preparation. Never invoked implicitly by inference."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest(kind):
    return json.loads((ROOT/"finscope"/f"{kind}_manifest.json").read_text())


def model_directory(kind):
    from .test_safety import case_directory
    return (case_directory() or ROOT)/"models"/kind/manifest(kind)["revision"]


def assets_present(kind):
    try:
        verify(kind)
        return True
    except (ValueError,OSError):
        return False


def valid_file(path, expected):
    if not path.is_file() or path.is_symlink() or path.stat().st_size != expected["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest() == expected["sha256"]


def verify(kind, directory=None):
    spec = manifest(kind)
    root = Path(directory) if directory is not None else model_directory(kind)
    names = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} if root.exists() else set()
    if names != set(spec["files"]) or not all(valid_file(root/name, expected) for name,expected in spec["files"].items()):
        raise ValueError("Pinned model files missing, extra or modified; prepare explicitly")
    return spec


class PreparationCancelled(Exception):
    pass


def prepare_models(*, acknowledge_licenses=False, progress=lambda **state:None, cancelled=lambda:False):
    if acknowledge_licenses is not True:
        raise ValueError("Acknowledge FinBERT CC BY-NC-SA 4.0 and MiniLM Apache-2.0 licences")
    from .task_queue import ProcessLock
    with ProcessLock(model_directory('finbert').parents[1]/'.prepare.lock'):
        _prepare(progress, cancelled)


def _prepare(progress, cancelled):
    import requests
    def check():
        if cancelled():raise PreparationCancelled('Preparation cancelled; verified files retained')
    total=sum(e['size'] for k in ('finbert','minilm') for e in manifest(k)['files'].values())
    done=0
    for kind in ('finbert','minilm'):
        spec=manifest(kind);root=model_directory(kind)
        for name,expected in spec['files'].items():
            check();target=root/name
            if valid_file(target,expected):
                done+=expected['size'];progress(done=done,total=total,file=kind+'/'+name);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            partial=target.with_name(target.name+'.partial')
            # Never append an unverified interrupted download. Completed files are reused.
            if partial.is_symlink() or target.is_symlink():raise ValueError('Model path is a symlink')
            response=requests.get(f"https://huggingface.co/{spec['model_id']}/resolve/{spec['revision']}/{name}",
                                  stream=True,timeout=(15,30))
            try:
                response.raise_for_status();received=0
                with partial.open('wb') as stream:
                    for chunk in response.iter_content(1024*1024):
                        check();received+=len(chunk)
                        if received>expected['size']:raise ValueError('Model download exceeds pinned size')
                        stream.write(chunk);progress(done=done+received,total=total,file=kind+'/'+name)
                check()
                if not valid_file(partial,expected):raise ValueError('Model download integrity failed')
                partial.replace(target);done+=expected['size']
            finally:response.close()
        verify(kind)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--acknowledge-model-licenses",action="store_true")
    args=parser.parse_args()
    if args.prepare:
        prepare_models(acknowledge_licenses=args.acknowledge_model_licenses)
    print(json.dumps({kind:{"revision":manifest(kind)["revision"],"prepared":assets_present(kind)}
                      for kind in ("finbert","minilm")},indent=2))
