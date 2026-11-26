"""Price arithmetic, low-rank and compressed-literal records at competing boundaries."""

from functools import lru_cache
import zlib
from regions import elf_recipe, elf_header, constants
from wire import blocks, var

ID = 16
DEPENDENCIES = ("regions",)
PROFILES = ("single", "fixed", "intervals", "intervals-regions")
LENGTHS = (1, 4, 8, 12, 16, 24, 32, 48, 64)


@lru_cache(maxsize=1)
def repdigits():
    table = {}
    for base in (2, 3, 5, 10, 16, 256):
        for r in range(3, 257):
            unit = (base**r - 1) // (base - 1)
            for digit in range(1, min(base, 16)):
                table.setdefault(digit * unit, (base - 1, r - 1, digit))
    return table


def record(kind, width, body):
    return bytes([kind]) + var(width) + var(len(body)), body


def choices(block, regions=False):
    n = len(block)
    yield record(0, n, zlib.compress(block))
    if n <= 256:
        recipe = repdigits().get(int.from_bytes(block, "big"))
        if recipe:
            yield record(1, n, bytes(recipe))
    # Each row is one byte. Express rank-one matrices by a basis and row selectors.
    basis = next((x for x in block if x), 0)
    if all(row in (0, basis) for row in block):
        mask = sum((row != 0) << i for i, row in enumerate(block))
        yield record(2, n, bytes([basis]) + mask.to_bytes((n + 7) // 8, "little"))
    if regions:
        if n == 64:
            header = elf_recipe(block)
            if header is not None:
                yield record(3, n, header)
        if n == 8 and block in constants():
            yield record(4, n, bytes([constants().index(block)]))


def price(pair):
    return sum(map(len, pair))


@lru_cache(maxsize=16384)
def smallest_short_record(block, regions):
    return min(choices(block, regions), key=price)


def pack(data, profile, ref, stats):
    if profile == "single":
        records = [min(choices(data), key=price)] if data else []
        expected = sum(map(price, records))
    elif profile == "fixed":
        records = [min(choices(block), key=price) for block in blocks(data, 32)]
        expected = sum(map(price, records))
    else:
        size = len(data)
        use_regions = profile == "intervals-regions"
        whole = min(choices(data, use_regions), key=price) if size else None
        # A path of short records pays at least three metadata bytes per 64 raw bytes.
        # A strictly cheaper whole record is necessarily the original DP winner.
        whole_wins = size > max(LENGTHS) and price(whole) < 3 * ((size + max(LENGTHS) - 1) // max(LENGTHS))
        best = [0] * (size + 1)
        path = {}
        if whole_wins:
            best[0] = price(whole)
            path[0] = size, whole
        for pos in reversed(range(0 if whole_wins else size)):
            best[pos] = float("inf")
            widths = {min(w, size - pos) for w in LENGTHS}
            if pos == 0:
                widths.add(size)
            for width in sorted(widths):
                pair = whole if width == size else smallest_short_record(data[pos : pos + width], use_regions)
                cost = price(pair) + best[pos + width]
                if cost < best[pos]:
                    best[pos] = cost
                    path[pos] = (width, pair)
        records = []
        pos = 0
        while pos < size:
            width, pair = path[pos]
            records.append(pair)
            pos += width
        expected = best[0]
    meta = b"".join(a for a, b in records)
    body = b"".join(b for a, b in records)
    if expected != len(meta) + len(body):
        raise ValueError("Interval price disagrees with serialization")
    stats.update(
        records=len(records),
        record_bytes=expected,
        method_counts={
            name: sum(a[0] == i for a, b in records)
            for i, name in enumerate(("literal", "repdigit", "rank", "ELF", "constant"))
        },
    )
    return meta, body


def unpack(size, profile, meta, body, ref, stats):
    out = bytearray()
    while len(out) < size:
        kind, width, n = meta.byte(), meta.var(), meta.var()
        data = body.take(n)
        if kind == 0:
            block = zlib.decompress(data)
        elif kind == 1:
            b, r, c = data
            block = (c * ((b + 1) ** (r + 1) - 1) // b).to_bytes(width, "big")
        elif kind == 2:
            mask = int.from_bytes(data[1:], "little")
            block = bytes(data[0] if mask >> i & 1 else 0 for i in range(width))
        elif kind == 3:
            block = elf_header(data)
        else:
            block = constants()[data[0]]
        if len(block) != width:
            raise ValueError("Invalid candidate width")
        out.extend(block)
    return out
