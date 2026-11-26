def datasets(codec, fixtures, rng):
    for name in ("frequent-multiplier", "conditional-offset"):
        pairs = []
        for _ in range(160):
            a = rng.choice((2, 3, 7, 240)) if name == "conditional-offset" else 240
            c = (
                100 * a + rng.randrange(-2, 3)
                if name == "conditional-offset"
                else rng.randrange(-40, 40)
            )
            pairs.append(codec.PAIR.pack(a, c))
        yield name, b"".join(pairs), b""
    for name in ("affine-0.bin", "affine-1.bin"):
        yield name, (fixtures / name).read_bytes(), b""
