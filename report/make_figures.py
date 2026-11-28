"""Build every chart in the report from the data files and run outputs.

    python3 report/make_figures.py            # all figures
    python3 report/make_figures.py enwik8     # one figure

Inputs (all inside the repository unless noted):
  report/data/*.json                       hand-entered numbers with their status (carried over / published)
  research/large-scale/results/archives.jsonl   verified benchmark receipts
  report/data/baseline-panel.jsonl         standard tools on every input (copied from runs/baselines)
  report/data/lab/*                        logs of the recovered lab experiments (copied from runs/lab)
"""

import json
from pathlib import Path
import re
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charts import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "report/data"
FIGS = {}


def figure(fn):
    FIGS[fn.__name__] = fn
    return fn


def load(name):
    return json.loads((DATA / name).read_text())


# --------------------------------------------------------------------------------------------------
@figure
def enwik8():
    """Chapter 5: every system on the full enwik8, ours vs standard tools vs published results."""
    ours = load("enwik8-ours.json")["rows"]
    pub = {(r["program"], r["options"] or ""): r["enwik8_bytes"] for r in load("published.json")["enwik8"]}
    rows = [
        ("gzip -9", pub[("gzip", "-9")], "published"),
        ("bzip2 -9", pub[("bzip2", "-9")], "published"),
        ("Statico M1 (ours, grammar)", ours[0]["bytes"], "ours"),
        ("zstd -22 --ultra", pub[("zstd", "-22 --ultra")], "published"),
        ("xz -9e (1 GiB dictionary)", pub[("xz", "--lzma2=preset=9e,dict=1GiB,lc=4,pb=0")], "published"),
        ("Statico + better rule choice (ours)", ours[1]["bytes"], "ours"),
        ("PPMd order 10 (7-Zip)", pub[("7zip", "-m0=ppmd:mem=1630m:o=10 ...")], "published"),
        ("CM v1 (ours, first mixer)", ours[2]["bytes"], "ours"),
        ("GLZA (best grammar coder)", pub[("glza", "c -x -o0.6 -p4 -r16000")], "published"),
        ("lpaq1", pub[("lpaq1", "9")], "published"),
        ("CM2 v10 (ours)", ours[7]["bytes"], "ours"),
        ("paq8l -8", pub[("paq8l", "-8")], "published"),
        ("CM3 v9 (ours, best)", ours[-1]["bytes"], "ours"),
        ("paq8hp12 (dictionary-tuned for enwik)", pub[("paq8hp12any", "-8")], "published"),
        ("durilca'kingsize (PPM, 13 GB RAM)", pub[("durilca'kingsize", "-m13000 -o41 -t2")], "published"),
        ("paq8px v206 -12L", pub[("paq8px_v206fix1", "-12L")], "published"),
        ("nncp v3.2 (GPU transformer)", pub[("nncp", "")], "published"),
        ("cmix v21", pub[("cmix", "-t")], "published"),
    ]
    rows.sort(key=lambda r: -r[1])

    def draw(fig, ax, t):
        y = np.arange(len(rows))
        colors = [t[k] for _, _, k in rows]
        ax.barh(y, [b / 1e6 for _, b, _ in rows], color=colors, height=0.62)
        ax.set_yticks(y, [n for n, _, _ in rows])
        for i, (_, b, k) in enumerate(rows):
            ax.text(b / 1e6 + 0.3, i, f"{b / 1e6:.2f}", va="center", fontsize=8.5,
                    color=t["text"], fontweight="bold" if k == "ours" else "normal")
        ax.set_xlabel("Compressed size of enwik8 in MB (100 MB of Wikipedia). Shorter is better.")
        ax.set_xlim(0, 40)
        from charts import style
        style(ax, t)
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(color=t["ours"], label="ours (this repository)"),
                           Patch(color=t["published"], label="published result (LTCB table)")],
                  loc="upper right", frameon=False, labelcolor=t["text"], fontsize=9)

    render("enwik8", draw, size=(8.5, 6.2))


def ratio_chart(name, rows, title=None, height=None):
    """Diverging bars: log2(ours / best standard). rows = [(label, ours, best, best_name), ...]."""
    import math
    from charts import style
    rows = sorted(rows, key=lambda r: r[1] / r[2], reverse=True)
    lo, hi = -4.0, 2.0

    def draw(fig, ax, t):
        y = np.arange(len(rows))
        vals = [math.log2(o / b) for _, o, b, _ in rows]
        shown = [min(max(v, lo), hi) for v in vals]
        colors = [t["win"] if v < -0.005 else (t["loss"] if v > 0.005 else t["neutral"]) for v in vals]
        ax.barh(y, shown, color=colors, height=0.62)
        ax.axvline(0, color=t["muted"], linewidth=1)
        ax.set_yticks(y, [r[0] for r in rows])
        for i, ((_, o, b, bn), v, s) in enumerate(zip(rows, vals, shown)):
            pct = (o / b - 1) * 100
            txt = f"{pct:+.1f}% vs {bn}" if abs(pct) >= 0.1 else f"{pct:+.4f}% vs {bn}"
            txt = "−" + txt[1:] if pct < 0 else txt
            if v < lo:
                txt = f"{b / o:,.0f}× smaller than {bn}"
            elif v > hi:
                txt = f"{o / b:,.0f}× larger than {bn}"
            elif pct > 100:
                txt = f"{o / b:.1f}× the size of {bn}"
            ax.text(s + (0.06 if s >= 0 else -0.06), i, txt, va="center", ha="left" if s >= 0 else "right",
                    fontsize=8, color=t["text"])
        ticks = [-4, -3, -2, -1, 0, 1, 2]
        ax.set_xticks(ticks, ["÷16", "÷8", "÷4", "÷2", "same", "×2", "×4"])
        ax.set_xlim(lo - 2.3, hi + 2.3)
        ax.set_xlabel("Our archive ÷ best standard tool on the same bytes (log scale; left = smaller)")
        style(ax, t)
        if title:
            ax.set_title(title, loc="left", fontsize=10)

    render(name, draw, size=(9, height or 0.34 * len(rows) + 1.4))


def scoreboard_rows(kinds, chapter=None):
    rows = []
    for r in load("scoreboard.json"):
        if r["kind"] in kinds and r["best_standard_bytes"] and (chapter is None or r["chapter"] == chapter):
            rows.append((r["label"], r["ours_bytes"], r["best_standard_bytes"], r["best_standard"]))
    return rows


_RECEIPTS = None


def best_ours(dataset, prefixes):
    """Smallest verified archive on `dataset` among codecs whose name starts with one of `prefixes`."""
    global _RECEIPTS
    if _RECEIPTS is None:
        _RECEIPTS = [json.loads(x) for x in (ROOT / "research/large-scale/results/archives.jsonl").open()]
    sizes = [r["archive_plus_reference_bytes"] for r in _RECEIPTS
             if r["dataset"] == dataset and r["codec"].startswith(tuple(prefixes))]
    return min(sizes) if sizes else None


def best_standard(dataset):
    for r in load("scoreboard.json"):
        if r["dataset"] == dataset and r["standard"]:
            name, size = min(r["standard"].items(), key=lambda kv: kv[1])
            return size, name
    return None, None


def method_rows(spec):
    """spec = [(label, dataset, [codec prefixes]), ...] -> ratio_chart rows (skips unmeasured pairs)."""
    rows = []
    for label, dataset, prefixes in spec:
        o = best_ours(dataset, prefixes)
        b, bn = best_standard(dataset)
        if o and b:
            rows.append((label, o, b, bn))
    return rows


@figure
def dynamics():
    """Chapter 2: automaton and matrix-factor methods on planted inputs vs real inputs."""
    spec = [
        ("3-D automaton + low rank · planted volume", "evolved-volume", ["tensor-"]),
        ("4-D automaton + bit factors · planted field", "noisy-spacetime", ["four-"]),
        ("Byte orbit + Kronecker factors · planted panels", "modular-panels", ["modular-"]),
        ("Learned cellular rule · planted field", "learned-field", ["learned-"]),
        ("Shared automaton clock · planted matrices", "shared-orbit-1000", ["checker-"]),
        ("Automaton dictionary · planted stamps", "evolved-stamps", ["checker-bitmap-orbit"]),
        ("3-D automaton + low rank · Silesia numerical", "numerical", ["tensor-"]),
        ("3-D automaton + low rank · Silesia samba", "samba", ["tensor-"]),
        ("4-D automaton + bit factors · Silesia numerical", "numerical", ["four-"]),
        ("4-D automaton + bit factors · Silesia samba", "samba", ["four-"]),
        ("Byte orbit + Kronecker factors · Silesia numerical", "numerical", ["modular-"]),
        ("Shared automaton clock · Silesia numerical", "numerical", ["checker-direct", "checker-joint"]),
        ("Equivalent factor bases (exp. 08) · Silesia numerical", "numerical", ["pilot08-"]),
        ("Learned cellular rule · video clip 1", "luma-jake", ["learned-"]),
        ("Learned cellular rule · video clip 3", "luma-rei", ["learned-"]),
        ("Recursive GF(2) factors · scanned manual", "manual-graphs", ["gfh-", "pilot07-"]),
        ("Walsh–Hadamard bit planes (exp. 09) · scanned manual", "manual-graphs", ["pilot09-"]),
    ]
    ratio_chart("dynamics", method_rows(spec))


HUNT = ROOT / "research/coincidence-hunt/results"
FAMILY_NAMES = {"digits+sequences": "Digits of constants, classic sequences", "roots+fractions": "Roots and fractions",
                "random generators": "Random-number generator seeds", "formulas": "Formulas f(i), size ≤ 6",
                "recurrences": "Recurrences x(k+1) = f(x(k), k)", "integer sequences": "Named integer sequences",
                "Fourier": "Walsh–Hadamard / cosine (Fourier)", "geometry": "Automata, Langton's ant, grids, shapes"}


def hunt_families(log):
    """Parse a coincidence-hunt log -> list of dicts per family."""
    text = log.read_text()
    out = []
    for block in text.split("\n=== ")[1:]:
        name = block.split(":")[0].strip()
        cand = re.search(r"-> ([0-9.e+]+) candidates \(naming one costs ([0-9.]+) bits\)", block)
        best = re.search(r"best: (\d+) bits = (.*?), (\d+) wrong", block)
        run = re.search(r"longest exact run from the start: (\d+) bits", block)
        out.append(dict(family=name, candidates=float(cand.group(1)), name_bits=float(cand.group(2)),
                        best_bits=int(best.group(1)) if best else None, best=best.group(2) if best else "",
                        exact_run=int(run.group(1)) if run else 0))
    return out


@figure
def hunt():
    """Chapter 1: total bits per rule family on 300 characters of Wikipedia vs ordinary tools."""
    from charts import style
    fams = [f for f in hunt_families(HUNT / "anarchism.log") if f["best_bits"]]
    tools = json.loads((DATA / "hunt-baselines.json").read_text())
    rows = [(FAMILY_NAMES.get(f["family"], f["family"]), f["best_bits"], "ours") for f in fams]
    rows += [(k, v, "standard") for k, v in tools["tools"].items() if not k.startswith("CM3")]
    rows.append(("Raw text (300 characters × 8 bits)", 2400, "neutral"))
    rows.sort(key=lambda r: r[1])

    def draw(fig, ax, t):
        y = np.arange(len(rows))
        ax.barh(y, [r[1] for r in rows], color=[t[r[2]] for r in rows], height=0.62)
        ax.set_yticks(y, [r[0] for r in rows])
        ax.invert_yaxis()
        for i, r in enumerate(rows):
            ax.text(r[1] + 25, i, f"{r[1]:,}", va="center", fontsize=8.5, color=t["text"])
        ax.set_xlim(0, 2800)
        ax.set_xlabel("Bits to rebuild the 300 characters exactly, everything included. Shorter is better.")
        style(ax, t)
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(color=t["ours"], label="best rule found in each family (10 billion tried)"),
                           Patch(color=t["standard"], label="ordinary compressors on the same 300 characters")],
                  loc="upper center", bbox_to_anchor=(0.35, -0.13), ncol=2, frameon=False, labelcolor=t["text"],
                  fontsize=9)

    render("hunt", draw, size=(9, 5.2))


@figure
def counting():
    """Chapter 1: bits found by luck vs bits needed to name the winner; planted controls far above the line."""
    from charts import style
    d = load("counting.json")

    def draw(fig, ax, t):
        xs = np.array([16, 40])
        ax.plot(xs, xs, color=t["muted"], linewidth=1.2, linestyle="--")
        ax.text(39.6, 47, "line: bits found =\nbits needed to name it", color=t["muted"], fontsize=8.5, ha="right")
        rx = [p[1] for p in d["real"]]
        ry = [p[2] for p in d["real"]]
        ax.scatter(rx, ry, s=46, color=t["ours"], edgecolors=t["surface"], linewidths=1.5, zorder=3,
                   label="real targets (text, compressed output, random bytes)")
        px = [p[1] for p in d["planted"]]
        py = [p[2] for p in d["planted"]]
        ax.scatter(px, py, s=56, marker="D", color=t["standard"], edgecolors=t["surface"], linewidths=1.5,
                   zorder=3, label="planted controls (made by a rule in the family)")
        place = {"primes as text": (-8, 6, "right"), "formula as letters": (8, 6, "left"),
                 "rule 30 output": (-8, 6, "right"), "two rules XORed": (8, 6, "left")}
        for name, x, y, capped in d["planted"]:
            dx, dy, ha = place.get(name, (8, 4, "left"))
            ax.annotate(name + (" (≥)" if capped else ""), (x, y), xytext=(dx, dy), ha=ha,
                        textcoords="offset points", fontsize=8, color=t["text"])
        ax.set_yscale("log")
        ax.set_ylim(12, 6000)
        ax.set_xlim(16, 40)
        ax.set_yticks([16, 32, 64, 128, 256, 512, 1024, 2400], ["16", "32", "64", "128", "256", "512", "1,024", "2,400"])
        ax.set_xlabel("Bits needed to name the winning rule (log₂ of the number of candidates searched)")
        ax.set_ylabel("Bits the rule reproduces exactly")
        style(ax, t, grid_axis="both")
        ax.legend(loc="upper left", frameon=False, labelcolor=t["text"], fontsize=9)

    render("counting", draw, size=(8.5, 5.6))


def paired_best(dataset, prefixes):
    """Best prepared size per backend for one dataset among profiles with the given prefixes."""
    best = {}
    for line in (ROOT / "research/large-scale/results/preprocessing.jsonl").open():
        r = json.loads(line)
        if r["dataset"] != dataset or not r["profile"].startswith(tuple(prefixes)):
            continue
        for k, b in r["backends"].items():
            if k not in best or b["prepared"]["bytes"] < best[k][1]:
                best[k] = (b["raw"]["bytes"], b["prepared"]["bytes"], r["profile"])
    return best


@figure
def reshape():
    """Chapter 3: the same compressor before and after a reversible reshape (real inputs and controls)."""
    from charts import style
    spec = [
        ("NOAA weather 1990: fields to streams", "noaa-1990-prefix", ["lattice-rows"]),
        ("NOAA weather 2020: fields to streams", "noaa-2020-prefix", ["lattice-rows"]),
        ("Forest-cover table: fields to streams", "covertype-prefix", ["lattice-rows"]),
        ("Silesia numerical: lattice prediction", "numerical", ["lattice-"]),
        ("Scanned manual: scanline XOR + quadtree", "manual-graphs", ["checker-bitmap-xor"]),
        ("Wikipedia: BWT and spelling views", "wiki-transfer", ["views-"]),
        ("Silesia webster: fields to streams", "webster", ["lattice-rows"]),
        ("Silesia nci: fields to streams", "nci", ["lattice-rows"]),
        ("CONTROL nci, characters shuffled in rows", "nci-row-shuffled", ["lattice-rows"]),
        ("CONTROL manual, scanlines shuffled", "graphs-shuffled-lines", ["checker-bitmap-xor"]),
    ]
    backends = [("gzip-6", "gzip -6"), ("zstd-3", "zstd -3"), ("xz-6", "xz -6")]
    data = []
    for label, d, pre in spec:
        b = paired_best(d, pre)
        if b:
            data.append((label, [(b[k][1] / b[k][0] - 1) * 100 if k in b else 0 for k, _ in backends]))

    def draw(fig, ax, t):
        y = np.arange(len(data))
        h = 0.26
        cols = list(t["ramp"])  # gzip, zstd, xz: one grey ramp, weakest to strongest compressor
        for j, (_, name) in enumerate(backends):
            vals = [row[1][j] for row in data]
            ax.barh(y + (j - 1) * h, vals, height=h - 0.03, color=cols[j], label=name)
        ax.axvline(0, color=t["muted"], linewidth=1)
        ax.set_yticks(y, [r[0] for r in data])
        ax.invert_yaxis()
        ax.set_xlim(-75, 75)
        ax.set_xlabel("Change in compressed size after reshaping, same compressor (%). Left = smaller.")
        style(ax, t)
        ax.legend(loc="lower right", frameon=False, labelcolor=t["text"], fontsize=9, title="compressor",
                  title_fontsize=9)
        ax.get_legend().get_title().set_color(t["text"])

    render("reshape", draw, size=(9, 6.2))


@figure
def specialised():
    """Chapter 4: models written for one kind of data vs the best domain or general tool."""
    rows = []
    for r in load("scoreboard.json"):
        if r["chapter"] == 4 and r["kind"] in ("real", "derived") and r["best_standard_bytes"]:
            rows.append((r["label"], r["ours_bytes"], r["best_standard_bytes"], r["best_standard"]))
    fax = load("fax.json")
    best = min(fax["standard"].items(), key=lambda kv: kv[1])
    rows.append(("Fax test page (Canterbury ptt5, 0.5 MB)", list(fax["ours"].values())[0], best[1],
                 best[0].split(" (")[0]))
    ratio_chart("specialised", rows)


CM_STEPS = [
    ("cmlab-v1", "CM v1: orders 1–6, word, match, 2 mixers"),
    ("cm2lab-v2", "CM2 v2: + longer orders, word pairs, markup"),
    ("cm2lab-v3", "CM2 v3: bit-history states, indirect context"),
    ("cm2lab-v4", "CM2 v4: number and line-format contexts"),
    ("cm2lab-v5", "CM2 v5: mixer chosen by order-2 node"),
    ("cm2lab-v6", "CM2 v6"),
    ("cm2lab-v7", "CM2 v7"),
    ("cm2lab-v8", "CM2 v8: more indirect contexts, faster decay"),
    ("cm2lab-v9", "CM2 v9: tuned knobs (coordinate descent)"),
    ("cm2lab-v10", "CM2 v10: word-skip and 12-byte contexts"),
    ("cm3-v5", "CM3 v5: cache-line tables + LSTM 192"),
    ("cm3-v7", "CM3 v7: LSTM learning-rate decay"),
    ("cm3-v8", "CM3 v8: best of 32 earlier matches"),
    ("cm3-v9", "CM3 v9: 2nd mixing layer, 2nd match, stems"),
]


def cm_size(log):
    m = re.search(r"(\d+) bytes\s+[0-9.]+ bits/byte", log.read_text()) if log.exists() else None
    return int(m.group(1)) if m else None


@figure
def cm_history():
    """Chapter 5: every CM version on the same first 10 MB of enwik8 (same table budget per family)."""
    from charts import style
    folder = ROOT / "research/context-mixer/history/results"
    rows = [(label, cm_size(folder / f"{key}.log")) for key, label in CM_STEPS]
    rows = [r for r in rows if r[1]]
    if not rows:
        return
    panel = {r["tool"]: r["archive_bytes"] for r in map(json.loads, (DATA / "baseline-panel.jsonl").open())
             if r["dataset"] == "e10m" and r["verified"]}
    refs = [(n, panel.get(k)) for k, n in (("xz-9e", "xz -9e"), ("ppmd-o10", "PPMd o10"), ("brotli-11", "brotli -11"))]
    refs = [r for r in refs if r[1]]

    def draw(fig, ax, t):
        y = np.arange(len(rows))
        ax.barh(y, [b / 1e6 for _, b in rows], color=t["ours"], height=0.62)
        ax.set_yticks(y, [n for n, _ in rows])
        ax.invert_yaxis()
        for i, (_, b) in enumerate(rows):
            ax.text(b / 1e6 + 0.01, i, f"{b:,}", va="center", fontsize=8, color=t["text"])
        for name, v in refs:
            ax.axvline(v / 1e6, color=t["standard"], linewidth=1.2, linestyle="--")
            ax.text(v / 1e6, -0.9, name, color=t["standard"], fontsize=8, ha="center")
        lo = min(b for _, b in rows) / 1e6 - 0.1
        ax.set_xlim(lo, max([b for _, b in rows] + [v for _, v in refs]) / 1e6 + 0.25)
        ax.set_xlabel("Bytes for the first 10 MB of enwik8 (MB, axis does not start at 0). Shorter is better.")
        style(ax, t)

    render("cm-history", draw, size=(9, 0.36 * len(rows) + 1.6))


@figure
def scoreboard_real():
    """README: every real or real-derived input, our best archive vs the best standard tool."""
    ratio_chart("scoreboard-real", scoreboard_rows({"real", "derived"}))


@figure
def scoreboard_planted():
    """README: planted detector tests and random controls."""
    ratio_chart("scoreboard-planted", scoreboard_rows({"planted", "control"}))


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(FIGS)
    for name in wanted:
        FIGS[name]()
        print("figure", name)
