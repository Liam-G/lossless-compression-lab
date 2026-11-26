"""Replay all sixty GFH1 profiles and validate the historical full-profile archives."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

import codec


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent
    refs = json.loads((root / "fixtures/original-sizes.json").read_text())
    rows = []
    for name, expected in refs.items():
        source = root / "fixtures" / (name + ".bin")
        original = source.read_bytes()
        with TemporaryDirectory() as trial:
            tmp = Path(trial)
            historical = source.with_suffix(".gfh")
            for profile in codec.PROFILES:
                arc = tmp / (profile + ".gfh")
                start = perf_counter()
                with source.open("rb") as src, arc.open("w+b") as dest:
                    codec.pack(src, dest, profile, 100, 3, 2)
                encoded = perf_counter()
                stats = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            root / "codec.py",
                            "unpack",
                            arc,
                            tmp / "restored",
                        ]
                    )
                )
                if (
                    tmp / "restored"
                ).read_bytes() != original or arc.stat().st_size != expected[profile]:
                    raise ValueError((name, profile))
                if profile == "full" and historical.read_bytes() != arc.read_bytes():
                    raise ValueError("Historical archive differs")
                rows.append(
                    dict(
                        dataset=name,
                        profile=profile,
                        input_bytes=len(original),
                        archive_bytes=arc.stat().st_size,
                        sha256=hashlib.sha256(original).hexdigest(),
                        encode_s=round(encoded - start, 4),
                        nodes=json.dumps(stats["nodes"], sort_keys=True),
                        verified=True,
                    )
                )
    with (args.output / "trials.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
