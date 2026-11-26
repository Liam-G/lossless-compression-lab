"""Independent noisy rank-two panels connected by a four-dimensional update."""

import argparse
from pathlib import Path
import numpy as np
from codec import BLOCK, STEPS, evolve

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    rng = np.random.default_rng(572366)
    with args.output.open("xb") as out:
        for page in range((24 << 20) // BLOCK):
            count = BLOCK // 16
            bases = rng.integers(1, 256, (count // 8, 2), dtype=np.uint8).repeat(
                8, axis=0
            )
            flags = rng.integers(0, 4, (count, 16), dtype=np.uint8)
            field = (flags & 1) * bases[:, 0, None] ^ ((flags >> 1) & 1) * bases[
                :, 1, None
            ]
            # One bit error in half of the panels, even before the automaton evolves them.
            rows = np.arange(0, count, 2)
            field[rows, rng.integers(0, 16, len(rows))] ^= 1 << rng.integers(
                0, 8, len(rows), dtype=np.uint8
            )
            grid = field.reshape(-1, 8, 16, 8)
            for _ in range(STEPS[(page // 2) % len(STEPS)]):
                evolve(grid, page % 2, False)
            out.write(grid.tobytes())
