"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    base = bytes(range(128))
    source = base[64:] + b"insert" + base[:64]
    for profile in c.PROFILES:
        archive, _ = encode(c, source, profile, base)
        assert decode(c, archive, base)[0] == source
        try:
            decode(c, archive, base[::-1])
        except ValueError:
            continue
        raise AssertionError("Incorrect reference accepted")
