"""Rebuild formula witnesses from their digits, bases and repeat counts plus exact field errors."""

import argparse
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd
from data import WITNESS

HEADER = struct.Struct(">4sQB")
GROUP = struct.Struct(">I")
STREAM = struct.Struct(">BI")
PROFILES = ("direct", "columns", "arithmetic", "joint")


def take(src, n):
    data = src.read(n)
    if len(data) != n:
        raise ValueError("Truncated witness record")
    return data


@lru_cache(maxsize=8192)
def repdigit(c, b, r):
    if not 1 <= c < b or not 1 <= r or b.bit_length() * r > 16384:
        raise ValueError("Unsupported formula parameters")
    return c * ((pow(b, r) - 1) // (b - 1))


def inferred(parameters):
    answer = np.empty((len(parameters), 3), dtype="<u4")
    for i, values in enumerate(parameters.tolist()):
        d = repdigit(*values[:3])
        if len(values) == 6:
            d, remainder = divmod(d, repdigit(*values[3:]))
            if remainder:
                raise ValueError("Nonintegral witness")
        if d.bit_length() > 64:
            raise ValueError("Value exceeds the witness field")
        answer[i] = (d & 0xFFFFFFFF, d >> 32, sum(x.bit_length() for x in values))
    return answer


def adjust_params(params, reverse):
    vals = params.copy()
    for j in range(0, vals.shape[1], 3):
        mask = vals[:, j + 2] == 1
        if reverse:
            vals[mask, j + 1] += vals[mask, j] + 1
        else:
            vals[mask, j + 1] -= vals[mask, j] + 1
    return vals


def lanes(data):
    return data.view(np.uint8).reshape(-1, 4).T.copy().tobytes()


def unlanes(raw):
    return np.frombuffer(raw, np.uint8).reshape(4, -1).T.copy().ravel().view("<u4")


def save_column(values, coder):
    values = values.copy()
    if not np.any(values):
        return STREAM.pack(0, 0)
    delta = values.copy()
    delta[1:] -= values[:-1]
    options = [(1, coder.compress(lanes(values))), (2, coder.compress(lanes(delta)))]
    mode, body = min(options, key=lambda o: len(o[1]))
    return STREAM.pack(mode, len(body)) + body


def read_column(src, count):
    mode, n = STREAM.unpack(take(src, STREAM.size))
    if mode == 0 and n == 0:
        return np.zeros(count, "<u4")
    if mode not in (1, 2):
        raise ValueError("Invalid integer column")
    z = zstd.ZstdDecompressor().decompress(take(src, n), max_output_size=count * 4)
    if len(z) != count * 4:
        raise ValueError("Incorrect column width")
    values = unlanes(z)
    return np.cumsum(values, dtype="<u4") if mode == 2 else values


def groups(data):
    src = BytesIO(data)
    magic, n3, n6 = WITNESS.unpack(take(src, WITNESS.size))
    if magic != b"WIT1" or len(data) != WITNESS.size + 24 * n3 + 36 * n6:
        raise ValueError("Invalid witness target")
    return [
        np.frombuffer(take(src, n * width * 4), "<u4").reshape(n, width)
        for n, width in ((n3, 6), (n6, 9))
    ]


def encode(data, profile):
    coder = zstd.ZstdCompressor(level=9)
    best = (len(data), 0, data)

    def offer(mode, body):
        nonlocal best
        if len(body) < best[0]:
            best = len(body), mode, body

    offer(1, coder.compress(data))
    if profile != "direct":
        try:
            tables = groups(data)
        except (ValueError, struct.error):
            tables = None
        if tables is not None:
            for mode in (
                [2, 3, 4]
                if profile == "joint"
                else ([2] if profile == "columns" else [3])
            ):
                parts = BytesIO()
                for table in tables:
                    parts.write(GROUP.pack(len(table)))
                    if mode == 2:
                        fields = table
                    else:
                        params = table[:, 2:-1]
                        try:
                            pred = inferred(params)
                        except ValueError:
                            break
                        residual = table[:, [0, 1, -1]] ^ pred
                        fields = np.column_stack(
                            (adjust_params(params, False), residual)
                        )
                    if mode == 3:
                        packed = coder.compress(fields.tobytes())
                        parts.write(GROUP.pack(len(packed)))
                        parts.write(packed)
                    else:
                        for column in fields.T:
                            parts.write(save_column(column, coder))
                else:
                    offer(mode, parts.getvalue())
    length, mode, body = best
    return HEADER.pack(b"WFW1", len(data), mode) + body, dict(
        mode=mode, payload_bytes=length
    )


def decode(archive):
    magic, size, mode = HEADER.unpack_from(archive)
    if magic != b"WFW1" or mode > 4:
        raise ValueError("Invalid witness archive")
    payload = archive[HEADER.size :]
    if mode == 0:
        result = payload
    elif mode == 1:
        result = zstd.ZstdDecompressor().decompress(payload, max_output_size=size)
    else:
        src = BytesIO(payload)
        parts = []
        counts = []
        for width in (6, 9):
            (n,) = GROUP.unpack(take(src, 4))
            counts.append(n)
            if n * width * 4 > size:
                raise ValueError("Too many witnesses")
            if mode == 3:
                (length,) = GROUP.unpack(take(src, 4))
                raw = zstd.ZstdDecompressor().decompress(
                    take(src, length), max_output_size=n * width * 4
                )
                fields = np.frombuffer(raw, "<u4").reshape(n, width)
            else:
                fields = np.column_stack([read_column(src, n) for _ in range(width)])
            if mode == 2:
                table = fields
            else:
                params = adjust_params(fields[:, :-3], True)
                values = inferred(params) ^ fields[:, -3:]
                table = np.column_stack((values[:, :2], params, values[:, 2]))
            parts.append(table.astype("<u4", copy=False).tobytes())
        if src.read(1):
            raise ValueError("Trailing witness data")
        result = WITNESS.pack(b"WIT1", *counts) + b"".join(parts)
    if len(result) != size:
        raise ValueError("Incorrect output size")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.out.open("xb") as f:
        if a.mode == "encode":
            archive, stats = encode(a.source.read_bytes(), a.profile)
            f.write(archive)
            print(json.dumps(stats))
        else:
            f.write(decode(a.source.read_bytes()))
