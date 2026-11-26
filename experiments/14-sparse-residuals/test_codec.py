"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    for source in (bytes(32), bytes([255]) * 32, bytes([128, 1]) * 16):
        for mode in c.PROFILES:
            archive, _ = encode(c, source, mode)
            assert decode(c, archive)[0] == source
