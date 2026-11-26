from regions import constants


def datasets(codec, fixtures, rng):
    data = bytearray()
    for _ in range(6):
        data.extend(rng.randbytes(11))
        data.extend(((5**64 - 1) // 4).to_bytes(24, "big"))
        data.extend(bytes(rng.choice((0, 0xA5)) for _ in range(16)))
        data.extend(constants()[3])
    yield "mixed-11-24-16-8", bytes(data), b""
    # Different factors and masks prevent repeated complete motifs from dominating.
    data = bytearray()
    for exponent in rng.sample(range(74, 101), 12):
        data.extend(rng.randbytes(48))
        data.extend(((5**exponent - 1) // 4).to_bytes(32, "big"))
        basis = rng.randrange(1, 256)
        data.extend(bytes(rng.choice((0, basis)) for _ in range(64)))
        data.extend(rng.choice(constants()))
    yield "mixed-varying-recipes", bytes(data), b""
    for name in ("rusage.elf", "scanner.elf", "medical.bin"):
        yield name, (fixtures / name).read_bytes()[:512], b""
