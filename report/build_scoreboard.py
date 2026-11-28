"""Build report/data/scoreboard.json: for every benchmark input, our best archive against the best standard tool.

Sources
  research/large-scale/results/archives.jsonl   every verified receipt (ours and standard codecs)
  report/data/baseline-panel.jsonl              gzip/bzip2/xz/zstd-19/brotli/PPMd on the same inputs
  report/data/rerun-status.jsonl                outcome of re-running each receipt for this report

    python3 report/build_scoreboard.py
"""

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "report/data"

STANDARD = {"zstd3", "zstd19", "xz9e", "djvu", "djvu-wide", "djvu-multi", "group4", "png1", "jbig", "jxl",
            "png", "webp", "ffv1", "h264lossless"}
NICE = {"zstd3": "zstd -3", "zstd19": "zstd -19", "xz9e": "xz -9e", "djvu": "DjVu", "djvu-wide": "DjVu",
        "djvu-multi": "DjVu", "group4": "CCITT G4", "png1": "PNG", "jbig": "JBIG", "jxl": "JPEG XL",
        "png": "PNG", "webp": "WebP", "ffv1": "FFV1", "h264lossless": "H.264 lossless", "gzip-9": "gzip -9",
        "bzip2-9": "bzip2 -9", "xz-9e": "xz -9e", "zstd-19-long": "zstd -19", "brotli-11": "brotli -11",
        "ppmd-o10": "PPMd"}

# dataset -> (kind, short description, chapter)
INPUTS = {
    "wiki-dev": ("real", "Wikipedia text, 24 MiB", 5),
    "wiki-transfer": ("real", "Wikipedia text, another 24 MiB", 5),
    "enwik8": ("real", "Wikipedia text, enwik8 (100 MB)", 5),
    "numerical": ("real", "Silesia numerical files (mr + x-ray + sao)", 3),
    "nci": ("real", "Silesia nci (chemical database)", 3),
    "mozilla": ("real", "Silesia mozilla (Firefox binaries)", 3),
    "samba": ("real", "Silesia samba (source tarball)", 3),
    "webster": ("real", "Silesia webster (dictionary)", 3),
    "noaa-1990-prefix": ("real", "NOAA weather records 1990", 3),
    "noaa-2020-prefix": ("real", "NOAA weather records 2020", 3),
    "covertype-prefix": ("real", "UCI forest-cover table", 3),
    "manual-graphs": ("real", "Scanned manual: Graphviz guides", 4),
    "manual-library": ("real", "Scanned manual: Graphviz library", 4),
    "manual-transfer": ("real", "Scanned manual: NASM", 4),
    "manual-valgrind": ("real", "Scanned manual: Valgrind", 4),
    "luma-jake": ("real", "Video clip 1 (grayscale frames)", 4),
    "luma-kath": ("real", "Video clip 2 (grayscale frames)", 4),
    "luma-rei": ("real", "Video clip 3 (grayscale frames)", 4),
    "wall0.ppm": ("real", "Photo 1 (RGB)", 4),
    "wall1.ppm": ("real", "Photo 2 (RGB)", 4),
    "wall2.ppm": ("real", "Photo 3 (RGB)", 4),
    "numpy-update": ("real", "NumPy release given the previous one", 4),
    "mesa-update": ("real", "Mesa release given the previous one", 4),
    "place-distances": ("derived", "Distances between 4,600 real places", 4),
    "arc-distances": ("derived", "Great-circle angles between the same places", 4),
    "affine-pairs": ("derived", "Our archived formula instructions", 1),
    "formula-text": ("derived", "Our formula listing as text", 1),
    "cofattore-Q.base256": ("derived", "Q: the record archive as an integer", 6),
    "neif-archive9": ("derived", "Neif: a later enwik9 archive", 6),
    "whiteboard-costs": ("self", "Census tables printed by our enumerator", 1),
    "whiteboard-witnesses": ("self", "Witness records printed by our enumerator", 1),
    "nonunit-witnesses": ("self", "New witness records printed by our enumerator", 1),
    "evolved-volume": ("planted", "3-D field from a hidden automaton + low rank", 2),
    "noisy-spacetime": ("planted", "4-D noisy field from a hidden automaton", 2),
    "modular-panels": ("planted", "Byte orbit hiding a Kronecker product", 2),
    "learned-field": ("planted", "Field from a hidden cellular rule", 2),
    "shared-orbit-1000": ("planted", "Matrices 1,000 automaton steps from simple", 2),
    "evolved-stamps": ("planted", "Stamps evolved by an automaton", 3),
    "hidden-products": ("planted", "Products hiding a repdigit factor", 1),
    "three-seeds": ("planted", "Sums of three generators", 1),
    "walk-distances": ("planted", "Distances along a random planar walk", 4),
    "uniform": ("control", "Uniform random bytes", 0),
    "random-triangle": ("control", "Random triangle of distances", 0),
    "shuffled-witnesses": ("control", "Witness records with values shuffled", 1),
    "nci-row-shuffled": ("control", "nci with characters shuffled inside rows", 3),
    "graphs-shuffled-lines": ("control", "Graphviz pages with scanlines shuffled", 3),
}


def jsonl(path):
    return [json.loads(line) for line in path.open()] if path.exists() else []


def pct(a, b):
    p = (a / b - 1) * 100
    s = f"{p:+.1f}%" if abs(p) >= 0.1 else f"{p:+.3f}%"
    s = s.replace("-", "−")
    return f"**{s}**" if p < 0 else s


def fill(path, marker, body):
    """Replace the text between <!-- BEGIN marker --> and <!-- END marker --> (inserting the pair at a
    <!-- marker --> placeholder the first time)."""
    text = path.read_text()
    begin, end = f"<!-- BEGIN {marker} -->", f"<!-- END {marker} -->"
    if begin not in text:
        text = text.replace(f"<!-- {marker} -->", begin + "\n" + end)
    a, _, rest = text.partition(begin)
    _, _, b = rest.partition(end)
    path.write_text(a + begin + "\n" + body.strip() + "\n" + end + b)


def chapter_tables(rows):
    """Tables inside the report chapters, generated from scoreboard.json so they never drift."""
    report = ROOT / "report"
    lines = ["| Input | Kind | Best standard tool on the raw bytes | Our best (archive or transform → tool) | Difference |",
             "|---|---|---:|---:|---:|"]
    for r in rows:
        if r["chapter"] != 3 or not r["best_standard_bytes"]:
            continue
        lines.append(f"| {r['label']} | {r['kind']} | {r['best_standard_bytes']:,} ({r['best_standard']}) | "
                     f"{r['ours_bytes']:,} (`{r['ours_codec']}`) | {pct(r['ours_bytes'], r['best_standard_bytes'])} |")
    lines.append("")
    lines.append("*Generated by [`build_scoreboard.py`](build_scoreboard.py) from the receipts and the baseline panel. "
                 "A transform is credited only when it beats the same tool on the raw bytes.*")
    fill(report / "3-reshaping.md", "CH3-TABLE", "\n".join(lines))


def rerun_summary():
    """report/data/rerun-summary.md from rerun-status.jsonl."""
    rows = jsonl(DATA / "rerun-status.jsonl")
    receipts = jsonl(ROOT / "research/large-scale/results/archives.jsonl")
    skipped = sum(r["dataset"] == "enwik9" for r in receipts)
    pending = len(receipts) - skipped - len(rows)
    count = {}
    for r in rows:
        count[r["verdict"]] = count.get(r["verdict"], 0) + 1
    out = ["# Rerun of every published benchmark receipt", "",
           "For this report every receipt in [`archives.jsonl`](../../research/large-scale/results/archives.jsonl) "
           "was run again from scratch with [`rerun_all.py`](../../research/large-scale/rerun_all.py): encode, decode "
           "in a separate process, compare every byte, then compare the new archive with the published one.", "",
           "| Outcome | Receipts |", "|---|---:|"]
    names = {"identical": "Identical archive (same size and SHA-256)",
             "same-size": "Same size, different bytes", "different": "Different size",
             "failed": "Failed (encoder, decoder or comparison)"}
    for k in ("identical", "same-size", "different", "failed"):
        out.append(f"| {names[k]} | {count.get(k, 0)} |")
    out.append(f"| Not rerun (enwik9 inputs; this report tests on enwik8) | {skipped} |")
    if pending:
        out.append(f"| Still running when this page was generated | {pending} |")
    odd = [r for r in rows if r["verdict"] != "identical"]
    if odd:
        out += ["", "## Receipts that did not reproduce identically", "",
                "| Input | Codec | Published bytes | New bytes | Outcome | Note |", "|---|---|---:|---:|---|---|"]
        for r in odd:
            new = f"{r['new_bytes']:,}" if r["new_bytes"] else "—"
            out.append(f"| {r['dataset']} | `{r['codec']}` | {r['published_bytes']:,} | {new} | {r['verdict']} | "
                       f"{r.get('error', '')[:120]} |")
    out.append("")
    (DATA / "rerun-summary.md").write_text("\n".join(out))


def main():
    receipts = jsonl(ROOT / "research/large-scale/results/archives.jsonl")
    panel = jsonl(DATA / "baseline-panel.jsonl")
    rerun = {(r["dataset"], r["codec"]): r["verdict"] for r in jsonl(DATA / "rerun-status.jsonl")}
    std = collections.defaultdict(dict)
    ours = collections.defaultdict(list)
    for r in receipts:
        size = r["archive_plus_reference_bytes"]
        if r["codec"] in STANDARD:
            name = NICE[r["codec"]]
            std[r["dataset"]][name] = min(size, std[r["dataset"]].get(name, size))
        else:
            ours[r["dataset"]].append((size, r["codec"], rerun.get((r["dataset"], r["codec"]), "carried over")))
    # Our reversible transform followed by an unchanged standard back end (fully serialized, round-trip checked).
    for r in jsonl(ROOT / "research/large-scale/results/preprocessing.jsonl"):
        if not r.get("verified", True):
            continue
        for backend, b in r["backends"].items():
            # Credit the transform only when it beats the same back end on the raw bytes.
            if b["prepared"]["bytes"] < b["raw"]["bytes"]:
                ours[r["dataset"]].append((b["prepared"]["bytes"], f"{r['profile']} + {backend}", "carried over"))
    # The same transforms re-run for this report, followed by every panel tool (credited only when the transform
    # beats that same tool on the raw bytes).
    raw_by_tool = {(r["dataset"], r["tool"]): r["archive_bytes"] for r in panel if r["verified"]}
    for r in jsonl(DATA / "paired-panel.jsonl"):
        base = raw_by_tool.get((r["dataset"], r["tool"]))
        if r["verified"] and base and r["archive_bytes"] < base:
            ours[r["dataset"]].append((r["archive_bytes"], f"{r['profile']} → {NICE[r['tool']]}", "re-verified"))
    for r in panel:
        if r["verified"]:
            name = NICE[r["tool"]]
            std[r["dataset"]][name] = min(r["archive_bytes"], std[r["dataset"]].get(name, r["archive_bytes"]))
    rows = []
    for d, (kind, label, chapter) in INPUTS.items():
        if d not in ours:
            continue
        n = next(r["input_bytes"] for r in receipts if r["dataset"] == d)
        size, codec, status = min(ours[d])
        best_std = min(std[d].items(), key=lambda kv: kv[1]) if std[d] else (None, None)
        rows.append(dict(dataset=d, kind=kind, label=label, chapter=chapter, input_bytes=n,
                         ours_codec=codec, ours_bytes=size, ours_status=status,
                         best_standard=best_std[0], best_standard_bytes=best_std[1], standard=std[d],
                         panel_complete=all(t in std[d] for t in ("gzip -9", "bzip2 -9", "brotli -11", "PPMd"))))
    (DATA / "scoreboard.json").write_text(json.dumps(rows, indent=1))
    chapter_tables(rows)
    for r in rows:
        b = r["best_standard_bytes"]
        ratio = f"{r['ours_bytes'] / b:6.3f}" if b else "   -  "
        print(f"{r['kind']:8} {r['dataset']:22} ours {r['ours_bytes']:>12,} ({r['ours_codec']}) "
              f"best std {b or 0:>12,} ({r['best_standard']}) ratio {ratio} panel={r['panel_complete']}")


if __name__ == "__main__":
    main()
    rerun_summary()
