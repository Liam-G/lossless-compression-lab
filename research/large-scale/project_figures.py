"""Publication figures for the per-project reports, derived from verified receipts."""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from textwrap import fill

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REGISTER = HERE / "results" / "figures.json"
BACKENDS = ("gzip-6", "zstd-3", "xz-6")
LABELS = ("gzip 6", "Zstd 3", "XZ 6")
COLORS = ("#9d4e18", "#00675d", "#554891")


def gain(row, backend):
    b = row["backends"][backend]
    return 100 * (b["raw"]["bytes"] - b["prepared"]["bytes"]) / b["raw"]["bytes"]


def h0_cost(row):
    return row["prepared"]["h0"] * row["prepared"]["bytes"] / row["raw"]["bytes"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Figures:
    """Check inputs and artwork using the stdlib. Only rendering needs Matplotlib."""

    def __init__(self, check):
        self.check = check
        self.old = json.loads(REGISTER.read_text()) if REGISTER.exists() else {}
        self.current = {}
        self.renderer = digest(Path(__file__).read_bytes())

    def add(self, path, data, draw):
        key = str(path.relative_to(ROOT))
        payload = json.dumps(
            [self.renderer, key, data], separators=(",", ":"), sort_keys=True
        )
        fingerprint = digest(payload.encode())
        actual = digest(path.read_bytes()) if path.exists() else None
        entry = [fingerprint, actual]
        if actual is None or entry != self.old.get(key):
            if self.check:
                raise ValueError(f"Stale or missing research figure: {key}")
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            with plt.rc_context(
                {
                    "svg.fonttype": "none",
                    "svg.hashsalt": "compression-lab",
                    "font.size": 10,
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "axes.labelcolor": "#273842",
                }
            ):
                fig = draw(plt, data)
                path.parent.mkdir(parents=True, exist_ok=True)
                svg = BytesIO()
                fig.savefig(
                    svg,
                    format="svg",
                    bbox_inches="tight",
                    pad_inches=0.18,
                    metadata={"Date": None, "Creator": "Lossless Compression Lab"},
                )
                plt.close(fig)
            artwork = (
                b"\n".join(line.rstrip() for line in svg.getvalue().splitlines())
                + b"\n"
            )
            path.write_bytes(artwork)
            entry[1] = digest(artwork)
        self.current[key] = entry

    def finish(self):
        if self.current == self.old:
            return
        if self.check:
            raise ValueError("Research figure register is out of date")
        REGISTER.write_text(json.dumps(self.current, indent=2, sort_keys=True) + "\n")


def archive_data(datasets, baselines, preferred):
    cells = []
    for name in sorted(datasets, key=lambda n: (n != preferred, n)):
        rows = datasets[name]
        controls = baselines.get((name, rows[0]["input_sha256"]), [])
        for is_control, group in ((False, rows), (True, controls)):
            for r in group:
                label = r["codec"]
                if reference := r["knobs"].get("reference"):
                    label += " / " + reference
                cells.append(
                    (
                        name,
                        label,
                        is_control,
                        r["archive_plus_reference_bytes"],
                        r["input_bytes"],
                    )
                )
    return cells


def archive_figure(plt, cells):
    import numpy as np
    from matplotlib.colors import BoundaryNorm, ListedColormap

    names = list(dict.fromkeys(c[0] for c in cells))
    chunks = [names[i : i + 5] for i in range(0, len(names), 5)]
    panels = []
    for group in chunks:
        values = {
            (label, ds): 100 * total / raw
            for ds, label, _, total, raw in cells
            if ds in group
        }
        sizes = {
            (label, ds): (total, raw)
            for ds, label, _, total, raw in cells
            if ds in group
        }
        labels = sorted(
            {(control, label) for ds, label, control, _, _ in cells if ds in group}
        )
        panels.append((group, labels, values, sizes))
    heights = [0.32 * len(labels) + 0.9 for _, labels, _, _ in panels]
    fig, axes = plt.subplots(
        len(panels),
        1,
        figsize=(8.0, sum(heights) + 0.5),
        squeeze=False,
        gridspec_kw={"height_ratios": heights},
        layout="constrained",
    )
    colors = ListedColormap(
        ["#a6d5c8", "#c6e5dc", "#e0f1e9", "#f1f6ed", "#f8eedb", "#f3d5ba", "#ebb49e"]
    )
    colors.set_bad("#f3f4f5")
    norm = BoundaryNorm([0, 10, 25, 50, 100, 100.0000001, 125, float("inf")], colors.N)
    for ax, (group, labels, values, sizes) in zip(axes.flat, panels):
        matrix = np.array(
            [
                [values.get((label, name), np.nan) for name in group]
                for _, label in labels
            ]
        )
        ax.imshow(
            matrix, cmap=colors, norm=norm, aspect="auto", interpolation="nearest"
        )
        ax.set_xticks(range(len(group)), [fill(n, 16) for n in group], fontsize=9)
        ax.xaxis.tick_top()
        ax.set_yticks(
            range(len(labels)), [fill(label, 39) for _, label in labels], fontsize=9
        )
        ax.tick_params(length=0, pad=5)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, (control, method) in enumerate(labels):
            if control and i and not labels[i - 1][0]:
                ax.axhline(i - 0.5, color="#687982", lw=1.2)
            for j, value in enumerate(matrix[i]):
                if np.isnan(value):
                    label = "—"
                else:
                    total, raw = sizes[method, group[j]]
                    if round(value, 1) == 100:
                        label = f"{total - raw:+,} B"
                    elif value < 0.1:
                        label = f"{total:,} B total"
                    else:
                        label = f"{value:.1f}%"
                ax.text(
                    j, i, label, ha="center", va="center", fontsize=9, color="#1c303a"
                )
        ax.set_xticks(np.arange(-0.5, len(group)), minor=True)
        ax.set_yticks(np.arange(-0.5, len(labels)), minor=True)
        ax.grid(which="minor", color="white", lw=1)
        ax.tick_params(which="minor", length=0)
    fig.suptitle(
        "Delivered size relative to the original input", fontsize=14, weight="bold"
    )
    return fig


def paired_figure(plt, rows):
    from matplotlib.lines import Line2D

    n = len(rows)
    fig, (left, middle, right) = plt.subplots(
        1,
        3,
        figsize=(11.5, 2.25 + n * 0.40),
        sharey=True,
        width_ratios=(1, 1, 1.3),
        layout="constrained",
    )
    for ax in (left, middle, right):
        ax.set_ylim(n - 0.45, -0.55)
        ax.grid(axis="x", alpha=0.22)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    left.set_yticks(range(n), [row[0] for row in rows], fontsize=9)
    limit = max(8, max(max(row[1:5]) for row in rows)) * 1.04
    for ax, title in (
        (left, "H0 · byte frequencies"),
        (middle, "H1 · previous-byte context"),
    ):
        ax.set_title(title, loc="left")
        ax.set_xlabel("Estimated bits per original byte")
        ax.set_xlim(0, limit)
    right.set_title("Change in compressed size", loc="left")
    right.set_xlabel(
        "Percent saved vs same compressor on raw\nNegative values mean a larger archive"
    )
    right.axvline(0, color="#52616a", lw=1)
    for i, (_, h0_before, h0_after, h1_before, h1_after, savings) in enumerate(rows):
        for ax, before, after in (
            (left, h0_before, h0_after),
            (middle, h1_before, h1_after),
        ):
            ax.plot([before, after], [i, i], color="#7a8b96", lw=2)
            ax.scatter(
                before, i, s=55, facecolors="white", edgecolors="#35464e", zorder=3
            )
            ax.scatter(after, i, s=17, color="#00675d", zorder=4)
        for offset, score, color, marker in zip(
            (-0.17, 0, 0.17), savings, COLORS, ("s", "o", "^")
        ):
            right.scatter(score, i + offset, s=27, color=color, marker=marker, zorder=3)
    right.margins(x=0.10)
    left.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                lw=0,
                markerfacecolor="white",
                markeredgecolor="#35464e",
                label="Original",
            ),
            Line2D([], [], marker="o", lw=0, color="#00675d", label="Prepared"),
        ],
        loc="lower left",
        bbox_to_anchor=(0, 1.13),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    right.legend(
        handles=[
            Line2D([], [], marker=m, lw=0, color=c, label=t)
            for m, c, t in zip(("s", "o", "^"), COLORS, LABELS)
        ],
        loc="lower left",
        bbox_to_anchor=(0, 1.13),
        ncol=3,
        frameon=False,
        fontsize=9,
    )
    return fig


def all_pairs_figure(plt, rows):
    fig, axes = plt.subplots(
        1, 3, figsize=(12, 4.4), sharex=True, sharey=True, layout="constrained"
    )
    for i, (ax, label, color) in enumerate(zip(axes, LABELS, COLORS)):
        ax.axvline(0, color="#697983", lw=1)
        ax.axhline(0, color="#697983", lw=1)
        ax.scatter(
            [r[0] for r in rows],
            [r[1][i] for r in rows],
            s=22,
            color=color,
            alpha=0.56,
            edgecolors="none",
        )
        ax.set_title(label, loc="left", weight="bold")
        ax.grid(alpha=0.17)
    axes[0].set_ylabel("Compressed bytes saved (%)")
    fig.supxlabel(
        "Original H0 minus prepared H0 × prepared length / raw length (bits per original byte)"
    )
    return fig
