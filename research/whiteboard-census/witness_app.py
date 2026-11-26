"""Ship the witness enumerator, inverse, computation parameters and exact corrections."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
import zlib

from costs import EXE, difference
from extract_witness import HEADER
from regenerate import infer, predict

HERE = Path(__file__).resolve().parent


def package(source, target, profile):
    raw = source.read_bytes()
    n = k = flags = mode = 0
    body = zlib.compress(raw, 6)
    members = {"__main__.py": (HERE / "extract_witness.py").read_bytes()}
    parameters = infer(raw)
    if parameters:
        bits, budget, subset = parameters
        native = profile != "generic"
        with TemporaryDirectory(dir=target.parent) as tmp:
            base = predict(bits, budget, subset, native, Path(tmp))
        if len(base) == len(raw):
            matched = base == raw
            delta = b"" if matched else zlib.compress(difference(raw, base), 9)
            key = "enumerate" if profile == "binary" else "enumerate.c"
            decoder = (
                EXE.with_name(EXE.name + "-host")
                if profile == "binary"
                else HERE / "enumerate.c"
            ).read_bytes()
            # Charge an upper bound on the extra ZIP member before choosing it.
            if 32 + len(delta) + len(decoder) + 128 + 2 * len(key) < len(body):
                mode = 1 if matched else 2
                n, k, flags = bits, budget, subset | (native << 1)
                body = hashlib.sha256(base).digest() + delta
                members[key] = decoder
    members["model"] = HEADER.pack(b"WRP1", mode, n, k, flags, len(raw)) + body
    with ZipFile(target, "x") as archive:
        for name, data in members.items():
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                data,
                compress_type=ZIP_STORED if name == "model" else ZIP_DEFLATED,
                compresslevel=9,
            )
    return dict(
        mode=mode, members={k: len(v) for k, v in members.items()}, profile=profile
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--delivery", choices=("source", "binary", "generic"), required=True)
    a = p.parse_args()
    print(json.dumps(package(a.source, a.dest, a.delivery)))
