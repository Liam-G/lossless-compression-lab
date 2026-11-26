"""Near products with decimal concatenation inside each operand."""

from math import isqrt
from time import process_time_ns
from wire import blocks, var, zig, signed

ID = 2
PROFILES = tuple(
    f"{strategy}-{mode}"
    for strategy in ("first", "best")
    for mode in ("exact", "correct", "split", "combined")
)
CONTRASTS = [
    (s + "_gain", s + "-correct", s + "-split", s + "-combined") for s in ("first", "best")
]
WIDTH = 16


def operand(value, split):
    best = b"\0" + var(value)
    if split:
        for width in range(1, len(str(value))):
            prefix, suffix = divmod(value, 10**width)
            record = bytes([width]) + var(prefix) + var(suffix)
            if len(record) < len(best):
                best = record
    return best


def read_operand(stream):
    width, high = stream.byte(), stream.var()
    return high * 10**width + stream.var() if width else high


def pack(data, profile, ref, stats):
    strategy, mode = profile.split("-")
    sizes = bytearray()
    payload = bytearray()
    products = examined = 0
    for block in blocks(data, WIDTH):
        value = int.from_bytes(block, "big")
        best = block
        offsets = (0, 1, -1, 2, -2) if mode in ("correct", "combined") else (0,)
        # Both strategies get the same per-word CPU ceiling and candidate order.
        deadline = process_time_ns() + 5_000_000
        found = False
        for small in range(2, 130):
            for delta in offsets:
                target = value + delta
                if target < 4:
                    continue
                for divisor in (small, isqrt(target) - small + 2):
                    examined += 1
                    if divisor < 2 or target % divisor:
                        continue
                    split = mode in ("split", "combined")
                    recipe = (
                        var(zig(delta))
                        + operand(divisor, split)
                        + operand(target // divisor, split)
                    )
                    if len(recipe) < len(best):
                        best = recipe
                        found = True
                if strategy == "first" and found:
                    break
            if (strategy == "first" and found) or process_time_ns() >= deadline:
                break
        tag = int(len(best) < len(block))
        products += tag
        sizes.append(tag)
        payload.extend(best)
    stats.update(products=products, divisors_examined=examined, cpu_cap_us_per_word=5000)
    return sizes, payload


def unpack(size, profile, meta, body, ref, stats):
    result = bytearray()
    while len(result) < size:
        width = min(WIDTH, size - len(result))
        if meta.byte():
            delta = signed(body.var())
            value = read_operand(body) * read_operand(body) - delta
            result.extend(value.to_bytes(width, "big"))
        else:
            result.extend(body.take(width))
    return result
