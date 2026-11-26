"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode

    raw = ((3**65 - 1) // 2 + 3**17).to_bytes(16, "big")
    archive, stats = encode(c, raw, "local-bytes")
    assert len(archive) < len(raw) + 11 and decode(c, archive)[0] == raw
