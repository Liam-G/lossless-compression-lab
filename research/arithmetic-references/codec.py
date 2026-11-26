"""Patch against a byte reference or an arithmetically transformed reference."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
import zstandard as zstd

HEADER = struct.Struct(">4sBBQ32s")
DIRECT, DICTIONARY, XOR, EXACT = range(4)
# A fixed-width prediction is reduced modulo the destination width when necessary.
OPS = (1, 3, -3, 12, -12, 256, -256, 3072, -3072, 37632, -37632)
PROFILES = ("direct", "patch", "numeric", "joint", "exact")


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").digest()


def reference_view(raw, op, size):
    if op == 1:
        return raw
    x = int.from_bytes(raw, "big")
    predicted = x * op if op > 0 else x // -op
    if predicted.bit_length() > 8 * size:
        predicted &= (1 << (8 * size)) - 1
    return predicted.to_bytes(size, "big")


def xor_bytes(a, b):
    aa = np.frombuffer(a, np.uint8)
    bb = np.frombuffer(b, np.uint8)
    out = aa.copy()
    n = min(len(aa), len(bb))
    out[:n] ^= bb[:n]
    return out.tobytes()


def probe(target, base):
    # Dispersed exact byte probes rank candidate scales even when only a few regions match.
    length = min(len(target), len(base))
    if not length:
        return 0
    offsets = np.linspace(0, max(0, length - 128), min(1024, length), dtype=np.int64)
    offset = (offsets[:, None] + np.arange(min(128, length))).ravel()
    a = np.frombuffer(target, np.uint8)[offset]
    b = np.frombuffer(base, np.uint8)[offset]
    return int(np.count_nonzero(a == b))


def patch(source, base, target, reverse=False):
    # Zstandard chooses matches across the entire supplied reference.
    args = ["zstd", "-q", "-T1", "--long=27", f"--patch-from={base}"]
    subprocess.run(
        args + (["-d"] if reverse else ["-9"]) + [source, "-o", target], check=True
    )


def encode(src, ref, dest, profile):
    target = src.read_bytes()
    reference = ref.read_bytes()
    coder = zstd.ZstdCompressor(level=9)
    best = coder.compress(target)
    selected = (DIRECT, 0)
    if profile == "direct":
        candidates = []
    else:
        candidates = [0]
        if profile in ("numeric", "joint", "exact"):
            if len(target):
                scores = [
                    (probe(target, reference_view(reference, op, len(target))), i)
                    for i, op in enumerate(OPS)
                    if i
                ]
                candidates.extend(
                    i for _, i in sorted(scores, key=lambda x: (-x[0], x[1]))[:2]
                )
    with TemporaryDirectory(dir=dest.parent) as scratch:
        tmp = Path(scratch)
        for i in candidates:
            prediction = reference_view(reference, OPS[i], len(target))
            if profile == "exact" and prediction == target:
                best, selected = b"", (EXACT, i)
                break
            if profile in ("numeric", "joint", "exact"):
                trial = coder.compress(xor_bytes(target, prediction))
                if len(trial) < len(best):
                    best, selected = trial, (XOR, i)
            if profile in ("patch", "joint", "exact") and prediction:
                path = ref
                if i:
                    path = tmp / f"view-{i}"
                    path.write_bytes(prediction)
                patched = tmp / f"patch-{i}"
                patch(src, path, patched)
                if patched.stat().st_size < len(best):
                    best, selected = patched.read_bytes(), (DICTIONARY, i)
    mode, i = selected
    with dest.open("xb") as f:
        f.write(
            HEADER.pack(
                b"ARF1",
                mode,
                i,
                len(target),
                digest(ref) if mode != DIRECT else bytes(32),
            )
        )
        f.write(best)
    return {
        "mode": ("direct", "patch", "xor", "exact")[mode],
        "operator": OPS[i],
        "reference_used": mode != DIRECT,
    }


def decode(src, ref, dest):
    with src.open("rb") as f:
        magic, mode, i, size, needed = HEADER.unpack(f.read(HEADER.size))
        record = f.read()
    if (
        magic != b"ARF1"
        or mode not in (DIRECT, DICTIONARY, XOR, EXACT)
        or i >= len(OPS)
    ):
        raise ValueError("Invalid reference header")
    if mode == DIRECT:
        result = zstd.ZstdDecompressor().decompress(record, max_output_size=size)
    else:
        if ref is None or digest(ref) != needed:
            raise ValueError("Reference SHA-256 mismatch")
        prediction = reference_view(ref.read_bytes(), OPS[i], size)
        if mode == EXACT:
            if record:
                raise ValueError("Unexpected payload after exact reference")
            result = prediction
        elif mode == XOR:
            delta = zstd.ZstdDecompressor().decompress(record, max_output_size=size)
            result = xor_bytes(delta, prediction)
        else:
            with TemporaryDirectory(dir=dest.parent) as scratch:
                tmp = Path(scratch)
                base = ref
                if i:
                    base = tmp / "base"
                    base.write_bytes(prediction)
                archive = tmp / "patch"
                archive.write_bytes(record)
                path = tmp / "decoded"
                patch(archive, base, path, True)
                result = path.read_bytes()
    if len(result) != size:
        raise ValueError("Wrong decoded size")
    with dest.open("xb") as f:
        f.write(result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--reference", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    if a.mode == "encode":
        if a.reference is None:
            p.error("Supply the reference for candidate selection")
        print(json.dumps(encode(a.source, a.reference, a.destination, a.profile)))
    else:
        decode(a.source, a.reference, a.destination)
