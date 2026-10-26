"""Explicit demo-model preparation. Never invoked implicitly by inference."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest(kind):
    return json.loads((ROOT/"finscope"/f"{kind}_manifest.json").read_text())


def model_directory(kind):
    return ROOT/"models"/kind/manifest(kind)["revision"]


def assets_present(kind):
    root=model_directory(kind)
    return all((root/name).is_file() and (root/name).stat().st_size==entry["size"]
               for name,entry in manifest(kind)["files"].items())


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


def prepare_models(*, acknowledge_licenses=False):
    if acknowledge_licenses is not True:
        raise ValueError("Acknowledge FinBERT CC BY-NC-SA 4.0 and MiniLM Apache-2.0 licences")
    import requests
    for kind in ("finbert","minilm"):
        spec = manifest(kind); root = model_directory(kind)
        for name, expected in spec["files"].items():
            target = root/name
            if valid_file(target,expected):
                continue
            target.parent.mkdir(parents=True,exist_ok=True)
            partial = target.with_name(target.name+".partial")
            response = requests.get(f'https://huggingface.co/{spec["model_id"]}/resolve/{spec["revision"]}/{name}',
                                    stream=True, timeout=(15,120))
            response.raise_for_status()
            with partial.open("wb") as stream:
                for chunk in response.iter_content(1024*1024):stream.write(chunk)
            if not valid_file(partial,expected):
                raise ValueError("Model download integrity failed; no model loaded")
            partial.replace(target)
        verify(kind)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--acknowledge-model-licenses",action="store_true")
    args=parser.parse_args()
    if args.prepare:
        prepare_models(acknowledge_licenses=args.acknowledge_model_licenses)
    print(json.dumps({kind:{"revision":manifest(kind)["revision"],"prepared":model_directory(kind).exists()}
                      for kind in ("finbert","minilm")},indent=2))
