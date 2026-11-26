"""Walsh–Hadamard predictor with exact XOR residuals and optional bit planes."""

import zlib
from functools import lru_cache
from wire import blocks, var, zig, signed, xor

ID = 9
PROFILES = ("direct", "planes", "spectral", "combined")
CONTRASTS = [("combined_gain", "planes", "spectral", "combined")]


def layout(block, planes):
    bits = [(v >> k) & 1 for v in block for k in range(8)]
    return [bit for k in range(8) for bit in bits[k::8]] if planes else bits


def to_bytes(bits):
    return bytes(sum(bit << i for i, bit in enumerate(part)) for part in blocks(bits, 8))


def fwht(values):
    values = list(values)
    stride = 1
    while stride < len(values):
        for i in range(0, len(values), 2 * stride):
            for j in range(i, i + stride):
                a, b = values[j], values[j + stride]
                values[j], values[j + stride] = a + b, a - b
        stride *= 2
    return values


def prediction(length, terms):
    if not terms:
        return bytes(length // 8)
    spectrum = [0] * (1 << (length - 1).bit_length())
    for index, amplitude in terms:
        spectrum[index] = amplitude
    return to_bytes([int(v > 0) for v in fwht(spectrum)[:length]])


@lru_cache(maxsize=8192)
def encode_block(block, profile):
    bits = layout(block, profile in ("planes", "combined"))
    raw = to_bytes(bits)
    options = [(b"\0", zlib.compress(raw))]
    if profile in ("spectral", "combined"):
        signs = [2 * b - 1 for b in bits]
        signs += [0] * ((1 << (len(bits) - 1).bit_length()) - len(bits))
        coeff = fwht(signs)
        order = sorted(range(len(coeff)), key=lambda i: -abs(coeff[i]))
        for k in (1, 2, 4, 8):
            terms = [(i, coeff[i]) for i in order[:k]]
            header = bytes([len(terms)]) + b"".join(var(i) + var(zig(a)) for i, a in terms)
            options.append((header, zlib.compress(xor(raw, prediction(len(bits), terms)))))
    header, errors = min(options, key=lambda ab: len(ab[0]) + len(ab[1]) + len(var(len(ab[1]))))
    return header, errors


def pack(data, profile, ref, stats):
    meta, body = bytearray(), bytearray()
    histogram = {}
    for block in blocks(data, 32):
        header, errors = encode_block(block, profile)
        histogram[header[0]] = histogram.get(header[0], 0) + 1
        meta.extend(header + var(len(errors)))
        body.extend(errors)
    stats["coefficient_counts"] = histogram
    return meta, body


def unpack(size, profile, meta, body, ref, stats):
    out = bytearray()
    while len(out) < size:
        n = min(32, size - len(out))
        terms = [(meta.var(), signed(meta.var())) for _ in range(meta.byte())]
        residual = zlib.decompress(body.take(meta.var()))
        raw = xor(residual, prediction(8 * n, terms))
        if profile in ("planes", "combined"):
            bits = layout(raw, False)
            raw = bytes(sum(bits[k * n + i] << k for k in range(8)) for i in range(n))
        out.extend(raw)
    return out
