"""Measure original mixed-arity trees on an entire input and quartics on nested prefixes."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True)
    rows = []
    with TemporaryDirectory(dir=a.output) as tmp:
        tmp = Path(tmp)
        for profile in (
            "center-2",
            "mixed-9-11",
            "seeded-128",
            "quartic-4096",
            "quartic-65536",
            "quartic-1048576",
        ):
            with TemporaryDirectory(dir=tmp) as trial:
                trial = Path(trial)
                arc, restored = trial / "archive", trial / "restored"
                source = a.input
                if profile.startswith("quartic"):
                    source = trial / "input"
                    with a.input.open("rb") as f:
                        source.write_bytes(f.read(int(profile.split("-")[1])))
                    cli = [sys.executable, HERE / "quartic-trees/codec.py"]
                    encode = cli + ["encode", source, arc]
                    decode = cli + ["decode", arc, restored]
                else:
                    cli = [HERE / "build/factor-tree"]
                    mode, arity, selector = {
                        "center-2": ("split-mixed", "2", "0"),
                        "mixed-9-11": ("split-mixed", "9,11", "-9"),
                        "seeded-128": ("split-seeded", "128", "2"),
                    }[profile]
                    encode = cli + [
                        mode,
                        source,
                        arc,
                        trial / "levels.tsv",
                        "1048576",
                        arity,
                        selector,
                    ]
                    decode = cli + ["join", arc, restored]
                start = perf_counter()
                log = subprocess.check_output(encode)
                middle = perf_counter()
                subprocess.run(decode, check=True, stdout=subprocess.DEVNULL)
                end = perf_counter()
                subprocess.run(["cmp", source, restored], check=True)
                with source.open("rb") as f:
                    sha = hashlib.file_digest(f, "sha256").hexdigest()
                rows.append(
                    dict(
                        profile=profile,
                        input_bytes=source.stat().st_size,
                        archive_bytes=arc.stat().st_size,
                        input_sha256=sha,
                        encode_s=round(middle - start, 4),
                        decode_s=round(end - middle, 4),
                        verified=True,
                    )
                )
                if profile.startswith("quartic"):
                    (a.output / (profile + ".json")).write_text(
                        json.dumps(json.loads(log), indent=2) + "\n"
                    )
                else:
                    (a.output / (profile + "-levels.tsv")).write_bytes(
                        (trial / "levels.tsv").read_bytes()
                    )
        with (a.output / "trials.csv").open("x", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
