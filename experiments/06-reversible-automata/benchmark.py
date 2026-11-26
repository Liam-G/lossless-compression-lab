def datasets(codec, fixtures, rng):
    for rule in ("checker", "margolus"):
        words = []
        for i in range(24):
            word = sum(1 << j for j in rng.sample(range(64), 3))
            for _ in range(1 + i % 7):
                word = codec.step(word, rule)
            words.append(word.to_bytes(8, "little"))
        yield rule + "-sparse-orbits", b"".join(words), b""
    for name in ("fax.bin", "fax-mid.bin", "medical.bin"):
        yield name, (fixtures / name).read_bytes()[:192], b""
