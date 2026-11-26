"""Factor placement and formula ablation with hidden products and native corpus slices."""

import argparse
import csv
import hashlib
import json
import random
import subprocess
from pathlib import Path
from time import perf_counter
import factor_forest as forest


def cases(root):
    rng = random.Random(495273)
    data = bytearray()
    for i in range(512):
        # Two children of a 508-bit quotient; one is an exact cross-base ratio.
        r = rng.choice(range(96, 253, 12))
        formula = ((1 << r) - 1) // 13
        literal = rng.getrandbits(252)
        q = (formula << 254 | literal) if i % 2 else (literal << 254 | formula)
        data.extend((17 * q - rng.choice((-1, 0, 1))).to_bytes(64, "big"))
    yield "hidden-products", bytes(data)
    yield "noise", rng.randbytes(len(data))
    for name in ("silesia/mr", "silesia/x-ray", "canterbury/kennedy.xls"):
        with (root / name).open("rb") as f:
            f.seek(16384)
            yield name.split("/")[-1], f.read(len(data))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("corpus", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    args.output.mkdir(parents=True)
    with (args.output / "trials.csv").open("x") as out:
        writer = None
        for name, data in cases(args.corpus):
            zstd = subprocess.check_output(["zstd", "-q3c"], input=data)
            assert subprocess.check_output(["zstd", "-qdc"], input=zstd) == data
            for profile in forest.PROFILES:
                start = perf_counter()
                arc = forest.encode(data, profile)
                encoded = perf_counter()
                decoded, stats = forest.decode(arc)
                end = perf_counter()
                if decoded != data:
                    raise ValueError("Tree failed to recover input")
                row = dict(
                    dataset=name,
                    profile=profile,
                    input_bytes=len(data),
                    archive_bytes=len(arc),
                    zstd3_bytes=len(zstd),
                    encode_s=round(encoded - start, 4),
                    decode_s=round(end - encoded, 4),
                    sha256=hashlib.sha256(data).hexdigest(),
                    nodes=json.dumps(stats, sort_keys=True),
                    verified=True,
                )
                if writer is None:
                    writer = csv.DictWriter(out, fieldnames=row, lineterminator="\n")
                    writer.writeheader()
                writer.writerow(row)


if __name__ == "__main__":
    main()
