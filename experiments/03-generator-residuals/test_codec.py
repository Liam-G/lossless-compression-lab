"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    for mode in ("add", "xor"):
        number = c.generate("product", 17, 16)
        number = number - 3 if mode == "add" else number ^ (1 << 89)
        raw = number.to_bytes(16, "big")
        archive, stats = encode(c, raw, "product-" + mode + "-32")
        assert stats["generated_blocks"] == 1 and decode(c, archive)[0] == raw
