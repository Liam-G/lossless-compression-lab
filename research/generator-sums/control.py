"""Distinct 4 KiB sums, alternating exact predictions and short signed corrections."""

import argparse
from pathlib import Path
from random import Random
from decoder import prediction

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    rng = Random(763721)
    seen = set()
    with a.output.open("xb") as dest:
        while len(seen) < 6144:
            seeds = tuple(rng.randrange(256) for _ in range(3))
            if seeds in seen:
                continue
            residual = rng.randrange(-65535, 65536) if len(seen) % 2 else 0
            value = prediction(seeds, 4096) + residual
            if 0 <= value < 1 << 32768:
                seen.add(seeds)
                dest.write(value.to_bytes(4096, "big"))
