"""Sparse seeds on reversible 8 by 8 Checkerboard and Margolus orbits."""

from subsets import bits_needed, rank, unrank
from wire import blocks

ID = 6
DEPENDENCIES = ("subsets",)
PROFILES = ("zero",) + tuple(
    f"{rule}-{limit}-{mode}"
    for rule in ("checker", "margolus")
    for limit in (3, 15)
    for mode in ("fixed", "restricted")
)
FULL = (1 << 64) - 1
EVEN = 0x55AA55AA55AA55AA


def phase(word, parity):
    left = (word >> 1 & 0x7F7F7F7F7F7F7F7F) | (word & 0x0101010101010101) << 7
    right = (word << 1 & 0xFEFEFEFEFEFEFEFE) | (word >> 7 & 0x0101010101010101)
    vertical = (word << 8) | (word >> 8) | (word >> 56) | (word << 56)
    return word ^ (parity & FULL & ((left & right) ^ vertical))


def step(word, rule, reverse=False):
    phases = (1, 0) if reverse else (0, 1)
    for offset in phases:
        if rule == "checker":
            word = phase(word, FULL ^ EVEN if offset else EVEN)
            continue
        for y in range(offset, 8, 2):
            for x in range(offset, 8, 2):
                loc = [
                    8 * y + x,
                    8 * y + (x + 1) % 8,
                    8 * ((y + 1) % 8) + (x + 1) % 8,
                    8 * ((y + 1) % 8) + x,
                ]
                bits = [(word >> k) & 1 for k in loc]
                # Involutive billiard rule: complement diagonal pairs and toggle 1/3 particles.
                code = sum(v << j for j, v in enumerate(bits))
                mapping = {1: 14, 14: 1, 2: 13, 13: 2, 4: 11, 11: 4, 8: 7, 7: 8, 5: 10, 10: 5}
                change = code ^ mapping.get(code, code)
                word ^= sum(((change >> j) & 1) << k for j, k in enumerate(loc))
    return word


def minority(word):
    return min(word.bit_count(), 64 - word.bit_count())


def bounds(seed, limit, rule):
    lo, hi = 0, limit
    before = after = seed
    for t in range(1, limit + 1):
        after = step(after, rule)
        if minority(after) <= minority(seed):
            hi = t - 1
            break
    for t in range(1, limit + 1):
        before = step(before, rule, True)
        if minority(before) < minority(seed):
            lo = limit - t + 1
            break
    return lo, hi


def pack(data, profile, ref, stats):
    rule, limit, mode = ("checker", "0", "fixed") if profile == "zero" else profile.split("-")
    limit = int(limit)
    tags, body = bytearray(), bytearray()
    indices = []
    for block in blocks(data[: len(data) // 8 * 8], 8):
        word = int.from_bytes(block, "little")
        seed = current = word
        index = 0
        for t in range(1, limit + 1):
            current = step(current, rule, True)
            if minority(current) < minority(seed):
                seed, index = current, t
        count = seed.bit_count()
        length = (bits_needed(64, count) + 7) // 8
        lo, hi = bounds(seed, limit, rule) if mode == "restricted" else (0, limit)
        width = (hi - lo).bit_length()
        if length * 8 + width >= 64:
            tags.append(255)
            body.extend(block)
        else:
            tags.append(count)
            body.extend(rank(seed).to_bytes(length, "big"))
            if not lo <= index <= hi:
                raise ValueError("Unreconstructible step")
            indices.append(format(index - lo, f"0{width}b") if width else "")
    bits = "".join(indices)
    step_bytes = int(bits or "0", 2).to_bytes((len(bits) + 7) // 8, "little")
    stats.update(step_bits=len(bits), step_bytes=len(step_bytes), seed_bytes=len(body))
    # Low-order padding length lets the decoder read the big-endian bit string.
    return bytes(tags) + bytes([len(bits) % 8]) + step_bytes, bytes(body) + data[
        len(data) // 8 * 8 :
    ]


def unpack(size, profile, meta, body, ref, stats):
    rule, limit, mode = ("checker", "0", "fixed") if profile == "zero" else profile.split("-")
    limit = int(limit)
    tags = meta.take(size // 8)
    remainder = meta.byte()
    stream = meta.read()
    length = 8 * len(stream) - ((8 - remainder) % 8)
    indices = int.from_bytes(stream, "little")
    out = bytearray()
    for count in tags:
        if count == 255:
            out.extend(body.take(8))
            continue
        n = (bits_needed(64, count) + 7) // 8
        seed = unrank(64, count, int.from_bytes(body.take(n), "big"))
        lo, hi = bounds(seed, limit, rule) if mode == "restricted" else (0, limit)
        width = (hi - lo).bit_length()
        length -= width
        steps = lo + ((indices >> length) & ((1 << width) - 1))
        if steps > hi:
            raise ValueError("Invalid orbit index")
        for _ in range(steps):
            seed = step(seed, rule)
        out.extend(seed.to_bytes(8, "little"))
    if length:
        raise ValueError("Unused orbit indices")
    return out + body.take(size % 8)
