def datasets(codec, fixtures, rng):
    original = bytes(255 if (i & 3) == 0 else 0 for i in range(512))
    for count in (0, 16, 128):
        sample = bytearray(original)
        for pos in rng.sample(range(len(sample) * 8), count):
            sample[pos // 8] ^= 1 << (pos % 8)
        yield f"periodic-noise{count}", bytes(sample), b""
    # A positive control drawn directly from the predictor's signed basis.
    walsh = bytearray()
    for index in rng.sample(range(1, 256), 16):
        bits = [int((index & j).bit_count() % 2 == 0) for j in range(256)]
        walsh.extend(codec.to_bytes(bits))
    yield "planted-Walsh-basis", bytes(walsh), b""
    for name in ("fax.bin", "fax-mid.bin", "medical.bin"):
        yield name, (fixtures / name).read_bytes(), b""
