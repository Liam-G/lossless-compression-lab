#!/usr/bin/env python3
"""PART 1 control: transform search on random and already-compressed data.

usage:
  python3 -I part1_search.py --dickens PATH --work DIR --outdir DIR [--selftest]
                             [--only rand|dickens_xz] [--stats-only]

Targets
  rand        8 MiB from numpy.random.default_rng(12345).bytes(8*1024*1024)
  dickens_xz  `xz -9e -T1 -c < dickens`

Candidates (2064 per target), index -> transform
  0..1023     delta(w), w = idx+1      y[i] = x[i] - x[i-w] mod 256 (y[i] = x[i] for i < w)
  1024..2047  shuffle(w), w = idx-1023 column-major regrouping: x[0::w] ++ x[1::w] ++ ...
  2048..2063  bits(k), k = idx-2047    bit stream (MSB first) cut into k-bit symbols, zero padded;
                                       each symbol stored in 1 byte (k<=8) or 2 bytes big-endian (k>8)

(i) estimates, in bits, over the symbol stream of the transformed data
  h0  plug-in order-0 entropy:  m*H0
  h1  plug-in order-1 entropy:  sum_ab n_ab*log2(n_a/n_ab)  (+ k bits for the first symbol)
  kt0/kt1  code length of an adaptive order-0/order-1 arithmetic coder with the
           Krichevsky-Trofimov estimator (a length a real decoder-synchronous coder reaches;
           unlike the plug-in number it pays for learning the statistics)

(ii) real sizes: back-ends `xz -9e -T1 -c FILE` and `zstd -19 --single-thread -q -c FILE`.
  Container = 2 header bytes (big-endian uint16 = idx<<4 | pad_bits) + back-end output.
  Every container is decoded again from the container file alone and compared by SHA-256.
"""
import argparse, hashlib, json, math, os, random, subprocess, sys, time
import numpy as np
from scipy.special import gammaln

LN2 = math.log(2.0)
NCAND = 2064
BACKENDS = {
    "xz":   (["xz", "-9e", "-T1", "-c"],                        ["xz", "-dc", "-T1"]),
    "zstd": (["zstd", "-19", "--single-thread", "-q", "-c"],    ["zstd", "-dc", "-q"]),
}
MAGIC = {b"\xfd7zXZ\x00": "xz", b"\x28\xb5\x2f\xfd": "zstd"}


# ----------------------------------------------------------------- transforms
def cand_desc(idx):
    if idx < 1024:
        return ("delta", idx + 1)
    if idx < 2048:
        return ("shuffle", idx - 1023)
    return ("bits", idx - 2047)


def t_delta(x, w):
    y = x.copy()
    y[w:] -= x[:-w]
    return y


def inv_delta(y, w):
    n = y.size
    rows = -(-n // w)
    pad = rows * w - n
    a = np.concatenate([y, np.zeros(pad, np.uint8)]) if pad else y
    return np.add.accumulate(a.reshape(rows, w), axis=0, dtype=np.uint8).reshape(-1)[:n]


def _shuffle_keep(n, w):
    full, r = divmod(n, w)
    rows = full + 1
    keep = np.ones(rows * w, bool)
    keep[np.arange(r, w) * rows + full] = False      # pad cells: last row of columns r..w-1
    return rows, keep


def t_shuffle(x, w):
    n = x.size
    full, r = divmod(n, w)
    if r == 0:
        return np.ascontiguousarray(x.reshape(full, w).T).reshape(-1)
    rows, keep = _shuffle_keep(n, w)
    a = np.zeros(rows * w, np.uint8)
    a[:n] = x
    return np.ascontiguousarray(a.reshape(rows, w).T).reshape(-1)[keep]


def inv_shuffle(y, w):
    n = y.size
    full, r = divmod(n, w)
    if r == 0:
        return np.ascontiguousarray(y.reshape(w, full).T).reshape(-1)
    rows, keep = _shuffle_keep(n, w)
    a = np.zeros(rows * w, np.uint8)
    a[keep] = y
    return np.ascontiguousarray(a.reshape(w, rows).T).reshape(-1)[:n]


def t_bits(x, k):
    """-> (payload uint8 array, pad_bits, symbol array)"""
    bits = np.unpackbits(x)
    nb = bits.size
    m = -(-nb // k)
    pad = m * k - nb
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, np.uint8)])
    if k == 1:
        return bits, pad, bits
    b = bits.reshape(m, k)
    p = np.packbits(b, axis=1)                        # left aligned
    if k <= 8:
        sym = p.reshape(-1) >> (8 - k)
        return sym, pad, sym
    v = ((p[:, 0].astype(np.uint16) << 8) | p[:, 1]) >> (16 - k)
    payload = np.ascontiguousarray(v.astype(">u2")).view(np.uint8)
    return payload, pad, v


def inv_bits(payload, k, pad):
    if k == 1:
        bits = payload & 1
        m = bits.size
    elif k <= 8:
        m = payload.size
        bits = np.ascontiguousarray(np.unpackbits(payload.reshape(m, 1), axis=1)[:, 8 - k:]).reshape(-1)
    else:
        assert payload.size % 2 == 0
        m = payload.size // 2
        bits = np.ascontiguousarray(np.unpackbits(payload.reshape(m, 2), axis=1)[:, 16 - k:]).reshape(-1)
    nb = m * k - pad
    assert nb % 8 == 0
    return np.packbits(bits[:nb])


def forward(x, idx):
    """-> (payload bytes array, pad_bits, symbols, symbol_bits)"""
    kind, p = cand_desc(idx)
    if kind == "delta":
        y = t_delta(x, p)
        return y, 0, y, 8
    if kind == "shuffle":
        y = t_shuffle(x, p)
        return y, 0, y, 8
    payload, pad, sym = t_bits(x, p)
    return payload, pad, sym, p


def inverse(payload, idx, pad):
    kind, p = cand_desc(idx)
    if kind == "delta":
        return inv_delta(payload, p)
    if kind == "shuffle":
        return inv_shuffle(payload, p)
    return inv_bits(payload, p, pad)


# ------------------------------------------------------------------ estimates
def order0_counts(sym, k):
    K = 1 << k
    c = np.zeros(K, np.int64)
    CH = 1 << 23
    for i in range(0, sym.size, CH):
        c += np.bincount(sym[i:i + CH], minlength=K)
    return c


def pair_counts(sym, k):
    """-> (nonzero pair counts n_ab, context totals n_a over sym[:-1])"""
    m = sym.size
    K = 1 << k
    if 2 * k <= 24:
        c = np.zeros(1 << (2 * k), np.int64)
        CH = 1 << 23
        for i in range(0, m - 1, CH):
            j = min(i + CH, m - 1)
            a = sym[i:j].astype(np.int64)
            a <<= k
            a |= sym[i + 1:j + 1]
            c += np.bincount(a, minlength=1 << (2 * k))
        ctx = c.reshape(K, K).sum(axis=1)
        return c[c > 0], ctx
    a = sym[:-1].astype(np.int64)
    a <<= k
    a |= sym[1:]
    _, cnt = np.unique(a, return_counts=True)
    ctx = np.bincount(sym[:-1], minlength=K)
    return cnt, ctx


def estimates(sym, k):
    c0 = order0_counts(sym, k)
    m = int(c0.sum())
    nz = c0[c0 > 0].astype(np.float64)
    K = float(1 << k)
    h0 = (m * math.log(m) - float((nz * np.log(nz)).sum())) / LN2
    kt0 = (float(gammaln(m + K / 2) - gammaln(K / 2))
           - float((gammaln(nz + 0.5) - gammaln(0.5)).sum())) / LN2
    pn, ctx = pair_counts(sym, k)
    pn = pn.astype(np.float64)
    cn = ctx[ctx > 0].astype(np.float64)
    h1 = (float((cn * np.log(cn)).sum()) - float((pn * np.log(pn)).sum())) / LN2 + k
    kt1 = (float((gammaln(cn + K / 2) - gammaln(K / 2)).sum())
           - float((gammaln(pn + 0.5) - gammaln(0.5)).sum())) / LN2 + k
    return dict(n_sym=m, h0_bits=h0, h1_bits=h1, kt0_bits=kt0, kt1_bits=kt1,
                distinct_sym=int(nz.size), distinct_pairs=int(pn.size))


# -------------------------------------------------------------------- helpers
def clean_env():
    env = dict(os.environ)
    for k in ("XZ_DEFAULTS", "XZ_OPT", "ZSTD_CLEVEL", "ZSTD_NBTHREADS"):
        env.pop(k, None)
    env["LC_ALL"] = "C"
    return env


ENV = clean_env()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def run_to_fd(cmd, out_fd):
    p = subprocess.Popen(cmd, stdout=out_fd, stdin=subprocess.DEVNULL, env=ENV)
    _, st, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(st)
    return p.returncode, ru.ru_utime + ru.ru_stime, ru.ru_maxrss


def encode_container(x, idx, backend, work, tag):
    """transform x with candidate idx, compress, write header+payload container."""
    payload, pad, _, _ = forward(x, idx)
    tpath = os.path.join(work, "p1_%s.tr" % tag)
    cpath = os.path.join(work, "p1_%s.container" % tag)
    with open(tpath, "wb") as fh:
        fh.write(memoryview(np.ascontiguousarray(payload)))
    tr_bytes = int(payload.size)
    del payload
    hdr = ((idx << 4) | pad).to_bytes(2, "big")
    fd = os.open(cpath, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)
    os.write(fd, hdr)
    rc, cpu, rss = run_to_fd(BACKENDS[backend][0] + [tpath], fd)
    os.close(fd)
    os.remove(tpath)
    return cpath, dict(rc=rc, cpu_s=cpu, maxrss_kb=rss, transformed_bytes=tr_bytes, pad_bits=pad,
                       header_bytes=2, cmd=" ".join(BACKENDS[backend][0]) + " <transformed file>")


def decode_container(cpath):
    """decode using only the container file -> original bytes (numpy uint8)"""
    fd = os.open(cpath, os.O_RDONLY)
    hdr = os.read(fd, 2)
    v = int.from_bytes(hdr, "big")
    idx, pad = v >> 4, v & 15
    magic = os.pread(fd, 6, 2)
    backend = None
    for mg, name in MAGIC.items():
        if magic.startswith(mg):
            backend = name
    if backend is None:
        raise ValueError("unknown payload magic")
    p = subprocess.Popen(BACKENDS[backend][1], stdin=fd, stdout=subprocess.PIPE, env=ENV)
    data = p.stdout.read()
    p.stdout.close()
    _, st, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(st)
    os.close(fd)
    if p.returncode != 0:
        raise ValueError("decoder failed")
    payload = np.frombuffer(data, np.uint8)
    return inverse(payload, idx, pad), idx, backend, ru.ru_utime + ru.ru_stime


def selftest():
    rng = np.random.default_rng(1)
    for n in (10007, 4096, 1025, 3000):
        x = rng.integers(0, 256, n, dtype=np.uint8)
        x[: n // 3] = (np.arange(n // 3) % 7).astype(np.uint8)      # some structure
        for idx in range(NCAND):
            payload, pad, sym, k = forward(x, idx)
            back = inverse(np.ascontiguousarray(payload), idx, pad)
            assert back.dtype == np.uint8 and back.size == n and np.array_equal(back, x), (n, idx)
            kind, p = cand_desc(idx)
            if kind == "delta":
                ref = bytes((x[i] - (x[i - p] if i >= p else 0)) & 0xFF for i in range(min(n, 3000)))
                assert bytes(payload[:len(ref)]) == ref
            elif kind == "shuffle":
                assert np.array_equal(payload, np.concatenate([x[j::p] for j in range(p)]))
            else:
                s = "".join("{:08b}".format(b) for b in bytes(x[:200]))
                want = [int(s[i:i + p], 2) for i in range(0, len(s) - p + 1, p)][:50]
                assert [int(t) for t in sym[:len(want)]] == want
        # estimates sanity: order-0 plug-in on bytes equals direct formula
    x = rng.integers(0, 256, 50000, dtype=np.uint8)
    e = estimates(x, 8)
    c = np.bincount(x, minlength=256).astype(float)
    pr = c[c > 0] / c.sum()
    assert abs(e["h0_bits"] - (-(pr * np.log2(pr)).sum() * x.size)) < 1e-6
    # order-1 by brute force
    d = {}
    for a, b in zip(x[:-1].tolist(), x[1:].tolist()):
        d[(a, b)] = d.get((a, b), 0) + 1
    ca = {}
    for (a, b), v in d.items():
        ca[a] = ca.get(a, 0) + v
    h1 = sum(v * math.log2(ca[a] / v) for (a, b), v in d.items()) + 8
    assert abs(e["h1_bits"] - h1) < 1e-6, (e["h1_bits"], h1)
    # KT order-0 by sequential simulation
    cnt = [0] * 256
    L = 0.0
    for t, s in enumerate(x[:5000].tolist()):
        L -= math.log2((cnt[s] + 0.5) / (t + 128.0))
        cnt[s] += 1
    assert abs(estimates(x[:5000], 8)["kt0_bits"] - L) < 1e-6
    # the unique() path (k=13) against the bincount path semantics
    payload, pad, sym, k = forward(x, 2047 + 13)
    e13 = estimates(sym, 13)
    d = {}
    sl = sym.tolist()
    for a, b in zip(sl[:-1], sl[1:]):
        d[(a, b)] = d.get((a, b), 0) + 1
    ca = {}
    for (a, b), v in d.items():
        ca[a] = ca.get(a, 0) + v
    h1 = sum(v * math.log2(ca[a] / v) for (a, b), v in d.items()) + 13
    assert abs(e13["h1_bits"] - h1) < 1e-6
    print("selftest ok")


# ----------------------------------------------------------------------- main
def make_targets(a):
    t = {}
    rp = os.path.join(a.work, "rand8m.bin")
    if not os.path.exists(rp):
        b = np.random.default_rng(12345).bytes(8 * 1024 * 1024)
        with open(rp + ".tmp", "wb") as fh:
            fh.write(b)
        os.replace(rp + ".tmp", rp)
    t["rand"] = rp
    dp = os.path.join(a.work, "dickens.xz")
    if not os.path.exists(dp):
        fd = os.open(dp + ".tmp", os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)
        rc, cpu, rss = run_to_fd(["xz", "-9e", "-T1", "-c", a.dickens], fd)
        os.close(fd)
        assert rc == 0
        os.replace(dp + ".tmp", dp)
    t["dickens_xz"] = dp
    return t


def do_stats(name, x, outdir):
    path = os.path.join(outdir, "part1_stats_%s.json" % name)
    if os.path.exists(path):
        return json.load(open(path))
    rows = []
    t0 = time.time()
    for idx in range(NCAND):
        payload, pad, sym, k = forward(x, idx)
        e = estimates(sym, k)
        kind, p = cand_desc(idx)
        e.update(idx=idx, kind=kind, param=p, sym_bits=k, pad_bits=pad,
                 transformed_bytes=int(payload.size))
        rows.append(e)
        if idx % 256 == 0:
            print("stats %s idx=%d t=%.0fs" % (name, idx, time.time() - t0), flush=True)
    res = dict(target=name, n=int(x.size), sha256=sha256_bytes(x.tobytes()), cpu_note="numpy",
               candidates=rows)
    with open(path + ".tmp", "w") as fh:
        json.dump(res, fh)
    os.replace(path + ".tmp", path)
    return res


def select(stats):
    rows = stats["candidates"]
    key = lambda r: (min(r["h0_bits"], r["h1_bits"]), r["idx"])
    ranked = sorted(rows, key=key)
    top40 = [r["idx"] for r in ranked[:40]]
    top5_h0 = [r["idx"] for r in sorted(rows, key=lambda r: (r["h0_bits"], r["idx"]))[:5]]
    pool = [i for i in range(NCAND) if i not in set(top40)]
    rnd40 = random.Random(12345).sample(pool, 40)
    forced = [1024] + list(range(2063, 2047, -1))        # identity (shuffle w=1) + bits k=16..1
    order = []
    for i in top40 + rnd40 + top5_h0 + forced:
        if i not in order:
            order.append(i)
    return dict(top40=top40, random40=rnd40, top5_h0=top5_h0, forced=forced, order=order)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dickens")
    ap.add_argument("--work")
    ap.add_argument("--outdir")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stats-only", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    targets = make_targets(a)
    runs_path = os.path.join(a.outdir, "part1_runs.jsonl")
    done = set()
    if os.path.exists(runs_path):
        for line in open(runs_path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("rt_ok"):
                done.add((r["target"], r["idx"], r["backend"]))
    sel_all = {}
    for name in ("dickens_xz", "rand"):
        if a.only and a.only != name:
            continue
        x = np.fromfile(targets[name], np.uint8)
        sha = sha256_bytes(x.tobytes())
        stats = do_stats(name, x, a.outdir)
        assert stats["sha256"] == sha and stats["n"] == x.size
        sel = select(stats)
        sel_all[name] = sel
        with open(os.path.join(a.outdir, "part1_selection_%s.json" % name), "w") as fh:
            json.dump(sel, fh)
        if a.stats_only:
            continue
        # plain back-end on the untransformed file (idx = -1, no header)
        for backend in BACKENDS:
            if (name, -1, backend) in done:
                continue
            ppath = os.path.join(a.work, "p1_plain.out")
            fd = os.open(ppath, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)
            rc, cpu, rss = run_to_fd(BACKENDS[backend][0] + [targets[name]], fd)
            os.close(fd)
            out = subprocess.run(BACKENDS[backend][1] + [ppath], stdout=subprocess.PIPE, env=ENV)
            ok = rc == 0 and out.returncode == 0 and sha256_bytes(out.stdout) == sha
            rec = dict(target=name, idx=-1, kind="plain", param=0, backend=backend,
                       size=os.path.getsize(ppath), header_bytes=0, n=int(x.size), rt_ok=bool(ok),
                       cpu_s=cpu, maxrss_kb=rss,
                       cmd=" ".join(BACKENDS[backend][0]) + " " + os.path.basename(targets[name]))
            os.remove(ppath)
            with open(runs_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(rec, flush=True)
        for idx in sel["order"]:
            for backend in BACKENDS:
                if (name, idx, backend) in done:
                    continue
                t0 = time.time()
                cpath, info = encode_container(x, idx, backend, a.work, name)
                size = os.path.getsize(cpath)
                back, didx, dbackend, dcpu = decode_container(cpath)
                ok = (info["rc"] == 0 and didx == idx and dbackend == backend
                      and back.size == x.size and sha256_bytes(back.tobytes()) == sha)
                del back
                os.remove(cpath)
                kind, p = cand_desc(idx)
                rec = dict(target=name, idx=idx, kind=kind, param=p, backend=backend, size=size,
                           n=int(x.size), rt_ok=bool(ok), dec_cpu_s=dcpu, wall_s=time.time() - t0)
                rec.update(info)
                with open(runs_path, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                print("%s %s(%d) %s size=%d (%+d vs raw) cpu=%.1fs rt=%s" % (
                    name, kind, p, backend, size, size - x.size, info["cpu_s"], ok), flush=True)
    print("part1 done", flush=True)


if __name__ == "__main__":
    main()
