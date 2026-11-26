"""Independent large positive controls for arithmetic factor trees and cellular matrices."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tensor-orbits"))
import codec as tensor


def write_products(stream):
    rng = random.Random(128713)
    for _ in range(384):
        page = bytearray()
        for i in range(1024):
            r = rng.choice(range(96, 253, 12))
            quotient = ((1 << r) - 1) // 13
            other = rng.getrandbits(252)
            value = (quotient << 254 | other) if i % 2 else (other << 254 | quotient)
            page.extend((17 * value - rng.choice((-1, 0, 1))).to_bytes(64, "big"))
        stream.write(page)


def write_volume(stream):
    rng = np.random.default_rng(730135)
    for i in range(3072):
        basis = rng.integers(1, 256, (512, 2), dtype=np.uint8)
        basis[:, 1] = np.where(
            basis[:, 0] == basis[:, 1], np.where(basis[:, 0] == 1, 2, 1), basis[:, 1]
        )
        coords = rng.integers(0, 2, (512, 16, 2), dtype=np.uint8)
        rows = np.bitwise_xor.reduce(coords * basis[:, None, :], axis=2)
        slab = bytearray(tensor.restore_panels(rows))
        for _ in range(tensor.STEPS[(i // 2) % 4]):
            tensor.advance(slab, i % 2, False)
        stream.write(slab)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, func, seed in (
        ("hidden-products", write_products, 128713),
        ("evolved-volume", write_volume, 730135),
    ):
        target = args.output / name
        with target.open("xb") as f:
            func(f)
        assert target.stat().st_size == 24 << 20
        with target.open("rb") as f:
            manifest[name] = dict(
                bytes=target.stat().st_size,
                sha256=hashlib.file_digest(f, "sha256").hexdigest(),
                seed=seed,
            )
    (args.output / "controls.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
