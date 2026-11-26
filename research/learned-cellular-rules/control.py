"""Generate independent unknown rule tables and correlated cross-plane innovations."""

import argparse
from pathlib import Path
import numpy as np
from codec import FRAMES, change_basis, transform

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--seed", type=int, default=842105)
    p.add_argument(
        "--kind", choices=("correlated", "independent", "uniform"), default="correlated"
    )
    args = p.parse_args()
    rng = np.random.default_rng(args.seed)
    with args.output.open("xb") as out:
        for bank in range(8):
            size = (FRAMES, 360, 640)
            if args.kind == "uniform":
                out.write(rng.integers(0, 256, size, dtype=np.uint8).tobytes())
                continue
            residual = rng.integers(0, 4, size, dtype=np.uint8)
            for b in range(2, 8):
                residual |= (rng.integers(0, 128, size, dtype=np.uint8) == 0).astype(
                    np.uint8
                ) << b
            masks = bytes(int(rng.integers(1 << b, 2 << b)) for b in range(8))
            residual = change_basis(residual, masks, True)
            if args.kind == "independent":
                # Change only cross-plane alignment. Each plane retains its exact number of ones.
                shifted = np.zeros_like(residual)
                for b in range(8):
                    shift = (b * 7919 + bank * 997) * 61
                    shifted |= np.roll(residual & (1 << b), shift)
                residual = shifted
            residual[0] = rng.integers(0, 256, size[1:], dtype=np.uint8)
            rules = rng.integers(0, 2**32, 8, dtype=np.uint32)
            # The two high-entropy innovation planes use a known-zero rule.
            rules[:2] = 0
            out.write(transform(residual, rules, bool(bank % 2), True).tobytes())
