"""Check the published receipts, the pinned raw files and original evidence against their hashes."""

import argparse
import csv
from pathlib import Path

from bench import digest
from replay import resolve
from report import experiment_pages, read_trials

HERE = Path(__file__).resolve().parent


def audit(raw=None, workspace=None):
    receipts = read_trials([HERE / "results/archives.jsonl"])
    groups = experiment_pages()
    projects = set()
    files = {}
    for row in receipts:
        family = row["codec"].partition("-")[0]
        if family in groups:
            projects.add(groups[family])
        files[row["dataset"]] = row["input_sha256"]
        knobs = row["knobs"]
        if "reference" in knobs:
            files[knobs["reference"]] = knobs["reference_sha256"]
    missing = set(groups.values()) - projects
    if missing:
        raise ValueError(
            "Projects without a primary trial: "
            + ", ".join(sorted(p.name for p in missing))
        )
    print(
        f"{len(receipts)} verified receipt identities, {len(projects)} projects, {len({r['dataset'] for r in receipts})} targets"
    )
    if raw:
        for name, sha in sorted(files.items()):
            resolve(name, sha, raw, workspace or Path(".."))
        print(f"{len(files)} source and reference hashes checked")
    if workspace:
        for index in ("report-index.tsv", "supplementary.tsv"):
            with (HERE.parent / "evidence" / index).open() as stream:
                entries = list(csv.DictReader(stream, delimiter="\t"))
            for entry in entries:
                source = workspace / entry["workspace_path"]
                if (
                    source.stat().st_size != int(entry["bytes"])
                    or digest(source) != entry["sha256"]
                ):
                    raise ValueError(f"Changed evidence file: {source}")
            print(f"{len(entries)} verified entries in {index}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, help="Also hash all raw inputs and references")
    p.add_argument(
        "--workspace", type=Path, help="Also check the original report register"
    )
    a = p.parse_args()
    audit(a.raw, a.workspace)
