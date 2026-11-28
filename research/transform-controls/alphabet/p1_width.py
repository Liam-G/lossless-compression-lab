#!/usr/bin/env python3
"""p1_width.py - PART 1: re-read the bit string as k-bit symbols.

Worker process.  Run two of them (lane 0 and lane 1); they share one job list,
claim jobs through work/claims/, and append one JSON line per finished
(file, k, bit order) to raw/p1_rows.jsonl.  Resumable: finished keys are skipped.

  python3 -I p1_width.py --corpus /path/to/corpus --lane 0 [--deadline EPOCH] [--phase main|lsb|ext]

Samples: ptt5 whole; first 4,194,304 bytes of dickens, x-ray, mr, sao; 4 MiB of
numpy.random.default_rng(12345).bytes().
"""
import os, sys, time, argparse, math
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I drops the script dir
import numpy as np
import common as C
import tf

MIB4 = 4 * 1024 * 1024
FILES = [
    ("ptt5", "canterbury/ptt5", None),
    ("dickens", "silesia/dickens", MIB4),
    ("x-ray", "silesia/x-ray", MIB4),
    ("mr", "silesia/mr", MIB4),
    ("sao", "silesia/sao", MIB4),
    ("random", None, MIB4),
]
K_MAIN = [8, 16, 32, 24, 12, 4, 2, 7, 6, 10, 14, 20, 5, 3, 1]
K_LSB = [16, 12, 4]
ROWS = os.path.join(C.RAW, "p1_rows.jsonl")
CLAIMS = os.path.join(C.WORK, "claims")


def load_sample(corpus, name, rel, limit):
    if rel is None:
        return np.random.default_rng(12345).bytes(limit)
    with open(os.path.join(corpus, rel), "rb") as f:
        return f.read() if limit is None else f.read(limit)


def entropy_stats(sym, k, nbits_orig):
    """Plug-in (maximum-likelihood) order-0 entropy of the k-bit symbol stream,
    plus an honest two-part code length that also pays for the model."""
    if k <= 24:
        cnt = np.bincount(sym.astype(np.int64), minlength=1)
        cnt = cnt[cnt > 0]
    else:
        cnt = np.unique(sym, return_counts=True)[1]
    n = int(cnt.sum())
    D = int(cnt.size)
    p = cnt.astype(np.float64) / n
    H = float(-(p * np.log2(p)).sum())
    plug_bits = n * H
    ln2 = math.log(2.0)
    A = float(2 ** k)
    alpha_bits = (math.lgamma(A + 1) - math.lgamma(D + 1) - math.lgamma(A - D + 1)) / ln2   # which D of 2^k symbols occur
    count_bits = (math.lgamma(n) - math.lgamma(D) - math.lgamma(n - D + 1)) / ln2           # C(n-1, D-1) count vectors
    return {"n_symbols": n, "distinct": D, "H_bits_per_symbol": H,
            "H_bits_per_orig_bit": plug_bits / nbits_orig,
            "plugin_bytes": plug_bits / 8.0,
            "model_alphabet_bits": alpha_bits, "model_count_bits": count_bits,
            "twopart_bytes": (plug_bits + alpha_bits + count_bits) / 8.0}


def job_list(phase):
    jobs = []
    if phase in ("main", "all"):
        for k in K_MAIN:
            for name, rel, lim in FILES:
                jobs.append((name, k, False))
    if phase in ("lsb", "all"):
        for k in K_LSB:
            for name, rel, lim in FILES:
                jobs.append((name, k, True))
    if phase in ("ext", "all"):
        # full k = 1..32 grid, both bit orders, on the small file only
        for k in range(1, 33):
            if k not in K_MAIN:
                jobs.append(("ptt5", k, False))
        for k in range(1, 33):
            if k not in K_LSB and k != 8:
                jobs.append(("ptt5", k, True))
    return jobs


def key_of(name, k, lsb):
    return "%s|%d|%s" % (name, k, "lsb" if lsb else "msb")


def claim(key):
    os.makedirs(CLAIMS, exist_ok=True)
    p = os.path.join(CLAIMS, "p1_" + key.replace("|", "_"))
    for _ in range(2):
        try:
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                pid = int(open(p).read().strip() or "0")
                os.kill(pid, 0)
                return False          # live owner
            except (ValueError, ProcessLookupError, FileNotFoundError):
                try:
                    os.remove(p)      # stale claim
                except FileNotFoundError:
                    pass
            except PermissionError:
                return False
    return False


def run_job(lane, name, data, sha_orig, k, lsb):
    t0 = time.time()
    base = C.sizes_for(lane, data, C.B_P1)            # "without" (cache hit after first time)
    header, payload, sym = tf.regroup(data, k, lsb, want_symbols=True)
    ent = entropy_stats(sym, k, 8 * len(data))
    del sym
    back = tf.regroup_inv(header, payload)
    tr_ok = (C.sha256(back) == sha_orig and len(back) == len(data))
    del back
    identity = (payload == data)
    shaT = C.sha256(payload)
    recs = C.sizes_for(lane, payload, C.B_P1)         # "with": same command lines
    row = {
        "part": 1, "file": name, "n_orig": len(data), "sha256_orig": sha_orig,
        "k": k, "bitorder": "lsb" if lsb else "msb",
        "header_hex": header.hex(), "header_len": len(header),
        "pad_bits": header[3], "n_T": len(payload), "sha256_T": shaT,
        "transform_roundtrip_ok": tr_ok, "identity": identity,
        "entropy": ent,
        "backends": {}, "wall_s": None, "lane": lane.i, "ts": time.time(),
    }
    for be in C.B_P1:
        r = recs[be]
        b = base[be]
        row["backends"][be] = {
            "cmd": r["cmd"],
            "size_orig": b["size"],
            "size_T": r["size"],
            "total_with": r["size"] + len(header),
            "delta_bytes": r["size"] + len(header) - b["size"],
            "ratio_with_over_without": (r["size"] + len(header)) / b["size"],
            "cpu_c": r["cpu_c"], "cpu_d": r["cpu_d"],
            "maxrss_c_kb": r["maxrss_c_kb"], "maxrss_d_kb": r["maxrss_d_kb"],
            "codec_roundtrip_ok": r["roundtrip_ok"],
            "accepted": bool(r["roundtrip_ok"] and tr_ok),
        }
    row["wall_s"] = time.time() - t0
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--lane", type=int, required=True)
    ap.add_argument("--deadline", type=float, default=0.0)
    ap.add_argument("--phase", default="all")
    a = ap.parse_args()
    lane = C.Lane(a.lane)
    meta = {n: (rel, lim) for n, rel, lim in FILES}
    samples = {}
    for name, k, lsb in job_list(a.phase):
        key = key_of(name, k, lsb)
        done = {key_of(r["file"], r["k"], r["bitorder"] == "lsb") for r in C.read_jsonl(ROWS)}
        if key in done:
            continue
        if a.deadline and time.time() > a.deadline:
            print("deadline reached before", key, flush=True)
            break
        if not claim(key):
            continue
        if name not in samples:
            d = load_sample(a.corpus, name, *meta[name])
            samples[name] = (d, C.sha256(d))
        data, sha_orig = samples[name]
        with lane:
            row = run_job(lane, name, data, sha_orig, k, lsb)
        C.append_jsonl(ROWS, row)
        bs = " ".join("%s=%d(%+d)" % (be, v["total_with"], v["delta_bytes"]) for be, v in row["backends"].items())
        print("%s nT=%d ok=%s id=%s %s  [%.0fs]" % (key, row["n_T"], row["transform_roundtrip_ok"], row["identity"], bs, row["wall_s"]), flush=True)
    print("worker %d finished" % a.lane, flush=True)


if __name__ == "__main__":
    main()
