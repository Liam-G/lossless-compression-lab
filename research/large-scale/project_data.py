"""Make two 24 MiB captures of the original lab's mathematical descriptions."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

SIZE = 24 << 20
PAIR = struct.Struct(">hh")


def signed(source):
    value = shift = 0
    while True:
        byte = source.read(1)
        if not byte:
            raise EOFError("Incomplete affine operand")
        value |= (byte[0] & 127) << shift
        if byte[0] < 128:
            return -(value // 2) - 1 if value & 1 else value // 2
        shift += 7


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    folder = a.workspace / "lab/hutter/divisors/q-correzioni-fattori"
    manifest = {}
    with gzip.open(folder / "Q.formula-integrale.txt.gz", "rb") as f:
        text = f.read(SIZE)
    if len(text) != SIZE:
        raise ValueError("Formula listing is too short")
    with (a.output / "formula-text").open("xb") as out:
        out.write(text)
    manifest["formula-text"] = dict(
        bytes=SIZE,
        sha256=hashlib.sha256(text).hexdigest(),
        source="First 24 MiB of the inflated original Q formula listing",
    )
    with (
        (folder / "formula.bin").open("rb") as f,
        (a.output / "affine-pairs").open("xb") as out,
    ):
        while out.tell() < SIZE:
            batch = bytearray()
            for _ in range(8192):
                tag = f.read(1)
                if not tag:
                    raise ValueError("Original operation stream is too short")
                b = tag[0]
                m = signed(f) if b == 255 else 240
                c = signed(f) if b >= 254 else b - 100
                batch.extend(PAIR.pack(m, c))
            out.write(batch)
        consumed = f.tell()
    with (a.output / "affine-pairs").open("rb") as f:
        manifest["affine-pairs"] = dict(
            bytes=SIZE,
            sha256=hashlib.file_digest(f, "sha256").hexdigest(),
            original_bytes_consumed=consumed,
            source="First 6,291,456 original affine instructions as big-endian signed 16-bit pairs",
        )
    (a.output / "project-data.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
