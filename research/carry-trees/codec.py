"""Choose split boundaries and invertible integer multipliers by the final encoded byte count."""

import argparse
from collections import Counter
from arithmetic import transform
from pathlib import Path
import json
import struct
import zstandard as zstd

HEADER = struct.Struct(">4sQ")
ROOT = 4 << 20
MIN_LEAF = 1 << 16
STORED, ZSTD, SPLIT, MAP = range(4)
FACTORS = (
    2,
    3,
    4,
    5,
    7,
    8,
    9,
    11,
    12,
    13,
    16,
    17,
    25,
    31,
    37,
    63,
    127,
    255,
    257,
    65535,
    65537,
)
OPS = tuple((f, inv) for f in FACTORS for inv in (False, True))
PROFILES = ("direct", "arithmetic", "split", "joint")


def shortlist(data, coder):
    # The search sees the beginning, middle and end, including short structured prefixes.
    width = min(1024, len(data))
    starts = {0, len(data) - width, (len(data) - width) // 2}
    if len(data) > 4 * width:
        starts.update(((len(data) - width) // 4, 3 * (len(data) - width) // 4))
    samples = [data[s : s + width] for s in sorted(starts)]

    def score(op):
        factor, inv = op
        return sum(len(coder.compress(transform(s, factor, inv))) for s in samples)

    return sorted(range(len(OPS)), key=lambda i: (score(OPS[i]), i))[:2]


def leaf(data, coder):
    packed = coder.compress(data)
    if len(packed) + 4 < len(data):
        return bytes([ZSTD]) + struct.pack(">I", len(packed)) + packed
    return bytes([STORED]) + data


def choose(old, new):
    return new if len(new) < len(old) else old


def encode_node(data, coder, profile):
    best = leaf(data, coder)
    can_split = len(data) > MIN_LEAF
    half = len(data) // 2
    if can_split and profile in ("split", "joint"):
        best = choose(
            best,
            bytes([SPLIT])
            + encode_node(data[:half], coder, profile)
            + encode_node(data[half:], coder, profile),
        )
    if profile in ("arithmetic", "joint"):
        for i in shortlist(data, coder):
            mapped = transform(data, *OPS[i])
            child = leaf(mapped, coder)
            if can_split and profile == "joint":
                # A single split below the multiplier keeps cross-boundary carries.
                child = choose(
                    child,
                    bytes([SPLIT])
                    + leaf(mapped[:half], coder)
                    + leaf(mapped[half:], coder),
                )
            best = choose(best, bytes([MAP, i]) + child)
    return best


def take(src, n):
    data = src.read(n)
    if len(data) != n:
        raise ValueError("Incomplete carry-tree node")
    return data


def decode_node(src, size, decoder, stats, depth=0):
    if depth > 16:
        raise ValueError("Excessive tree depth")
    tag = take(src, 1)[0]
    if tag == STORED:
        stats["literal"] += 1
        return take(src, size)
    if tag == ZSTD:
        n = struct.unpack(">I", take(src, 4))[0]
        if n > size:
            raise ValueError("Invalid compressed length")
        data = decoder.decompress(take(src, n), max_output_size=size)
        if len(data) != size:
            raise ValueError("Incorrect decoded leaf size")
        stats["zstd"] += 1
        return data
    if tag == SPLIT and size > 1:
        stats["split"] += 1
        half = size // 2
        return decode_node(src, half, decoder, stats, depth + 1) + decode_node(
            src, size - half, decoder, stats, depth + 1
        )
    if tag == MAP:
        i = take(src, 1)[0]
        if i >= len(OPS):
            raise ValueError("Invalid arithmetic operator")
        factor, enc_inverse = OPS[i]
        stats[f"{'divide' if enc_inverse else 'multiply'}-{factor}"] += 1
        child = decode_node(src, size, decoder, stats, depth + 1)
        return transform(child, factor, not enc_inverse)
    raise ValueError("Invalid tree opcode")


def pack(src, out, profile):
    out.write(HEADER.pack(b"CRT1", src.seek(0, 2)))
    src.seek(0)
    coder = zstd.ZstdCompressor(level=3)
    while data := src.read(ROOT):
        out.write(encode_node(data, coder, profile))


def unpack(src, out):
    magic, left = HEADER.unpack(take(src, HEADER.size))
    if magic != b"CRT1":
        raise ValueError("Invalid carry-tree archive")
    counts = Counter()
    d = zstd.ZstdDecompressor()
    while left:
        n = min(left, ROOT)
        out.write(decode_node(src, n, d, counts))
        left -= n
    if src.read(1):
        raise ValueError("Unexpected trailing bytes")
    return counts


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("op", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.source.open("rb") as src, a.dest.open("xb") as out:
        if a.op == "encode":
            pack(src, out, a.profile)
        else:
            print(json.dumps(unpack(src, out)))
