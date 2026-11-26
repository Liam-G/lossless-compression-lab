"""Width-preserving archive around the original recursive quartic engine."""

import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ENGINE = Path(__file__).resolve().parents[1] / "build/quartic"
HEADER = struct.Struct(">4sQQ")


def convert(mode, source, dest):
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        tmp = Path(tmp)
        raw = source.read_bytes()
        if mode == "encode":
            n = len(raw)
            significant = raw.lstrip(b"\0")
            width = (
                (8 * (len(significant) - 1) + significant[0].bit_length())
                if significant
                else 0
            )
            body = b""
        else:
            magic, n, width = HEADER.unpack_from(raw)
            if magic != b"QW01" or (width + 7) // 8 > n:
                raise ValueError("Invalid quartic frame")
            body = raw[HEADER.size :]
            if width == 0 and body:
                raise ValueError("Unexpected zero-tree payload")
        stats = {}
        if width:
            engine_input = source
            if mode == "decode":
                engine_input = tmp / "body"
                engine_input.write_bytes(body)
            engine_output = tmp / "result"
            run = subprocess.check_output(
                [ENGINE, mode, str(width), engine_input, engine_output]
            )
            stats = json.loads(run)
            body = engine_output.read_bytes()
        result = (
            HEADER.pack(b"QW01", n, width) + body
            if mode == "encode"
            else body.rjust(n, b"\0")
        )
        if mode == "decode" and len(result) != n:
            raise ValueError("Quartic result exceeds declared length")
        with dest.open("xb") as f:
            f.write(result)
        return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["encode", "decode"])
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    a = p.parse_args()
    print(json.dumps(convert(a.mode, a.source, a.destination)))
