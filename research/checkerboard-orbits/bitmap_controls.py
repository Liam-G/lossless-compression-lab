"""Build an evolved stamp field or a lossless permutation of full source scanlines."""

import argparse
from pathlib import Path
import numpy as np
from bitmap import checker, raster, HEIGHT, ROW

SEED = 771037


def generate(dst, rotated=False):
    rng = np.random.Generator(np.random.PCG64(SEED))
    stamps = np.frombuffer(rng.bytes(32 * 8), "<u8")
    for _ in range(512):
        ids = rng.integers(0, 32, (HEIGHT // 8, ROW), dtype=np.uint8)
        active = rng.integers(0, 8, ids.shape, dtype=np.uint8) == 0
        words = np.where(active, stamps[ids], np.uint64(0)).astype("<u8")
        dst.write(checker(raster(words), forward=True, rotated=rotated).tobytes())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--rotated",
        action="store_true",
        help="Use the rotated local rule on the same stamps",
    )
    mode.add_argument(
        "--shuffle-rows",
        type=Path,
        help="Shuffle this input instead of generating stamps",
    )
    a = p.parse_args()
    if a.shuffle_rows:
        source = np.frombuffer(a.shuffle_rows.read_bytes(), np.uint8).reshape(-1, ROW)
        rng = np.random.Generator(np.random.PCG64(SEED))
        with a.output.open("xb") as dst:
            dst.write(source[rng.permutation(len(source))].tobytes())
    else:
        with a.output.open("xb") as dst:
            generate(dst, a.rotated)
