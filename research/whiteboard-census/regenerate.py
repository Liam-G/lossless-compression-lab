"""Regenerate a witness sequence and transmit the exact corrections for this enumerator."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
import zstandard as zstd

from changes import pack_changes, unpack_changes
from costs import EXE, difference
from data import WITNESS
from witnesses import groups

HEADER = struct.Struct(">4sQBBBB")
MEMBER = struct.Struct(">32s")
PROFILES = ("generic", "native")


def predict(n, k, subset, native, directory):
    exe = EXE.with_name(EXE.name + "-host") if native else EXE
    prefix = directory / "run"
    subprocess.run([exe, str(n), str(k), prefix], stdout=subprocess.DEVNULL, check=True)
    three = prefix.with_suffix(".rec3.bin").read_bytes() if not subset else b""
    six = np.fromfile(prefix.with_suffix(".rec6.bin"), dtype="<u4").reshape(-1, 9)
    if subset:
        six = six[(six[:, 5] != 1) | (six[:, 7] != 1)]
    return WITNESS.pack(b"WIT1", len(three) // 24, len(six)) + three + six.tobytes()


def infer(raw):
    try:
        three, six = groups(raw)
    except (ValueError, struct.error):
        return None
    if not len(six) or np.any(six[:, 1]):
        return None
    n, k = int(six[:, 0].max()).bit_length(), int(six[:, -1].max())
    if not (9 <= n <= 28 and 8 <= k <= n - 1):
        return None
    return n, k, int(len(three) == 0)


def encode(raw, profile, directory):
    coder = zstd.ZstdCompressor(level=9)
    mode, body = min(
        [(0, raw), (1, coder.compress(raw))], key=lambda item: len(item[1])
    )
    n = k = flags = 0
    mismatch = None
    parameters = infer(raw)
    if parameters:
        bits, budget, subset = parameters
        native = profile == "native"
        prediction = predict(bits, budget, subset, native, directory)
        if len(prediction) == len(raw):
            delta = difference(raw, prediction)
            mismatch = int(np.count_nonzero(np.frombuffer(delta, np.uint8)))
            choices = [(2, b"")] if not mismatch else [(3, coder.compress(delta))]
            if 0 < mismatch <= len(raw) // 4:
                choices.append((4, coder.compress(pack_changes(delta))))
            candidate, payload = min(choices, key=lambda item: len(item[1]))
            payload = MEMBER.pack(hashlib.sha256(prediction).digest()) + payload
            if len(payload) < len(body):
                mode, body = candidate, payload
                n, k, flags = bits, budget, subset | (native << 1)
    return HEADER.pack(b"WRT1", len(raw), mode, n, k, flags) + body, dict(
        mode=mode, bits=n, budget=k, flags=flags, mismatch_bytes=mismatch
    )


def decode(archive, directory):
    magic, size, mode, n, k, flags = HEADER.unpack_from(archive)
    if magic != b"WRT1" or mode > 4 or flags > 3:
        raise ValueError("Invalid witness regeneration header")
    body = archive[HEADER.size :]
    if mode < 2:
        raw = (
            body
            if mode == 0
            else zstd.ZstdDecompressor().decompress(body, max_output_size=size)
        )
    else:
        if not 9 <= n <= 28 or not 8 <= k <= n - 1:
            raise ValueError("Invalid census dimensions")
        prediction = predict(n, k, flags & 1, flags & 2, directory)
        if (
            len(prediction) != size
            or hashlib.sha256(prediction).digest() != body[: MEMBER.size]
        ):
            raise ValueError("Enumerator produced a different witness sequence")
        patch = body[MEMBER.size :]
        if mode == 2:
            if patch:
                raise ValueError("Unexpected correction")
            raw = prediction
        else:
            residual = zstd.ZstdDecompressor().decompress(patch)
            if mode == 4:
                residual = unpack_changes(residual, size)
            if len(residual) != size:
                raise ValueError("Incorrect correction length")
            raw = difference(prediction, residual)
    if len(raw) != size:
        raise ValueError("Incorrect reconstructed length")
    return raw


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="generic")
    a = parser.parse_args()
    with (
        TemporaryDirectory(dir=a.destination.parent) as tmp,
        a.destination.open("xb") as out,
    ):
        raw = a.source.read_bytes()
        if a.mode == "encode":
            value, stats = encode(raw, a.profile, Path(tmp))
            print(json.dumps(stats))
        else:
            value = decode(raw, Path(tmp))
        out.write(value)
