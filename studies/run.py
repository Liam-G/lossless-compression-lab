"""Run the three cross-experiment studies from a clean checkout."""

import argparse
import hashlib
import importlib.util
import random
import subprocess
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lab
import wire

STUDIES = ("formula-factor-grammar", "automaton-factor-residual", "reference-formula-intervals")


def run(name, output):
    directory = Path(__file__).parent / name
    spec = importlib.util.spec_from_file_location("study", directory / "benchmark.py")
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    cases = list(study.datasets(ROOT / "fixtures", random.Random(lab.SEED)))
    cases.insert(
        1, ("uniform", random.Random(lab.SEED + 1).randbytes(len(cases[0][1])), cases[0][2])
    )
    rows = []
    for dataset, data, ref in cases:
        compressed = subprocess.check_output(["zstd", "-q3c"], input=data)
        if subprocess.check_output(["zstd", "-qdc"], input=compressed) != data:
            raise ValueError("Baseline mismatch")
        for profile in study.PROFILES:
            start = perf_counter()
            archive, stats = wire.encode(study, data, profile, ref)
            encoded = perf_counter()
            restored, _ = wire.decode(study, archive, ref)
            end = perf_counter()
            if restored != data:
                raise ValueError("Joint archive mismatch")
            uses_base = stats.pop("uses_base", False)
            rows.append(
                dict(
                    dataset=dataset,
                    profile=profile,
                    raw_bytes=len(data),
                    archive_bytes=len(archive),
                    metadata_bytes=stats.pop("metadata_bytes"),
                    base_plus_archive=len(archive) + (len(ref) if uses_base else 0),
                    zstd_bytes=len(compressed),
                    encode_ms=round(1000 * (encoded - start), 3),
                    decode_ms=round(1000 * (end - encoded), 3),
                    sha256=hashlib.sha256(data).hexdigest(),
                    verified=True,
                )
            )
    output.mkdir(parents=True)
    lab.csv_file(output / "trials.csv", rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=STUDIES)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.study, args.output)
