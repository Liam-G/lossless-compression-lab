"""Re-run every published benchmark receipt, one at a time, and record whether it reproduced.

Resumable: a receipt whose output file already exists is skipped. A failing trial is logged and the
queue continues. Each new receipt is compared with the published one:

  identical   same archive size and SHA-256
  same-size   same size, different bytes (e.g. a CPU-budgeted search took another path)
  different   different size (the new size is what the report shows, marked as changed)
  failed      the encoder, decoder or byte comparison failed

Usage: python3 research/large-scale/rerun_all.py runs/rerun [--skip enwik9] [--only DATASET ...]
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from replay import resolve  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--raw", type=Path, default=Path("runs/large/raw"))
    p.add_argument("--workspace", type=Path, default=Path(".."))
    p.add_argument("--skip", nargs="*", default=["enwik9"])
    p.add_argument("--only", nargs="*")
    a = p.parse_args()

    rows = [json.loads(line) for line in (HERE / "results/archives.jsonl").open()]
    rows = [r for r in rows if r["dataset"] not in a.skip]
    if a.only:
        rows = [r for r in rows if r["dataset"] in a.only]
    # Quick trials first so results arrive early; ties keep the published order.
    order = sorted(range(len(rows)), key=lambda i: rows[i]["encode_s"] + rows[i]["decode_s"])
    a.output.mkdir(parents=True, exist_ok=True)
    status = a.output / "status.jsonl"
    log = a.output / "progress.log"
    done = 0
    for n, i in enumerate(order):
        r = rows[i]
        out = a.output / r["dataset"] / f"{i:03}-{r['codec']}.jsonl"
        if out.exists():
            done += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        started = time.time()
        verdict, new = "failed", None
        error = ""
        try:
            src = resolve(r["dataset"], r["input_sha256"], a.raw, a.workspace)
            cmd = [sys.executable, HERE / "bench.py", src, out, r["codec"]]
            knobs = r.get("knobs", {})
            if "reference" in knobs:
                cmd += ["--reference",
                        resolve(knobs["reference"], knobs["reference_sha256"], a.raw, a.workspace)]
            env = dict(os.environ)
            env["PILOT_WORKERS"] = str(knobs.get("workers", 1))
            env["PILOT_NATIVE_GF2"] = "1" if knobs.get("native_gf2", False) else "0"
            subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL,
                           stderr=open(out.with_suffix(".err"), "w"))
            new = json.loads(out.read_text().splitlines()[-1])
            if new["archive_sha256"] == r["archive_sha256"]:
                verdict = "identical"
            elif new["archive_bytes"] == r["archive_bytes"]:
                verdict = "same-size"
            else:
                verdict = "different"
        except Exception as exc:  # keep going; the report marks it
            error = repr(exc)[:300]
            if out.exists():
                out.rename(out.with_suffix(".partial"))
        line = dict(index=i, dataset=r["dataset"], codec=r["codec"], verdict=verdict,
                    published_bytes=r["archive_bytes"],
                    new_bytes=new["archive_bytes"] if new else None,
                    seconds=round(time.time() - started, 1), error=error)
        with status.open("a") as s:
            print(json.dumps(line), file=s)
        done += 1
        with log.open("a") as s:
            print(f"{time.strftime('%H:%M:%S')} [{done}/{len(rows)}] {verdict:9} "
                  f"{r['dataset']} {r['codec']} {r['archive_bytes']} -> "
                  f"{line['new_bytes']} ({line['seconds']} s) {error}", file=s, flush=True)
    with log.open("a") as s:
        print("ALL DONE", file=s)


if __name__ == "__main__":
    main()
