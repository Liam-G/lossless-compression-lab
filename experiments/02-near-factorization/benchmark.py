def datasets(codec, fixtures, rng):
    products = [(10**25 + rng.randrange(1, 100)) * rng.choice((17, 31, 67, 113)) for _ in range(32)]
    for name, delta in (("hidden-products", 0), ("perturbed-products", 1)):
        yield name, b"".join((n - delta).to_bytes(16, "big") for n in products), b""
    for name in ("integer.bin", "rusage.elf", "scanner.elf"):
        yield name, (fixtures / name).read_bytes()[:512], b""
