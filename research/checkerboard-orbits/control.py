"""Build 96 independent pages of sparse 8×8 seeds and evolve each page a shared distance."""

import argparse
from pathlib import Path
import numpy as np
from codec import BLOCK, evolve

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    rng = np.random.default_rng(386205)
    with args.output.open("xb") as out:
        for page in range(96):
            n = BLOCK // 8
            words = np.zeros(n, np.uint64)
            for _ in range(5):
                words |= np.left_shift(
                    np.uint64(1), rng.integers(0, 64, n, dtype=np.uint64)
                )
            evolve(words, (37, 113, 509, 997)[page % 4])
            out.write(words.tobytes())
