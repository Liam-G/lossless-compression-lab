"""Shared chart style for the report: every figure is written twice, for light and dark page themes.

Markdown embeds both with <picture> so GitHub shows the one matching the reader's theme:

    <picture><source media="(prefers-color-scheme: dark)" srcset="figures/x-dark.svg">
    <img alt="..." src="figures/x-light.svg"></picture>

Colour has one job per chart:
  OURS      categorical slot 1 (blue)    - a method from this repository
  STANDARD  categorical slot 2 (orange)  - a standard tool measured here on the same bytes
  PUBLISHED categorical slot 3 (aqua)    - a third-party number taken from a published table
Wins and losses use the diverging blue <-> red pair with a grey midpoint.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIGURES = Path(__file__).resolve().parent / "figures"

THEMES = {
    "light": dict(surface="#ffffff", text="#191919", muted="#666666", grid="#e6e6e6",
                  ours="#257de0", standard="#f47230", published="#00b894",
                  win="#1b64be", loss="#dc3c3d", neutral="#bdbdbd",
                  ramp=("#c9c9c9", "#8f8f8f", "#4f4f4f")),
    "dark": dict(surface="#191919", text="#efefef", muted="#9c9c9c", grid="#333333",
                 ours="#338ced", standard="#e76624", published="#00a888",
                 win="#519ced", loss="#eb6263", neutral="#555555",
                 ramp=("#5a5a5a", "#9a9a9a", "#dcdcdc")),
}


def style(ax, t, grid_axis="x"):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["muted"])
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=t["muted"], labelcolor=t["text"], labelsize=9, length=3)
    ax.grid(axis=grid_axis, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(t["text"])
    ax.yaxis.label.set_color(t["text"])
    ax.title.set_color(t["text"])


def render(name, draw, size=(8, 4.5)):
    """draw(fig, ax, theme_dict) for both themes; writes figures/<name>-light.svg and -dark.svg."""
    FIGURES.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "path", "font.size": 10})
    for mode, t in THEMES.items():
        fig, ax = plt.subplots(figsize=size)
        fig.patch.set_facecolor(t["surface"])
        draw(fig, ax, t)
        fig.tight_layout()
        fig.savefig(FIGURES / f"{name}-{mode}.svg", facecolor=t["surface"], metadata={"Date": None})
        plt.close(fig)


def picture(name, alt, prefix="figures"):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{prefix}/{name}-dark.svg">'
            f'<img alt="{alt}" src="{prefix}/{name}-light.svg"></picture>')


def mb(x):
    return f"{x / 1e6:,.2f} MB"
