def datasets(codec, fixtures, rng):
    base = rng.randbytes(512)
    for n in (1, 16, 64):
        yield f"insert-{n}", base[:139] + rng.randbytes(n) + base[139:], base
    yield "moved-region", base[300:] + base[:300], base
    for name, old, new in (
        ("source-revisions", "grammar-fd90565.txt", "grammar-1061fc7.txt"),
        ("logo-revisions", "logo-old.png", "logo-new.png"),
    ):
        source = (fixtures / old).read_bytes()
        target = (fixtures / new).read_bytes()
        yield name, target, source
        yield name + "-insert16", target[:19] + rng.randbytes(16) + target[19:], source
