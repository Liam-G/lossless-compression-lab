"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    rows = bytes([0, 0x14, 0x87, 0x93] * 4)
    coords, basis, errors = c.approximate(rows)
    assert not any(errors)
    for mode in ("swap", "xor"):
        revised, v = c.transform(coords, basis, mode)
        assert bytes(c.combinations(v)[i] ^ e for i, e in zip(revised, errors)) == rows
