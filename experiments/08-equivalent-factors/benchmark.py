def datasets(codec, fixtures, rng):
    matrices = []
    for _ in range(24):
        a, b = rng.sample(range(1, 256), 2)
        values = (0, a, b, a ^ b)
        matrices.append(bytearray([a, b] + [rng.choice(values) for _ in range(14)]))
    for mode in ("isolated", "burst", "one-row"):
        out = bytearray()
        for matrix in matrices:
            sample = matrix.copy()
            positions = {
                "isolated": (2, 35, 76, 112),
                "burst": (22, 23, 24, 25),
                "one-row": (40, 42, 44, 46),
            }[mode]
            for pos in positions:
                sample[pos // 8] ^= 1 << (pos % 8)
            out.extend(sample)
        yield mode, bytes(out), b""
    for name in ("fax.bin", "fax-mid.bin", "medical.bin"):
        yield name, (fixtures / name).read_bytes(), b""
