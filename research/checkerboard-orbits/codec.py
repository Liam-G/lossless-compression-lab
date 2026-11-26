"""Price a shared predecessor time against individual times on toroidal 8×8 matrices."""

import argparse
import ctypes as ct
from collections import Counter
from functools import cache
import json
from pathlib import Path
import struct
import numpy as np
import zstandard as zstd

HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BHI")
BLOCK = 1 << 18
LIMIT = 1000
DIRECT, SHARED, INDIVIDUAL, STORED = range(4)
PROFILES = ("direct", "individual", "shared", "joint")


@cache
def native():
    so = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/checker-orbit.so"))
    ptr = ct.c_void_p
    so.find_minimum.argtypes = [ptr, ptr, ptr, ct.c_size_t, ct.c_uint]
    so.score_shared.argtypes = [ptr, ct.c_size_t, ptr, ct.c_uint]
    so.apply_orbit.argtypes = [ptr, ptr, ct.c_size_t, ct.c_uint, ct.c_bool]
    for fn in (so.find_minimum, so.score_shared, so.apply_orbit):
        fn.restype = None
    return so


def evolve(words, t=0, times=None, inverse=False):
    native().apply_orbit(
        words.ctypes.data,
        times.ctypes.data if times is not None else None,
        len(words),
        t,
        inverse,
    )


def options(data, profile, coder):
    yield STORED, 0, data
    yield DIRECT, 0, coder.compress(data)
    end = len(data) // 8 * 8
    if not end or profile == "direct":
        return
    words = np.frombuffer(data[:end], "<u8")
    tail = data[end:]
    if profile in ("shared", "joint"):
        sample = words[
            np.linspace(0, len(words) - 1, min(192, len(words)), dtype=np.int64)
        ]
        scores = np.zeros(LIMIT + 1, "<u4")
        native().score_shared(
            sample.ctypes.data, len(sample), scores.ctypes.data, LIMIT
        )
        # Whole-page Zstandard sizes settle ties and false leads in the sample.
        for t in np.argsort(scores, kind="stable")[:3]:
            if t:
                result = words.copy()
                evolve(result, int(t), inverse=True)
                yield SHARED, int(t), coder.compress(result.tobytes() + tail)
    if profile in ("individual", "joint"):
        seeds = np.empty_like(words)
        times = np.empty(len(words), "<u2")
        native().find_minimum(
            words.ctypes.data, seeds.ctypes.data, times.ctypes.data, len(words), LIMIT
        )
        fields = times.view(np.uint8).reshape(-1, 2).T.copy().tobytes()
        yield INDIVIDUAL, 0, coder.compress(fields + seeds.tobytes() + tail)


def pack(source, out, profile):
    out.write(HEADER.pack(b"CBO1", source.seek(0, 2)))
    source.seek(0)
    hist = Counter()
    coder = zstd.ZstdCompressor(level=3)
    while data := source.read(BLOCK):
        kind, t, payload = min(options(data, profile, coder), key=lambda e: len(e[2]))
        out.write(RECORD.pack(kind, t, len(payload)))
        out.write(payload)
        hist[f"{kind}/{t}"] += 1
    return hist


def unpack(src, out):
    magic, left = HEADER.unpack(src.read(HEADER.size))
    if magic != b"CBO1":
        raise ValueError("Invalid orbit archive")
    decoder = zstd.ZstdDecompressor()
    while left:
        size = min(left, BLOCK)
        n = size // 8
        kind, t, length = RECORD.unpack(src.read(RECORD.size))
        if kind > STORED or t > LIMIT or (kind != SHARED and t) or length > size:
            raise ValueError("Invalid orbit descriptor")
        payload = src.read(length)
        if len(payload) != length:
            raise ValueError("Truncated page")
        raw = (
            payload
            if kind == STORED
            else decoder.decompress(payload, max_output_size=size + 2 * n)
        )
        if len(raw) != size + (2 * n if kind == INDIVIDUAL else 0):
            raise ValueError("Unexpected page length")
        if kind in (SHARED, INDIVIDUAL):
            times = None
            if kind == INDIVIDUAL:
                times = (
                    np.frombuffer(raw[: 2 * n], np.uint8)
                    .reshape(2, n)
                    .T.copy()
                    .ravel()
                    .view("<u2")
                )
                if np.any(times > LIMIT):
                    raise ValueError("Invalid per-matrix step")
                raw = raw[2 * n :]
            words = np.frombuffer(raw[: 8 * n], "<u8").copy()
            evolve(words, t, times)
            raw = words.tobytes() + raw[8 * n :]
        out.write(raw)
        left -= size
    if src.read(1):
        raise ValueError("Unexpected trailing data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("op", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.source.open("rb") as src, a.dest.open("xb") as out:
        if a.op == "encode":
            print(json.dumps(pack(src, out, a.profile)))
        else:
            unpack(src, out)
