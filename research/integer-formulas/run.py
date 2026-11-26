"""Choose a whole-integer formula and evaluate its self-contained descriptor."""

import argparse
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import composite
import formula
import modular

MODES = (
    "floor",
    "nearest",
    "mixed",
    "modular",
    "composite",
    "modular-adjusted",
    "composite-adjusted",
)


def encode(mode, src, dst):
    if mode.endswith("-adjusted"):
        data = bytearray(src.read_bytes())
        if not data:
            with dst.open("xb") as output:
                output.write(b"QMA1\x10")
            return
        low = data[-1] & 7
        data[-1] = (data[-1] & 248) | 1
        raised = data[-1] == 1 and not any(data[:-1])
        if raised:
            data[-1] = 9
        with TemporaryDirectory(dir=dst.parent) as directory:
            normalized = Path(directory) / "normalized"
            inner = Path(directory) / "square"
            normalized.write_bytes(data)
            encode(mode.removesuffix("-adjusted"), normalized, inner)
            with dst.open("xb") as output, inner.open("rb") as payload:
                output.write(b"QMA1" + bytes([low + 8 * raised]))
                shutil.copyfileobj(payload, output)
    elif mode == "modular":
        modular.encode(src, dst)
    elif mode == "composite":
        with TemporaryDirectory(dir=dst.parent) as directory:
            root = Path(directory) / "root"
            modular.encode(src, root)
            composite.encode(src, root, dst, 8192)
    else:
        formula.encode(src, dst, mode)


def decode(src, dst):
    decoders = {
        b"QFE1": formula.decode,
        b"QMS1": modular.decode,
        b"QFC1": composite.decode,
    }
    with src.open("rb") as source:
        magic = source.read(4)
        if magic in decoders:
            decoders[magic](src, dst)
            return
        if magic != b"QMA1":
            raise ValueError("Unknown integer formula")
        flags = source.read(1)
        if flags == b"\x10" and not source.read(1):
            with dst.open("xb"):
                pass
            return
        if not flags or flags[0] >= 16:
            raise ValueError("Unknown modular correction")
        with TemporaryDirectory(dir=dst.parent) as directory:
            inner = Path(directory) / "square"
            raw = Path(directory) / "normalized"
            with inner.open("xb") as stored:
                shutil.copyfileobj(source, stored)
            with inner.open("rb") as stored:
                kind = stored.read(4)
            if kind not in (b"QMS1", b"QFC1"):
                raise ValueError("Missing modular square")
            decoders[kind](inner, raw)
            data = bytearray(raw.read_bytes())
    if not data or data[-1] % 8 != 1:
        raise ValueError("Invalid normalized integer")
    if flags[0] & 8:
        if data[-1] != 9 or any(data[:-1]):
            raise ValueError("Invalid small-integer correction")
        data[-1] = 0
    data[-1] = (data[-1] & 248) | (flags[0] & 7)
    with dst.open("xb") as output:
        output.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=(*MODES, "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.mode == "decode":
        decode(args.source, args.destination)
    else:
        encode(args.mode, args.source, args.destination)


if __name__ == "__main__":
    main()
