"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from wire import Reader

    value = 10**25 + 13
    packed = c.operand(value, True)
    assert len(packed) < len(c.operand(value, False))
    assert c.read_operand(Reader(packed)) == value
