"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    for rule in ("checker", "margolus"):
        seed = 0x1234567890ABDCFE
        assert c.step(c.step(seed, rule), rule, True) == seed
        assert c.step(c.step(seed, rule, True), rule) == seed
