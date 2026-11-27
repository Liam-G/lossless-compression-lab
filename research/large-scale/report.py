"""Validate benchmark receipts and build a sorted, searchable record of all archives."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

MINIMUM = 20 << 20
HASH = re.compile("[0-9a-f]{64}")


def read_trials(files):
    records = []
    datasets = {}
    seen = {}
    for file in sorted(files):
        for line in file.read_text().splitlines():
            row = json.loads(line)
            name, n = row["dataset"], row["input_bytes"]
            if row["verified"] is not True or n < MINIMUM or row["archive_bytes"] <= 0:
                raise ValueError(f"Incomplete benchmark in {file}")
            if not all(
                HASH.fullmatch(row[k]) for k in ("input_sha256", "archive_sha256")
            ):
                raise ValueError(f"Missing checksum in {file}")
            fingerprint = n, row["input_sha256"]
            if datasets.setdefault(name, fingerprint) != fingerprint:
                raise ValueError(f"Conflicting source for {name}")
            knobs = row["knobs"]
            identity = name, row["codec"], knobs.get("reference_sha256", "")
            if identity in seen:
                if seen[identity]["archive_sha256"] != row["archive_sha256"]:
                    raise ValueError(f"Different archive for {identity}")
                continue
            seen[identity] = row
            charge = knobs.get("reference_bytes", 0)
            if row.get("selections", {}).get("reference_used") is False:
                charge = 0
            row["delivered_reference_bytes"] = charge
            row["archive_plus_reference_bytes"] = row["archive_bytes"] + charge
            if "reference" in knobs and not HASH.fullmatch(knobs["reference_sha256"]):
                raise ValueError("Missing reference checksum")
            records.append(row)
    return sorted(
        records,
        key=lambda r: (r["dataset"], r["codec"], r["knobs"].get("reference", "")),
    )


def experiment_pages():
    root = Path(__file__).resolve().parents[2]
    groups = {}
    for folder in sorted((root / "experiments").glob("[0-9][0-9]-*")):
        groups["pilot" + folder.name[:2]] = folder
    for i, name in enumerate(
        (
            "formula-factor-grammar",
            "automaton-factor-residual",
            "reference-formula-intervals",
        ),
        17,
    ):
        groups["study" + str(i)] = root / "studies" / name
    families = {
        "qrt decimal": "factor-trees",
        "whiteboard forest": "whiteboard-trees",
        "shared": "shared-factor-forest",
        "carry scale": "carry-trees",
        "prime": "prime-index-trees",
        "integer": "integer-formulas",
        "sum": "generator-sums",
        "census witness censusapp regenerate witnessapp": "whiteboard-census",
        "portable": "portable-arithmetic",
        "qft255 rps32": "repdigit-intervals",
        "quartic": "quartic-trees",
        "gfh": "hierarchical-gf2",
        "tensor": "tensor-orbits",
        "checker": "checkerboard-orbits",
        "modular": "modular-kronecker",
        "four": "four-dimensional-factors",
        "learned": "learned-cellular-rules",
        "lattice": "lattice-prediction",
        "distance": "distance-geometry",
        "shape": "shape-context",
        "glyph": "glyph-residuals",
        "views": "text-views",
        "wiki wcm": "wiki-structures",
        "relative": "arithmetic-references",
        "wavelet": "reversible-wavelets",
        "motion": "motion-residuals",
        "cm3": "context-mixer",
        "statico": "statico",
    }
    for keys, name in families.items():
        for key in keys.split():
            groups[key] = root / "research" / name
    return groups


def project_index(records, output):
    from os.path import relpath

    paired_path = Path(__file__).resolve().parent / "results/preprocessing.jsonl"
    paired = (
        {
            (r["raw"]["sha256"], r["profile"]): r
            for r in map(json.loads, paired_path.read_text().splitlines())
        }
        if paired_path.exists()
        else {}
    )
    groups = experiment_pages()
    projects = {}
    for folder in groups.values():
        projects.setdefault(folder, [])
    for row in records:
        family = row["codec"].split("-")[0]
        if family in groups:
            projects[groups[family]].append(row)
    lines = [
        "# Measurements by experiment",
        "",
        "Compare the original input (raw bytes) with the complete encoded file (archive bytes). Bytes saved equals the raw size minus the archive and any required reference. Positive values mean compression. Negative values mean expansion. Projects that use a reference also show the total if the receiver needs that reference delivered. Shared decoder software is excluded. Select an input for same-file baselines and timings.",
        "",
        "For entropy before and after preprocessing and matched standard-compressor comparisons, see the [paired preprocessing study]("
        + relpath(
            Path(__file__).resolve().parent / "results/preprocessing.md",
            output.resolve(),
        )
        + ").",
        "",
    ]
    for folder, rows in projects.items():
        if not rows:
            continue
        slug = folder.name
        title = (folder / "README.md").read_text().splitlines()[0].removeprefix("# ")
        link = relpath(folder / "README.md", output.resolve())
        lines.extend(
            [
                f'<a id="{slug}"></a>',
                f"## {title}",
                "",
                f"[Implementation and protocol]({link})",
                "",
            ]
        )
        comparisons = [
            paired[(r["input_sha256"], r["codec"])]
            for r in rows
            if (r["input_sha256"], r["codec"]) in paired
        ]
        if comparisons:
            lines.extend(
                [
                    "**Preprocessing before Zstandard 3**",
                    "",
                    "| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |",
                    "|---|---|---:|---:|---:|",
                ]
            )
            for r in comparisons:
                a, b = r["raw"], r["prepared"]
                sizes = r["backends"]["zstd-3"]
                lines.append(
                    f"| {r['dataset']} | {r['profile']} | {a['h0']:.4f} → {b['h0']:.4f} | {a['h1']:.4f} → {b['h1']:.4f} | {sizes['raw']['bytes']:,} → {sizes['prepared']['bytes']:,} |"
                )
            lines.extend(["", "**Standalone archive sizes**", ""])
        include_reference = any(row["delivered_reference_bytes"] for row in rows)
        columns = ["Input", "Profile", "Raw bytes", "Archive bytes"]
        if include_reference:
            columns.append("Archive + required reference (bytes)")
        columns.append("Bytes saved")
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("|---|---|" + "---:|" * (len(columns) - 2))
        for row in sorted(
            rows,
            key=lambda r: (r["dataset"], r["codec"], r["knobs"].get("reference", "")),
        ):
            name = row["dataset"]
            anchor = re.sub(r"[^a-z0-9-]", "", name.lower())
            method = row["codec"]
            if "reference" in row["knobs"]:
                method += f" ({row['knobs']['reference']})"
            raw = row["input_bytes"]
            total = row["archive_plus_reference_bytes"]
            cells = [
                f"[{name}](by-dataset.md#{anchor})",
                method,
                f"{raw:,}",
                f"{row['archive_bytes']:,}",
            ]
            if include_reference:
                cells.append(f"{total:,}")
            saved = raw - total
            cells.append(f"{saved:+,}" if saved else "0")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    (output / "by-experiment.md").write_text("\n".join(lines).rstrip() + "\n")


def write(records, output):
    output.mkdir(exist_ok=True, parents=True)
    project_index(records, output)
    grouped = defaultdict(list)
    with (output / "archives.jsonl").open("w") as stream:
        for row in records:
            grouped[row["dataset"]].append(row)
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    lines = [
        "# All large-file measurements",
        "",
        f"{len(records)} verified archives across {len(grouped)} named inputs. Each row represents one complete encode, decode and byte comparison. Inputs can overlap across studies. Times are seconds from one run on a shared machine. Archive and reference sizes are bytes.",
        "",
        "The charged total includes the raw reference when the decoder requires it. Shared codec software is excluded. The [machine-readable receipts](archives.jsonl) include full input and archive hashes, selected parameters, and peak KiB where collected.",
        "",
    ]
    for name, rows in grouped.items():
        lines.extend(
            [
                f"## {name}",
                "",
                f"{rows[0]['input_bytes']:,} raw bytes · SHA-256 `{rows[0]['input_sha256']}`",
                "",
                "| Codec | Archive | With required reference | Bits per raw byte | Encode s | Decode s |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for r in sorted(
            rows,
            key=lambda r: (
                r["archive_plus_reference_bytes"],
                r["archive_bytes"],
                r["codec"],
            ),
        ):
            label = r["codec"]
            if "reference" in r["knobs"]:
                label += f" (base {r['knobs']['reference']})"
            lines.append(
                f"| {label} | {r['archive_bytes']:,} | {r['archive_plus_reference_bytes']:,} | {8 * r['archive_bytes'] / r['input_bytes']:.5f} | {r['encode_s']:.3f} | {r['decode_s']:.3f} |"
            )
        lines.append("")
    (output / "by-dataset.md").write_text("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("measurements", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    records = read_trials(a.measurements.glob("*.jsonl"))
    if not records:
        p.error("No completed receipts found")
    write(records, a.output)
    print(f"Indexed {len(records)} archives.")
