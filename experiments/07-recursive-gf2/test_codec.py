"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import encode, decode
    from struct import pack

    rows = (0x3E, 0x44, 0x7A, 0) * 4
    moved = c.step(c.step(rows, 16), 16)
    assert c.step(c.step(moved, 16, True), 16, True) == rows
    raw = pack("<16H", *moved) * 3 + b"tail"
    archive, _ = encode(c, raw, "pre-3")
    recovered, stats = decode(c, archive)
    assert recovered == raw and any("factor" in k for k in stats["paths"])
