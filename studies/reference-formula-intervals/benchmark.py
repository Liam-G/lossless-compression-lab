from collections import defaultdict
from hashlib import sha256
from lab import load
from regions import elf_header, constants
from wire import Reader, var

ID = 19
PROFILES = ("copies", "formulas", "mixed")
patch, regions = load(12, "codec"), load(15, "codec")


def pack(data, profile, ref, stats):
    candidates = defaultdict(list)

    def add(start, n, kind, recipe):
        record = var(start) + var(n) + bytes([kind]) + var(len(recipe)) + recipe
        if n > len(record):
            candidates[start].append((n, kind, record))

    if profile != "formulas":
        for start, source, n in patch.copy_matches(ref, data):
            add(start, n, 4, var(source))
    if profile != "copies":
        for item in regions.candidates(data, "combined"):
            add(*item)
    # The first external copy pays the reference digest. Carry that state through the DP.
    cost = [[0, 0] for _ in range(len(data) + 1)]
    choices = {}
    for i in reversed(range(len(data))):
        for pinned in (0, 1):
            cost[i][pinned] = 1 + cost[i + 1][pinned]
            for n, kind, record in candidates.get(i, ()):
                needs = int(kind == 4)
                price = len(record) + 32 * int(needs and not pinned) + cost[i + n][pinned | needs]
                if price < cost[i][pinned]:
                    cost[i][pinned] = price
                    choices[i, pinned] = (n, needs, record)
    meta, body = bytearray(), bytearray()
    i = pinned = 0
    while i < len(data):
        item = choices.get((i, pinned))
        if item:
            n, needs, record = item
            pinned |= needs
            meta.extend(record)
            i += n
        else:
            body.append(data[i])
            i += 1
    digest = sha256(ref).digest() if pinned else b""
    assert len(meta) + len(digest) + len(body) == cost[0][0]
    stats["uses_base"] = bool(pinned)
    return bytes([pinned]) + digest + meta, body


def unpack(size, profile, meta, body, ref, stats):
    if meta.byte() and meta.take(32) != sha256(ref).digest():
        raise ValueError("Reference mismatch")
    out = bytearray()
    while meta.tell() < meta.getbuffer().nbytes:
        start, n, kind = meta.var(), meta.var(), meta.byte()
        recipe = meta.take(meta.var())
        out.extend(body.take(start - len(out)))
        if kind == 4:
            source = Reader(recipe).var()
            value = ref[source : source + n]
        elif kind == 3:
            pos = start - Reader(recipe).var()
            value = out[pos : pos + n]
        elif kind == 2:
            value = recipe * n
        elif kind == 1:
            value = constants()[recipe[0]]
        else:
            value = elf_header(recipe)
        out.extend(value)
    return out + body.read()


def datasets(f, rng):
    base = rng.randbytes(1024)
    yield "copied-and-generated", base[:512] + bytes(200) + base[514:], base
    for name, old, new in (
        ("src", "grammar-fd90565.txt", "grammar-1061fc7.txt"),
        ("logo", "logo-old.png", "logo-new.png"),
    ):
        yield name, (f / new).read_bytes(), (f / old).read_bytes()
