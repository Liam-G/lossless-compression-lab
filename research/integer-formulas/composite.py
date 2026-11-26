"""A sparse polynomial in 256, an integer quotient, and one square modulo 256**m."""

import argparse
import json
from pathlib import Path
import gmpy2 as g
from formula import readint, varint


def encoded_size(value):
    return max(1, (value.bit_length() + 6) // 7)


def fields(prefix, d):
    pad = ((d - 1).bit_length() + 7) // 8
    return (d * int.from_bytes(prefix, "big")).to_bytes(len(prefix) + pad, "big"), pad


def nonzero_entries(digits):
    previous = -1
    for i, x in enumerate(digits):
        if x:
            yield i - previous - 1, x
            previous = i


def find_prefix(sample, width, root_bytes):
    divisors = sorted(
        set(range(1, 257))
        | {a * b for a in (1, 3, 4, 12, 48) for b in (255, 257, 65535, 65537)}
    )
    best = None
    # Length of the smallest square root at each possible suffix width.
    lengths = []
    for offset in range(len(sample) + 1):
        j = offset
        m = width - offset
        if m == 1:
            u = root_bytes[j] & 127
            lengths.append((min(u, 128 - u).bit_length() + 7) // 8)
            continue
        negate = bool(root_bytes[j] & 64)
        top = (~root_bytes[j] if negate else root_bytes[j]) & 127
        if top:
            lengths.append(m)
            continue
        j += 1
        blank = 255 if negate else 0
        while j < width - 1 and root_bytes[j] == blank:
            j += 1
        # Root is odd, so the last byte of either positive root is nonzero.
        lengths.append(width - j)
    for d in divisors:
        digits, pad = fields(sample, d)
        previous = -1
        count = payload = 0
        for i, c in enumerate(digits):
            if c:
                payload += encoded_size(i - previous - 1) + 1
                count += 1
                previous = i
            used = i + 1 - pad
            if not 0 <= used <= len(sample):
                continue
            cost = (
                4
                + encoded_size(width)
                + encoded_size(used)
                + encoded_size(d)
                + encoded_size(count)
                + payload
                + lengths[used]
            )
            if best is None or cost < best[0]:
                best = cost, used, d
    return best, len(divisors)


def encode(source, modulus_formula, dest, limit):
    width = source.stat().st_size
    with source.open("rb") as f:
        sample = f.read(min(limit, width - 1))
    with modulus_formula.open("rb") as f:
        if f.read(4) != b"QMS1":
            raise ValueError("Expected a QMS1 root")
        bits, zeros = readint(f), readint(f)
        if (bits + 7) // 8 + zeros != width:
            raise ValueError("Inconsistent width")
        root_bytes = f.read().rjust(width, b"\0")
    (size, used, d), tested = find_prefix(sample, width, root_bytes)
    digits, pad = fields(sample, d)
    prefix = digits[: used + pad]
    entries = list(nonzero_entries(prefix))
    m = width - used
    half = g.mpz(1) << (8 * m - 1)
    # The QMS1 seed squares to Q mod 2**bits. Its low bits also give the
    # suffix as soon as that suffix has at most 'bits' bits of precision.
    if 8 * m > bits:
        # A root modulo a shorter power need not lift without adjustment.
        from modular import min_root

        lower = g.mpz.from_bytes(source.read_bytes(), "big") % (half * 2)
        s = min_root(lower, 8 * m)
    else:
        u = g.f_mod_2exp(g.mpz.from_bytes(root_bytes[used:], "big"), 8 * m - 1)
        s = min(u, half - u)
    with dest.open("xb") as f:
        f.write(
            b"QFC1" + varint(width) + varint(used) + varint(d) + varint(len(entries))
        )
        for skip, c in entries:
            f.write(varint(skip) + bytes([c]))
        f.write(s.to_bytes((s.bit_length() + 7) // 8, "big"))
    if 8 * m <= bits and dest.stat().st_size != size:
        raise ArithmeticError("Serialized size differs from quoted size")
    return dict(
        input_bytes=width,
        prefix_bytes=used,
        divisor=d,
        nonzero_coefficients=len(entries),
        suffix_bytes=m,
        root_bits=s.bit_length(),
        root_bytes=(s.bit_length() + 7) // 8,
        prefix_lengths_tried=len(sample) + 1,
        divisors_tried=tested,
        formula_bytes=dest.stat().st_size,
    )


def decode(source, dest):
    with source.open("rb") as f:
        if f.read(4) != b"QFC1":
            raise ValueError("Invalid signature")
        width, used, d, count = (readint(f) for _ in range(4))
        if d == 0 or used >= width:
            raise ValueError("Invalid dimensions")
        remaining = used + ((d - 1).bit_length() + 7) // 8
        p = g.mpz(0)
        for _ in range(count):
            gap = readint(f)
            digit = f.read(1)
            if not digit or gap >= remaining:
                raise ValueError("Truncated polynomial")
            p = (p << (8 * (gap + 1))) + digit[0]
            remaining -= gap + 1
        p <<= 8 * remaining
        s = g.mpz.from_bytes(f.read(), "big")
    m = width - used
    suffix = g.f_mod_2exp(g.square(s), 8 * m)
    q = ((p // d) << (8 * m)) + suffix
    with dest.open("xb") as f:
        f.write(q.to_bytes(width, "big"))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("encode", "decode"))
    cli.add_argument("source", type=Path)
    cli.add_argument("dest", type=Path)
    cli.add_argument("--root", type=Path)
    cli.add_argument("--limit", type=int, default=8192)
    args = cli.parse_args()
    if args.mode == "decode":
        decode(args.source, args.dest)
    elif args.root is None or args.limit < 0 or not args.source.stat().st_size:
        cli.error("Provide --root and a positive input size")
    else:
        print(
            json.dumps(encode(args.source, args.root, args.dest, args.limit), indent=2)
        )
