"""Three serializations for signed affine instructions with two evaluation orders."""

from collections import Counter
import struct
from time import perf_counter_ns
from wire import var, zig, signed

ID = 10
PROFILES = ("fixed", "dictionary", "conditional")
PAIR = struct.Struct(">hh")


def evaluate(ops, balanced):
    if not balanced:
        x = 0
        for a, c in ops:
            x = a * x + c
        return x
    layer = list(ops)
    while len(layer) > 1:
        following = []
        for i in range(0, len(layer) - 1, 2):
            a, c = layer[i]
            b, d = layer[i + 1]
            following.append((b * a, b * c + d))
        if len(layer) % 2:
            following.append(layer[-1])
        layer = following
    return layer[0][1] if layer else 0


def pack(data, profile, ref, stats):
    split = len(data) // 4 * 4
    ops = list(PAIR.iter_unpack(data[:split]))
    meta, body = bytearray(), bytearray()
    if profile == "fixed":
        for a, c in ops:
            if a == 240 and -100 <= c <= 153:
                body.append(c + 100)
            elif a == 240:
                body.extend(bytes([254]) + var(zig(c)))
            else:
                body.extend(bytes([255]) + var(zig(a)) + var(zig(c)))
    else:
        counts = Counter(a for a, c in ops)
        order = [a for a, _ in counts.most_common()]
        ids = {a: i for i, a in enumerate(order)}
        meta.extend(var(len(order)))
        offsets = {}
        for a in order:
            meta.extend(var(zig(a)))
        if profile == "conditional":
            hist = {a: Counter() for a in order}
            for a, c in ops:
                hist[a][c] += 1
            for a in order:
                offsets[a] = hist[a].most_common(1)[0][0]
                meta.extend(var(zig(offsets[a])))
        for a, c in ops:
            body.extend(var(ids[a]) + var(zig(c - offsets.get(a, 0))))
    return meta, bytes(body) + data[split:]


def unpack(size, profile, meta, body, ref, stats):
    ops = []
    if profile != "fixed":
        order = [signed(meta.var()) for _ in range(meta.var())]
        offsets = (
            [signed(meta.var()) for _ in order] if profile == "conditional" else [0] * len(order)
        )
    for _ in range(size // 4):
        if profile == "fixed":
            tag = body.byte()
            a = signed(body.var()) if tag == 255 else 240
            c = signed(body.var()) if tag >= 254 else tag - 100
        else:
            index = body.var()
            a, c = order[index], signed(body.var()) + offsets[index]
        ops.append((a, c))
    start = perf_counter_ns()
    first = evaluate(ops, False)
    mid = perf_counter_ns()
    second = evaluate(ops, True)
    end = perf_counter_ns()
    if first != second:
        raise ValueError("Affine evaluation mismatch")
    stats.update(sequential_ns=mid - start, balanced_ns=end - mid, result_bits=first.bit_length())
    return b"".join(PAIR.pack(*op) for op in ops) + body.take(size % 4)
