def datasets(codec, fixtures, rng):
    for radix in (10, 36):
        catalog = codec.catalog(4, "signed", radix)
        for width in (4, 12):
            data = b"".join(rng.choice(catalog)[:width] for _ in range(192 // width))
            yield f"base{radix}-prefix{width}", data, b""
        yield (
            f"random-base{radix}",
            bytes(rng.choice(codec.ALPHABET[:radix]) for _ in range(192)),
            b"",
        )
    for name in ("identifiers-codec.txt", "identifiers-grammar.txt"):
        yield name, (fixtures / name).read_bytes(), b""
