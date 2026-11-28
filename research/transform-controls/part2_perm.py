#!/usr/bin/env python3
"""PART 2 control: what a permutation costs.

usage: python3 -I part2_perm.py --file PATH --work DIR --out JSON

Measures on FILE (silesia/dickens):
  * sorted bytes of the file, compressed with `xz -9e -T1` (round trip of the SORTED file checked)
  * log2( n! / prod_c count_c! )  = bits to name which arrangement of the sorted bytes is the file
    (math.lgamma, cross-checked by a direct sum of log2 over integers)
  * n*H0 (plug-in order-0 entropy)
  * real sizes of the original: xz -9e, bzip2 -9, 7z PPMd orders 4/8/16 (each round-trip checked)
  * log2(n!) for an arbitrary permutation of n positions vs 8n
  * bzip2: number of BWT blocks (bit-level scan for the 48-bit block magic) -> 24-bit origin
    pointer per block is the only side information the decoder needs to undo the permutation
  * extra check: a pseudo-random shuffle (numpy default_rng(12345).permutation) of the file's bytes
    compressed with the same xz -9e command
"""
import argparse, hashlib, json, math, os, subprocess, sys
import numpy as np

LN2 = math.log(2.0)


def clean_env():
    env = dict(os.environ)
    for k in ("XZ_DEFAULTS", "XZ_OPT", "ZSTD_CLEVEL", "ZSTD_NBTHREADS", "BZIP2", "BZIP"):
        env.pop(k, None)
    env["LC_ALL"] = "C"
    return env


ENV = clean_env()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, stdin_path=None, stdout_path=None, cwd=None):
    fi = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
    fo = open(stdout_path, "wb") if stdout_path else subprocess.DEVNULL
    p = subprocess.Popen(cmd, stdin=fi, stdout=fo, stderr=subprocess.PIPE, env=ENV, cwd=cwd)
    err = p.stderr.read()
    p.stderr.close()
    _, st, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(st)
    for f in (fi, fo):
        if hasattr(f, "close"):
            f.close()
    return dict(rc=p.returncode, cpu_s=ru.ru_utime + ru.ru_stime, maxrss_kb=ru.ru_maxrss,
                stderr=err.decode("utf-8", "replace")[-300:])


def stream_codec(name, enc, dec, src, src_sha, work):
    out = os.path.join(work, "p2_tmp.out")
    r = run(enc, stdin_path=src, stdout_path=out)
    size = os.path.getsize(out)
    d = subprocess.run(dec, stdin=open(out, "rb"), stdout=subprocess.PIPE, env=ENV)
    ok = r["rc"] == 0 and d.returncode == 0 and sha(d.stdout) == src_sha
    rec = dict(name=name, cmd=" ".join(enc) + " < " + os.path.basename(src), dec_cmd=" ".join(dec),
               size=size, rt_ok=bool(ok), cpu_s=r["cpu_s"], maxrss_kb=r["maxrss_kb"])
    return rec, out


def count_bz2_blocks(path):
    """count bit-aligned occurrences of the block magic 0x314159265359 and the
    end-of-stream magic 0x177245385090 at any of the 8 bit offsets"""
    data = open(path, "rb").read()
    big = int.from_bytes(data, "big")
    res = {}
    for label, magic in (("block", 0x314159265359), ("eos", 0x177245385090)):
        mb = magic.to_bytes(6, "big")
        cnt = 0
        for sh in range(8):
            shifted = (big >> sh).to_bytes(len(data), "big")
            pos = shifted.find(mb)
            while pos != -1:
                cnt += 1
                pos = shifted.find(mb, pos + 1)
        res[label] = cnt
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    raw = open(a.file, "rb").read()
    x = np.frombuffer(raw, np.uint8)
    n = int(x.size)
    src_sha = sha(raw)
    res = dict(file=os.path.basename(a.file), n=n, n_bits=8 * n, sha256=src_sha)

    counts = np.bincount(x, minlength=256).astype(np.int64)
    cl = [int(c) for c in counts]
    res["distinct_byte_values"] = int((counts > 0).sum())
    res["counts"] = cl

    # (ii) bits to name the arrangement: log2 multinomial
    ln_multi = math.lgamma(n + 1) - math.fsum(math.lgamma(c + 1) for c in cl)
    res["log2_multinomial_bits_lgamma"] = ln_multi / LN2
    # cross-check: direct summation of logs (independent of lgamma)
    def log2_fact_sum(m):
        if m < 2:
            return 0.0
        tot = 0.0
        CH = 1 << 22
        for i in range(2, m + 1, CH):
            j = min(i + CH, m + 1)
            tot += math.fsum(np.log2(np.arange(i, j, dtype=np.float64)).tolist())
        return tot
    l2n = log2_fact_sum(n)
    res["log2_multinomial_bits_directsum"] = l2n - math.fsum(log2_fact_sum(c) for c in cl)
    res["log2_multinomial_bytes"] = res["log2_multinomial_bits_lgamma"] / 8

    # (iii) n*H0
    nz = counts[counts > 0].astype(np.float64)
    h0 = float(-(nz / n * np.log2(nz / n)).sum())
    res["H0_bits_per_byte"] = h0
    res["nH0_bits"] = n * h0
    res["nH0_bytes"] = n * h0 / 8
    res["nH0_minus_log2multinomial_bits"] = res["nH0_bits"] - res["log2_multinomial_bits_lgamma"]

    # general statement: arbitrary permutation of n positions
    res["log2_nfact_bits_lgamma"] = math.lgamma(n + 1) / LN2
    res["log2_nfact_bits_directsum"] = l2n
    res["log2_nfact_bytes"] = res["log2_nfact_bits_lgamma"] / 8
    res["log2_nfact_over_file_bits"] = res["log2_nfact_bits_lgamma"] / (8 * n)
    res["log2_nfact_bits_per_position"] = res["log2_nfact_bits_lgamma"] / n
    # small-n sanity of the formula against exact integer factorials
    chk = []
    for m in (10, 1000, 100000):
        exact = math.log2(math.factorial(m)) if m <= 1000 else None
        if exact is None:
            f = math.factorial(m)
            sh = f.bit_length() - 64
            exact = math.log2(f >> sh) + sh
        chk.append(dict(n=m, exact_log2_factorial=exact, lgamma=math.lgamma(m + 1) / LN2))
    res["factorial_formula_check"] = chk

    runs = []
    # (i) sorted file
    sp = os.path.join(a.work, "p2_sorted.bin")
    xs = np.sort(x, kind="stable")
    xs.tofile(sp)
    sorted_sha = sha(xs.tobytes())
    rec, out = stream_codec("sorted|xz-9e", ["xz", "-9e", "-T1", "-c"], ["xz", "-dc", "-T1"],
                            sp, sorted_sha, a.work)
    rec["note"] = ("round trip reproduces the SORTED file only; it is not a compressed form of the "
                   "original (the arrangement is missing)")
    runs.append(rec)
    res["sorted_xz_bytes"] = rec["size"]
    res["histogram_as_256_uint32_bytes"] = 1024
    os.remove(sp)

    # extra: random shuffle of the bytes, same back-end
    rp = os.path.join(a.work, "p2_shuffled.bin")
    perm = np.random.default_rng(12345).permutation(n)
    xr = x[perm]
    xr.tofile(rp)
    rec, out = stream_codec("randomly-permuted|xz-9e", ["xz", "-9e", "-T1", "-c"],
                            ["xz", "-dc", "-T1"], rp, sha(xr.tobytes()), a.work)
    rec["note"] = ("round trip reproduces the SHUFFLED file only; the permutation "
                   "(default_rng(12345).permutation(n)) is regenerated from the seed")
    runs.append(rec)
    res["shuffled_xz_bytes"] = rec["size"]
    os.remove(rp)
    del perm, xr, xs

    # originals
    rec, out = stream_codec("orig|xz-9e", ["xz", "-9e", "-T1", "-c"], ["xz", "-dc", "-T1"],
                            a.file, src_sha, a.work)
    runs.append(rec)
    res["orig_xz_bytes"] = rec["size"]
    rec, out = stream_codec("orig|bzip2-9", ["bzip2", "-9", "-c"], ["bzip2", "-dc"],
                            a.file, src_sha, a.work)
    blocks = count_bz2_blocks(out)
    rec["bwt_blocks"] = blocks["block"]
    rec["eos_markers"] = blocks["eos"]
    rec["origin_pointer_bits_total"] = 24 * blocks["block"]
    runs.append(rec)
    res["orig_bzip2_bytes"] = rec["size"]
    res["bzip2_bwt_blocks"] = blocks["block"]
    res["bzip2_bwt_side_info_bits"] = 24 * blocks["block"]
    os.remove(out)

    # 7z PPMd orders 4, 8, 16
    best = None
    for order in (4, 8, 16):
        arc = os.path.join(a.work, "p2_ppmd.7z")
        if os.path.exists(arc):
            os.remove(arc)
        cmd = ["7z", "a", "-t7z", "-mmt=1", "-m0=PPMd:o=%d:mem=256m" % order, "-bso0", "-bsp0",
               arc, a.file]
        r = run(cmd)
        size = os.path.getsize(arc)
        d = subprocess.run(["7z", "x", "-so", "-mmt=1", arc], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, env=ENV)
        ok = r["rc"] == 0 and d.returncode == 0 and sha(d.stdout) == src_sha
        lst = subprocess.run(["7z", "l", "-slt", arc], stdout=subprocess.PIPE, env=ENV).stdout.decode()
        packed = [l.split("=")[1].strip() for l in lst.splitlines() if l.startswith("Packed Size")]
        rec = dict(name="orig|7z-PPMd-o%d" % order, cmd=" ".join(cmd[:-2]) + " ARCHIVE dickens",
                   dec_cmd="7z x -so -mmt=1 ARCHIVE", size=size, rt_ok=bool(ok), cpu_s=r["cpu_s"],
                   maxrss_kb=r["maxrss_kb"], packed_stream_bytes=int(packed[0]) if packed and packed[0] else None,
                   note="size = whole .7z archive (packed stream + container headers incl. file name)")
        runs.append(rec)
        if ok and (best is None or size < best[1]):
            best = (order, size)
        os.remove(arc)
    res["orig_ppmd_best_order"] = best[0]
    res["orig_ppmd_best_bytes"] = best[1]
    res["runs"] = runs
    res["all_rt_ok"] = all(r["rt_ok"] for r in runs)

    # derived comparisons (bytes)
    lm = res["log2_multinomial_bytes"]
    res["compare_bytes"] = dict(
        arrangement_index=lm, nH0=res["nH0_bytes"], sorted_xz=res["sorted_xz_bytes"],
        sorted_xz_plus_arrangement=res["sorted_xz_bytes"] + lm,
        hist1024_plus_arrangement=1024 + lm,
        orig_xz=res["orig_xz_bytes"], orig_bzip2=res["orig_bzip2_bytes"],
        orig_ppmd_best=res["orig_ppmd_best_bytes"], shuffled_xz=res["shuffled_xz_bytes"],
        arbitrary_permutation=res["log2_nfact_bytes"], file=n)
    with open(a.out + ".tmp", "w") as fh:
        json.dump(res, fh, indent=1)
    os.replace(a.out + ".tmp", a.out)
    pr = {k: v for k, v in res.items() if k not in ("counts", "runs")}
    print(json.dumps(pr, indent=1))
    for r in runs:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
