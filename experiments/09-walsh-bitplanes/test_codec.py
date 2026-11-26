"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    spectrum = c.fwht([1, -1, 1, -1] * 4)
    assert spectrum[1] == 16
    assert c.prediction(16, [(1, 16)]) == bytes([85, 85])
