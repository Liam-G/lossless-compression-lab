"""Encode and decode a text prefix with three controlled CM3 profiles."""

import argparse
import csv
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

HERE = Path(__file__).resolve().parent
PROFILES = {
    "context": {"CM3_BITS": "13"},
    "two-layers": {"CM3_BITS": "13", "CM3_MCAND": "32", "CM3_M2": "1", "CM3_L2": "6"},
}
PROFILES["two-layers-lstm"] = {
    **PROFILES["two-layers"],
    "CM3_LSTM": "32",
    "CM3_LSTM2": "1",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.source.open("rb") as source:
        data = source.read(131072)
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("CM3_")}
    rows = []
    with TemporaryDirectory() as folder:
        directory = Path(folder)
        original = directory / "input"
        original.write_bytes(data)
        archive = directory / "archive"
        restored = directory / "restored"
        for name, knobs in PROFILES.items():
            env = {**clean_env, **knobs}
            engine = HERE.parent / "build/cm3"
            start = perf_counter()
            subprocess.run([engine, "c", original, archive], check=True, env=env)
            middle = perf_counter()
            subprocess.run([engine, "d", archive, restored], check=True, env=env)
            end = perf_counter()
            if restored.read_bytes() != data:
                raise ValueError(f"CM3 round trip failed for {name}")
            rows.append(
                dict(
                    profile=name,
                    input_bytes=len(data),
                    archive_bytes=archive.stat().st_size,
                    encode_s=round(middle - start, 4),
                    decode_s=round(end - middle, 4),
                    sha256=hashlib.sha256(data).hexdigest(),
                    verified=True,
                )
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
