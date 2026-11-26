"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    ops = [(-2, 3), (5, -7), (0, -4), (-3, -2)]
    assert c.evaluate(ops, False) == c.evaluate(ops, True) == 10
    assert c.evaluate([], True) == 0
