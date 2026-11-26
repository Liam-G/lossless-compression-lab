def datasets(codec, fixtures, rng):
    for family in ("power", "sum", "product"):
        inputs = [codec.generate(family, rng.randrange(64), 16) for _ in range(24)]
        for method in ("small-offset", "bit-flips"):
            values = [
                (n + 3 if method == "small-offset" else n ^ (1 << 77) ^ 2) % 2**128 for n in inputs
            ]
            yield family + "-" + method, b"".join(n.to_bytes(16, "big") for n in values), b""
    for name in ("integer.bin", "medical.bin"):
        yield name, (fixtures / name).read_bytes(), b""
