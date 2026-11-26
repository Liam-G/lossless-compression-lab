"""Try reversible integer predictors on a grid, then code digit or bit planes."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import lzma

import numpy as np
import zstandard as zstd

BLOCK = 1 << 20
HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BBBHI")
PROFILES = (
    "direct",
    "layout",
    "predict",
    "joint",
    "direct19",
    "joint19",
    "direct-xz",
    "joint-xz",
)
# Each step is a finite difference over a lag, with zeros before the block.
PLAIN, DELTA, XOR, MIXED, CURVE = range(5)
RAW, LANES, PLANES = range(3)
LAGS = (
    1,
    2,
    3,
    4,
    6,
    8,
    12,
    13,
    16,
    24,
    32,
    48,
    64,
    70,
    80,
    96,
    128,
    192,
    216,
    256,
    384,
    512,
    768,
    1024,
    1536,
    1728,
    2048,
    4096,
)
STORED = 255


def delta(v, lag, xor=False):
    out = v.copy()
    if xor:
        out[lag:] ^= v[:-lag]
    else:
        out[lag:] -= v[:-lag]
    return out


def integrate(v, lag, xor=False):
    if lag >= len(v):
        return v
    rows = (len(v) + lag - 1) // lag
    padded = np.zeros(rows * lag, dtype=v.dtype)
    padded[: len(v)] = v
    grid = padded.reshape(rows, lag)
    op = np.bitwise_xor if xor else np.add
    op.accumulate(grid, axis=0, dtype=v.dtype, out=grid)
    return padded[: len(v)]


def predict(v, method, lag):
    if method == PLAIN:
        return v
    if method == XOR:
        return delta(v, lag, True)
    residual = delta(v, lag)
    if method in (MIXED, CURVE):
        residual = delta(residual, 1 if method == MIXED else lag)
    # Zigzag at the declared machine width, including the most negative value.
    return (residual << 1) ^ (
        np.zeros_like(residual) - (residual >> (8 * v.itemsize - 1))
    )


def recover(v, method, lag):
    if method == PLAIN:
        return v
    if method == XOR:
        return integrate(v, lag, True)
    result = (v >> 1) ^ (np.zeros_like(v) - (v & 1))
    if method in (MIXED, CURVE):
        result = integrate(result, 1 if method == MIXED else lag)
    return integrate(result, lag)


def layout(v, kind):
    if kind == RAW:
        return v.tobytes()
    lanes = v.view(np.uint8).reshape(-1, v.itemsize).T.copy()
    if kind == LANES:
        return lanes.tobytes()
    # Eight samples per tile. Retain a literal tail of up to seven samples in each lane.
    end = lanes.shape[1] // 8 * 8
    bits = np.unpackbits(lanes[:, :end, None], axis=2, bitorder="little")
    planes = np.packbits(bits.transpose(0, 2, 1), axis=2, bitorder="little")
    return planes.tobytes() + lanes[:, end:].tobytes()


def unlayout(raw, width, kind):
    if kind == RAW:
        return np.frombuffer(raw, dtype=f"<u{width}")
    data = np.frombuffer(raw, np.uint8)
    n = len(raw) // width
    if kind == LANES:
        lanes = data.reshape(width, n)
    else:
        aligned = n // 8 * 8
        packed = data[: aligned * width].reshape(width, 8, aligned // 8)
        planes = np.unpackbits(packed, axis=2, bitorder="little")
        head = np.packbits(
            planes.transpose(0, 2, 1), axis=2, bitorder="little"
        ).reshape(width, aligned)
        lanes = np.concatenate(
            (head, data[aligned * width :].reshape(width, n - aligned)), axis=1
        )
    return lanes.T.copy().reshape(-1).view(f"<u{width}")


def shortlist(v):
    max_lag = min(len(v) // 3, LAGS[-1])
    if max_lag < 2:
        return [1]
    pos = np.linspace(max_lag, len(v) - 1, min(4096, len(v) - max_lag), dtype=np.int64)
    now = v[pos].astype(np.int64)
    scores = []
    for lag in LAGS:
        if lag > max_lag:
            break
        diff = np.abs(now - v[pos - lag].astype(np.int64))
        scores.append((np.log2(1 + diff).mean(), lag))
    return sorted({1, *[lag for _, lag in sorted(scores)[:2]]})


def choices(block, profile):
    layouts = (RAW, LANES, PLANES) if profile in ("layout", "joint") else (RAW,)
    for width in (1, 2, 4):
        end = len(block) // width * width
        if not end:
            continue
        v = np.frombuffer(block[:end], dtype=f"<u{width}")
        predictors = [(PLAIN, 1)]
        if profile in ("predict", "joint"):
            for lag in shortlist(v):
                predictors.extend((method, lag) for method in (DELTA, XOR, CURVE))
                if lag > 1:
                    predictors.append((MIXED, lag))
        for method, lag in predictors:
            residual = predict(v, method, lag)
            for kind in layouts:
                if (width == 1 and kind == LANES) or (
                    width > 1 and method == PLAIN and kind == RAW
                ):
                    continue
                yield (width, method, kind, lag), layout(residual, kind) + block[end:]


def pack(source, dest, profile):
    coder = zstd.ZstdCompressor(level=3)
    strong = profile.endswith("19") or profile.endswith("-xz")
    shape = profile.removesuffix("19").removesuffix("-xz")
    signature = b"LTX1" if profile.endswith("-xz") else b"LTP1"
    strong_zstd = zstd.ZstdCompressor(level=19) if profile.endswith("19") else None
    counts = Counter()
    dest.write(HEADER.pack(signature, source.seek(0, 2)))
    source.seek(0)
    while block := source.read(BLOCK):
        best = block
        selected = (1, STORED, RAW, 1)
        finalists = []
        for config, trial in choices(block, shape):
            payload = coder.compress(trial)
            if strong:
                # A quick full-block price ranks transforms. Always reprice the original.
                finalists.append((len(payload), config, trial))
                finalists.sort(key=lambda row: row[0])
                del finalists[3:]
            elif len(payload) < len(best):
                best, selected = payload, config
        if strong:
            direct = (1, PLAIN, RAW, 1)
            if all(config != direct for _, config, _ in finalists):
                finalists.append((0, direct, block))
            for _, config, trial in finalists:
                payload = (
                    strong_zstd.compress(trial)
                    if strong_zstd is not None
                    else lzma.compress(trial, format=lzma.FORMAT_XZ, preset=6)
                )
                if len(payload) < len(best):
                    best, selected = payload, config
        dest.write(RECORD.pack(*selected, len(best)))
        dest.write(best)
        counts[str(selected)] += 1
    return counts


def unpack(source, dest):
    magic, left = HEADER.unpack(source.read(HEADER.size))
    if magic not in (b"LTP1", b"LTX1"):
        raise ValueError("Invalid lattice archive")
    decoder = zstd.ZstdDecompressor()
    while left:
        size = min(left, BLOCK)
        width, method, kind, lag, length = RECORD.unpack(source.read(RECORD.size))
        if width not in (1, 2, 4) or kind > PLANES or lag not in LAGS or length > size:
            raise ValueError("Invalid lattice block")
        payload = source.read(length)
        if len(payload) != length:
            raise ValueError("Truncated block")
        if method == STORED:
            block = payload
        elif method in (PLAIN, DELTA, XOR, MIXED, CURVE):
            raw = (
                lzma.decompress(payload, format=lzma.FORMAT_XZ)
                if magic == b"LTX1"
                else decoder.decompress(payload, max_output_size=size)
            )
            if len(raw) != size:
                raise ValueError("Invalid decoded size")
            end = size // width * width
            block = (
                recover(unlayout(raw[:end], width, kind), method, lag).tobytes()
                + raw[end:]
            )
        else:
            raise ValueError("Unknown predictor")
        if len(block) != size:
            raise ValueError("Invalid block length")
        dest.write(block)
        left -= size
    if source.read(1):
        raise ValueError("Unexpected trailing data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", choices=PROFILES, default="joint")
    args = parser.parse_args()
    with args.input.open("rb") as src, args.output.open("xb") as dest:
        if args.command == "encode":
            print(json.dumps(pack(src, dest, args.profile)))
        else:
            unpack(src, dest)


if __name__ == "__main__":
    main()
