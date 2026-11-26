"""Block BWT with a frozen seed catalog and a common DEFLATE residual coder."""

import zlib
from functools import lru_cache
from wire import blocks, var, xor

ID = 13
PROFILES = tuple(
    f"{mode}-{width}" for width in (16, 64) for mode in ("direct", "bwt", "predict", "combined")
)
CONTRASTS = [(f"gain_{w}", f"bwt-{w}", f"predict-{w}", f"combined-{w}") for w in (16, 64)]


def bwt(data):
    order = sorted(range(len(data)), key=lambda offset: data[offset:] + data[:offset])
    return bytes(data[i - 1] for i in order), order.index(0)


def inverse(data, row):
    order = sorted(range(len(data)), key=data.__getitem__)
    out = bytearray()
    for _ in data:
        row = order[row]
        out.append(data[row])
    return out


@lru_cache(maxsize=4096)
def predict(index, n):
    state = (index - 1) % 8 + 1
    out = bytearray()
    while len(out) < n:
        if index <= 8:
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        else:
            state ^= (state << 13) & 0xFFFFFFFF
            state ^= state >> 17
            state ^= (state << 5) & 0xFFFFFFFF
        out.extend(state.to_bytes(4, "big"))
    return bytes(out[:n])


def pack(data, profile, ref, stats):
    mode, width = profile.split("-")
    meta, payload = bytearray(), bytearray()
    row_bytes = seed_bytes = 0
    for raw in blocks(data, int(width)):
        block = raw
        if mode in ("bwt", "combined"):
            block, row = bwt(raw)
            meta.append(row)
            row_bytes += 1
        best = zlib.compress(block)
        if mode in ("predict", "combined"):
            seed = 0
            for i in range(1, 17):
                candidate = zlib.compress(xor(block, predict(i, len(block))))
                if len(candidate) < len(best):
                    best, seed = candidate, i
            meta.append(seed)
            seed_bytes += 1
        meta.extend(var(len(best)))
        payload.extend(best)
    stats.update(primary_index_bytes=row_bytes, seed_bytes=seed_bytes)
    return meta, payload


def unpack(size, profile, meta, body, ref, stats):
    mode, _ = profile.split("-")
    out = bytearray()
    while len(out) < size:
        row = meta.byte() if mode in ("bwt", "combined") else None
        seed = meta.byte() if mode in ("predict", "combined") else 0
        block = zlib.decompress(body.take(meta.var()))
        if seed:
            block = xor(block, predict(seed, len(block)))
        out.extend(inverse(block, row) if row is not None else block)
    return out
