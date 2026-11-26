"""Assemble the original whiteboard sweep outputs without duplicating or padding any entries."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

WITNESS = struct.Struct("<4sII")


def make(workspace, dest):
    folder = workspace / "lab/whiteboard/work/q1"
    manifest = {}
    dest.mkdir(exist_ok=True, parents=True)
    for name, paths in {
        "whiteboard-costs": ("n24.f3.u8", "n24.f6.u8"),
        "whiteboard-witnesses": ("n26.rec3.bin", "n26.rec6.bin"),
    }.items():
        data = [(folder / p).read_bytes() for p in paths]
        head = (
            WITNESS.pack(b"WIT1", len(data[0]) // 24, len(data[1]) // 36)
            if name.endswith("witnesses")
            else b""
        )
        target = dest / name
        with target.open("xb") as out:
            out.write(head)
            for block in data:
                out.write(block)
        with target.open("rb") as src:
            digest = hashlib.file_digest(src, "sha256").hexdigest()
        manifest[name] = dict(
            bytes=target.stat().st_size,
            sha256=digest,
            members=[
                dict(path=p, bytes=len(d), sha256=hashlib.sha256(d).hexdigest())
                for p, d in zip(paths, data)
            ],
        )
    (dest / "whiteboard.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace", type=Path)
    p.add_argument("destination", type=Path)
    a = p.parse_args()
    make(a.workspace, a.destination)
