"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    source = (b"((abc)+(abc))" + bytes(range(128, 256))) * 8
    for profile in ("grammar", "dag"):
        archive, stats = encode(c, source, profile)
        assert stats["rule_count"] and decode(c, archive)[0] == source
