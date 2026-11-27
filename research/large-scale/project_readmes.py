"""Publish the canonical large-file measurements inside each project README."""

import argparse
from collections import defaultdict
from html import escape
import json
from os.path import relpath
from pathlib import Path
import re

from primary import CHOICES
from report import experiment_pages, read_trials

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
START = "<!-- BEGIN generated project measurements -->"
END = "<!-- END generated project measurements -->"
JUMP = "[View this project's benchmark tables](#large-file-benchmark)"
BACKENDS = ("gzip-6", "zstd-3", "xz-6")
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


def measurement_block(folder, datasets, preferred, pairs, baselines):
    index = relpath(RESULTS / "by-dataset.md", folder)
    summary = [
        START,
        "",
        "Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.",
    ]
    if any(
        (r["dataset"], r["codec"]) in pairs for rows in datasets.values() for r in rows
    ):
        summary += [
            "",
            "H0 measures byte frequencies. H1 conditions on the previous byte. Both use bits per byte of their own stream. Post H0 per raw byte accounts for changes in stream length. In the paired compressor tables, a positive percentage means preprocessing made the compressed file smaller.",
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
    if JUMP not in text:
        title, nl, rest = text.partition("\n")
        text = title + nl + "\n" + JUMP + "\n" + rest
    return text


def refresh(check=False):
    groups = experiment_pages()
    preferred = {groups[family]: name for family, (name, _) in CHOICES.items()}
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
            measurement_block(folder, datasets, preferred[folder], pairs, baselines),
        )
        if updated != original:
            updates[path] = updated
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
        "--check", action="store_true", help="Check generated tables without writing"
    )
    count = refresh(parser.parse_args().check)
    print(f"Verified benchmark tables in {count} project READMEs.")
