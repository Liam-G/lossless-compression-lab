"""Re-run the best reversible transform per real input, then compress its output with the full baseline panel.

For every real or real-derived input in results/preprocessing.jsonl, the profile whose prepared stream compressed
smallest with xz -6 is run again from scratch (prepare -> independent inverse -> byte comparison). The prepared
stream is then compressed by every panel tool (gzip -9, bzip2 -9, xz -9e, zstd -19 --long, brotli -11, PPMd),
each with a round trip. The output rows are comparable with baseline_panel.py rows on the raw input.

Usage: python3 research/large-scale/paired_panel.py runs/large/raw runs/paired-panel.jsonl [--jobs 3]
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from baseline_panel import TOOLS, run_ppmd, run_stream  # noqa: E402
from preprocess import prepare  # noqa: E402

SKIP_KINDS = {"uniform", "evolved-stamps", "rotated-stamps", "hidden-products", "learned-field",
              "modular-panels", "noisy-spacetime", "shared-orbit-1000", "whiteboard-witnesses",
              "shuffled-witnesses"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--jobs", type=int, default=3)
    a = p.parse_args()
    best = {}
    for line in (HERE / "results/preprocessing.jsonl").open():
        r = json.loads(line)
        if r["dataset"] in SKIP_KINDS:
            continue
        size = r["backends"]["xz-6"]["prepared"]["bytes"]
        if r["dataset"] not in best or size < best[r["dataset"]][0]:
            best[r["dataset"]] = (size, r["profile"])
    done = set()
    if a.output.exists():
        done = {(json.loads(x)["dataset"], json.loads(x)["tool"]) for x in a.output.open()}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    work = a.output.parent / "paired-work"
    work.mkdir(exist_ok=True)
    for dataset, (_, profile) in sorted(best.items()):
        tools = [t for t in list(TOOLS) + ["ppmd-o10"] if (dataset, t) not in done]
        if not tools:
            continue
        src = a.raw / dataset
        with tempfile.TemporaryDirectory(dir=work) as td:
            tmp = Path(td)
            prepared = prepare(src, profile, tmp)
            path = tmp / "prepared"
            path.write_bytes(prepared)
            back = tmp / "restored"
            subprocess.run([sys.executable, HERE / "preprocess.py", "restore", path, back], check=True)
            inverse_ok = back.read_bytes() == src.read_bytes()
            digest = hashlib.sha256(prepared).hexdigest()

            def one(tool):
                with tempfile.TemporaryDirectory(dir=tmp) as t2:
                    t2 = Path(t2)
                    arc, out, te, tdd = run_ppmd(path, t2) if tool == "ppmd-o10" else run_stream(tool, path, t2)
                    ok = subprocess.run(["cmp", "-s", str(path), str(out)]).returncode == 0
                    row = dict(dataset=dataset, profile=profile, tool=tool, prepared_bytes=len(prepared),
                               prepared_sha256=digest, inverse_verified=inverse_ok, verified=ok and inverse_ok,
                               archive_bytes=arc.stat().st_size, encode_s=round(te, 3), decode_s=round(tdd, 3))
                with lock, a.output.open("a") as f:
                    print(json.dumps(row), file=f, flush=True)
                    print(f"{dataset:22} {profile:32} {tool:13} {row['archive_bytes']:>12,} "
                          f"{'ok' if row['verified'] else 'FAILED'}", flush=True)

            with ThreadPoolExecutor(a.jobs) as pool:
                list(pool.map(one, tools))


if __name__ == "__main__":
    main()
