"""Lossless row-length routing, column transposition and vertical prediction on byte streams."""

import argparse
import ctypes
from functools import cache
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

BLOCK = 1 << 18
HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BI")
COUNT = struct.Struct(">I")
ROW_MODES = ("literal", "framed", "above", "delta", "columns", "joint")
LANES = {"fields": (8, 1), "positions": (1, 16), "field-positions": (8, 16)}
ROUTE_MODES = (*ROW_MODES, *LANES)
FRONT = {"prefix": 1, "field-prefix": 8}
MODES = (*ROUTE_MODES, *FRONT)
PROFILES = (*MODES, "select", "route-select")


@cache
def library():
    path = Path(__file__).resolve().parents[1] / "build/field-lanes.so"
    return ctypes.CDLL(str(path))


@cache
def router():
    function = library().field_lanes
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_int,
    ]
    function.restype = ctypes.c_int
    return function


def field_stream(data, size, mode, inverse=False):
    if not inverse and len(data) != size:
        raise ValueError("Incorrect input size for field routing")
    fields, columns = LANES[mode]
    count = fields * columns
    if inverse:
        if len(data) != size + count * 4:
            raise ValueError("Incorrect field stream length")
        lengths = np.frombuffer(data, dtype=">u4", count=count).astype(np.uint32)
        data = data[count * 4 :]
    else:
        lengths = np.zeros(count, np.uint32)
    result = np.empty(size, np.uint8)
    if router()(
        data, result.ctypes.data, size, lengths.ctypes.data, fields, columns, inverse
    ):
        raise ValueError("Inconsistent field lane lengths")
    prefix = b"" if inverse else lengths.astype(">u4").tobytes()
    return prefix + result.tobytes()


@cache
def front_router():
    function = library().front_fields
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_int,
    ]
    function.restype = ctypes.c_int64
    return function


def front_stream(data, size, mode, inverse=False):
    lanes = FRONT[mode]
    if inverse:
        if len(data) < 4 * lanes:
            raise ValueError("Missing field prefix lengths")
        lengths = np.frombuffer(data, dtype=">u4", count=lanes).astype(np.uint32)
        data = data[lanes * 4 :]
    else:
        lengths = np.zeros(lanes, np.uint32)
    result = np.empty(size if inverse else 2 * size, np.uint8)
    count = front_router()(
        data,
        len(data),
        result.ctypes.data,
        len(result),
        lengths.ctypes.data,
        lanes,
        inverse,
    )
    if count < 0:
        raise ValueError("Invalid front-coded field")
    header = b"" if inverse else lengths.astype(">u4").tobytes()
    return header + result[:count].tobytes()


def read_exact(src, n):
    data = src.read(n)
    if len(data) != n:
        raise ValueError("Truncated row stream")
    return data


def lengths_header(lengths):
    short = np.minimum(lengths, 255).astype(np.uint8)
    long = lengths[lengths >= 255].astype("<u4")
    return COUNT.pack(len(short)) + short.tobytes() + long.tobytes()


def read_lengths(src, size):
    (count,) = COUNT.unpack(read_exact(src, COUNT.size))
    if not 1 <= count <= size + 1:
        raise ValueError("Invalid row count")
    lengths = np.frombuffer(read_exact(src, count), np.uint8).astype(np.int64)
    extended = lengths == 255
    wide = np.frombuffer(read_exact(src, int(extended.sum()) * 4), "<u4")
    if np.any(wide < 255):
        raise ValueError("Noncanonical row width")
    lengths[extended] = wide
    if lengths.sum() + count - 1 != size:
        raise ValueError("Row lengths do not cover the block")
    return lengths


def transform(payload, lengths, mode, inverse=False):
    if mode == "framed":
        return payload
    values = np.frombuffer(payload, np.uint8)
    starts = lengths.cumsum() - lengths
    if mode == "above":
        result = values.copy()
        prior = result if inverse else values
        op = np.add if inverse else np.subtract
        for i in range(1, len(lengths)):
            start, prev = starts[i], starts[i - 1]
            width = min(lengths[i], lengths[i - 1])
            op(
                values[start : start + width],
                prior[prev : prev + width],
                out=result[start : start + width],
            )
            if lengths[i] > lengths[i - 1]:
                # The previous line's terminating LF is an observable byte too.
                j = start + width
                result[j] = op(values[j : j + 1], np.uint8(10))[0]
        return result.tobytes()

    transpose = mode in ("columns", "joint")
    predict = mode in ("delta", "joint")
    result = np.empty_like(values)
    order = np.argsort(lengths, kind="stable")
    widths, counts = np.unique(lengths[order], return_counts=True)
    row = cursor = 0
    for width, count in zip(widths, counts):
        ids = order[row : row + count]
        row += count
        if width == 0:
            continue
        positions = starts[ids, None] + np.arange(width)
        end = cursor + width * count
        if inverse and transpose:
            matrix = values[cursor:end].reshape(width, count).T
        else:
            matrix = values[positions]
        if predict:
            if inverse:
                matrix = np.cumsum(matrix, axis=0, dtype=np.uint8)
            else:
                # Advanced indexing above created a private copy.
                matrix[1:] -= matrix[:-1]
        if transpose and not inverse:
            result[cursor:end] = matrix.T.ravel()
        else:
            result[positions] = matrix
        cursor = end
    return result.tobytes()


def encode(source, dest, profile):
    size = source.seek(0, 2)
    source.seek(0)
    dest.write(HEADER.pack(b"RGP1", size))
    selected = Counter()
    cost = zstd.ZstdCompressor(level=3)
    candidates = {"select": ROW_MODES, "route-select": ROUTE_MODES}.get(
        profile, (profile,)
    )
    if profile not in PROFILES:
        raise ValueError(f"Unknown row profile {profile}")
    needs_rows = any(mode in ROW_MODES[1:] for mode in candidates)
    while raw := source.read(BLOCK):
        if needs_rows:
            lines = raw.split(b"\n")
            lengths = np.fromiter(map(len, lines), np.int64, count=len(lines))
            header = lengths_header(lengths)
            values = b"".join(lines)
        best_price = None
        for name in candidates:
            if name == "literal":
                body = raw
            elif name in FRONT:
                body = front_stream(raw, len(raw), name)
            elif name in LANES:
                body = field_stream(raw, len(raw), name)
            else:
                body = header + transform(values, lengths, name)
            price = len(cost.compress(body)) if len(candidates) > 1 else len(body)
            if best_price is None or price < best_price:
                best_price, chosen, packed = price, name, body
        dest.write(RECORD.pack(MODES.index(chosen), len(packed)))
        dest.write(packed)
        selected[chosen] += 1
    return dict(selected)


def decode(source, dest):
    magic, remaining = HEADER.unpack(read_exact(source, HEADER.size))
    if magic != b"RGP1":
        raise ValueError("Invalid row stream")
    while remaining:
        size = min(remaining, BLOCK)
        mode, length = RECORD.unpack(read_exact(source, RECORD.size))
        if mode >= len(MODES) or length > max(2 * size + 32, size + 512):
            raise ValueError("Invalid row block")
        body = read_exact(source, length)
        if mode == 0:
            if len(body) != size:
                raise ValueError("Incorrect literal size")
            dest.write(body)
        elif MODES[mode] in FRONT:
            dest.write(front_stream(body, size, MODES[mode], True))
        elif MODES[mode] in LANES:
            dest.write(field_stream(body, size, MODES[mode], True))
        else:
            src = BytesIO(body)
            lengths = read_lengths(src, size)
            payload = read_exact(src, size - len(lengths) + 1)
            if src.read(1):
                raise ValueError("Trailing row data")
            values = transform(payload, lengths, MODES[mode], True)
            delimiters = (lengths.cumsum() + np.arange(len(lengths)))[:-1]
            mask = np.ones(size, dtype=bool)
            mask[delimiters] = False
            raw = np.full(size, 10, np.uint8)
            raw[mask] = np.frombuffer(values, np.uint8)
            dest.write(raw.tobytes())
        remaining -= size
    if source.read(1):
        raise ValueError("Trailing prepared data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "restore", "encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="select")
    a = p.parse_args()
    with a.source.open("rb") as src, a.output.open("xb") as dst:
        if a.action == "prepare":
            print(json.dumps(encode(src, dst, a.profile)))
        elif a.action == "restore":
            decode(src, dst)
        elif a.action == "encode":
            prepared = BytesIO()
            choices = encode(src, prepared, a.profile)
            dst.write(
                b"RGR1" + zstd.ZstdCompressor(level=3).compress(prepared.getvalue())
            )
            print(json.dumps(choices))
        else:
            if read_exact(src, 4) != b"RGR1":
                raise ValueError("Invalid compressed row stream")
            with zstd.ZstdDecompressor().stream_reader(src) as prepared:
                decode(prepared, dst)
