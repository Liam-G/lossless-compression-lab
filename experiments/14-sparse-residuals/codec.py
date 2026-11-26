"""Enumerative, Rice gap and adaptive KT context codes for binary masks."""

from itertools import chain, repeat
from subsets import rank, unrank, bits_needed
from wire import blocks, var

ID = 14
DEPENDENCIES = ("subsets",)
PROFILES = ("enumerative", "rice", "context", "adaptive")


def padded(bits):
    return int(bits.ljust((len(bits) + 7) // 8 * 8, "0") or "0", 2).to_bytes(
        (len(bits) + 7) // 8, "big"
    )


def context(data, n, decode=False):
    low, high, pending = 0, 2**32 - 1, 0
    half, quarter = 2**31, 2**30
    bits = chain((int(b) for byte in data for b in f"{byte:08b}"), repeat(0))
    code = 0
    if decode:
        for _ in range(32):
            code = 2 * code + next(bits)
    output = []
    counts = {}
    history = 0
    for pos in range(n):
        key = (pos % 8, history)
        zero, total = counts.get(key, (1, 2))
        pivot = low + (high - low + 1) * zero // total
        bit = int(code >= pivot) if decode else next(bits)
        if decode:
            output.append(str(bit))
        if bit:
            low = pivot
        else:
            high = pivot - 1
        counts[key] = (zero + 2 * (1 - bit), total + 2)
        history = (history * 2 + bit) % 4
        while True:
            if high < half:
                shift = 0
            elif low >= half:
                shift = half
            elif low >= quarter and high < 3 * quarter:
                shift = quarter
            else:
                break
            if decode:
                code = 2 * (code - shift) + next(bits)
            elif shift == quarter:
                pending += 1
            else:
                digit = int(shift == half)
                output.extend([str(digit), str(1 - digit) * pending])
                pending = 0
            low, high = 2 * (low - shift), 2 * (high - shift) + 1
    if not decode:
        digit = int(low >= quarter)
        output.extend([str(digit), str(1 - digit) * (pending + 1)])
    return padded("".join(output))


def record(block, mode):
    n = 8 * len(block)
    value = int.from_bytes(block, "little")
    k = value.bit_count()
    if mode == "enumerative":
        return var(k), rank(value).to_bytes((bits_needed(n, k) + 7) // 8, "big")
    if mode == "context":
        return b"", context(block, n)
    gaps = []
    previous = -1
    for i in range(n):
        if value >> i & 1:
            gaps.append(i - previous - 1)
            previous = i

    def cost(p):
        return sum((g >> p) + 1 + p for g in gaps)

    p = min(range(8), key=cost)
    bits = "".join("1" * (g >> p) + "0" + (format(g % 2**p, f"0{p}b") if p else "") for g in gaps)
    return bytes([p]) + var(k), padded(bits)


def pack(data, profile, ref, stats):
    meta, body = bytearray(), bytearray()
    counts = {}
    for block in blocks(data, 32):
        options = []
        for mode in PROFILES[:3] if profile == "adaptive" else (profile,):
            header, payload = record(block, mode)
            head = (
                (bytes([PROFILES.index(mode)]) if profile == "adaptive" else b"")
                + header
                + var(len(payload))
            )
            options.append((mode, head, payload))
        mode, head, payload = min(options, key=lambda t: len(t[1]) + len(t[2]))
        meta.extend(head)
        body.extend(payload)
        counts[mode] = counts.get(mode, 0) + 1
    stats["mode_counts"] = counts
    return meta, body


def unpack(size, profile, meta, body, ref, stats):
    out = bytearray()
    while len(out) < size:
        width = min(32, size - len(out))
        mode = PROFILES[meta.byte()] if profile == "adaptive" else profile
        if mode == "context":
            out.extend(context(body.take(meta.var()), width * 8, True))
            continue
        p = meta.byte() if mode == "rice" else 0
        k = meta.var()
        data = body.take(meta.var())
        if mode == "enumerative":
            value = unrank(width * 8, k, int.from_bytes(data, "big"))
        else:
            bits = iter("".join(f"{v:08b}" for v in data))
            value = 0
            pos = -1
            for _ in range(k):
                q = 0
                while next(bits) == "1":
                    q += 1
                r = int("".join(next(bits) for _ in range(p)) or "0", 2)
                pos += 1 + (q << p) + r
                value |= 1 << pos
        out.extend(value.to_bytes(width, "little"))
    return out
