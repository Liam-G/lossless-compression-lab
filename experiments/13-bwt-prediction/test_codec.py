"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    for source in (b"banana", b"abababab", bytes(range(64))):
        transformed, row = c.bwt(source)
        assert bytes(c.inverse(transformed, row)) == source
