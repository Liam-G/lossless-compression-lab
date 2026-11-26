from functools import lru_cache
from lab import load
from wire import blocks, var

ID = 17
PROFILES = ("literal-leaves", "arithmetic-leaves", "shared-leaves", "combined")
arithmetic = load(1, "codec")
factors = load(2, "codec")
grammar = load(11, "codec")


@lru_cache(maxsize=1)
def catalog():
    return arithmetic.catalog(True)


def pack(data, profile, ref, stats):
    dictionary = {}
    body = bytearray()
    for word in blocks(data, 16):
        value = int.from_bytes(word, "big")
        a = next((d for d in range(2, 130) if value >= 2 * d and value % d == 0), 1)
        body.extend(var(a))
        n = value // a
        literal = factors.operand(n, False)
        recipe = catalog().get(n) if profile in ("arithmetic-leaves", "combined") else None
        leaf = b"\0" + literal
        if recipe and 1 + len(recipe) < len(literal):
            leaf = bytes([1, len(recipe)]) + recipe
        if profile in ("shared-leaves", "combined"):
            if n in dictionary:
                leaf = b"\2" + grammar.token_bytes(256 + dictionary[n])
            else:
                dictionary[n] = len(dictionary)
        body.extend(leaf)
    return b"", body


def unpack(size, profile, meta, body, ref, stats):
    table = []
    out = bytearray()
    while len(out) < size:
        a, tag = body.var(), body.byte()
        if tag == 2:
            n = table[grammar.read_token(body) - 256]
        else:
            n = (
                arithmetic.reconstruct(body.take(body.byte()))
                if tag
                else factors.read_operand(body)
            )
            if profile in ("shared-leaves", "combined"):
                table.append(n)
        out.extend((a * n).to_bytes(min(16, size - len(out)), "big"))
    return out


def datasets(f, rng):
    values = [((1 << p) - 1) // 13 for p in (72, 84, 96, 108)]
    yield (
        "shared-quotient-factors",
        b"".join((2 * rng.choice(values)).to_bytes(16, "big") for _ in range(80)),
        b"",
    )
    yield "real-cofactor-words", (f / "integer.bin").read_bytes(), b""
