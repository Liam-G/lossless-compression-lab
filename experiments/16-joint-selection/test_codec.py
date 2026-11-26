"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    source = (bytes([165, 0, 0, 165]) * 8) + ((5**64 - 1) // 4).to_bytes(24, "big")
    sizes = []
    for mode in c.PROFILES:
        archive, stats = encode(c, source, mode)
        assert stats["record_bytes"] + 12 == len(archive) or stats["record_bytes"] + 11 == len(
            archive
        )
        assert decode(c, archive)[0] == source
        sizes.append(len(archive))
    assert sizes[2] <= min(sizes[:2]) and sizes[3] <= sizes[2]
