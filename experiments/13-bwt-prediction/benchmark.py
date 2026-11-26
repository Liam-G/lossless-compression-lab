def datasets(codec, fixtures, rng):
    yield "lcg-seeds", b"".join(codec.predict(i % 8 + 1, 16) for i in range(32)), b""
    records = [bytes([i // 8, i % 8]) * 4 for i in range(64)]
    yield "ordered-records", b"".join(records), b""
    rng.shuffle(records)
    yield "shuffled-records", b"".join(records), b""
    for name in ("bytecode-bwt.bin", "bytecode-base.bin"):
        yield name, (fixtures / name).read_bytes(), b""
