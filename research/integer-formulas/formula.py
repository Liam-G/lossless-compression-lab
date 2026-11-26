"""QFE1 stores a flat signed sum of terms s*(s+d), with d equal to 0 or 1."""

import argparse
import json
from pathlib import Path

import gmpy2 as g


def varint(n):
    if n < 0:
        raise ValueError("Unsigned integer required")
    out = bytearray()
    while n >= 128:
        out.append(128 | (n & 127))
        n >>= 7
    out.append(n)
    return out


def readint(stream):
    value = shift = 0
    while True:
        digit = stream.read(1)
        if not digit:
            raise ValueError("Truncated formula")
        value |= (digit[0] & 127) << shift
        if digit[0] < 128:
            return value
        shift += 7


def decompose(target, mode):
    while target:
        sign = 1 if target > 0 else -1
        root, remainder = g.isqrt_rem(abs(target))
        # All three errors are relative to the same floor square.
        options = [(remainder, root, 0)]
        if mode == "mixed":
            options.append((remainder - root, root, 1))
        if mode != "floor":
            options.append((remainder - 2 * root - 1, root + 1, 0))
        error, seed, delta = min(options, key=lambda entry: abs(entry[0]))
        yield seed, delta, sign
        target = sign * error


def encode(source, dest, mode):
    width = source.stat().st_size
    value = g.mpz.from_bytes(source.read_bytes(), "big")
    bits = value.bit_length()
    terms = []
    with dest.open("xb") as out:
        out.write(b"QFE1" + varint(width))
        for seed, delta, sign in decompose(value, mode):
            nbits = seed.bit_length()
            nbytes = (nbits + 7) // 8
            out.write(varint(4 * nbytes + 2 * delta + (sign < 0)))
            out.write(seed.to_bytes(nbytes, "big"))
            terms.append(dict(seed_bits=nbits, delta=delta, sign=sign))
        out.write(b"\0")
    return dict(
        mode=mode,
        input_bytes=width,
        input_bits=bits,
        terms=terms,
        coefficient_bytes=sum((t["seed_bits"] + 7) // 8 for t in terms),
        sum_seed_bits=sum(t["seed_bits"] for t in terms),
        descriptor_bytes=dest.stat().st_size,
    )


def decode(source, dest):
    with source.open("rb") as stream:
        if stream.read(4) != b"QFE1":
            raise ValueError("Unknown signature")
        width = readint(stream)
        total = g.mpz(0)
        while tag := readint(stream):
            length, flags = divmod(tag, 4)
            if not 1 <= length <= width:
                raise ValueError("Invalid length")
            data = stream.read(length)
            if len(data) != length:
                raise ValueError("Truncated coefficient")
            seed = g.mpz.from_bytes(data, "big")
            term = g.square(seed)
            if flags & 2:
                term += seed
            total += -term if flags & 1 else term
        if stream.read(1):
            raise ValueError("Trailing data")
    with dest.open("xb") as out:
        out.write(total.to_bytes(width, "big"))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("floor", "nearest", "mixed", "decode"))
    cli.add_argument("source", type=Path)
    cli.add_argument("dest", type=Path)
    args = cli.parse_args()
    if args.mode == "decode":
        decode(args.source, args.dest)
    else:
        print(json.dumps(encode(args.source, args.dest, args.mode), indent=2))
