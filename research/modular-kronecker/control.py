"""Build fresh byte-valued tensor products, perturb single cells, then evolve each bank."""

import argparse
from pathlib import Path
import numpy as np
from codec import BLOCK, factors_to_grid, step


def generate(path, seed, free_pivot=False):
    rng = np.random.default_rng(seed)
    with path.open("xb") as out:
        for bank in range(96):
            shape = (BLOCK // 256, 16)
            a = rng.integers(0, 256, shape, dtype=np.uint8)
            b = rng.integers(0, 256, shape, dtype=np.uint8)
            if not free_pivot:
                a[:, 0] |= 1
                b[:, 0] |= 1
            grid = factors_to_grid(a, b)
            noise = rng.integers(0, 128, grid.shape, dtype=np.uint8) == 0
            grid[noise] += rng.integers(1, 256, np.count_nonzero(noise), dtype=np.uint8)
            for _ in range((1, 2, 4)[bank % 3]):
                step(grid)
            out.write(grid.tobytes())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--seed", type=int, default=971827)
    p.add_argument("--free-pivot", action="store_true")
    a = p.parse_args()
    generate(a.out, a.seed, a.free_pivot)
