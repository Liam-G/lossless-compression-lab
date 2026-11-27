"""Lossless packed-bitmap predictors, quadrant occupancy and repeated 8x8 leaves."""

import argparse
from collections import Counter
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

ROW = 216  # 1,728 pixels, most significant bit first
HEIGHT = 256
BLOCK = ROW * HEIGHT
HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BI")
BASE_MODES = tuple(
    f"{p}-{layout}"
    for p in ("direct", "xor", "orbit")
    for layout in ("flat", "tree", "book")
)
MODES = (
    *BASE_MODES,
    *(
        f"{p}-{form}"
        for p in ("direct", "xor", "orbit")
        for form in ("planes", "hot", "hotplanes")
    ),
    "rotated-book",
)
PROFILES = (*MODES, "select")


def checker(grid, forward, rotated=False):
    """Two parity steps with zero exterior pixels and no wrap between strips."""
    state = grid.copy()
    even = np.where(np.arange(len(state)) % 2 == 0, 0xAA, 0x55).astype(np.uint8)[
        :, None
    ]
    for mask in (even, ~even) if forward else (~even, even):
        left = state >> 1
        left[:, 1:] |= state[:, :-1] << 7
        right = state << 1
        right[:, :-1] |= state[:, 1:] >> 7
        vertical = np.zeros_like(state)
        if rotated:
            vertical[1:-1] = state[:-2] & state[2:]
            flip = vertical ^ (left | right)
        else:
            vertical[1:] |= state[:-1]
            vertical[:-1] |= state[1:]
            flip = (left & right) ^ vertical
        state ^= mask & flip
    return state


def predict(grid, mode, inverse=False):
    if mode == "direct":
        return grid
    if mode in ("orbit", "rotated"):
        return checker(grid, forward=inverse, rotated=mode == "rotated")
    if inverse:
        return np.bitwise_xor.accumulate(grid, axis=0)
    result = grid.copy()
    result[1:] ^= grid[:-1]
    return result


def children(grid):
    h, w = grid.shape
    return (
        grid.reshape(h // 2, 2, w // 2, 2)
        .transpose(0, 2, 1, 3)
        .reshape(h // 2, w // 2, 4)
    )


def leaf_words(grid):
    return np.ascontiguousarray(grid.reshape(-1, 8, ROW).transpose(0, 2, 1)).view(
        "<u8"
    )[..., 0]


def raster(words):
    return (
        words.view(np.uint8)
        .reshape(len(words), ROW, 8)
        .transpose(0, 2, 1)
        .reshape(-1, ROW)
    )


def leaf_bytes(words, planar):
    rows = words.astype("<u8", copy=False).view(np.uint8).reshape(-1, 8)
    return (rows.T if planar else rows).tobytes()


def read_leaves(src, count, planar):
    data = take(src, 8 * count)
    if planar:
        data = np.frombuffer(data, np.uint8).reshape(8, count).T.tobytes()
    return np.frombuffer(data, "<u8")


def layout(grid, mode):
    if mode == "flat":
        return grid.tobytes()
    words = leaf_words(grid)
    leaf = words != 0
    small = children(leaf)
    middle = small.any(axis=2)
    large = children(middle)
    top = large.any(axis=2)
    header = b"".join(
        np.packbits(bits).tobytes() for bits in (top, large[top], small[middle])
    )
    payload = words[leaf]
    if mode in ("tree", "planes"):
        return header + leaf_bytes(payload, mode == "planes")
    book, ids, counts = np.unique(payload, return_inverse=True, return_counts=True)
    if mode in ("hot", "hotplanes"):
        ranked = np.argsort(-counts, kind="stable")[:255]
        chosen = ranked[counts[ranked] >= 2]
        codes = np.zeros(len(book), np.uint8)
        codes[chosen] = np.arange(1, len(chosen) + 1)
        tags = codes[ids]
        planar = mode == "hotplanes"
        return b"".join(
            (
                header,
                bytes([len(chosen)]),
                leaf_bytes(book[chosen], planar),
                tags.tobytes(),
                leaf_bytes(payload[tags == 0], planar),
            )
        )
    index_type = "u1" if len(book) <= 256 else "<u2"
    return (
        header
        + struct.pack(">H", len(book))
        + book.astype("<u8").tobytes()
        + ids.astype(index_type).tobytes()
    )


def take(src, count):
    data = src.read(count)
    if len(data) != count:
        raise ValueError("Truncated bitmap stream")
    return data


def bits(src, n):
    packed = np.frombuffer(take(src, (n + 7) // 8), np.uint8)
    flat = np.unpackbits(packed)
    if flat[n:].any():
        raise ValueError("Nonzero mask padding")
    return flat[:n].astype(bool)


def unlayout(body, h, mode):
    if mode == "flat":
        if len(body) != h * ROW:
            raise ValueError("Incorrect raster size")
        return np.frombuffer(body, np.uint8).reshape(h, ROW)
    src = BytesIO(body)
    shape = h // 32, ROW // 4
    active = bits(src, shape[0] * shape[1]).reshape(shape)
    for _ in range(2):
        y, x = active.shape
        groups = np.zeros((y, x, 4), bool)
        occupied = bits(src, 4 * int(active.sum())).reshape(-1, 4)
        if not occupied.any(axis=1).all():
            raise ValueError("Empty occupied quadrant")
        groups[active] = occupied
        active = groups.reshape(y, x, 2, 2).transpose(0, 2, 1, 3).reshape(y * 2, x * 2)
    count = int(active.sum())
    if mode in ("tree", "planes"):
        values = read_leaves(src, count, mode == "planes")
    elif mode in ("hot", "hotplanes"):
        planar = mode == "hotplanes"
        entries = take(src, 1)[0]
        book = read_leaves(src, entries, planar)
        tags = np.frombuffer(take(src, count), np.uint8)
        known = tags != 0
        if count and int(tags.max()) > entries:
            raise ValueError("Unknown frequent bitmap leaf")
        values = np.empty(count, "<u8")
        values[known] = book[tags[known] - 1]
        values[~known] = read_leaves(src, int((~known).sum()), planar)
    else:
        (entries,) = struct.unpack(">H", take(src, 2))
        if entries > count:
            raise ValueError("Excess bitmap dictionary entries")
        book = np.frombuffer(take(src, 8 * entries), "<u8")
        width = 1 if entries <= 256 else 2
        ids = np.frombuffer(take(src, width * count), "u1" if width == 1 else "<u2")
        if count and int(ids.max()) >= entries:
            raise ValueError("Unknown bitmap leaf")
        values = book[ids]
    if np.any(values == 0) or src.read(1):
        raise ValueError("Invalid bitmap leaves or trailing bytes")
    words = np.zeros(active.shape, "<u8")
    words[active] = values
    return raster(words)


def padded_height(n):
    return 32 * ((n + 32 * ROW - 1) // (32 * ROW))


def strip(raw):
    h = padded_height(len(raw))
    return np.frombuffer(raw.ljust(h * ROW, b"\0"), np.uint8).reshape(h, ROW)


def inspect(src):
    stats = {name: Counter() for name in ("direct", "xor", "orbit", "rotated")}
    digest = hashlib.sha256()
    size = 0
    while raw := src.read(BLOCK):
        size += len(raw)
        digest.update(raw)
        grid = strip(raw)
        for name, totals in stats.items():
            words = leaf_words(predict(grid, name))
            occupied = words[words != 0]
            _, counts = np.unique(occupied, return_counts=True)
            frequent = np.sort(counts[counts >= 2])[-255:]
            totals.update(
                tiles=words.size,
                occupied=len(occupied),
                distinct=len(counts),
                frequent_occurrences=int(frequent.sum()),
                strips=1,
            )
    return dict(bytes=size, sha256=digest.hexdigest(), predictors=stats)


def encode(src, dst, profile):
    size = src.seek(0, 2)
    src.seek(0)
    dst.write(HEADER.pack(b"CBP1", size))
    choices = Counter()
    cost = zstd.ZstdCompressor(level=3)
    modes = BASE_MODES if profile == "select" else (profile,)
    while raw := src.read(BLOCK):
        grid = strip(raw)
        grids = {}
        best = None
        for mode in modes:
            predictor, form = mode.split("-")
            if predictor not in grids:
                grids[predictor] = predict(grid, predictor)
            body = layout(grids[predictor], form)
            price = len(cost.compress(body)) if len(modes) > 1 else len(body)
            if best is None or price < best[0]:
                best = price, mode, body
        _, mode, body = best
        dst.write(RECORD.pack(MODES.index(mode), len(body)))
        dst.write(body)
        choices[mode] += 1
    return dict(choices)


def decode(src, dst):
    tag, remaining = HEADER.unpack(take(src, HEADER.size))
    if tag != b"CBP1":
        raise ValueError("Invalid bitmap stream")
    while remaining:
        n = min(BLOCK, remaining)
        h = padded_height(n)
        mode, length = RECORD.unpack(take(src, RECORD.size))
        if mode >= len(MODES) or length > 2 * h * ROW:
            raise ValueError("Invalid bitmap strip")
        predictor, form = MODES[mode].split("-")
        grid = unlayout(take(src, length), h, form)
        raw = predict(grid, predictor, inverse=True).tobytes()
        if any(raw[n:]):
            raise ValueError("Nonzero raster padding")
        dst.write(raw[:n])
        remaining -= n
    if src.read(1):
        raise ValueError("Trailing bitmap records")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "action", choices=("encode", "decode", "prepare", "restore", "inspect")
    )
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="select")
    a = p.parse_args()
    with a.source.open("rb") as src, a.output.open("xb") as dst:
        if a.action == "inspect":
            dst.write((json.dumps(inspect(src), sort_keys=True) + "\n").encode())
        elif a.action == "encode":
            prepared = BytesIO()
            choices = encode(src, prepared, a.profile)
            dst.write(
                b"CBZ1" + zstd.ZstdCompressor(level=3).compress(prepared.getbuffer())
            )
            print(json.dumps(choices))
        elif a.action == "decode":
            if take(src, 4) != b"CBZ1":
                raise ValueError("Invalid bitmap archive")
            with zstd.ZstdDecompressor().stream_reader(src) as stream:
                decode(stream, dst)
        elif a.action == "prepare":
            print(json.dumps(encode(src, dst, a.profile)))
        else:
            decode(src, dst)
