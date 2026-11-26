"""Predict the cost tables of the historical repdigit census and store exact corrections."""

import argparse
from pathlib import Path
import json
import struct
import subprocess
from tempfile import TemporaryDirectory
import numpy as np
import zstandard as zstd
from changes import infer_unit_denominators, pack_changes, unpack_changes

HEADER = struct.Struct(">4sQBBB")
EXE = Path(__file__).resolve().parents[1] / "build/whiteboard-census"
PROFILES = ("direct", "analytic", "narrow", "inferred", "gaps", "events", "exact")


def predict(n, k, kind, tmp):
    length = 1 << n
    if kind == 2:
        # Every positive d has a one-digit description with c=d and b=d+1.
        f3 = bytearray(length)
        f3[0] = 255
        for bits in range(1, n + 1):
            start = 1 << (bits - 1)
            end = 1 << bits
            f3[start:end] = bytes([2 * bits + 1]) * (end - start)
            f3[end - 1] += 1
        return bytes(f3) + b"\xff" * length
    prefix = tmp / "table"
    subprocess.run([EXE, str(n), str(k), prefix], stdout=subprocess.DEVNULL, check=True)
    return (
        prefix.with_suffix(".f3.u8").read_bytes()
        + prefix.with_suffix(".f6.u8").read_bytes()
    )


def difference(a, b):
    return (np.frombuffer(a, np.uint8) ^ np.frombuffer(b, np.uint8)).tobytes()


def encode(data, profile, tmp):
    coder = zstd.ZstdCompressor(level=9)
    size = len(data)
    mode, n, k, payload = 0, 0, 0, data
    z = coder.compress(data)
    if len(z) < len(payload):
        mode, payload = 1, z
    bits = size.bit_length() - 2
    if 9 <= bits <= 26 and size == 2 << bits and profile != "direct":
        choices = [(2, 0)]
        if profile in ("narrow", "inferred", "gaps", "events", "exact"):
            choices.append((3, max(8, bits - 3)))
        if profile == "exact":
            choices.append((3, bits - 1))
        for kind, budget in choices:
            estimate = predict(bits, budget, kind, tmp)
            patch = (
                b"" if data == estimate else coder.compress(difference(data, estimate))
            )
            if len(patch) < len(payload):
                mode, n, k, payload = kind, bits, budget, patch
            if kind != 3:
                continue
            predictors = [(5, estimate)]
            if profile in ("inferred", "events"):
                derived = infer_unit_denominators(estimate, bits)
                predictors.append((6, derived))
                patch = coder.compress(difference(data, derived))
                if len(patch) < len(payload):
                    mode, n, k, payload = 4, bits, budget, patch
            if profile in ("gaps", "events"):
                for gap_mode, base in predictors:
                    delta = difference(data, base)
                    if np.count_nonzero(np.frombuffer(delta, np.uint8)) > size // 4:
                        continue
                    events = coder.compress(pack_changes(delta))
                    if len(events) < len(payload):
                        mode, n, k, payload = gap_mode, bits, budget, events
    return HEADER.pack(b"WCT1", size, mode, n, k) + payload, dict(
        mode=mode, bits=n, budget=k, residual_bytes=len(payload)
    )


def decode(archive, tmp):
    magic, size, mode, n, k = HEADER.unpack_from(archive)
    if magic != b"WCT1" or mode > 6:
        raise ValueError("Invalid cost-table archive")
    payload = archive[HEADER.size :]
    if mode == 0:
        result = payload
    elif mode == 1:
        result = zstd.ZstdDecompressor().decompress(payload, max_output_size=size)
    else:
        if not 9 <= n <= 26 or size != 2 << n or (mode >= 3 and not 8 <= k <= n - 1):
            raise ValueError("Invalid census dimensions")
        result = predict(n, k, mode, tmp)
        if mode in (4, 6):
            result = infer_unit_denominators(result, n)
        if payload:
            body = zstd.ZstdDecompressor().decompress(payload, max_output_size=size)
            result = difference(
                result, unpack_changes(body, size) if mode in (5, 6) else body
            )
    if len(result) != size:
        raise ValueError("Invalid cost array length")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="exact")
    a = p.parse_args()
    with TemporaryDirectory(dir=a.out.parent) as tmp, a.out.open("xb") as f:
        if a.mode == "encode":
            archive, stats = encode(a.source.read_bytes(), a.profile, Path(tmp))
            f.write(archive)
            print(json.dumps(stats))
        else:
            f.write(decode(a.source.read_bytes(), Path(tmp)))
