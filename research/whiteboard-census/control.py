"""Break the relation between witness parameters and their values while retaining their marginals."""

import argparse
from pathlib import Path
import numpy as np
from data import WITNESS
from witnesses import groups

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    rng = np.random.default_rng(109973)
    tables = groups(a.source.read_bytes())
    with a.out.open("xb") as output:
        output.write(WITNESS.pack(b"WIT1", *(len(t) for t in tables)))
        for table in tables:
            scrambled = table.copy()
            positions = rng.permutation(len(table))
            scrambled[:, [0, 1, -1]] = table[positions][:, [0, 1, -1]]
            output.write(scrambled.tobytes())
