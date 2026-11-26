"""Find the closest sum across all 256**3 seed triples using sorted pair sums."""

import argparse
from bisect import bisect_left, bisect_right
from functools import lru_cache
import json
import os

from decoder import HEADER, generate, prediction


@lru_cache(maxsize=6)
def index(width):
    terms = [[generate(term, seed, width) for seed in range(256)] for term in range(3)]
    pairs = sorted(
        (b + c, y, z) for y, b in enumerate(terms[1]) for z, c in enumerate(terms[2])
    )
    return terms[0], pairs, [row[0] for row in pairs]


def nearest_indices(target, keys):
    pos = bisect_left(keys, target)
    return range(max(0, pos - 1), min(len(keys), pos + 1))


def nearest(data):
    width = len(data)
    prefix_width = min(6, width)
    target = int.from_bytes(data[:prefix_width], "big")
    first, pairs, keys = index(prefix_width)
    # Bound the search using any valid triple. First terms are sorted by seed.
    bound = abs(first[data[0]] + keys[0] - target)
    lo = bisect_left(first, target - bound - keys[-1])
    hi = bisect_right(first, target + bound - keys[0])
    best_distance = bound
    best_seeds = (data[0], pairs[0][1], pairs[0][2])
    for x in range(lo, hi):
        goal = target - first[x]
        for pos in nearest_indices(goal, keys):
            distance = abs(keys[pos] - goal)
            if distance <= best_distance:
                best_distance = distance
                best_seeds = (x, pairs[pos][1], pairs[pos][2])
    if width == prefix_width:
        return best_seeds, target - prediction(best_seeds, width)

    # In prefix units, discarded suffixes change a signed difference by < 3.
    # Beyond best_distance + 6 a candidate cannot improve the initial match.
    radius = best_distance + 6
    lo = bisect_left(first, target - radius - keys[-1])
    hi = bisect_right(first, target + radius - keys[0])
    value = int.from_bytes(data, "big")
    best_residual = None
    for x in range(lo, hi):
        goal = target - first[x]
        for pos in range(
            bisect_left(keys, goal - radius), bisect_right(keys, goal + radius)
        ):
            _, y, z = pairs[pos]
            seeds = (x, y, z)
            residual = value - prediction(seeds, width)
            if best_residual is None or abs(residual) < abs(best_residual):
                best_seeds, best_residual = seeds, residual
    return best_seeds, best_residual


def varint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return result


def encode(src, out, block):
    size = os.fstat(src.fileno()).st_size
    out.write(HEADER.pack(b"QGS1", size, block))
    total_residual = total_descriptors = count = 0
    first_leaf = None
    remaining = size
    while remaining:
        width = min(remaining, block or remaining)
        data = src.read(width)
        if len(data) != width:
            raise ValueError("Truncated input")
        seeds, residual = nearest(data)
        bits = abs(residual).bit_length()
        length = (bits + 7) // 8
        descriptor = varint(2 * (width - length) + (residual < 0))
        out.write(bytes(seeds))
        out.write(descriptor)
        out.write(abs(residual).to_bytes(length, "big"))
        if first_leaf is None:
            first_leaf = dict(
                seeds=seeds,
                input_bits=int.from_bytes(data, "big").bit_length(),
                residual_bits=bits,
                residual_sign=(residual > 0) - (residual < 0),
            )
        total_residual += length
        total_descriptors += len(descriptor)
        count += 1
        remaining -= width
    return dict(
        input_bytes=size,
        block_bytes=block,
        blocks=count,
        first=first_leaf,
        residual_bytes=total_residual,
        seed_bytes=3 * count,
        sign_and_length_bytes=total_descriptors,
        header_bytes=HEADER.size,
        archive_bytes=out.tell(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("archive")
    parser.add_argument("--block", default=0, type=int, help="0 = one integer")
    args = parser.parse_args()
    if not 0 <= args.block < 2**32:
        parser.error("Invalid block size")
    with open(args.source, "rb") as src, open(args.archive, "xb") as out:
        print(json.dumps(encode(src, out, args.block), indent=2))
