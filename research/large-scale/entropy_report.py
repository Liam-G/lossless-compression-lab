"""Publish the paired byte-entropy and off-the-shelf compressor measurements."""

import argparse
import json
from pathlib import Path

from entropy_bench import BACKENDS, MINIMUM

HERE = Path(__file__).resolve().parent
PLOTS = [
    ("wiki-transfer", "pilot01-adaptive-ratios", "Wikipedia · repdigit formulas"),
    ("wiki-transfer", "views-bwt", "Wikipedia · BWT"),
    ("noaa-2020-prefix", "lattice-rows-fields", "NOAA · CSV field routing"),
    ("noaa-2020-prefix", "lattice-rows-delta", "NOAA · equal-width row differences"),
    ("covertype-prefix", "lattice-rows-field-positions", "Covertype · field and position"),
    ("manual-library", "checker-bitmap-xor-tree", "Graphviz manual · XOR + tile tree"),
    ("numerical", "lattice-joint", "Numerical data · lattice prediction"),
    ("whiteboard-witnesses", "witness-joint", "Original witnesses · formula columns"),
    ("hidden-products", "shared-shared", "Generated products · factor tree"),
    ("modular-panels", "modular-joint", "Generated panels · cellular orbit"),
    ("evolved-stamps", "checker-bitmap-orbit-book", "Generated stamps · CA + dictionary"),
]


def saving(trial, backend):
    sizes = trial["backends"][backend]
    return 100 * (1 - sizes["prepared"]["bytes"] / sizes["raw"]["bytes"])


def write_report(rows, folder):
    folder.mkdir(parents=True, exist_ok=True)
    seen = set()
    baselines = {}
    for r in rows:
        identity = r["dataset"], r["profile"]
        if identity in seen or r["verified"] is not True or r["raw"]["bytes"] < MINIMUM:
            raise ValueError(f"Invalid or duplicate measurement for {identity}")
        seen.add(identity)
        if set(r["backends"]) != set(BACKENDS):
            raise ValueError(f"Incomplete backend comparison for {identity}")
        baseline = r["raw"], {k: v["raw"] for k, v in r["backends"].items()}
        if baselines.setdefault(r["dataset"], baseline) != baseline:
            raise ValueError(f"Conflicting raw baseline for {r['dataset']}")

    prefix = [
        "# Preprocessing before standard compression",
        "",
        f"{len(rows)} measured input/profile pairs on {len(baselines)} distinct inputs. Each raw input is at least 20 MiB. Each pair uses exactly the same source bytes on both paths.",
        "",
        "1. Compress the original input directly with gzip, Zstandard or XZ.",
        "2. Serialize the reversible preprocessing output, including headers, choices, lengths, dictionaries, model parameters, literal fallbacks and residuals. Measure this stream before backend compression, then compress it with the same executable and settings as the original.",
        "3. Decompress both paths and compare every byte. An independent invocation of the inverse preprocessor must also recover the original input exactly.",
        "",
        "## Empirical entropy before and after preprocessing",
        "",
        "**H0** is the entropy of the observed byte histogram. **H1** is the entropy of the next byte given the immediately preceding byte, weighted by observed adjacent pairs. Both are in bits per byte of their own stream. The first byte has no predecessor. **Post H0 per input byte** multiplies post H0 by prepared length / original length, so a shorter representation with higher byte entropy can still score well. These are empirical coding estimates for two simple models.",
        "",
        "| Input | Preprocessor | Original bytes | Prepared bytes | H0 before → after | H1 before → after | Post H0 per input byte |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        a, b = r["raw"], r["prepared"]
        prefix.append(
            f"| {r['dataset']} | {r['profile']} | {a['bytes']:,} | {b['bytes']:,} | {a['h0']:.4f} → {b['h0']:.4f} | {a['h1']:.4f} → {b['h1']:.4f} | {b['h0'] * b['bytes'] / a['bytes']:.4f} |"
        )
    lines = prefix + [
        "",
        "## Whole-stream compressor results",
        "",
        "Each cell gives **compressed original bytes → compressed prepared bytes (percentage saved)**. Positive percentages mean preprocessing helped that compressor. Every run used one whole-stream invocation with stdin, one thread, the same settings on both paths and no external reference. Both recipients are assumed to have the software. The numbers include standard container framing.",
        "",
        "| Input | Preprocessor | Zstandard 3 | gzip 6 | XZ 6 |",
        "|---|---|---:|---:|---:|",
    ]
    for r in rows:
        cells = [r["dataset"], r["profile"]]
        for backend in BACKENDS:
            sizes = r["backends"][backend]
            cells.append(
                f"{sizes['raw']['bytes']:,} → {sizes['prepared']['bytes']:,} ({saving(r, backend):+.3f}%)"
            )
        lines.append("| " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Reproduction",
        "",
        "From the repository root, with the pinned inputs prepared and the research binaries built, run:",
        "",
        "```sh",
        "mkdir -p runs/paired",
        "python3 research/large-scale/entropy_bench.py lattice-joint runs/large/raw/numerical runs/paired/lattice.json",
        "python3 research/large-scale/preprocess.py prepare lattice-joint runs/large/raw/numerical runs/paired/numerical.pre",
        "python3 research/large-scale/preprocess.py restore runs/paired/numerical.pre runs/paired/numerical.out",
        "cmp runs/large/raw/numerical runs/paired/numerical.out",
        "```",
        "",
        "The numbered pilots here already emit a reversible record stream. The adapter preserves the encoder’s block choices. For block-compressed formats it removes the terminal Zstandard frames and updates their lengths. For row and bitmap profiles it removes the outer Zstandard wrapper and measures the complete RGP1 or CBP1 stream. On restore it supplies the framing expected by the corresponding decoder. All backends receive the same frozen representation, including the modes selected by the original encoder’s internal cost model. These observations cover the listed profiles and inputs.",
        "",
        "The [machine-readable receipts](preprocessing.jsonl) give the complete input, prepared and compressed stream hashes, commands, versions and byte counts. The [corpus manifest and preparation instructions](../README.md#inputs) describe their provenance.",
    ]
    (folder / "preprocessing.md").write_text("\n".join(lines) + "\n")
    (folder / "preprocessing.jsonl").write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        )
    )


def chart(rows, dest):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.transforms import blended_transform_factory

    lookup = {(r["dataset"], r["profile"]): r for r in rows}
    selected = [
        (lookup[(ds, profile)], label)
        for ds, profile, label in PLOTS
        if (ds, profile) in lookup
    ]
    if not selected:
        raise ValueError("No selected plot measurements in receipts")
    fig, (left, right) = plt.subplots(
        1,
        2,
        figsize=(11, 1.4 + 0.45 * len(selected)),
        gridspec_kw={"width_ratios": [1.25, 1]},
        facecolor="white",
    )
    fig.subplots_adjust(left=0.30, right=0.94, bottom=0.17, top=0.80, wspace=0.33)
    for ax in (left, right):
        ax.set_ylim(len(selected) - 0.5, -0.5)
        ax.set_yticks([])
        ax.grid(axis="x", color="#e1e8e9", linewidth=0.7)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis="x", length=0, pad=5)
    left.set_xlim(-0.2, 8.2)
    left.set_xticks([0, 2, 4, 6, 8])
    left.set_xlabel("Bits per byte of each stream")
    left.set_title("Byte entropy (H0)", loc="left")
    transform = blended_transform_factory(left.transAxes, left.transData)
    right.set_title("Savings with Zstandard 3", loc="left")
    right.set_xlabel("Reduction in compressed size (%)")
    scores = [saving(r, "zstd-3") for r, _ in selected]
    right.set_xlim(min(-8, min(scores) - 4), max(scores) + 16)
    right.axvline(0, color="#657882", lw=0.9)
    for y, (r, label) in enumerate(selected):
        a, b = r["raw"]["h0"], r["prepared"]["h0"]
        left.text(
            -0.04, y, label, va="center", ha="right", transform=transform, fontsize=10
        )
        left.plot([a, b], [y, y], c="#9aaab1", lw=2)
        left.scatter(
            a,
            y,
            s=65,
            facecolors="white",
            edgecolors="#425663",
            linewidths=1.5,
            zorder=3,
        )
        left.scatter(b, y, s=19, color="#007c72", zorder=4)
        score = scores[y]
        right.barh(y, score, height=0.42, color="#007c72" if score >= 0 else "#b25537")
        right.text(max(0, score) + 1.2, y, f"{score:+.2f}%", va="center", fontsize=9)
    left.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                ls="",
                markerfacecolor="white",
                markeredgecolor="#425663",
                label="Original",
            ),
            Line2D([], [], marker="o", ls="", color="#007c72", label="Prepared"),
        ],
        loc="lower left",
        bbox_to_anchor=(-0.03, 1.10),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    fig.savefig(dest, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", type=Path, nargs="+")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--chart", action="store_true")
    a = p.parse_args()
    rows = sorted(
        (json.loads(line) for f in a.files for line in f.read_text().splitlines()),
        key=lambda r: (r["dataset"], r["profile"]),
    )
    write_report(rows, a.output)
    if a.chart:
        chart(rows, a.output / "preprocessing.png")
