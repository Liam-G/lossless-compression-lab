"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    # floor(frac(sqrt(2)) * 10**12) has a published, independently checkable decimal expansion.
    assert c.catalog(2, "positive", 10)[2] == b"414213562373"
    patterns = c.catalog(4, "signed", 36)
    target = patterns[24][:6] + patterns[50][:6]
    segments = c.segments(target, patterns, True, 36)
    assert sum(tag % 32 for tag, body in segments) == len(target)
