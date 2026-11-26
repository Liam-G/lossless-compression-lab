"""Encode base-36 strings with certified prefixes of signed square-root sums."""

from functools import lru_cache
from itertools import product
from math import isqrt
from wire import blocks

ID = 4
PROFILES = tuple(
    f"{radix}-{terms}-{sign}-{cut}"
    for radix in (10, 36)
    for terms in (2, 4)
    for sign in ("positive", "signed")
    for cut in ("whole", "checkpoints")
)
ALPHABET = b"0123456789abcdefghijklmnopqrstuvwxyz"
WIDTH = 12


@lru_cache(maxsize=8)
def catalog(terms, sign, radix=36):
    scale = 1 << 192
    roots = [isqrt(x * scale * scale) for x in (2, 3, 5, 7)[:terms]]
    patterns = []
    for coefficients in product((0, 1, -1) if sign == "signed" else (0, 1), repeat=terms):
        low = sum(c * r + min(0, c) for c, r in zip(coefficients, roots))
        high = sum(c * r + max(0, c) for c, r in zip(coefficients, roots))
        multiplier = radix**WIDTH
        a, b = low * multiplier // scale, high * multiplier // scale
        if a != b:
            raise ArithmeticError("Precision insufficient to certify the digit prefix")
        value = a % multiplier
        digits = bytearray()
        for _ in range(WIDTH):
            value, digit = divmod(value, radix)
            digits.append(ALPHABET[digit])
        patterns.append(bytes(reversed(digits)))
    return patterns


def segments(block, patterns, checkpoints, radix):
    # Path cost counts tag, catalog index and packed literal rank.
    best = [None] * (len(block) + 1)
    best[-1] = (0, [])
    for i in reversed(range(len(block))):
        choices = []
        for width in range(1, len(block) - i + 1):
            if not checkpoints and (i or width != len(block)):
                continue
            part = block[i : i + width]
            candidates = [(width, part)]
            if all(c in ALPHABET[:radix] for c in part):
                rank = 0
                for c in part:
                    rank = radix * rank + ALPHABET.index(c)
                n = ((radix**width - 1).bit_length() + 7) // 8
                candidates.append((32 + width, rank.to_bytes(n, "big")))
            for index, digits in enumerate(patterns):
                if digits.startswith(part):
                    candidates.append((64 + width, bytes([index])))
                    break
            for tag, payload in candidates:
                cost, tail = best[i + width]
                choices.append((1 + len(payload) + cost, [(tag, payload)] + tail))
        if choices:
            best[i] = min(choices, key=lambda x: x[0])
    return best[0][1]


def pack(data, profile, ref, stats):
    radix, terms, sign, mode = profile.split("-")
    radix = int(radix)
    patterns = catalog(int(terms), sign, radix)
    tags, body = bytearray(), bytearray()
    for block in blocks(data, WIDTH):
        for tag, value in segments(block, patterns, mode == "checkpoints", radix):
            tags.append(tag)
            body.extend(value)
    stats.update(
        segments=len(tags),
        index_bytes=sum(x > 64 for x in tags),
        generated_characters=sum(x - 64 for x in tags if x > 64),
    )
    return tags, body


def unpack(size, profile, meta, body, ref, stats):
    radix, terms, sign, _ = profile.split("-")
    radix = int(radix)
    patterns = catalog(int(terms), sign, radix)
    out = bytearray()
    while len(out) < size:
        kind, width = divmod(meta.byte(), 32)
        if not 1 <= width <= WIDTH:
            raise ValueError("Invalid segment")
        if kind == 2:
            out.extend(patterns[body.byte()][:width])
        elif kind == 1:
            rank = int.from_bytes(body.take(((radix**width - 1).bit_length() + 7) // 8), "big")
            digits = bytearray()
            for _ in range(width):
                rank, digit = divmod(rank, radix)
                digits.append(ALPHABET[digit])
            out.extend(reversed(digits))
        elif kind == 0:
            out.extend(body.take(width))
        else:
            raise ValueError("Invalid segment type")
    return out
