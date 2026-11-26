"""Reverse a four-axis cellular field before approximate binary matrix factorization."""

import argparse
from collections import Counter
import ctypes as ct
from functools import cache
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

BLOCK = 1 << 16
PLANE = 1024  # eight z positions, sixteen rows and sixty-four packed x bits
STEPS = (1, 2, 4, 8, 16)
PROFILES = ("direct", "orbit", "rank", "equivalent", "joint")
HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BBI")
PLAIN, FACTORED, STORED = range(3)


@cache
def library():
    lib = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/panel-factors.so"))
    lib.factor_panels.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t, ct.c_bool]
    lib.restore_panels.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
    lib.factor_panels.restype = lib.restore_panels.restype = None
    return lib


def matrix(data, equivalent=False, inverse=False):
    width = 22 if inverse else 16
    rows = np.frombuffer(data, np.uint8)
    count, tail = divmod(len(rows), width)
    if tail:
        raise ValueError("Incomplete factor panel")
    out = np.empty(count * (16 if inverse else 22), np.uint8)
    args = (rows.ctypes.data, out.ctypes.data, count)
    if inverse:
        library().restore_panels(*args)
    else:
        library().factor_panels(*args, equivalent)
    return out.tobytes()


def half(grid, axis, parity, nonlinear):
    # Coordinates on the other parity remain fixed throughout the half-step.
    if axis == 3:
        left = grid << 1
        left[..., 1:] |= grid[..., :-1] >> 7
        if nonlinear:
            right = grid >> 1
            right[..., :-1] |= grid[..., 1:] << 7
            left &= right
        grid ^= left & (0xAA if parity else 0x55)
    else:
        rows = np.swapaxes(grid, axis, 0)
        if parity:
            target = rows[1::2]
            left = rows[0 : 2 * len(target) : 2]
            if nonlinear:
                n = len(rows[2::2])
                target[:n] ^= left[:n] & rows[2::2]
            else:
                target ^= left
        else:
            target = rows[2::2]
            previous = rows[1 : 2 * len(target) : 2]
            if nonlinear:
                n = len(rows[3::2])
                target[:n] ^= previous[:n] & rows[3::2]
            else:
                target ^= previous


def evolve(grid, rule, inverse):
    schedule = [(axis, parity) for axis in range(4) for parity in range(2)]
    for axis, parity in reversed(schedule) if inverse else schedule:
        half(grid, axis, parity, rule == 1)


def predecessors(block):
    for rule in (0, 1):
        grid = np.frombuffer(block, np.uint8).copy().reshape(-1, 8, 16, 8)
        for t in range(1, max(STEPS) + 1):
            evolve(grid, rule, True)
            if t in STEPS:
                yield rule, t, grid.tobytes()


def best_block(block, profile, coder):
    best = (len(block), STORED, 0, 0, block)

    def consider(kind, rule, t, data):
        nonlocal best
        payload = coder.compress(data)
        if len(payload) < best[0]:
            best = len(payload), kind, rule, t, payload

    consider(PLAIN, 0, 0, block)
    use_rank = profile in ("rank", "equivalent", "joint") and len(block) % 16 == 0
    use_orbit = profile in ("orbit", "joint") and len(block) % PLANE == 0

    def try_factors(rule, t, state):
        consider(FACTORED, rule, t, matrix(state))
        if profile in ("equivalent", "joint"):
            consider(FACTORED, rule, t, matrix(state, True))

    if use_rank:
        try_factors(0, 0, block)
    if use_orbit:
        shortlist = []
        for rule, t, state in predecessors(block):
            consider(PLAIN, rule, t, state)
            if use_rank:
                # Sixteen complete panels from each of sixteen dispersed strips.
                rows = np.frombuffer(state, np.uint8).reshape(-1, 256)
                sample = rows[
                    np.linspace(0, len(rows) - 1, min(16, len(rows)), dtype=int)
                ].tobytes()
                score = len(coder.compress(matrix(sample)))
                shortlist.append((score, rule, t, state))
        for _, rule, t, state in sorted(shortlist)[:2]:
            try_factors(rule, t, state)
    return best


def pack(src, out, profile):
    out.write(HEADER.pack(b"F4D1", src.seek(0, 2)))
    src.seek(0)
    coder = zstd.ZstdCompressor(level=3)
    counts = Counter()
    while block := src.read(BLOCK):
        length, kind, rule, t, payload = best_block(block, profile, coder)
        out.write(RECORD.pack(kind | rule << 2, t, length))
        out.write(payload)
        counts[f"{kind}/{rule}/{t}"] += 1
    return counts


def unpack(src, out):
    magic, left = HEADER.unpack(src.read(HEADER.size))
    if magic != b"F4D1":
        raise ValueError("Invalid spacetime factor header")
    while left:
        size = min(BLOCK, left)
        flags, t, length = RECORD.unpack(src.read(RECORD.size))
        kind, rule = flags & 3, flags >> 2
        if kind > STORED or rule > 1 or t not in (0, *STEPS) or length > size:
            raise ValueError("Invalid spacetime record")
        payload = src.read(length)
        if len(payload) != length:
            raise ValueError("Truncated payload")
        if kind != STORED:
            payload = zstd.ZstdDecompressor().decompress(payload)
            if kind == FACTORED:
                payload = matrix(payload, inverse=True)
        if len(payload) != size:
            raise ValueError("Invalid factor length")
        if t:
            grid = np.frombuffer(payload, np.uint8).copy().reshape(-1, 8, 16, 8)
            for _ in range(t):
                evolve(grid, rule, False)
            payload = grid.tobytes()
        out.write(payload)
        left -= size
    if src.read(1):
        raise ValueError("Unexpected trailing data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.input.open("rb") as src, a.output.open("xb") as out:
        if a.mode == "encode":
            print(json.dumps(pack(src, out, a.profile)))
        else:
            unpack(src, out)
