"""Check the published receipts, the pinned raw files and original evidence against their hashes."""

import argparse
import csv
import json
from pathlib import Path

from bench import digest
from project_readmes import refresh
from replay import resolve
from report import experiment_pages, read_trials

HERE = Path(__file__).resolve().parent


def check_preprocessing(receipts):
    directory = HERE / "results"
    archives = {(r["dataset"], r["codec"]): r for r in receipts}
    streams = {}
    for line in (directory / "preprocessing.jsonl").read_text().splitlines():
        row = json.loads(line)
        name, profile = row["dataset"], row["profile"]
        raw = row["raw"]
        archive = archives[name, profile]
        if (archive["input_bytes"], archive["input_sha256"]) != (
            raw["bytes"],
            raw["sha256"],
        ):
            raise ValueError(f"Preprocessing input mismatch for {name} / {profile}")
        streams[name, "raw"] = raw
        streams[name, profile] = row["prepared"]
    for name, pin in json.loads((HERE / "row-inputs.json").read_text()).items():
        stream = streams[name, "raw"]
        if (pin["bytes"], pin["sha256"]) != (stream["bytes"], stream["sha256"]):
            raise ValueError(f"Row input pin mismatch for {name}")
    for line in (directory / "bitmap-occupancy.jsonl").read_text().splitlines():
        row = json.loads(line)
        raw = streams[row["dataset"], "raw"]
        if (row["bytes"], row["sha256"]) != (raw["bytes"], raw["sha256"]):
            raise ValueError(
                f"Bitmap inspection used the wrong input for {row['dataset']}"
            )
    probes = (directory / "row-matches.jsonl").read_text().splitlines()
    for line in probes:
        probe = json.loads(line)
        mode = probe["profile"]
        key = "raw" if mode == "raw" else "lattice-rows-" + mode
        stream = streams[probe["dataset"], key]
        if (probe["bytes"], probe["sha256"]) != (stream["bytes"], stream["sha256"]):
            raise ValueError(
                f"Match probe used the wrong stream for {probe['dataset']} / {mode}"
            )
    print(f"{len(probes)} match probes agree with the paired stream hashes")


def audit(raw=None, workspace=None):
    receipts = read_trials([HERE / "results/archives.jsonl"])
    check_preprocessing(receipts)
    print(f"{refresh(check=True)} project READMEs match the published measurements")
    groups = experiment_pages()
    projects = set()
    files = {}
    for row in receipts:
        family = row["codec"].partition("-")[0]
        if family in groups:
            projects.add(groups[family])
        pins = [(row["dataset"], row["input_sha256"])]
        knobs = row["knobs"]
        if "reference" in knobs:
            pins.append((knobs["reference"], knobs["reference_sha256"]))
        for name, sha in pins:
            if files.setdefault(name, sha) != sha:
                raise ValueError(f"Conflicting input or reference hash for {name}")
    missing = set(groups.values()) - projects
    if missing:
        raise ValueError(
            "Projects without a primary trial: "
            + ", ".join(sorted(p.name for p in missing))
        )
    print(
        f"{len(receipts)} verified receipt identities, {len(projects)} projects, {len({r['dataset'] for r in receipts})} targets"
    )
    template = (
        (HERE.parents[1] / "templates/experiment/README.md").read_text().splitlines()
    )
    required = [line for line in template if line.startswith("## ")]
    for project in projects:
        sections = [
            line
            for line in (project / "README.md").read_text().splitlines()
            if line in required
        ]
        if sections != required:
            raise ValueError(f"Experiment template mismatch in {project.name}")
    print(f"{len(projects)} project folders match the shared experiment template")
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
