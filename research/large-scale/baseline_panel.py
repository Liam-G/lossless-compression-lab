"""Measure the same panel of standard compressors on every benchmark input, with a round trip each.

The panel is the yardstick for every result in the report: a method "wins" only if its complete archive is
smaller than the best member of this panel on the same bytes (plus the domain codecs measured elsewhere,
such as DjVu, JBIG2, JPEG XL or FFV1).

  gzip -9 | bzip2 -9 | xz -9e (1 thread) | zstd -19 --long=27 | brotli -q 11 -w 24 | 7z PPMd order 10, 768 MiB

Usage: python3 research/large-scale/baseline_panel.py runs/large/raw runs/baselines/panel.jsonl [--skip enwik9]
Resumable: (dataset, tool) pairs already in the output are skipped.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

TOOLS = {
    "gzip-9": (["gzip", "-9", "-n", "-c"], ["gzip", "-dc"]),
    "bzip2-9": (["bzip2", "-9", "-c"], ["bzip2", "-dc"]),
    "xz-9e": (["xz", "-9e", "-T1", "-c"], ["xz", "-dc"]),
    "zstd-19-long": (["zstd", "-19", "--long=27", "-T1", "-q", "-c"], ["zstd", "-d", "--long=27", "-q", "-c"]),
    "brotli-11": (["brotli", "-q", "11", "-w", "24", "-c"], ["brotli", "-d", "-c"]),
}


def sha(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def run_stream(tool, src, tmp):
    enc, dec = TOOLS[tool]
    arc, back = tmp / "a", tmp / "b"
    t0 = time.perf_counter()
    with open(arc, "wb") as out:
        subprocess.run(enc + [str(src)], stdout=out, check=True)
    t1 = time.perf_counter()
    with open(back, "wb") as out:
        subprocess.run(dec + [str(arc)], stdout=out, check=True)
    t2 = time.perf_counter()
    return arc, back, t1 - t0, t2 - t1


def run_ppmd(src, tmp):
    arc, outdir = tmp / "a.7z", tmp / "x"
    t0 = time.perf_counter()
    subprocess.run(["7z", "a", "-bd", "-bso0", "-t7z", "-m0=PPMd:mem=768m:o=10", "-mmt=1", str(arc), str(src)],
                   check=True)
    t1 = time.perf_counter()
    subprocess.run(["7z", "e", "-bd", "-bso0", f"-o{outdir}", str(arc)], check=True)
    t2 = time.perf_counter()
    return arc, outdir / src.name, t1 - t0, t2 - t1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--skip", nargs="*", default=["enwik9"])
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--extra", nargs="*", type=Path, default=[], help="more input files (e.g. corpus/enwik8/enwik8)")
    a = p.parse_args()
    done = set()
    if a.output.exists():
        for line in a.output.open():
            r = json.loads(line)
            done.add((r["dataset"], r["tool"]))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = sorted(f for f in a.raw.iterdir() if f.is_file() and f.suffix != ".json" and f.name not in a.skip)
    inputs += a.extra
    jobs = [(src, tool) for src in inputs if src.stat().st_size >= 1 << 20
            for tool in list(TOOLS) + ["ppmd-o10"] if (src.name, tool) not in done]
    lock = threading.Lock()
    digests = {}

    def one(job):
        src, tool = job
        with lock:
            if src not in digests:
                digests[src] = sha(src)
        with tempfile.TemporaryDirectory(dir=a.output.parent) as td:
            tmp = Path(td)
            arc, back, te, td_ = run_ppmd(src, tmp) if tool == "ppmd-o10" else run_stream(tool, src, tmp)
            ok = subprocess.run(["cmp", "-s", str(src), str(back)]).returncode == 0
            row = dict(dataset=src.name, tool=tool, input_bytes=src.stat().st_size, input_sha256=digests[src],
                       archive_bytes=arc.stat().st_size, verified=ok, encode_s=round(te, 3),
                       decode_s=round(td_, 3))
        with lock, a.output.open("a") as out:
            print(json.dumps(row), file=out, flush=True)
            print(f"{src.name:28} {tool:13} {row['archive_bytes']:>12,} {'ok' if ok else 'MISMATCH'}", flush=True)

    with ThreadPoolExecutor(a.jobs) as pool:
        list(pool.map(one, jobs))


if __name__ == "__main__":
    main()
