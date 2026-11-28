"""Rewrite every project page (research/*, experiments/*, studies/*) into one short, fixed layout.

    # Title
    > Verdict (computed from the receipts and the baseline panel) · chapter link
    ## Question
    ## How it works          (diagram + format notes)
    ## Results               (one compact table: input, kind, ours, best standard tool, difference)
    <details> all profiles, timings and entropy tables (the generated block kept by project_readmes.py)
    ## Small-scale results   (the original fixture results, if any)
    ## Run it
    <details> provenance (where the code came from)

The script is idempotent: it reads the sections of the current page (old or new layout) and rebuilds it.
    python3 report/project_pages.py [--check]
"""

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research/large-scale"))
sys.path.insert(0, str(ROOT / "report"))
from report import experiment_pages  # noqa: E402
from build_scoreboard import INPUTS, NICE, STANDARD  # noqa: E402

START = "<!-- BEGIN generated project measurements -->"
END = "<!-- END generated project measurements -->"
CHAPTER = {1: "1-formulas.md", 2: "2-dynamics.md", 3: "3-reshaping.md", 4: "4-specialised.md",
           5: "5-text.md", 6: "6-record-archive.md"}
KIND = {"real": "real", "derived": "derived from real", "self": "self-generated", "planted": "planted",
        "control": "control"}
# Which chapter tells each project's story (by folder name).
HOME = {
    "01": 1, "02": 1, "03": 1, "04": 1, "05": 1, "06": 2, "07": 2, "08": 2, "09": 2, "10": 1, "11": 1, "12": 4,
    "13": 3, "14": 4, "15": 4, "16": 4, "formula-factor-grammar": 1, "automaton-factor-residual": 2,
    "reference-formula-intervals": 4, "factor-trees": 1, "whiteboard-trees": 1, "shared-factor-forest": 1,
    "carry-trees": 1, "prime-index-trees": 1, "integer-formulas": 1, "generator-sums": 1,
    "whiteboard-census": 1, "portable-arithmetic": 6, "repdigit-intervals": 1, "quartic-trees": 1,
    "hierarchical-gf2": 2, "tensor-orbits": 2, "checkerboard-orbits": 2, "modular-kronecker": 2,
    "four-dimensional-factors": 2, "learned-cellular-rules": 2, "lattice-prediction": 3,
    "distance-geometry": 4, "shape-context": 4, "glyph-residuals": 4, "text-views": 3, "wiki-structures": 5,
    "arithmetic-references": 6, "reversible-wavelets": 4, "motion-residuals": 4, "context-mixer": 5,
    "statico": 5,
}


def sections(text):
    """Split a page into title, and {heading: body} for '## ' headings (### stay inside)."""
    lines = text.split("\n")
    title = lines[0]
    out, cur, buf = {}, None, []
    for line in lines[1:]:
        if line.startswith("## "):
            if cur is not None:
                out[cur] = "\n".join(buf).strip("\n")
            cur, buf = line[3:].strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip("\n")
    return title, out


def sub(body, heading):
    """Split '### heading' out of a section body -> (rest, sub_body)."""
    m = re.search(rf"^### {re.escape(heading)}\n(.*?)(?=^### |\Z)", body, flags=re.S | re.M)
    if not m:
        return body, ""
    return (body[:m.start()] + body[m.end():]).strip("\n"), m.group(1).strip("\n")


def jsonl(path):
    return [json.loads(x) for x in path.open()] if path.exists() else []


def tables():
    receipts = jsonl(ROOT / "research/large-scale/results/archives.jsonl")
    panel = jsonl(ROOT / "report/data/baseline-panel.jsonl")
    std = {}
    for r in receipts:
        if r["codec"] in STANDARD:
            d = std.setdefault(r["dataset"], {})
            d[NICE[r["codec"]]] = min(r["archive_plus_reference_bytes"], d.get(NICE[r["codec"]], 1 << 62))
    for r in panel:
        if r["verified"]:
            d = std.setdefault(r["dataset"], {})
            d[NICE[r["tool"]]] = min(r["archive_bytes"], d.get(NICE[r["tool"]], 1 << 62))
    return receipts, std


def result_rows(folder, groups, receipts, std):
    rows = {}
    for r in receipts:
        if groups.get(r["codec"].partition("-")[0]) != folder:
            continue
        d, size = r["dataset"], r["archive_plus_reference_bytes"]
        if d not in rows or size < rows[d][0]:
            rows[d] = (size, r["codec"], r["input_bytes"])
    n_of = {r["dataset"]: r["input_bytes"] for r in receipts}
    piped = {}
    for r in jsonl(ROOT / "research/large-scale/results/preprocessing.jsonl"):
        if groups.get(r["profile"].partition("-")[0]) != folder or not r.get("verified", True):
            continue
        for backend, b in r["backends"].items():
            size, d = b["prepared"]["bytes"], r["dataset"]
            if size >= b["raw"]["bytes"]:
                continue  # the transform did not help this back end, so it gets no credit
            cur = piped.get(d)
            if cur is None or size < cur[0]:
                piped[d] = (size, f"{r['profile']} → {backend}")
    panel_raw = {(r["dataset"], r["tool"]): r["archive_bytes"]
                 for r in jsonl(ROOT / "report/data/baseline-panel.jsonl") if r["verified"]}
    for r in jsonl(ROOT / "report/data/paired-panel.jsonl"):
        if groups.get(r["profile"].partition("-")[0]) != folder or not r["verified"]:
            continue
        base = panel_raw.get((r["dataset"], r["tool"]))
        if base and r["archive_bytes"] < base:
            cur = piped.get(r["dataset"])
            if cur is None or r["archive_bytes"] < cur[0]:
                piped[r["dataset"]] = (r["archive_bytes"], f"{r['profile']} → {NICE[r['tool']]}")
    out = []
    for d in set(rows) | set(piped):
        size, codec, n = rows.get(d, (None, None, n_of.get(d)))
        psize, pcodec = piped.get(d, (None, None))
        kind = INPUTS.get(d, ("other", d, 0))[0]
        label = INPUTS.get(d, (None, d, 0))[1]
        best = min(std.get(d, {}).items(), key=lambda kv: kv[1]) if std.get(d) else (None, None)
        top = min(x for x in (size, psize) if x)
        out.append(dict(dataset=d, label=label, kind=kind, n=n, standalone=size, standalone_codec=codec,
                        piped=psize, piped_codec=pcodec, ours=top, codec=codec if top == size else pcodec,
                        best=best[0], best_bytes=best[1]))
    order = {"real": 0, "derived": 1, "self": 2, "planted": 3, "control": 4, "other": 5}
    out.sort(key=lambda r: (order[r["kind"]], r["dataset"]))
    return out


def diff(r):
    if not r["best_bytes"]:
        return "—"
    p = (r["ours"] / r["best_bytes"] - 1) * 100
    if r["ours"] / r["best_bytes"] < 0.01:
        return f"**{r['best_bytes'] / r['ours']:,.0f}× smaller**"
    if r["ours"] / r["best_bytes"] >= 2:
        return f"{r['ours'] / r['best_bytes']:.1f}× larger"
    if abs(p) < 0.1:
        return f"{p:+.4f}%".replace("-", "−")
    return f"**{p:+.1f}%**".replace("-", "−") if p < 0 else f"{p:+.1f}%"


def verdict(rows):
    def best(kinds):
        c = [r for r in rows if r["kind"] in kinds and r["best_bytes"]]
        return min(c, key=lambda r: r["ours"] / r["best_bytes"]) if c else None

    real, planted = best({"real", "derived"}), best({"planted"})
    say = lambda r: f"{r['label']}, {diff(r).replace('**', '')} vs {r['best']}"  # noqa: E731
    if real and real["ours"] < real["best_bytes"] * 0.995:
        head = "wins on real data" if real["kind"] == "real" else "wins on data derived from real data"
        text = f"**Verdict: {head}.** Best: {say(real)}."
    elif real and real["ours"] <= real["best_bytes"] * 1.005:
        text = f"**Verdict: no meaningful gain on real data.** Best real input: {say(real)}."
    elif real:
        head = "detector only" if planted and planted["ours"] < planted["best_bytes"] else "loses on real data"
        text = f"**Verdict: {head}.** Best real input: {say(real)}."
    elif rows and rows[0]["kind"] == "self":
        text = "**Verdict: self-generated data only.** The input is the output of our own program."
    else:
        text = "**Verdict: planted data only.**"
    if planted:
        text += f" Planted control: {say(planted)}."
    return text


# Results that live outside the 20 MiB benchmark (smaller standard files or the full enwik8 runs).
EXTRA = {
    "shape-context": "On the complete Canterbury fax file `ptt5` (513,216 B): **28,037 B**, better than CCITT "
                     "Group 4 (32,344) and xz -9e (39,868) but worse than JBIG (25,917) and lossless DjVu (22,490); "
                     "cmix, published: 21,883.",
    "context-mixer": "On the full enwik8 (100 MB): **17,811,463 B**, better than paq8l -8 (17,916,450, published) "
                     "and xz (24,703,772); see [chapter 5](../../report/5-text.md).",
    "statico": "On the full enwik8: 26,346,968 B; with GLZA-style rule choice 23,774,125 B "
               "([grammar probes](../grammar-probes/README.md)).",
    "whiteboard-census": "Counting every number below 2²⁸ under a decodable price: 974 of 268 million get any "
                         "shorter description and none by 16 bits ([counts](counts)).",
}


def results_table(rows):
    lines = ["| Input | Kind | Raw bytes | Our archive | Our transform → standard tool | Best standard tool | Difference |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        best = f"{r['best_bytes']:,} ({r['best']})" if r["best_bytes"] else "—"
        alone = f"{r['standalone']:,} (`{r['standalone_codec']}`)" if r["standalone"] else "—"
        piped = f"{r['piped']:,} (`{r['piped_codec']}`)" if r["piped"] else "—"
        lines.append(f"| {r['label']} | {KIND.get(r['kind'], r['kind'])} | {r['n']:,} | {alone} | {piped} | "
                     f"{best} | {diff(r)} |")
    return "\n".join(lines)


def build(folder, groups, receipts, std):
    path = folder / "README.md"
    text = path.read_text()
    title, s = sections(text)
    key = folder.name[:2] if folder.parent.name == "experiments" else folder.name
    chapter = HOME[key]
    # --- pull pieces from either layout ---
    question = s.get("Question") or s.get("Question and prior work", "")
    question, provenance = sub(question, "Source files and compatibility")
    provenance = s.get("Provenance", provenance)
    provenance = re.sub(r"^<details><summary>.*?</summary>\n\n|\n\n</details>$", "", provenance.strip(), flags=re.S)
    how = s.get("How it works")
    if how is None:
        variants, diagram = sub(s.get("Variants and format", ""), "Method diagram")
        how = (diagram + "\n\n" + variants).strip()
    plain = json.loads((ROOT / "report/data/plain.json").read_text()).get(key)
    if plain:
        tech = re.search(r"<details><summary>Technical details</summary>\n\n(.*?)\n\n</details>", how, flags=re.S)
        diagram = re.search(r"```mermaid\n.*?```", how, flags=re.S)
        diagram = diagram.group(0) if diagram else ""
        if tech:
            technical = tech.group(1)
        else:
            rest = how.replace(diagram, "").strip()
            technical = (question.strip() + "\n\n" + rest).strip()
        question = plain[0]
        how = "\n\n".join(x for x in (diagram, plain[1], "<details><summary>Technical details</summary>\n\n"
                                          + technical + "\n\n</details>") if x)
    run = s.get("Run it") or s.get("Run the experiment", "")
    small = s.get("Small-scale results")
    if small is None:
        small = (s.get("Inputs and measurement", "") + "\n\n" + s.get("Results", "")).strip()
    bench = s.get("Large-file benchmark", "") or s.get("Results on 20 MiB inputs", "")
    block = bench[bench.find(START):bench.find(END) + len(END)] if START in bench else ""
    rows = result_rows(folder, groups, receipts, std)
    rel = "../../report/" if folder.parent.name in ("research", "experiments", "studies") else "../report/"
    extra = f"\n>\n> {EXTRA[key]}" if key in EXTRA else ""
    nav = (f"> {verdict(rows)}{extra}\n>\n> Part of [chapter {chapter}]({rel}{CHAPTER[chapter]}) of the "
           f"[report]({rel}README.md). Terms: [glossary]({rel}glossary.md).")
    parts = [title, "", nav, "", "## Question", "", question.strip(), "", "## How it works", "", how.strip(), "",
             "## Results on 20 MiB inputs", "",
             "Every archive below decoded byte-exact. *Our archive* is this project's own format. *Our transform → "
             "standard tool* reshapes the bytes reversibly and hands the result to gzip, zstd or xz; it is listed only "
             "where it beats that same tool on the raw bytes. *Best standard tool* is the smallest of gzip, bzip2, "
             "xz, Zstandard, Brotli and PPMd (plus domain codecs for images, scans and video) on the raw bytes. "
             "*Difference* compares the better of our two columns with it; negative = ours is smaller.", "", results_table(rows), ""]
    if block:
        parts += ["<details><summary>All profiles, timings and entropy measurements</summary>", "", block, "",
                  "</details>", ""]
    if small:
        parts += ["## Small-scale results", "", small.strip(), ""]
    parts += ["## Run it", "", run.strip(), ""]
    if provenance:
        parts += ["## Provenance", "", "<details><summary>Where this code came from</summary>", "",
                  provenance.strip(), "", "</details>", ""]
    new = "\n".join(parts).rstrip() + "\n"
    new = new.replace("[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)\n", "")
    return path, text, new


LAB_PORTS = {  # projects recovered from the lab notebooks; their pages are written by hand
    "coincidence-hunt": 1, "rules-vs-noise": 1, "block-programs": 1, "transform-controls": 3,
    "stride-scan": 3, "reshape-tournament": 3, "article-order": 3, "grammar-probes": 5, "bwt-lab": 5,
}
TITLES = {1: "1 · Formulas, numbers and coincidences", 2: "2 · Automata and matrix factors",
          3: "3 · Reshaping data for a standard compressor", 4: "4 · Specialised models", 5: "5 · Text compressors",
          6: "6 · The record archive"}


def index_text():
    """research/README.md: every project, grouped by report chapter, with its verdict line."""
    groups = experiment_pages()
    entries = {c: [] for c in TITLES}
    folders = sorted(set(groups.values())) + [ROOT / "research" / n for n in LAB_PORTS]
    for folder in folders:
        page = folder / "README.md"
        if not page.exists():
            continue
        text = page.read_text()
        title = text.split("\n", 1)[0].lstrip("# ").strip()
        m = re.search(r"^> \*\*Verdict[^*]*\*\*(.*?)(?=\n>\s*\n|\n\n)", text, flags=re.M | re.S)
        head = re.search(r"^> \*\*(Verdict[^*]*)\*\*", text, flags=re.M)
        verdict = (head.group(1).replace("Verdict: ", "").rstrip(".") if head else "")
        key = folder.name[:2] if folder.parent.name == "experiments" else folder.name
        chapter = LAB_PORTS.get(folder.name) or HOME.get(key)
        rel = folder.relative_to(ROOT / "research") if folder.parent.name == "research" else Path("..") / folder.relative_to(ROOT)
        detail = re.sub(r"\s*\n>\s*", " ", m.group(1)).strip().replace("|", "\\|") if m else ""
        entries[chapter].append(f"| [{title}]({rel}/README.md) | {verdict} | {detail} |")
    out = ["# Research projects", "",
           "Every method in this repository, grouped by the [report](../report/README.md) chapter that discusses it. "
           "Each folder holds the code, a one-page description (verdict, question, method, results, how to run) "
           "and its measurements. Numbered experiments live in [`experiments/`](../experiments) and combined "
           "studies in [`studies/`](../studies).", ""]
    for c, title in TITLES.items():
        out += [f"## {title}", "", "| Project | Verdict | Evidence |", "|---|---|---|", *sorted(entries[c]), ""]
    out += ["## Build", "", "```sh", "make -C research -j4        # native code used by the benchmark",
            "make -C research lab         # tools of the recovered lab experiments",
            "python3 research/test.py     # tests", "```", "",
            "Measurements and how to repeat them: [benchmark runner](large-scale/README.md) · "
            "[methods](../report/methods.md).", ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    groups = experiment_pages()
    receipts, std = tables()
    changed = []
    for folder in sorted(set(groups.values())):
        path, old, new = build(folder, groups, receipts, std)
        if new != old:
            changed.append(path)
            if not a.check:
                path.write_text(new)
    index = ROOT / "research/README.md"
    if index.read_text() != index_text():
        changed.append(index)
        if not a.check:
            index.write_text(index_text())
    print(("outdated: " if a.check else "rewrote: ") + str(len(changed)) + " pages")
    if a.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
