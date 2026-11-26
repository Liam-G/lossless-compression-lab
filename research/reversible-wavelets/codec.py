"""Reversible colour and parity lifting on RGB tiles with a common Zstandard backend."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import numpy as np
import zstandard as zstd

TILE = 256
HEADER = struct.Struct(">4sII")
RECORD = struct.Struct(">BI")
DIRECT = 0
STORED = 255
PROFILES = ("direct", "color", "lifting", "joint")
DEPTHS = (1, 2, 3)


def ppm_header(w, h):
    return f"P6\n{w} {h}\n255\n".encode("ascii")


def read_ppm(f):
    magic = f.readline(4)
    shape = f.readline(80)
    maxval = f.readline(5)
    w, h = map(int, shape.split())
    if min(w, h) < 1 or magic + shape + maxval != ppm_header(w, h):
        raise ValueError("Expected canonical 8-bit binary RGB PPM")
    raw = f.read()
    if len(raw) != 3 * w * h:
        raise ValueError("Invalid PPM length")
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def color(a, reverse=False):
    x, y, z = (a[..., i] for i in range(3))
    if reverse:
        green = x - ((y + z) >> 2)
        return np.stack((green + y, green, green + z), axis=-1)
    dr = x - y
    db = z - y
    return np.stack((y + ((dr + db) >> 2), dr, db), axis=-1)


def axis_pass(matrix, axis, reverse):
    data = np.swapaxes(matrix, axis, 0)
    size = len(data)
    if size <= 1:
        return
    ne = (size + 1) // 2
    if reverse:
        even, odd = data[:ne].copy(), data[ne:].copy()
    else:
        even, odd = data[::2].copy(), data[1::2].copy()
    nh = len(odd)

    def adjacent_high():
        left = np.concatenate((odd[:1], odd))[:ne]
        right = odd[np.minimum(np.arange(ne), nh - 1)]
        return (left + right + 2) >> 2

    def adjacent_low():
        return (even[:nh] + even[np.minimum(np.arange(nh) + 1, ne - 1)]) >> 1

    if reverse:
        even -= adjacent_high()
        odd += adjacent_low()
        data[::2] = even
        data[1::2] = odd
    else:
        odd -= adjacent_low()
        even += adjacent_high()
        data[:ne] = even
        data[ne:] = odd


def geometry(shape, depth):
    h, w = shape[:2]
    rectangles = []
    for _ in range(depth):
        rectangles.append((h, w))
        h, w = (h + 1) // 2, (w + 1) // 2
    return rectangles


def lift(a, depth, reverse):
    boxes = geometry(a.shape, depth)
    for h, w in reversed(boxes) if reverse else boxes:
        region = a[:h, :w]
        for axis in (0, 1) if reverse else (1, 0):
            axis_pass(region, axis, reverse)


def bands(a, depth):
    h, w = a.shape[:2]
    boxes = geometry(a.shape, depth)
    for h, w in boxes:
        y, x = (h + 1) // 2, (w + 1) // 2
        yield a[:y, x:w]
        yield a[y:h, :x]
        yield a[y:h, x:w]
        h, w = y, x
    yield a[:h, :w]


def coefficients(a, depth):
    fields = []
    for band in bands(a, depth):
        v = band.transpose(2, 0, 1).ravel()
        # All intermediate ranges for the three levels fit in signed 16 bits.
        u = ((v << 1) ^ (v >> 31)).astype("<u2")
        fields.extend(
            [u.astype(np.uint8).tobytes(), (u >> 8).astype(np.uint8).tobytes()]
        )
    return b"".join(fields)


def restore(raw, shape, depth, chromatic):
    a = np.empty(shape, np.int32)
    pos = 0
    for band in bands(a, depth):
        n = band.size
        lo = np.frombuffer(raw, dtype=np.uint8, count=n, offset=pos).astype(np.int32)
        hi = np.frombuffer(raw, dtype=np.uint8, count=n, offset=pos + n)
        pos += 2 * n
        u = lo + (hi.astype(np.int32) << 8)
        v = (u >> 1) ^ -(u & 1)
        h, w, _ = band.shape
        band[:] = v.reshape(3, h, w).transpose(1, 2, 0)
    if pos != len(raw):
        raise ValueError("Trailing coefficient data")
    lift(a, depth, True)
    if chromatic:
        a = color(a, True)
    if a.min() < 0 or a.max() > 255:
        raise ValueError("Invalid reconstructed RGB")
    return a.astype(np.uint8)


def candidates(tile, profile, coder):
    data = tile.tobytes()
    yield STORED, data
    yield DIRECT, coder.compress(data)
    depths = (0, *DEPTHS) if profile in ("lifting", "joint") else (0,)
    for chromatic in [False, True] if profile in ("color", "joint") else [False]:
        base = tile.astype(np.int32)
        if chromatic:
            base = color(base)
        for depth in depths:
            if not depth and not chromatic:
                continue
            a = base.copy()
            lift(a, depth, False)
            yield 1 + 2 * depth + int(chromatic), coder.compress(coefficients(a, depth))


def tiles(h, w):
    for y in range(0, h, TILE):
        for x in range(0, w, TILE):
            yield slice(y, min(y + TILE, h)), slice(x, min(x + TILE, w))


def pack(src, out, profile):
    a = read_ppm(src)
    h, w, _ = a.shape
    out.write(HEADER.pack(b"RWL1", w, h))
    coder = zstd.ZstdCompressor(level=3)
    hist = Counter()
    for y, x in tiles(h, w):
        mode, payload = min(
            candidates(a[y, x], profile, coder), key=lambda c: len(c[1])
        )
        out.write(RECORD.pack(mode, len(payload)))
        out.write(payload)
        hist[str(mode)] += 1
    return hist


def unpack(src, out):
    magic, w, h = HEADER.unpack(src.read(HEADER.size))
    if magic != b"RWL1" or min(h, w) < 1:
        raise ValueError("Invalid wavelet header")
    result = np.empty((h, w, 3), np.uint8)
    decoder = zstd.ZstdDecompressor()
    for y, x in tiles(h, w):
        mode, size = RECORD.unpack(src.read(RECORD.size))
        tile = result[y, x]
        if size > tile.size:
            raise ValueError("Invalid tile length")
        payload = src.read(size)
        if len(payload) != size:
            raise ValueError("Truncated tile")
        if mode in (STORED, DIRECT):
            raw = (
                payload
                if mode == STORED
                else decoder.decompress(payload, max_output_size=tile.size)
            )
            tile[:] = np.frombuffer(raw, np.uint8).reshape(tile.shape)
        else:
            depth, chromatic = divmod(mode - 1, 2)
            if depth > max(DEPTHS):
                raise ValueError("Unknown wavelet depth")
            raw = decoder.decompress(payload, max_output_size=2 * tile.size)
            tile[:] = restore(raw, tile.shape, depth, chromatic)
    if src.read(1):
        raise ValueError("Unexpected trailing data")
    out.write(ppm_header(w, h))
    out.write(result.tobytes())


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
