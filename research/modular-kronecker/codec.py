"""Reverse a byte-valued checkerboard orbit and fit a Kronecker product modulo 256."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

HEAD = struct.Struct(">4sQ")
BANK = struct.Struct(">BBII")
BLOCK = 256 * 1024
Y, X = np.indices((16, 16))
MASK = (Y + X) % 2
INVERSE = np.array([pow(i, -1, 256) if i % 2 else 0 for i in range(256)], np.uint8)


TRAILING = np.array([8] + [(i & -i).bit_length() - 1 for i in range(1, 256)], np.uint8)
PROFILES = (
    "direct",
    "factor",
    "orbit",
    "joint",
    "adaptive",
    "adaptive-joint",
    "valuation",
    "valuation-joint",
)


def step(grid, inverse=False):
    for parity in (1, 0) if inverse else (0, 1):
        neighbors = np.roll(grid, 1, 1) + np.roll(grid, -1, 2)
        np.add(neighbors, np.roll(grid, -1, 1) * np.uint8(3), out=neighbors)
        update = np.subtract if inverse else np.add
        update(grid, neighbors, out=grid, where=MASK == parity)


def factors_to_grid(a, b):
    products = a[:, :, None] * b[:, None, :]
    return products.reshape(-1, 4, 4, 4, 4).transpose(0, 1, 3, 2, 4).reshape(-1, 16, 16)


def split(grid, flexible=False, valuation=False):
    panels = grid.reshape(-1, 4, 4, 4, 4).transpose(0, 1, 3, 2, 4).reshape(-1, 16, 16)
    # Normalize the factor at (0,0) to one when that pivot is invertible.
    a = panels[:, :, 0]
    b = panels[:, 0, :] * INVERSE[a[:, 0], None]
    if flexible or valuation:
        # A and B carry the chosen factors, so the decoder never needs a pivot index.
        reduced = panels
        if valuation:
            common = TRAILING[np.bitwise_or.reduce(panels.reshape(-1, 256), axis=1)]
            reduced = panels >> common[:, None, None]
        pivot = (reduced.reshape(-1, 256) & 1).argmax(axis=1)
        batch = np.arange(len(panels))
        row, column = np.divmod(pivot, 16)
        a = panels[batch, :, column]
        b = reduced[batch, row, :] * INVERSE[reduced[batch, row, column], None]
    residual = grid - factors_to_grid(a, b)
    return a.T.tobytes() + b.T.tobytes() + residual.tobytes()


def join(data, count):
    n = count * 16
    if len(data) != count * 288:
        raise ValueError("Incorrect factor payload")
    a = np.frombuffer(data[:n], np.uint8).reshape(16, count).T
    b = np.frombuffer(data[n : 2 * n], np.uint8).reshape(16, count).T
    residual = np.frombuffer(data[2 * n :], np.uint8).reshape(count, 16, 16)
    return factors_to_grid(a, b) + residual


def encode(source, dest, profile):
    size = source.stat().st_size
    coder = zstd.ZstdCompressor(level=5)
    selections = Counter()
    with source.open("rb") as src, dest.open("xb") as out:
        out.write(HEAD.pack(b"MKR1", size))
        while raw := src.read(BLOCK):
            best = min(
                [(0, 0, raw), (1, 0, coder.compress(raw))],
                key=lambda item: len(item[2]),
            )
            count = len(raw) // 256
            if count:
                grid = (
                    np.frombuffer(raw[: count * 256], np.uint8)
                    .reshape(count, 16, 16)
                    .copy()
                )
                suffix = raw[count * 256 :]
                times = (
                    (0, 1, 2, 4)
                    if profile
                    in ("orbit", "joint", "adaptive-joint", "valuation-joint")
                    else (0,)
                )
                clock = 0
                for t in times:
                    while clock < t:
                        step(grid, True)
                        clock += 1
                    if t:
                        body = coder.compress(grid.tobytes() + suffix)
                        if len(body) < len(best[2]):
                            best = (2, t, body)
                    if profile not in ("direct", "orbit"):
                        body = coder.compress(
                            split(
                                grid,
                                profile.startswith("adaptive"),
                                profile.startswith("valuation"),
                            )
                            + suffix
                        )
                        if len(body) < len(best[2]):
                            best = (3, t, body)
            mode, time, body = best
            selections[f"{mode}/{time}"] += 1
            out.write(BANK.pack(mode, time, len(raw), len(body)))
            out.write(body)
    return dict(selections)


def read_exact(src, count):
    data = src.read(count)
    if len(data) != count:
        raise ValueError("Truncated modular panel stream")
    return data


def decode(source, dest):
    with source.open("rb") as src, dest.open("xb") as out:
        magic, remaining = HEAD.unpack(read_exact(src, HEAD.size))
        if magic != b"MKR1":
            raise ValueError("Invalid panel format")
        while remaining:
            mode, time, size, length = BANK.unpack(read_exact(src, BANK.size))
            if (
                mode > 3
                or time not in (0, 1, 2, 4)
                or (mode < 2 and time)
                or size != min(remaining, BLOCK)
            ):
                raise ValueError("Invalid panel header")
            count, tail = divmod(size, 256)
            body = read_exact(src, length)
            expected = size + (32 * count if mode == 3 else 0)
            data = (
                body
                if mode == 0
                else zstd.ZstdDecompressor().decompress(body, max_output_size=expected)
            )
            if len(data) != expected:
                raise ValueError("Incorrect panel length")
            if mode >= 2:
                body = data[: expected - tail]
                grid = (
                    join(body, count)
                    if mode == 3
                    else np.frombuffer(body, np.uint8).reshape(count, 16, 16).copy()
                )
                for _ in range(time):
                    step(grid)
                data = grid.tobytes() + data[expected - tail :]
            out.write(data)
            remaining -= size
        if src.read(1):
            raise ValueError("Trailing panel data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument(
        "--profile",
        choices=PROFILES,
        default="joint",
    )
    a = p.parse_args()
    if a.mode == "encode":
        print(json.dumps(encode(a.source, a.dest, a.profile)))
    else:
        decode(a.source, a.dest)
