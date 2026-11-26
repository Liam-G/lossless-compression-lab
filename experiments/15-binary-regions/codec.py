"""Select non-overlapping ELF, constant, run and backward-copy intervals."""

from collections import defaultdict
import re
from regions import elf_recipe, elf_header, constants
from wire import var

ID = 15
DEPENDENCIES = ("regions",)
PROFILES = ("literal", "header", "formulas", "combined")
CONTRASTS = [("combined_gain", "header", "formulas", "combined")]
NAMES = ("header", "constant", "run", "copy")


def candidates(data, profile):
    begin = 0
    if profile in ("header", "combined"):
        recipe = elf_recipe(data)
        if recipe is not None:
            yield 0, 64, 0, recipe
    if profile not in ("formulas", "combined"):
        return
    # Both formula profiles search the same region outside a recognized ELF header.
    begin = 64 if elf_recipe(data) is not None else 0
    for i, pattern in enumerate(constants()):
        pos = data.find(pattern, begin)
        while pos != -1:
            yield pos, 8, 1, bytes([i])
            pos = data.find(pattern, pos + 1)
    for match in re.finditer(rb"(.)\1{5,}", data[begin:], re.DOTALL):
        yield begin + match.start(), len(match.group()), 2, match.group(1)
    previous = {}
    for pos in range(begin, len(data) - 7):
        key = data[pos : pos + 8]
        old = previous.get(key)
        previous[key] = pos
        if old is not None and pos - old >= 8:
            width = 8
            while (
                width < min(64, pos - old, len(data) - pos)
                and data[old + width] == data[pos + width]
            ):
                width += 1
            yield pos, width, 3, var(pos - old)


def pack(data, profile, ref, stats):
    proposals = defaultdict(list)
    for start, width, kind, recipe in candidates(data, profile):
        record = var(start) + var(width) + bytes([kind]) + var(len(recipe)) + recipe
        if len(record) < width:
            proposals[start].append((width, kind, record))
    best = [0] * (len(data) + 1)
    chosen = {}
    for i in reversed(range(len(data))):
        best[i] = best[i + 1]
        for width, kind, record in proposals.get(i, ()):
            saving = width - len(record) + best[i + width]
            if saving > best[i]:
                best[i] = saving
                chosen[i] = (width, kind, record)
    meta, body = bytearray(), bytearray()
    totals = {name: [0, 0] for name in NAMES}
    pos = 0
    while pos < len(data):
        if pos in chosen:
            width, kind, record = chosen[pos]
            meta.extend(record)
            totals[NAMES[kind]][0] += width
            totals[NAMES[kind]][1] += len(record)
            pos += width
        else:
            body.append(data[pos])
            pos += 1
    stats["covered_and_record_bytes"] = totals
    return meta, body


def unpack(size, profile, meta, body, ref, stats):
    from wire import Reader

    out = bytearray()
    while meta.tell() < meta.getbuffer().nbytes:
        pos, width, kind = meta.var(), meta.var(), meta.byte()
        recipe = meta.take(meta.var())
        out.extend(body.take(pos - len(out)))
        if kind == 0:
            data = elf_header(recipe)
        elif kind == 1:
            data = constants()[recipe[0]]
        elif kind == 2:
            data = recipe * width
        else:
            start = pos - Reader(recipe).var()
            data = out[start : start + width]
        if len(data) != width:
            raise ValueError("Invalid region length")
        out.extend(data)
    return out + body.read()
