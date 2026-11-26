"""Verify separate archives at unchanged slab size, backend and method-tag cost."""

import argparse
import csv
import hashlib
import json
import lzma
from pathlib import Path
import random
import subprocess
from time import perf_counter
import numpy as np
import codec


def datasets(root):
    rng = np.random.default_rng(28119)
    slabs = []
    for i in range(32):
        # Independent rank-two subspaces per panel, evolved across all three axes.
        basis = rng.integers(1, 256, (512, 2), dtype=np.uint8)
        basis[:, 1] = np.where(
            basis[:, 1] == basis[:, 0], np.where(basis[:, 0] == 1, 2, 1), basis[:, 1]
        )
        coords = rng.integers(0, 2, (512, 16, 2), dtype=np.uint8)
        rows = np.bitwise_xor.reduce(coords * basis[:, None, :], axis=2)
        state = bytearray(codec.restore_panels(rows))
        for _ in range(codec.STEPS[i % 4]):
            codec.advance(state, i % 2, False)
        slabs.append(state)
    yield "evolved-rank2", b"".join(slabs)
    yield "uniform", random.Random(28119).randbytes(32 * codec.SLAB)
    for name in (
        "canterbury/ptt5",
        "canterbury/kennedy.xls",
        "silesia/mr",
        "silesia/x-ray",
        "enwik8/enwik8",
    ):
        with (root / name).open("rb") as f:
            yield name.split("/")[-1], f.read(1 << 20)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corpus", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True)
    trials = []
    summaries = []
    for name, data in datasets(a.corpus):
        sizes = {}
        for profile in codec.PROFILES:
            start = perf_counter()
            arc = codec.encode(data, profile)
            middle = perf_counter()
            restored, modes = codec.decode(arc)
            end = perf_counter()
            if restored != data:
                raise ValueError((name, profile))
            sizes[profile] = len(arc)
            trials.append(
                dict(
                    dataset=name,
                    profile=profile,
                    archive_bytes=len(arc),
                    encode_s=round(middle - start, 4),
                    decode_s=round(end - middle, 4),
                    selections=json.dumps(modes, sort_keys=True),
                    verified=True,
                )
            )
        zstd = subprocess.check_output(["zstd", "-q3c"], input=data)
        xz = lzma.compress(data, preset=9 | lzma.PRESET_EXTREME)
        if (
            lzma.decompress(xz) != data
            or subprocess.check_output(["zstd", "-qdc"], input=zstd) != data
        ):
            raise ValueError("Baseline mismatch")
        summaries.append(
            dict(
                dataset=name,
                input_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                **sizes,
                combined_gain=min(sizes["orbit"], sizes["rank"]) - sizes["combined"],
                zstd3=len(zstd),
                xz9e=len(xz),
            )
        )
    for file, rows in (("trials", trials), ("comparisons", summaries)):
        with (a.output / (file + ".csv")).open("x", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
