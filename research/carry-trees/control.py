"""Hide distinct real source fragments behind page-local arithmetic maps."""

import argparse
from pathlib import Path
from random import Random
from codec import transform

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    rng = Random(65079)
    with a.source.open("rb") as src, a.output.open("xb") as dest:
        while data := src.read(1 << 17):
            dest.write(
                transform(
                    data,
                    rng.choice((5, 12, 13, 17, 31, 257, 65537)),
                    bool(rng.getrandbits(1)),
                )
            )
