"""Learn spatial transition truth tables and an invertible binary basis for their residuals."""

import argparse
from collections import Counter
import ctypes as ct
from functools import cache
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

HEADER = struct.Struct(">4sIIQ")
RECORD = struct.Struct(">BBI")
FRAMES = 16
PROFILES = ("direct", "planes", "temporal", "rule", "basis", "joint", "coupled")
LITERALS = 255
CODES = np.arange(256, dtype=np.uint8)
PARITY = np.array([i.bit_count() & 1 for i in range(256)], np.uint8)


@cache
def library():
    api = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/cellular-rules.so"))
    ptr = ct.c_void_p
    api.fit.argtypes = [ptr, ptr, ct.c_int, ct.c_int, ct.c_int, ct.c_bool]
    api.translate.argtypes = [
        ptr,
        ptr,
        ptr,
        ct.c_int,
        ct.c_int,
        ct.c_int,
        ct.c_bool,
        ct.c_bool,
    ]
    api.fit.restype = api.translate.restype = None
    return api


def fit(grid, second):
    t, h, w = grid.shape
    rules = np.zeros(8, np.uint32)
    library().fit(grid.ctypes.data, rules.ctypes.data, w, h, t, second)
    return rules


def transform(grid, rules, second, reverse=False):
    t, h, w = grid.shape
    out = np.empty_like(grid)
    library().translate(
        grid.ctypes.data, out.ctypes.data, rules.ctypes.data, w, h, t, second, reverse
    )
    return out


def learn_basis(values):
    sample = values.ravel()[:: max(1, values.size // 65536)]
    histogram = np.bincount(sample, minlength=256)
    masks = []
    for bit in range(8):
        possible = np.arange(1 << bit, dtype=np.uint8) | (1 << bit)
        indicator = PARITY[possible[:, None] & CODES[None, :]]
        count = indicator.astype(np.int64) @ histogram
        score = np.minimum(count, len(sample) - count)
        masks.append(int(possible[np.argmin(score)]))
    return bytes(masks)


def coupled_fit(grid, second):
    """Fit each table conditional on parity of already modeled residual planes."""
    frames, h, w = grid.shape
    rules = np.zeros(8, np.uint32)
    masks = bytearray()
    if frames == 1:
        return rules, bytes(1 << b for b in range(8))
    # A fixed sampling budget makes the feasible truth tables and basis search cheap.
    rng = np.random.default_rng(611)
    count = min(65536, (frames - 1) * h * w)
    at = rng.choice((frames - 1) * h * w, count, replace=False)
    t, within = np.divmod(at, h * w)
    y, x = np.divmod(within, w)
    neighbors = (
        grid[t, y, x],
        np.where(x, grid[t, y, np.maximum(0, x - 1)], 0),
        np.where(x + 1 < w, grid[t, y, np.minimum(w - 1, x + 1)], 0),
        np.where(y, grid[t, np.maximum(0, y - 1), x], 0),
        np.where(y + 1 < h, grid[t, np.minimum(h - 1, y + 1), x], 0),
    )
    targets = grid[t + 1, y, x]
    if second:
        targets = targets ^ np.where(t, grid[np.maximum(0, t - 1), y, x], 0)
    residual_lower = np.zeros(count, np.uint8)
    for bit in range(8):
        cardinality = 1 << bit
        context = sum(
            (((v >> bit) & 1).astype(np.int64) << j) for j, v in enumerate(neighbors)
        )
        observed = (targets >> bit) & 1
        address = context * cardinality + residual_lower
        differences = (
            np.bincount(
                address,
                weights=1 - 2 * observed.astype(np.int32),
                minlength=32 * cardinality,
            )
            .astype(np.int64)
            .reshape(32, cardinality)
        )
        totals = np.bincount(context, minlength=32)
        # Walsh coefficients give (zeros - ones) for every candidate parity mask.
        step = 1
        while step < cardinality:
            groups = differences.reshape(32, -1, 2 * step)
            left = groups[:, :, :step].copy()
            right = groups[:, :, step:].copy()
            groups[:, :, :step] = left + right
            groups[:, :, step:] = left - right
            step *= 2
        regularizer = np.ceil(4 * np.sqrt(totals)).astype(np.int64)[:, None]
        flip = differences < -regularizer
        score = (np.where(flip, -differences - regularizer, differences)).sum(axis=0)
        choice = int(np.argmax(score))
        rule = sum(1 << k for k in np.flatnonzero(flip[:, choice]).tolist())
        rules[bit] = rule
        masks.append(cardinality | choice)
        residual_lower |= (observed ^ flip[context, choice].astype(np.uint8)) << bit
    return rules, bytes(masks)


def change_basis(data, masks, reverse=False):
    if len(masks) != 8 or any(m.bit_length() != b + 1 for b, m in enumerate(masks)):
        raise ValueError("Expected a triangular matrix with a unit diagonal")
    table = np.zeros(256, np.uint8)
    for b, m in enumerate(masks):
        table |= PARITY[CODES & m] << b
    if reverse:
        table = np.argsort(table).astype(np.uint8)
    return table[data]


def planes(data, reverse=False):
    a = data.ravel()
    n = len(a) // 8 * 8
    if reverse:
        field = np.unpackbits(a[:n].reshape(8, -1), axis=1)
        result = np.packbits(field.T, axis=1).ravel()
    else:
        field = np.unpackbits(a[:n, None], axis=1)
        result = np.packbits(field.T, axis=1).ravel()
    return np.concatenate((result, a[n:])).reshape(data.shape)


def encode_bank(grid, profile):
    raw = grid.tobytes()
    coder = zstd.ZstdCompressor(level=6)
    best = (len(raw), LITERALS, 0, raw)

    def offer(kind, layout, side, values):
        nonlocal best
        packed = side + coder.compress(values)
        if len(packed) < best[0]:
            best = len(packed), kind, layout, packed

    def price(kind, side, values):
        offer(kind, 0, side, values)
        if profile != "direct":
            offer(kind, 1, side, planes(values))
        if profile in ("basis", "joint", "coupled"):
            basis = learn_basis(values)
            factored = change_basis(values, basis)
            offer(kind, 2, side + basis, factored)
            offer(kind, 3, side + basis, planes(factored))

    price(0, b"", grid)
    if profile in ("temporal", "rule", "joint", "coupled"):
        delta = grid.copy()
        delta[1:] ^= grid[:-1]
        price(1, b"", delta)
    if profile in ("rule", "joint", "coupled"):
        for second in (False, True):
            rules = fit(grid, second)
            price(
                2 + second,
                rules.astype("<u4").tobytes(),
                transform(grid, rules, second),
            )
    if profile == "coupled":
        for second in (False, True):
            rules, basis = coupled_fit(grid, second)
            residual = transform(grid, rules, second)
            factored = change_basis(residual, basis)
            side = rules.astype("<u4").tobytes() + basis
            offer(2 + second, 2, side, factored)
            offer(2 + second, 3, side, planes(factored))
    return best


def pack(src, out, profile, w, h):
    size = src.seek(0, 2)
    src.seek(0)
    if min(w, h) < 1 or size % (w * h):
        raise ValueError("Expected whole frames")
    out.write(HEADER.pack(b"LCA1", w, h, size // (w * h)))
    hist = Counter()
    while raw := src.read(FRAMES * w * h):
        grid = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
        length, kind, layout, payload = encode_bank(grid, profile)
        out.write(RECORD.pack(kind, layout, length))
        out.write(payload)
        hist[f"{kind}/{layout}"] += 1
    return hist


def unpack(src, out):
    magic, w, h, remaining = HEADER.unpack(src.read(HEADER.size))
    if magic != b"LCA1" or not (w and h):
        raise ValueError("Invalid cellular grid")
    while remaining:
        t = min(FRAMES, remaining)
        size = t * h * w
        kind, layout, n = RECORD.unpack(src.read(RECORD.size))
        if (kind > 3 and kind != LITERALS) or layout > 3 or n > size:
            raise ValueError("Invalid cellular record")
        body = src.read(n)
        if len(body) != n:
            raise ValueError("Truncated cellular record")
        if kind == LITERALS:
            if n != size or layout:
                raise ValueError("Invalid literal bank")
            out.write(body)
        else:
            if kind >= 2:
                rules = np.frombuffer(body[:32], "<u4").astype(np.uint32)
                body = body[32:]
            if layout & 2:
                basis = body[:8]
                body = body[8:]
            residual = zstd.ZstdDecompressor().decompress(body, max_output_size=size)
            grid = np.frombuffer(residual, np.uint8).reshape(t, h, w)
            if layout & 1:
                grid = planes(grid, True)
            if layout & 2:
                grid = change_basis(grid, basis, True)
            if kind == 1:
                grid = np.bitwise_xor.accumulate(grid, axis=0)
            elif kind >= 2:
                grid = transform(grid, rules, kind == 3, True)
            out.write(grid.tobytes())
        remaining -= t
    if src.read(1):
        raise ValueError("Unexpected trailing data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=360)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.source.open("rb") as src, a.output.open("xb") as out:
        if a.mode == "encode":
            print(json.dumps(pack(src, out, a.profile, a.width, a.height)))
        else:
            unpack(src, out)
