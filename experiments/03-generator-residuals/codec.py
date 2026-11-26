"""Arithmetic and SHAKE generator families with additive and sparse XOR corrections."""

import hashlib
from functools import lru_cache
from wire import blocks, var, zig, signed

ID = 3
PROFILES = tuple(
    f"{family}-{method}-{limit}"
    for family in ("power", "sum", "product")
    for method in ("add", "xor")
    for limit in (8, 32, 64)
)


@lru_cache(maxsize=2048)
def generate(family, seed, width):
    modulus = 1 << (8 * width)
    if family == "power":
        return pow(seed + 2, 7, modulus)
    a, b = (
        int.from_bytes(hashlib.shake_256(bytes([domain, seed])).digest(width), "big")
        for domain in (0, 1)
    )
    return (a + b if family == "sum" else a * b) % modulus


def pack(data, profile, ref, stats):
    family, method, limit = profile.split("-")
    tags, payload = bytearray(), bytearray()
    used = 0
    for block in blocks(data, 16):
        value = int.from_bytes(block, "big")
        tag, best = 255, block
        for seed in range(int(limit)):
            guess = generate(family, seed, len(block))
            if method == "add":
                candidate = var(zig(value - guess))
            else:
                mask = value ^ guess
                # Low-byte mismatches are a lower bound on the sparse correction cost.
                if 1 + (mask & 255).bit_count() >= len(best):
                    continue
                positions = []
                while mask:
                    bit = mask & -mask
                    positions.append(bit.bit_length() - 1)
                    mask ^= bit
                candidate = bytes([len(positions), *positions])
            if len(candidate) < len(best):
                tag, best = seed, candidate
        used += tag != 255
        tags.append(tag)
        payload.extend(best)
    stats["generated_blocks"] = used
    return tags, payload


def unpack(size, profile, meta, body, ref, stats):
    family, method, _ = profile.split("-")
    out = bytearray()
    while len(out) < size:
        width, seed = min(16, size - len(out)), meta.byte()
        if seed == 255:
            out.extend(body.take(width))
            continue
        value = generate(family, seed, width)
        if method == "add":
            value += signed(body.var())
        else:
            for pos in body.take(body.byte()):
                value ^= 1 << pos
        out.extend(value.to_bytes(width, "big"))
    return out
