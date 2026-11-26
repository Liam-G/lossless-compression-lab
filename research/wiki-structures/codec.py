"""Price page permutations, arithmetic templates and links to a recoverable title vocabulary."""

import argparse
from collections import Counter
from io import BytesIO
import json
import lzma
from pathlib import Path
import re
import struct
import sys

import zstandard as zstd
import wiki_order
import wiki_templates

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from wire import Reader, var

HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BBBI")
BLOCK = 8 << 20
TITLE = re.compile(rb"(?m)^    <title>([^\r\n<]*)</title>\n")
LINK = re.compile(rb"\[\[([^\[\]\n|#<>]{3,240})(?=[|#]|\]\])")
PROFILES = (
    "direct",
    "templates",
    "ordering",
    "links",
    "joint",
    "direct-xz",
    "joint-xz",
)


def titles(data):
    return list(dict.fromkeys(TITLE.findall(data)))


def link_view(data):
    known = titles(data)
    indices = {t: i for i, t in enumerate(known)}
    hits = list(LINK.finditer(data))
    counts = Counter(m[1] for m in hits if m[1] not in indices)
    extra = [t for t, n in counts.most_common() if n >= 3 and (n - 1) * len(t) > 4 * n][
        :16384
    ]
    for t in extra:
        indices[t] = len(indices)
    dictionary = var(len(extra)) + b"".join(var(len(t)) + t for t in extra)
    parts = []
    gaps = bytearray()
    references = bytearray()
    cursor = count = 0
    for m in hits:
        token = indices.get(m[1])
        if token is None:
            continue
        start, end = m.span(1)
        chunk = data[cursor:start]
        gaps.extend(var(len(chunk)))
        references.extend(var(token))
        parts.append(chunk)
        count += 1
        cursor = end
    parts.append(data[cursor:])
    stripped = b"".join(parts)
    if titles(stripped) != known:
        raise ValueError("A substitution changed the available title table")
    return (
        dictionary
        + var(count)
        + var(len(gaps))
        + var(len(references))
        + gaps
        + references
        + stripped
    )


def unlink(view):
    stream = Reader(view)
    n = stream.var()
    if n > 16384:
        raise ValueError("Oversized link dictionary")
    extra = [stream.take(stream.var()) for _ in range(n)]
    total, ng, nr = stream.var(), stream.var(), stream.var()
    gaps = Reader(stream.take(ng))
    refs = Reader(stream.take(nr))
    body = stream.read()
    book = titles(body) + extra
    raw = Reader(body)
    result = BytesIO()
    for _ in range(total):
        gap = gaps.var()
        i = refs.var()
        if i >= len(book):
            raise ValueError("Invalid link index")
        result.write(raw.take(gap))
        result.write(book[i])
    result.write(raw.read())
    gaps.end()
    refs.end()
    return result.getvalue()


def candidates(data, profile):
    yield 0, 0, data
    if profile == "direct":
        return
    orders = [0, 1, 2] if profile in ("ordering", "joint") else [0]
    for order in orders:
        try:
            ordered = (
                wiki_order.encode(data, ("title", "similar")[order - 1])[0]
                if order
                else data
            )
        except ValueError:
            continue
        if order:
            yield order, 0, ordered
        if profile in ("links", "joint"):
            try:
                linked = link_view(ordered)
            except ValueError:
                pass
            else:
                yield order, 3, linked
        if profile in ("templates", "joint"):
            for arithmetic in (False, True):
                view, _ = wiki_templates.encode(ordered, arithmetic)
                yield order, 1 + int(arithmetic), view


def pack(src, out, profile):
    size = src.seek(0, 2)
    src.seek(0)
    out.write(HEADER.pack(b"WKS1", size))
    strong = profile.endswith("-xz")
    profile = profile.removesuffix("-xz")
    z = zstd.ZstdCompressor(level=6)
    histogram = Counter()
    while data := src.read(BLOCK):
        best = (len(data), 0, 0, 0, data)
        ranked = []
        for order, field, view in candidates(data, profile):
            packed = z.compress(view)
            option = (len(packed), order, field, 1, packed)
            if option[:4] < best[:4]:
                best = option
            if strong:
                ranked.append((len(packed), order, field, view))
                ranked = sorted(ranked, key=lambda x: x[:3])[:2]
        if strong:
            shortlist = {(order, field): view for _, order, field, view in ranked}
            shortlist.setdefault((0, 0), data)
            for (order, field), view in shortlist.items():
                packed = lzma.compress(view, preset=6)
                option = (len(packed), order, field, 2, packed)
                if option[:4] < best[:4]:
                    best = option
        length, order, field, backend, payload = best
        out.write(RECORD.pack(order, field, backend, length))
        out.write(payload)
        histogram[f"{order}/{field}/{backend}"] += 1
    return histogram


def unpack(src, out):
    magic, remaining = HEADER.unpack(src.read(HEADER.size))
    if magic != b"WKS1":
        raise ValueError("Invalid wiki structure archive")
    while remaining:
        expect = min(BLOCK, remaining)
        order, field, backend, n = RECORD.unpack(src.read(RECORD.size))
        if order > 2 or field > 3 or backend > 2 or n > expect:
            raise ValueError("Invalid page bank")
        body = src.read(n)
        if len(body) != n:
            raise ValueError("Truncated page bank")
        if backend == 1:
            body = zstd.ZstdDecompressor().decompress(body)
        if backend == 2:
            body = lzma.decompress(body)
        if field == 3:
            body = unlink(body)
        elif field:
            body = wiki_templates.decode(body)
        if order:
            body = wiki_order.decode(body)
        if len(body) != expect:
            raise ValueError("Incorrect page bank width")
        out.write(body)
        remaining -= expect
    if src.read(1):
        raise ValueError("Trailing page banks")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.source.open("rb") as src, a.output.open("xb") as out:
        if a.mode == "encode":
            print(json.dumps(pack(src, out, a.profile)))
        else:
            unpack(src, out)
