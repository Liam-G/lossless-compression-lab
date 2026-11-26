from lab import load
from wire import blocks, var, encode, decode

ID = 18
PROFILES = (
    "direct-enumerative",
    "orbit-enumerative",
    "orbit-rice",
    "orbit-context",
    "orbit-adaptive",
)
orbit, factoring, model, residual = (load(i, "codec") for i in (6, 7, 8, 14))


def decompose(block):
    coords, basis, errors = model.approximate(block)
    mask = sum(c << (i * 2) for i, c in enumerate(coords))
    return bytes(basis) + mask.to_bytes(2, "little"), errors


def pack(data, profile, ref, stats):
    transform, code = profile.split("-")
    meta, errors = bytearray(), bytearray()
    stop = len(data) // 8 * 8
    for block in blocks(data[:stop], 8):
        state = int.from_bytes(block, "little")
        candidates = []
        for t in range(4 if transform == "orbit" else 1):
            matrix = state.to_bytes(8, "little")
            factors, mask = decompose(matrix)
            exact_rank = factoring.factor(matrix, 8)[0]
            candidates.append((sum(v.bit_count() for v in mask), exact_rank, t, factors, mask))
            state = orbit.step(state, "checker", True)
        _, _, t, factors, mask = min(candidates)
        if transform == "orbit":
            meta.append(t)
        meta.extend(factors)
        errors.extend(mask)
    packed, _ = encode(residual, bytes(errors), code)
    return meta, var(len(packed)) + packed + data[stop:]


def unpack(size, profile, meta, body, ref, stats):
    errors, _ = decode(residual, body.take(body.var()))
    out = bytearray()
    for mask in blocks(errors, 8):
        t = meta.byte() if profile.startswith("orbit") else 0
        basis = meta.take(2)
        coords = int.from_bytes(meta.take(2), "little")
        table = model.combinations(basis)
        raw = bytes(table[(coords >> (2 * i)) & 3] ^ v for i, v in enumerate(mask))
        state = int.from_bytes(raw, "little")
        for _ in range(t):
            state = orbit.step(state, "checker")
        out.extend(state.to_bytes(8, "little"))
    return out + body.take(size % 8)


def datasets(f, rng):
    out = bytearray()
    for _ in range(48):
        a, b = rng.sample(range(1, 256), 2)
        rows = bytearray(rng.choice((0, a, b, a ^ b)) for _ in range(8))
        rows[0] ^= 1
        state = orbit.step(int.from_bytes(rows, "little"), "checker")
        out.extend(state.to_bytes(8, "little"))
    yield "evolved-noisy-rank-two", bytes(out), b""
    for name in ("fax-mid.bin", "medical.bin"):
        yield name, (f / name).read_bytes(), b""
