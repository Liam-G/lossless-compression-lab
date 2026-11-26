"""Try reversible 3D predecessors before exact GF(2) panel factorization."""

import argparse
from collections import Counter
import ctypes as ct
from functools import cache
from pathlib import Path
import struct
import zlib

import numpy as np

SLAB = 8192
HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BBH")
PROFILES = ("direct", "orbit", "rank", "combined")
STEPS = (1, 2, 4, 7)


@cache
def native():
    lib = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/evolve.so"))
    lib.evolve.argtypes = [
        ct.POINTER(ct.c_uint8),
        ct.c_size_t,
        ct.c_size_t,
        ct.c_size_t,
        ct.c_uint,
        ct.c_uint,
    ]
    lib.evolve.restype = ct.c_int
    return lib


def advance(state, rule, reverse):
    """Six native parity half-steps on open x, y and z axes; 16 × 64 bits per plane."""
    arr = (ct.c_uint8 * len(state)).from_buffer(state)
    if len(state) % 128 or native().evolve(
        arr, len(state) // 128, 16, 64, rule, int(reverse)
    ):
        raise ValueError("Invalid tensor geometry")


def panels(raw):
    return (
        np.frombuffer(raw, np.uint8)
        .reshape(-1, 16, 8)
        .transpose(0, 2, 1)
        .reshape(-1, 16)
    )


def restore_panels(rows):
    return rows.reshape(-1, 8, 16).transpose(0, 2, 1).tobytes()


def factor(raw):
    rows = panels(raw)
    ix = np.arange(len(rows))
    a = rows[ix, (rows != 0).argmax(axis=1)][:, None]
    other = (rows != 0) & (rows != a)
    b = np.where(other.any(axis=1), rows[ix, other.argmax(axis=1)], 0)[:, None]
    mixed = a ^ b
    literal = ((rows != 0) & (rows != a) & (rows != b) & (rows != mixed)).any(axis=1)
    ranks = np.where(
        literal, 3, (a[:, 0] != 0).astype(np.uint8) + (b[:, 0] != 0)
    ).astype(np.uint8)
    fields = [ranks.tobytes()]
    for rank in (1, 2):
        select = ranks == rank
        basis = a[select]
        group = rows[select]
        first = group == basis
        if rank == 2:
            both = group == mixed[select]
            first |= both
            second = (group == b[select]) | both
        fields.extend([basis.tobytes(), np.packbits(first, axis=1).tobytes()])
        if rank == 2:
            fields.extend([b[select].tobytes(), np.packbits(second, axis=1).tobytes()])
    fields.append(rows[literal].tobytes())
    return b"".join(fields)


def unfactor(data, size):
    n = size // 16
    stream = memoryview(data)
    pos = 0

    def array(count):
        nonlocal pos
        result = np.frombuffer(stream[pos : pos + count], np.uint8)
        pos += count
        if result.size != count:
            raise ValueError("Truncated panel lane")
        return result

    ranks = array(n)
    if np.any(ranks > 3):
        raise ValueError("Invalid panel tag")
    rows = np.zeros((n, 16), dtype=np.uint8)
    for rank in (1, 2):
        select = ranks == rank
        count = int(select.sum())

        def expand():
            atom = array(count)[:, None]
            coords = np.unpackbits(array(2 * count).reshape(count, 2), axis=1)
            return atom * coords

        group = expand()
        if rank == 2:
            group ^= expand()
        rows[select] = group
    count = int((ranks == 3).sum())
    rows[ranks == 3] = array(count * 16).reshape(count, 16)
    if pos != len(data):
        raise ValueError("Trailing panel data")
    return restore_panels(rows)


def options(block, profile):
    def candidates(state, rule, step):
        yield 0, rule, step, zlib.compress(state, 6)
        if profile in ("rank", "combined") and len(state) % 128 == 0:
            yield 1, rule, step, zlib.compress(factor(state), 6)

    yield from candidates(block, 0, 0)
    if profile in ("orbit", "combined") and len(block) % 128 == 0:
        for rule in (0, 1):
            state = bytearray(block)
            for t in range(1, max(STEPS) + 1):
                advance(state, rule, True)
                if t in STEPS:
                    yield from candidates(state, rule, t)


def encode(data, profile):
    out = bytearray(HEADER.pack(b"TGF1", len(data)))
    for start in range(0, len(data), SLAB):
        kind, rule, step, payload = min(
            options(data[start : start + SLAB], profile), key=lambda c: len(c[3])
        )
        out.extend(RECORD.pack(kind + 2 * rule, step, len(payload)))
        out.extend(payload)
    return bytes(out)


def decode(archive):
    magic, size = HEADER.unpack_from(archive)
    if magic != b"TGF1":
        raise ValueError("Invalid tensor archive")
    pos = HEADER.size
    out = bytearray()
    modes = Counter()
    while len(out) < size:
        flags, t, n = RECORD.unpack_from(archive, pos)
        pos += RECORD.size
        if flags > 3 or t not in (0, *STEPS) or pos + n > len(archive):
            raise ValueError("Invalid tensor record")
        raw = zlib.decompress(archive[pos : pos + n])
        pos += n
        width = min(size - len(out), SLAB)
        if flags & 1:
            raw = unfactor(raw, width)
        if len(raw) != width:
            raise ValueError("Invalid restored length")
        state = bytearray(raw)
        for _ in range(t):
            advance(state, flags >> 1, False)
        modes[f"rule{flags >> 1}-step{t}-" + ("rank" if flags & 1 else "raw")] += 1
        out.extend(state)
    if pos != len(archive):
        raise ValueError("Trailing archive bytes")
    return bytes(out), dict(modes)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["encode", "decode"])
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="combined")
    a = p.parse_args()
    raw = a.source.read_bytes()
    result = encode(raw, a.profile) if a.mode == "encode" else decode(raw)[0]
    with a.output.open("xb") as f:
        f.write(result)
