"""Two-factor GF(2) approximation with a lossless correction mask."""

import zlib
from wire import blocks, var

ID = 8
PROFILES = ("initial", "swap", "xor", "search")


def combinations(basis):
    values = [0]
    for vector in basis:
        values += [v ^ vector for v in values]
    return values


def approximate(rows):
    # Greedily minimize residual Hamming weight over observed candidate rows.
    basis = []
    for _ in range(2):
        candidates = set(rows) - set(combinations(basis))
        if not candidates:
            basis.append(0)
            continue

        def error(candidate):
            predictions = combinations(basis + [candidate])
            return sum(min((r ^ v).bit_count() for v in predictions) for r in rows)

        basis.append(min(candidates, key=lambda v: (error(v), v)))
    values = combinations(basis)
    coords = [min(range(4), key=lambda i: (r ^ values[i]).bit_count()) for r in rows]
    return coords, basis, bytes(r ^ values[c] for r, c in zip(rows, coords))


def transform(coords, basis, mode):
    a, b = basis
    if mode == "swap":
        return [((c & 1) << 1) | (c >> 1) for c in coords], [b, a]
    # b' = b XOR a; the first coordinate receives the second.
    return [c ^ (c >> 1) for c in coords], [a, b ^ a]


def fields(coords, basis):
    # Variable-width integer framing makes factor orientation measurable.
    columns = [sum((c >> j & 1) << i for i, c in enumerate(coords)) for j in range(2)]
    return b"".join(var(v) for v in columns), b"".join(var(v) for v in basis)


def pack(data, profile, ref, stats):
    u, v, e = bytearray(), bytearray(), bytearray()
    for block in blocks(data, 16):
        coords, basis, errors = approximate(block)
        options = [(coords, basis)]
        if profile in ("swap", "search"):
            options.append(transform(coords, basis, "swap"))
        if profile in ("xor", "search"):
            options.append(transform(coords, basis, "xor"))
        if profile == "search":
            for ops in (("swap", "xor"), ("xor", "swap"), ("xor", "swap", "xor")):
                pair = (coords, basis)
                for op in ops:
                    pair = transform(*pair, op)
                options.append(pair)
        a, b = min((fields(*pair) for pair in options), key=lambda ab: sum(map(len, ab)))
        u.extend(a)
        v.extend(b)
        e.extend(errors)
    errors = zlib.compress(e)
    stats.update(
        U_bytes=len(u),
        V_bytes=len(v),
        E_bytes=len(errors),
        error_bits=sum(x.bit_count() for x in e),
    )
    return var(len(u)) + var(len(v)), bytes(u + v) + errors


def unpack(size, profile, meta, body, ref, stats):
    from wire import Reader

    u, v = (Reader(body.take(meta.var())) for _ in range(2))
    errors = zlib.decompress(body.read())
    if len(errors) != size:
        raise ValueError("Wrong error mask length")
    out = bytearray()
    for block in blocks(errors, 16):
        x, y = u.var(), u.var()
        a, b = v.var(), v.var()
        for i, error in enumerate(block):
            out.append(error ^ (a if x >> i & 1 else 0) ^ (b if y >> i & 1 else 0))
    u.end()
    v.end()
    return out
