"""Repeat the published profile(s) on pinned inputs and compare their resulting archives."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from bench import digest
from report import read_trials

HERE = Path(__file__).resolve().parent
EXTERNAL = {
    "enwik8": "corpus/enwik8/enwik8",
    "enwik9": "corpus/enwik9/enwik9",
    "cofattore-Q.base256": "lab/hutter/divisors/work/cofattore-Q.base256",
    "cofattore-Q.txt": "lab/hutter/divisors/cofattore-Q.txt",
    "neif-archive9": "lab/hutter/leader_trial/neif-archive9",
    "fx2-cmix-transformer-archive9.bin": "lab/hutter/divisors/fx2-cmix-transformer-archive9.bin",
    "fx2-cmix-t-awarded.archive9": "lab/arena/work/colab-max-20261125/award/fx2-cmix-t-awarded.archive9",
}


def resolve(name, expected, raw, workspace):
    candidates = [raw / name]
    if name in EXTERNAL:
        candidates.append(workspace / EXTERNAL[name])
    for p in candidates:
        if p.is_file() and digest(p) == expected:
            return p
    raise ValueError(
        f"Supply the pinned {name} in {raw} or its original workspace path"
    )


def repeat(r, src, output, raw, workspace):
    cmd = [sys.executable, HERE / "bench.py", src, output, r["codec"]]
    knobs = r["knobs"]
    if "reference" in knobs:
        cmd += [
            "--reference",
            resolve(knobs["reference"], knobs["reference_sha256"], raw, workspace),
        ]
    env = dict(os.environ)
    env["PILOT_WORKERS"] = str(knobs.get("workers", 1))
    env["PILOT_NATIVE_GF2"] = "1" if knobs.get("native_gf2", False) else "0"
    subprocess.run(cmd, env=env, check=True)
    actual = json.loads(output.read_text())
    if (
        actual["archive_bytes"] != r["archive_bytes"]
        or actual["archive_sha256"] != r["archive_sha256"]
    ):
        raise ValueError(
            f"Exact decode verified but archive differs from pinned receipt for {r['codec']}"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset")
    p.add_argument("output", type=Path, help="Fresh directory for new receipts")
    p.add_argument(
        "profiles", nargs="*", help="Default: every published profile on this dataset"
    )
    p.add_argument("--raw", type=Path, default=Path("runs/large/raw"))
    p.add_argument("--workspace", type=Path, default=Path(".."))
    p.add_argument(
        "--reference-name",
        help="Restrict a conditional method to one published reference",
    )
    a = p.parse_args()
    rows = [
        r
        for r in read_trials([HERE / "results/archives.jsonl"])
        if r["dataset"] == a.dataset
        and (not a.profiles or r["codec"] in a.profiles)
        and (not a.reference_name or r["knobs"].get("reference") == a.reference_name)
    ]
    if not rows or set(a.profiles) - {r["codec"] for r in rows}:
        p.error("No published run matches one or more requested profiles")
    src = resolve(a.dataset, rows[0]["input_sha256"], a.raw, a.workspace)
    a.output.mkdir(parents=True, exist_ok=False)
    for index, r in enumerate(rows):
        output = a.output / f"{index:03}-{r['codec']}.jsonl"
        repeat(r, src, output, a.raw, a.workspace)
