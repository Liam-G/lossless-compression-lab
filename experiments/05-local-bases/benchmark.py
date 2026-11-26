def datasets(codec, fixtures, rng):
    words = []
    for i in range(32):
        b = rng.choice((3, 5, 10, 16))
        n = 80 // b.bit_length()
        word = (b**n - 1) // (b - 1) * rng.randrange(1, b)
        words.append((word + b ** (i % n)).to_bytes(16, "big"))
    yield "mixed-local-bases", b"".join(words), b""
    for name in ("integer.bin", "medical.bin"):
        yield name, (fixtures / name).read_bytes(), b""
