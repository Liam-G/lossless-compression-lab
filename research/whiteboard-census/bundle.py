"""Attach the actual source, executable, or executable with GMP to a measured table descriptor."""

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
from costs import EXE, encode

HERE = Path(__file__).resolve().parent


def build(source, target, delivery):
    with TemporaryDirectory(dir=target.parent) as tmp:
        descriptor, stats = encode(source.read_bytes(), "exact", Path(tmp))
    members = {"__main__.py": (HERE / "extract.py").read_bytes()}
    if stats["mode"] == 3:
        if delivery == "source":
            members["enumerate.c"] = (HERE / "enumerate.c").read_bytes()
        else:
            members["enumerate"] = EXE.read_bytes()
        if delivery == "gmp":
            name = subprocess.check_output(
                ["cc", "-print-file-name=libgmp.so.10"], text=True
            ).strip()
            members["libgmp.so.10"] = Path(name).read_bytes()
    members["table"] = descriptor
    with ZipFile(target, "x") as archive:
        for name, data in members.items():
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                data,
                compress_type=ZIP_STORED if name == "table" else ZIP_DEFLATED,
                compresslevel=9,
            )
    return dict(
        descriptor_bytes=len(descriptor),
        members={k: len(v) for k, v in members.items()},
        delivery=delivery,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--delivery", choices=("source", "binary", "gmp"), required=True)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.dest, a.delivery)))
