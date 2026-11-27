"""Reproduce the pinned gzip byte windows and an NCI within-line permutation control."""

import argparse
import gzip
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

import numpy as np
from ragged import BLOCK

SIZE = 24 << 20
SEED = 301057


def permute_rows(block, rng):
    values = np.frombuffer(block, np.uint8)
    mask = values != 10
    groups = np.cumsum(~mask)[mask]
    payload = values[mask]
    # Randomize the payload of each row while preserving all LF positions.
    keys = rng.integers(0, 2**32, len(payload), dtype=np.uint32)
    order = np.lexsort((keys, groups))
    result = values.copy()
    result[mask] = payload[order]
    return result.tobytes()


def create(kind, source, output, expected):
    if output.exists():
        raise FileExistsError(output)
    digest = hashlib.sha256()
    with NamedTemporaryFile(dir=output.parent) as tmp:
        if kind == "gzip-prefix":
            with gzip.open(source, "rb") as src:
                data = src.read(SIZE)
                if len(data) != SIZE:
                    raise ValueError("Compressed source does not contain 24 MiB")
                tmp.write(data)
                digest.update(data)
        else:
            rng = np.random.Generator(np.random.PCG64(SEED))
            with source.open("rb") as src:
                while block := src.read(BLOCK):
                    data = permute_rows(block, rng)
                    tmp.write(data)
                    digest.update(data)
        actual = digest.hexdigest()
        if expected and actual != expected:
            raise ValueError(f"Source changed: expected {expected}, found {actual}")
        tmp.flush()
        os.link(tmp.name, output)
    return actual


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=("gzip-prefix", "shuffle"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sha256")
    a = p.parse_args()
    print(create(a.kind, a.source, a.output, a.sha256))
