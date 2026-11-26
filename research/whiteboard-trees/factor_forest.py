"""Nested cofactor search with exact whiteboard leaves and bit-aligned concatenation."""

import argparse
from collections import Counter
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import struct
from tree import unit, varint, read_varint

HEADER = struct.Struct(">4sQ")
BLOCK = 64
PRIMES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
DELTAS = (0, 1, -1)
PROFILES = ("literal", "factor", "whiteboard", "leaf-factor", "nested")
LITERAL, SHORT, SPLIT, FACTOR, FORMULA = range(5)


@lru_cache(maxsize=1)
def book():
    entries = {}
    denominators = [(0, 0, 1)] + [
        (b, r, unit(b, r)) for b in (2, 3, 5, 7, 10) for r in (3, 4, 6, 8, 12)
    ]
    for base in (2, 3, 5, 7, 10, 16):
        for repeats in range(3, 517):
            value = unit(base, repeats)
            if value.bit_length() > 540:
                break
            for digit in range(1, base):
                numerator = value * digit
                prefix = bytes([FORMULA, base, digit]) + varint(repeats)
                for den_base, den_repeats, divisor in denominators:
                    if den_base == base:
                        continue
                    q, rem = divmod(numerator, divisor)
                    if rem or q.bit_length() > 512:
                        continue
                    wire = prefix + bytes([den_base, den_repeats])
                    if q not in entries or (len(wire), wire) < (
                        len(entries[q]),
                        entries[q],
                    ):
                        entries[q] = wire
    return entries


def quotient_width(width, p, delta):
    return (((1 << width) - 1 + delta) // p).bit_length()


def encode_word(value, width, profile):
    formulas = book() if profile in ("whiteboard", "nested", "leaf-factor") else {}
    factoring = profile in ("factor", "nested", "leaf-factor")

    @lru_cache(maxsize=None)
    def solve(n, w, levels, factors):
        length = (w + 7) // 8
        raw = n.to_bytes(length, "big")
        short = raw.lstrip(b"\0")
        options = [bytes([LITERAL]) + raw, bytes([SHORT, len(short)]) + short]
        if n in formulas:
            options.append(formulas[n])
        if levels and w >= 64:
            low = w // 2
            options.append(
                bytes([SPLIT])
                + solve(n >> low, w - low, levels - 1, factors)
                + solve(n % (1 << low), low, levels - 1, factors)
            )
        if factoring and factors and levels and w >= 16:
            # In the leaf ablation a factor can only terminate in an unsplit leaf.
            next_levels = 0 if profile == "leaf-factor" else levels - 1
            for d_idx, delta in enumerate(DELTAS):
                target = n + delta
                if target <= 1:
                    continue
                hits = [(i, p) for i, p in enumerate(PRIMES) if target % p == 0]
                for i, p in hits[-2:]:
                    child = solve(
                        target // p,
                        quotient_width(w, p, delta),
                        next_levels,
                        factors - 1,
                    )
                    options.append(bytes([FACTOR, 3 * i + d_idx]) + child)
        return min(options, key=len)

    return solve(value, width, 3, 2)


def encode(data, profile):
    return HEADER.pack(b"FWF1", len(data)) + b"".join(
        encode_word(int.from_bytes(block, "big"), 8 * len(block), profile)
        for i in range(0, len(data), BLOCK)
        for block in (data[i : i + BLOCK],)
    )


def take(stream, count):
    data = stream.read(count)
    if len(data) != count:
        raise ValueError("Truncated node")
    return data


def decode(archive):
    stream = BytesIO(archive)
    magic, size = HEADER.unpack(take(stream, HEADER.size))
    if magic != b"FWF1":
        raise ValueError("Invalid archive header")
    stats = Counter()

    def node(w, depth, inside_factor):
        if depth > 3:
            raise ValueError("Tree too deep")
        tag = take(stream, 1)[0]
        if tag in (LITERAL, SHORT):
            n = (w + 7) // 8 if tag == LITERAL else take(stream, 1)[0]
            value = int.from_bytes(take(stream, n), "big")
        elif tag == FORMULA:
            base, digit = take(stream, 2)
            repeats = read_varint(stream)
            d, t = take(stream, 2)
            if not 2 <= base <= 16 or not 1 <= digit < base or not 3 <= repeats <= 516:
                raise ValueError("Invalid numerator")
            if (d, t) != (0, 0) and not (2 <= d <= 10 and 3 <= t <= 12):
                raise ValueError("Invalid denominator")
            value, rem = divmod(digit * unit(base, repeats), unit(d, t) if d else 1)
            if rem:
                raise ValueError("Inexact formula")
            stats["quotient_leaves" if d else "direct_leaves"] += 1
            if inside_factor:
                stats["formula_below_factor"] += 1
        elif tag == SPLIT and w >= 64:
            low = w // 2
            value = (node(w - low, depth + 1, inside_factor) << low) + node(
                low, depth + 1, inside_factor
            )
            stats["splits"] += 1
            if inside_factor:
                stats["split_below_factor"] += 1
        elif tag == FACTOR:
            p_idx, d_idx = divmod(take(stream, 1)[0], 3)
            if p_idx >= len(PRIMES):
                raise ValueError("Invalid prime index")
            p, delta = PRIMES[p_idx], DELTAS[d_idx]
            value = p * node(quotient_width(w, p, delta), depth + 1, True) - delta
            stats["corrected_factors" if delta else "exact_factors"] += 1
        else:
            raise ValueError("Invalid node")
        if value < 0 or value.bit_length() > w:
            raise ValueError("Node exceeds width")
        return value

    out = bytearray()
    while len(out) < size:
        width = min(BLOCK, size - len(out))
        out.extend(node(8 * width, 0, False).to_bytes(width, "big"))
    if stream.read(1):
        raise ValueError("Trailing data")
    return bytes(out), dict(stats)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("encode", "decode"))
    cli.add_argument("input", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--profile", choices=PROFILES, default="nested")
    args = cli.parse_args()
    data = args.input.read_bytes()
    output = encode(data, args.profile) if args.mode == "encode" else decode(data)[0]
    with args.output.open("xb") as f:
        f.write(output)
