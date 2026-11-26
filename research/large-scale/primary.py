"""Run representative >=20 MiB trials for every requested project, including the Zstandard baseline."""

import argparse
from pathlib import Path
import subprocess
import sys

from bench import MINIMUM
from replay import resolve, repeat
from report import experiment_pages, read_trials, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# These choices emphasize the scientific question of each folder, regardless of its outcome.
CHOICES = {
    "pilot01": ("wiki-transfer", "pilot01-adaptive-ratios"),
    "pilot02": ("wiki-transfer", "pilot02-first-exact"),
    "pilot03": ("wiki-transfer", "pilot03-sum-add-8"),
    "pilot04": ("wiki-transfer", "pilot04-10-2-signed-checkpoints"),
    "pilot05": ("manual-graphs", "pilot05-local-bytes"),
    "pilot06": ("shared-orbit-1000", "pilot06-checker-3-fixed"),
    "pilot07": ("manual-graphs", "pilot07-pre-1"),
    "pilot08": ("numerical", "pilot08-search"),
    "pilot09": ("manual-library", "pilot09-combined"),
    "pilot10": ("affine-pairs", "pilot10-fixed"),
    "pilot11": ("formula-text", "pilot11-dag"),
    "pilot12": ("wiki-transfer", "pilot12-copies"),
    "pilot13": ("wiki-dev", "pilot13-combined-64"),
    "pilot14": ("numerical", "pilot14-adaptive"),
    "pilot15": ("mozilla", "pilot15-combined"),
    "pilot16": ("manual-library", "pilot16-intervals-regions"),
    "study17": ("hidden-products", "study17-combined"),
    "study18": ("manual-graphs", "study18-orbit-enumerative"),
    "study19": ("numpy-update", "study19-mixed"),
    "qrt": ("cofattore-Q.base256", "qrt-seeded"),
    "whiteboard": ("cofattore-Q.base256", "whiteboard"),
    "shared": ("hidden-products", "shared-shared"),
    "carry": ("cofattore-Q.base256", "scale-informed"),
    "prime": ("cofattore-Q.base256", "prime-tree"),
    "integer": ("cofattore-Q.base256", "integer-composite"),
    "sum": ("three-seeds", "sum-4096"),
    "qft255": ("cofattore-Q.base256", "qft255"),
    "quartic": ("wiki-transfer", "quartic"),
    "gfh": ("manual-graphs", "gfh-3-1"),
    "tensor": ("evolved-volume", "tensor-combined"),
    "checker": ("shared-orbit-1000", "checker-joint"),
    "modular": ("modular-panels", "modular-joint"),
    "four": ("noisy-spacetime", "four-joint"),
    "learned": ("learned-field", "learned-coupled"),
    "lattice": ("numerical", "lattice-joint-xz"),
    "distance": ("place-distances", "distance-three"),
    "shape": ("manual-graphs", "shape"),
    "glyph": ("manual-valgrind", "glyph-position"),
    "views": ("wiki-transfer", "views-joint"),
    "wiki": ("wiki-transfer", "wiki-joint-xz"),
    "relative": ("numpy-update", "relative-joint"),
    "wavelet": ("wall2.ppm", "wavelet-joint"),
    "motion": ("luma-rei", "motion-joint"),
    "cm3": ("wiki-dev", "cm3-mix"),
    "statico": ("enwik8", "statico"),
    "census": ("whiteboard-witnesses", "witness-joint"),
    "portable": ("cofattore-Q.base256", "portable-informed"),
}


def selected_projects(keys, group):
    mapping = experiment_pages()
    directories = list(dict.fromkeys(mapping.values()))
    selected = []
    for key in keys:
        family = (
            (f"pilot{int(key):02}" if int(key) <= 16 else f"study{int(key)}")
            if key.isdigit()
            else key
        )
        folder = mapping.get(family)
        if folder is None:
            folder = next((f for f in directories if f.name == key), None)
        if folder is None:
            raise ValueError(f"Unknown project {key}")
        if folder not in selected:
            selected.append(folder)
    if not selected:
        selected = [f for f in directories if group == "all" or f.parent.name == group]
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, help="New result directory")
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Repeat for experiment numbers, family names or folder names",
    )
    parser.add_argument(
        "--group", default="all", choices=("all", "experiments", "studies", "research")
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the selected trials without running them",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Replay every published trial of the selected projects",
    )
    parser.add_argument("--raw", type=Path, default=ROOT / "runs/large/raw")
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    parser.add_argument(
        "--input", type=Path, help="Use your own >=20 MiB file for one project"
    )
    parser.add_argument(
        "--codec", help="Profile for a custom input, e.g. pilot07-pre-1"
    )
    parser.add_argument(
        "--reference", type=Path, help="Reference for a custom conditional trial"
    )
    a = parser.parse_args()
    if not a.list and a.output is None:
        parser.error("Supply an output directory or --list")
    groups = experiment_pages()
    try:
        folders = selected_projects(a.project, a.group)
    except ValueError as err:
        parser.error(str(err))
    rows = read_trials([HERE / "results/archives.jsonl"])
    preferred = {groups[k]: v for k, v in CHOICES.items()}
    if a.input:
        if len(folders) != 1 or a.all_profiles:
            parser.error("--input needs one project and one profile")
        method = a.codec or preferred[folders[0]][1]
        if groups.get(method.partition("-")[0]) != folders[0]:
            parser.error("Codec belongs to a different project")
        if a.input.stat().st_size < MINIMUM:
            parser.error("Primary benchmark input must contain at least 20 MiB")
        if a.list:
            print(f"{folders[0].name} {a.input} {method} zstd3")
            return
        if method.startswith(("relative-", "pilot12-", "study19-")) and not a.reference:
            parser.error("Supply --reference for this conditional codec")
        a.output.mkdir(parents=True, exist_ok=False)
        command = [
            sys.executable,
            HERE / "bench.py",
            a.input,
            a.output / "trial.jsonl",
            method,
            "zstd3",
        ]
        if a.reference:
            command += ["--reference", a.reference]
        subprocess.run(command, check=True)
        write(read_trials([a.output / "trial.jsonl"]), a.output / "results")
        return
    if a.codec or a.reference:
        parser.error("Use --codec or --reference together with --input")
    plan = []
    for folder in folders:
        candidates = [
            r for r in rows if groups.get(r["codec"].partition("-")[0]) == folder
        ]
        if not candidates:
            parser.error(f"No published primary trial for {folder.name}")
        if not a.all_profiles:
            dataset, method = preferred[folder]
            matched = next(
                (
                    r
                    for r in candidates
                    if (r["dataset"], r["codec"]) == (dataset, method)
                ),
                None,
            )
            if matched is None:
                parser.error(
                    f"Selected primary receipt missing for {folder.name}: {dataset} / {method}"
                )
            candidates = [matched]
        for r in candidates:
            plan.append((folder.name, r))
    if a.list:
        for name, r in plan:
            print(name, r["dataset"], r["codec"], r["input_bytes"])
        return
    sources = {}
    for _, r in plan:
        identity = r["dataset"], r["input_sha256"]
        if identity not in sources:
            sources[identity] = resolve(*identity, a.raw, a.workspace)
        knobs = r["knobs"]
        if "reference" in knobs:
            identity = knobs["reference"], knobs["reference_sha256"]
            if identity not in sources:
                sources[identity] = resolve(*identity, a.raw, a.workspace)
    a.output.mkdir(parents=True, exist_ok=False)
    logs = []
    baselines = set()
    for i, (name, r) in enumerate(plan):
        directory = a.output / name
        directory.mkdir(exist_ok=True)
        target = directory / f"{i:04}-{r['codec']}.jsonl"
        src = sources[r["dataset"], r["input_sha256"]]
        repeat(r, src, target, a.raw, a.workspace)
        logs.append(target)
        if src not in baselines:
            directory = a.output / "baselines"
            directory.mkdir(exist_ok=True)
            result = directory / (src.name + ".jsonl")
            subprocess.run(
                [sys.executable, HERE / "bench.py", src, result, "zstd3"], check=True
            )
            baselines.add(src)
            logs.append(result)
    write(read_trials(logs), a.output / "results")


if __name__ == "__main__":
    main()
