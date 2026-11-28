"""Publish the canonical large-file measurements inside each project README."""

import argparse
import json
import re
from collections import defaultdict
from html import escape
from os.path import relpath
from pathlib import Path

from findings import update_findings
from primary import CHOICES
from project_figures import (
    BACKENDS,
    Figures,
    archive_data,
    archive_figure,
    gain,
    h0_cost,
    paired_figure,
)
from report import experiment_pages, read_trials

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
START = "<!-- BEGIN generated project measurements -->"
END = "<!-- END generated project measurements -->"
OLD_JUMP = "[View this project's benchmark tables](#large-file-benchmark)"
JUMP = "[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)"
BASELINE_LABELS = {
    "zstd3": "Zstandard 3",
    "zstd19": "Zstandard 19",
    "xz9e": "XZ 9 extreme",
    "djvu": "DjVu",
    "djvu-multi": "DjVu (separated foreground)",
    "djvu-wide": "DjVu (wide strips)",
    "group4": "CCITT Group 4",
    "png1": "1-bit PNG",
    "png": "PNG",
    "jbig": "JBIG",
    "jxl": "Lossless JPEG XL",
    "webp": "Lossless WebP",
    "ffv1": "FFV1",
    "h264lossless": "Lossless H.264",
}


def compression_cell(backend):
    before, after = (backend[k]["bytes"] for k in ("raw", "prepared"))
    return f"{before:,} → {after:,} ({100 * (before - after) / before:+.2f}%)"


def preprocessing_tables(rows):
    lines = [
        "**Entropy before and after preprocessing**",
        "",
        "| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        a, b = r["raw"], r["prepared"]
        lines.append(
            f"| `{r['profile']}` | {b['bytes']:,} | {a['h0']:.4f} → {b['h0']:.4f} | "
            f"{a['h1']:.4f} → {b['h1']:.4f} | {b['h0'] * b['bytes'] / a['bytes']:.4f} |"
        )
    lines += [
        "",
        "**Same compressor on original → prepared bytes**",
        "",
        "| Profile | gzip 6 | Zstandard 3 | XZ 6 |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        cells = [compression_cell(r["backends"][k]) for k in BACKENDS]
        lines.append(f"| `{r['profile']}` | " + " | ".join(cells) + " |")
    return lines


def archive_table(rows):
    conditional = any("reference" in r["knobs"] for r in rows)
    has_memory = any("encode_peak_kib" in r or "decode_peak_kib" in r for r in rows)
    columns = ["Profile", "Archive bytes"]
    if conditional:
        columns += ["Archive + required reference (bytes)"]
    columns += ["Bytes saved vs raw", "Encode (s)", "Decode (s)"]
    if has_memory:
        columns.append("Peak KiB (encode / decode)")
    lines = [
        "**Standalone archives**",
        "",
        "| " + " | ".join(columns) + " |",
        "|---|" + "---:|" * (len(columns) - 1),
    ]
    for r in rows:
        name = f"`{r['codec']}`"
        if "reference" in r["knobs"]:
            name += f" (base `{r['knobs']['reference']}`)"
        total = r["archive_plus_reference_bytes"]
        cells = [name, f"{r['archive_bytes']:,}"]
        if conditional:
            cells.append(f"{total:,}")
        cells.extend(
            [
                f"{r['input_bytes'] - total:+,}",
                f"{r['encode_s']:.3f}",
                f"{r['decode_s']:.3f}",
            ]
        )
        if has_memory:
            peaks = [
                f"{r[k]:,}" if k in r else "—"
                for k in ("encode_peak_kib", "decode_peak_kib")
            ]
            cells.append(" / ".join(peaks))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def measurement_block(folder, datasets, primary, pairs, baselines, figures):
    preferred, profile = primary
    chart = folder / "figures" / "archives.svg"
    figures.add(chart, archive_data(datasets, baselines, preferred), archive_figure)
    index = relpath(RESULTS / "by-dataset.md", folder)
    summary = [
        START,
        "",
        "Each archive passed a byte-for-byte round trip. *Bytes saved* is raw size minus archive (and any reference the decoder needs). Timings are one run on a shared desktop.",
    ]
    summary += [
        "",
        "These tables list every measured profile. The comparison with the best standard tool on each input "
        "(gzip, bzip2, xz, Zstandard, Brotli, PPMd and the domain codecs) is the Results table above.",
    ]
    any_pairs = any(
        (r["dataset"], r["codec"]) in pairs for rows in datasets.values() for r in rows
    )
    summary += [
        "",
        "### Archive comparison across inputs",
        "",
        "![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)",
        "",
        (
            "Read down a column to compare methods on identical input. Lower is better. "
            "100% is the raw file size. Where available, standard codecs appear below the dividing line. "
            "Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured."
        ),
    ]
    if any_pairs:
        summary += [
            "",
            "The paired figures below measure preprocessing separately. H0 measures byte frequencies. H1 conditions on the previous byte. The tables give both in bits per byte of their own stream. The figures express model costs per original byte. H0 counts every byte. H1 counts each adjacent pair, omitting the first byte’s marginal cost. Positive compressor savings mean a smaller compressed file.",
        ]
    else:
        summary += [
            "",
            "This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.",
        ]
    many_rows = sum(map(len, datasets.values())) > 30
    for name in sorted(datasets, key=lambda n: (n != preferred, n)):
        rows = datasets[name]
        raw = rows[0]
        title = f"{name} · {raw['input_bytes']:,} raw bytes"
        collapsed = many_rows and name != preferred
        if collapsed:
            summary += ["", "<details>", f"<summary>{escape(title)}</summary>", ""]
        else:
            summary += ["", f"### {title}", ""]
        matching = [
            pairs[name, r["codec"]] for r in rows if (name, r["codec"]) in pairs
        ]
        if matching:
            figfile = Path("figures") / f"paired-{name}.svg"
            plot_rows = [
                (
                    r["profile"],
                    r["raw"]["h0"],
                    h0_cost(r),
                    r["raw"]["h1"] * (r["raw"]["bytes"] - 1) / r["raw"]["bytes"],
                    r["prepared"]["h1"]
                    * (r["prepared"]["bytes"] - 1)
                    / r["raw"]["bytes"],
                    [gain(r, k) for k in BACKENDS],
                )
                for r in matching
            ]
            figures.add(folder / figfile, plot_rows, paired_figure)
            hits = [
                sum(
                    r["backends"][k]["prepared"]["bytes"]
                    < r["backends"][k]["raw"]["bytes"]
                    for r in matching
                )
                for k in BACKENDS
            ]
            summary += [
                f"![Normalized H0 and H1 before and after and compressed savings for each measured profile on {name}.]({figfile})",
                "",
                f"Of {len(matching)} measured profiles on this input, {hits[0]} reduced gzip size, {hits[1]} reduced Zstandard size and {hits[2]} reduced XZ size. Exact ties count separately from improvements.",
                "",
            ]
            summary += preprocessing_tables(matching) + [""]
        summary += archive_table(rows)
        if controls := baselines.get((name, raw["input_sha256"])):
            sizes = [
                f"{BASELINE_LABELS.get(r['codec'], r['codec'])} {r['archive_bytes']:,}"
                for r in controls
            ]
            summary += [
                "",
                "Same-input baseline archives (bytes) · " + " · ".join(sizes),
            ]
        anchor = re.sub(r"[^a-z0-9-]", "", name.lower())
        summary += ["", f"[Input hash and all measured codecs]({index}#{anchor})"]
        if collapsed:
            summary += ["", "</details>"]
    receipts = relpath(RESULTS / "archives.jsonl", folder)
    summary += [
        "",
        "### Reproduce the large-file comparison",
        "",
        "From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.",
        "",
        "```sh",
        f"python3 research/large-scale/primary.py runs/replay-{folder.name} --project {folder.name} --all-profiles",
        "```",
        "",
        f"[Dataset preparation]({relpath(HERE / 'README.md', folder)}#inputs) · [Archive hashes and settings]({receipts})",
    ]
    if any_pairs:
        example = next(
            pairs[name, entry["codec"]]
            for name in (preferred, *datasets)
            for entry in datasets[name]
            if (name, entry["codec"]) in pairs
        )
        summary += [
            "",
            "A separate paired run also records entropy, stream hashes and the three backend sizes.",
            "",
            "```sh",
            "mkdir -p runs/paired",
            f"python3 research/large-scale/entropy_bench.py {example['profile']} runs/large/raw/{example['dataset']} runs/paired/{folder.name}.json",
            "```",
            "",
            f"[All paired stream hashes and compressor versions]({relpath(RESULTS / 'preprocessing.jsonl', folder)})",
        ]
    return "\n".join([*summary, "", END])


def render(text, block):
    # Only this marked block and the navigation link belong to the generator.
    if START in text or END in text:
        if (
            text.count(START) != 1
            or text.count(END) != 1
            or text.index(START) > text.index(END)
        ):
            raise ValueError("Unbalanced project measurement markers")
        a, _, tail = text.partition(START)
        _, _, b = tail.partition(END)
        text = a + block + b
    else:
        a, marker, b = text.partition("\n## Connections\n")
        if not marker or "\n## Large-file benchmark\n" not in a:
            raise ValueError("Project README is missing its benchmark section")
        text = a.rstrip() + "\n\n" + block + "\n" + marker + b
    return text


def refresh(check=False):
    groups = experiment_pages()
    preferred = {groups[family]: primary for family, primary in CHOICES.items()}
    figures = Figures(check)
    projects = defaultdict(lambda: defaultdict(list))
    baselines = defaultdict(list)
    archives = read_trials([RESULTS / "archives.jsonl"])
    for r in archives:
        folder = groups.get(r["codec"].partition("-")[0])
        if folder is None:
            baselines[r["dataset"], r["input_sha256"]].append(r)
        else:
            projects[folder][r["dataset"]].append(r)
    pairs = {}
    identities = {(r["dataset"], r["codec"], r["input_sha256"]) for r in archives}
    for line in (RESULTS / "preprocessing.jsonl").read_text().splitlines():
        r = json.loads(line)
        key = r["dataset"], r["profile"]
        if (
            key in pairs
            or (*key, r["raw"]["sha256"]) not in identities
            or not r["verified"]
        ):
            raise ValueError(f"Unmatched or duplicate paired measurement {key}")
        pairs[key] = r
    updates = {}
    for folder in sorted(set(groups.values())):
        datasets = projects[folder]
        if not datasets:
            raise ValueError(f"No published benchmark for {folder.name}")
        path = folder / "README.md"
        original = path.read_text()
        updated = render(
            original,
            measurement_block(
                folder, datasets, preferred[folder], pairs, baselines, figures
            ),
        )
        if updated != original:
            updates[path] = updated
    study = HERE / "findings.md"
    original = study.read_text()
    updated = update_findings(original, pairs.values(), figures)
    if updated != original:
        updates[study] = updated
    figures.finish()
    if check and updates:
        raise ValueError(
            "Outdated project README tables: "
            + ", ".join(str(p.parent.name) for p in updates)
        )
    for path, updated in updates.items():
        path.write_text(updated)
    return len(projects)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check figures, analysis and tables without writing",
    )
    count = refresh(parser.parse_args().check)
    print(f"Verified research figures and benchmark tables in {count} project READMEs.")
