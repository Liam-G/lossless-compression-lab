"""QGS1: exact sum of three seeded integers and a signed residual, big endian."""

import hashlib
import struct
import sys
from functools import lru_cache

HEADER = struct.Struct(">4sQI")


def generate(term, seed, width):
    stream = hashlib.shake_256(b"QGS1" + bytes([term, seed]))
    head = bytes([seed]) if term == 0 else b""
    return int.from_bytes(head + stream.digest(width - 1), "big")


@lru_cache(maxsize=1024)
def small_term(term, seed, width):
    return generate(term, seed, width)


def prediction(seeds, width):
    fn = small_term if width <= 4096 else generate
    return sum(fn(term, seed, width) for term, seed in enumerate(seeds))


def read_exact(stream, length):
    data = stream.read(length)
    if len(data) != length:
        raise ValueError("Truncated archive")
    return data


def decode(src, out):
    magic, remaining, block = HEADER.unpack(read_exact(src, HEADER.size))
    if magic != b"QGS1":
        raise ValueError("Unknown signature")
    while remaining:
        width = min(block or remaining, remaining)
        seeds = read_exact(src, 3)
        code = 0
        shift = 0
        while True:
            digit = read_exact(src, 1)[0]
            code |= (digit & 127) << shift
            if code > 2 * width + 1:
                raise ValueError("Invalid residual length")
            if digit < 128:
                break
            shift += 7
            if shift > (2 * width + 1).bit_length():
                raise ValueError("Invalid descriptor")
        residual = int.from_bytes(read_exact(src, width - (code >> 1)), "big")
        value = prediction(seeds, width) + (-residual if code & 1 else residual)
        out.write(value.to_bytes(width, "big"))
        remaining -= width
    if src.read(1):
        raise ValueError("Unexpected trailing data")


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as src, open(sys.argv[2], "xb") as out:
        decode(src, out)
