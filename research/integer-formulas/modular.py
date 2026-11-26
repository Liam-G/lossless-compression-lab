"""QMS1: X = s**2 mod 2**b. Recover a compact choice among the four roots."""

import argparse
import json
from pathlib import Path
import gmpy2 as g
from formula import varint, readint


def min_root(x, bits):
    if x % 8 != 1 or bits < 3:
        raise ValueError(
            "Expected an integer congruent to 1 modulo 8 with at least three bits"
        )
    # If e = x*r*r-1 is divisible by 2**k, the Newton update gives
    # e' = (e**3-3*e**2)/4, divisible by 2**(2*k-2).
    r = g.mpz(1)
    k = 3
    while k < bits:
        k = min(bits, 2 * k - 2)
        low_x = g.f_mod_2exp(x, k + 1)
        rr = g.f_mod_2exp(g.square(r), k + 1)
        correction = (3 - g.f_mod_2exp(low_x * rr, k + 1)) // 2
        r = g.f_mod_2exp(r * correction, k)
    root = g.f_mod_2exp(x * r, bits - 1)
    return min(root, (g.mpz(1) << (bits - 1)) - root)


def encode(src, dest):
    width = src.stat().st_size
    x = g.mpz.from_bytes(src.read_bytes(), "big")
    bits = x.bit_length()
    s = min_root(x, bits)
    if g.f_mod_2exp(g.square(s), bits) != x:
        raise ArithmeticError("The root does not reproduce the target")
    payload = s.to_bytes((s.bit_length() + 7) // 8, "big")
    with dest.open("xb") as out:
        out.write(b"QMS1" + varint(bits) + varint(width - (bits + 7) // 8))
        out.write(payload)
    return dict(
        input_bytes=width,
        bits=bits,
        seed_bits=s.bit_length(),
        seed_bytes=len(payload),
        descriptor_bytes=dest.stat().st_size,
    )


def decode(src, dest):
    with src.open("rb") as stream:
        if stream.read(4) != b"QMS1":
            raise ValueError("Invalid signature")
        bits, zeros = readint(stream), readint(stream)
        s = g.mpz.from_bytes(stream.read(), "big")
    x = g.f_mod_2exp(g.square(s), bits)
    with dest.open("xb") as out:
        out.write(x.to_bytes(zeros + (bits + 7) // 8, "big"))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("encode", "decode"))
    cli.add_argument("source", type=Path)
    cli.add_argument("dest", type=Path)
    args = cli.parse_args()
    if args.mode == "decode":
        decode(args.source, args.dest)
    else:
        print(json.dumps(encode(args.source, args.dest), indent=2))
