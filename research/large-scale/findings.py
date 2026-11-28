"""Summarize every paired trial while keeping repeated measurements of one input visible."""

from collections import defaultdict
from pathlib import Path
from statistics import mean

from project_figures import BACKENDS, LABELS, all_pairs_figure, gain, h0_cost

START = "<!-- BEGIN paired analysis -->"
END = "<!-- END paired analysis -->"


def update_findings(text, pairs, figures):
    rows = sorted(pairs, key=lambda r: (r["dataset"], r["profile"]))
    by_input = defaultdict(list)
    for r in rows:
        by_input[r["raw"]["sha256"]].append(r)
    unique = {(r["raw"]["sha256"], r["prepared"]["sha256"]): r for r in rows}
    points = [
        (r["raw"]["h0"] - h0_cost(r), [gain(r, b) for b in BACKENDS]) for r in rows
    ]
    figures.add(
        Path(__file__).resolve().parent / "results/entropy-agreement.svg",
        points,
        all_pairs_figure,
    )
    lines = [
        START,
        "",
        f"The paired set contains **{len(rows)} input/profile comparisons on {len(by_input)} distinct input hashes**. Each raw file is at least 20 MiB. Each point represents one verified pair. The {len(rows)} pairs yield {len(unique)} distinct raw/prepared hash pairs. Profiles that produce identical streams occupy the same point.",
        "",
        "![Three scatterplots of normalized H0 reduction against compressed size reduction, one panel per compressor.](results/entropy-agreement.svg)",
        "",
        "Moving right means a lower estimated zero-order cost per original byte. Moving up means a smaller final file. Upper-left points are practical wins despite a worse H0 estimate. Lower-right points improve the H0 estimate and still increase the archive. Both differences use the fully serialized stream.",
        "",
        "| Backend | Smaller / tied / larger | Smaller, with higher H0 cost | Larger, with lower H0 cost | Smaller among distinct streams | Mean share smaller within each input |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for i, (k, label) in enumerate(zip(BACKENDS, LABELS)):
        smaller = sum(y[i] > 0 for _, y in points)
        ties = sum(y[i] == 0 for _, y in points)
        win_up = sum(x < 0 and y[i] > 0 for x, y in points)
        loss_down = sum(x > 0 and y[i] < 0 for x, y in points)
        unique_wins = sum(gain(r, k) > 0 for r in unique.values())
        balanced = mean(
            sum(gain(r, k) > 0 for r in group) / len(group)
            for group in by_input.values()
        )
        lines.append(
            f"| {label} | {smaller} / {ties} / {len(rows) - smaller - ties} | {win_up} | {loss_down} | {unique_wins}/{len(unique)} | {100 * balanced:.1f}% |"
        )
    lines += [
        "",
        "Counts use exact integer byte comparisons. The last column first computes the fraction of measured profiles that save bytes on each input, then averages those fractions with equal weight per input hash. The selection of methods varies by input. Neither count estimates a success probability on new files.",
        "",
        END,
    ]
    if (
        text.count(START) != 1
        or text.count(END) != 1
        or text.index(START) > text.index(END)
    ):
        raise ValueError("Invalid paired analysis markers")
    return text.split(START)[0] + "\n".join(lines) + text.split(END)[1]
