#!/usr/bin/env python3
"""common.py - shared helpers for the lab/alphabet measurements.

* Back-end command lines (identical for "with transform" and "without").
  Every back-end is run with cwd = a lane directory and the input ALWAYS named
  in.bin, so container overhead (7z member name etc.) is constant.
* Content-addressed compression log: one JSON line per (sha256(input), backend)
  in raw/compress_log.jsonl.  Re-running is a cache hit (resumable).
* Each compression is followed by a full decompression whose output is hashed
  with SHA-256 and compared with the SHA-256 of the input.
* CPU seconds and peak RSS come from meas.py (one child per measuring process,
  resource.getrusage(RUSAGE_CHILDREN) deltas).
* Two lanes (flock) cap concurrency at 2 heavy processes for all drivers.
"""
import os, sys, json, hashlib, subprocess, fcntl, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
RAW = os.path.join(HERE, "raw")
MEAS = os.path.join(HERE, "meas.py")
CLOG = os.path.join(RAW, "compress_log.jsonl")
PPMD_MEM = "512m"

BACKENDS = {
    "xz9e": {
        "c": ["xz", "-9e", "-T1", "-c", "in.bin"], "out": "out.xz", "to_stdout": True,
        "d": ["xz", "-dc", "out.xz"]},
    "zstd22": {
        "c": ["zstd", "--ultra", "-22", "--single-thread", "-c", "in.bin"], "out": "out.zst", "to_stdout": True,
        "d": ["zstd", "-dc", "out.zst"]},
    "bzip2_9": {
        "c": ["bzip2", "-9", "-c", "in.bin"], "out": "out.bz2", "to_stdout": True,
        "d": ["bzip2", "-dc", "out.bz2"]},
}
for _o in (4, 8, 16):
    BACKENDS["ppmd_o%d" % _o] = {
        "c": ["7z", "a", "-t7z", "-m0=PPMd:o=%d:mem=%s" % (_o, PPMD_MEM), "-mmt=1", "-bd", "-y", "out.7z", "in.bin"],
        "out": "out.7z", "to_stdout": False,
        "d": ["7z", "x", "-so", "out.7z"]}

B_P1 = ["xz9e", "zstd22", "ppmd_o8", "ppmd_o16"]
B_FULL = ["xz9e", "zstd22", "bzip2_9", "ppmd_o4", "ppmd_o8", "ppmd_o16"]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def cmd_str(be):
    b = BACKENDS[be]
    c = " ".join(b["c"])
    if b["to_stdout"]:
        c += " > " + b["out"]
    return c


def append_jsonl(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (json.dumps(rec, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path, "rb") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except Exception:
                        pass
    return out


def load_cache():
    c = {}
    for r in read_jsonl(CLOG):
        if r.get("roundtrip_ok"):
            c[(r["sha256_in"], r["backend"])] = r
    return c


class Lane:
    """Exclusive lane: at most one heavy process per lane, two lanes in total."""

    def __init__(self, i):
        self.i = i
        self.dir = os.path.join(WORK, "lane%d" % i)
        os.makedirs(self.dir, exist_ok=True)
        self.fd = os.open(os.path.join(WORK, "lane%d.lock" % i), os.O_WRONLY | os.O_CREAT, 0o644)

    def __enter__(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        time.sleep(0.3)  # let another driver waiting on this lane get in
        return False


def run_meas(cmd, cwd, stdout_file=None, hash_stdout=False):
    argv = [sys.executable, "-I", MEAS]
    if stdout_file:
        argv += ["--stdout", stdout_file]
    if hash_stdout:
        argv += ["--sha256-stdout"]
    argv += ["--"] + cmd
    p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError("meas failed: %r %r" % (cmd, p.stderr[-500:]))
    return json.loads(p.stdout.decode().strip().splitlines()[-1])


def compress_one(lane, be, sha_in, n_in):
    """lane.dir/in.bin must already hold the input.  Returns the log record."""
    b = BACKENDS[be]
    out = os.path.join(lane.dir, b["out"])
    if os.path.exists(out):
        os.remove(out)
    rc = run_meas(b["c"], lane.dir, stdout_file=b["out"] if b["to_stdout"] else None)
    if rc["rc"] != 0:
        raise RuntimeError("compress failed %s: %s" % (be, rc))
    size = os.path.getsize(out)
    rd = run_meas(b["d"], lane.dir, hash_stdout=True)
    ok = (rd["rc"] == 0 and rd["sha256"] == sha_in and rd["out_bytes"] == n_in)
    os.remove(out)
    rec = {
        "sha256_in": sha_in, "n_in": n_in, "backend": be, "cmd": cmd_str(be),
        "decode_cmd": " ".join(b["d"]) + " | sha256",
        "size": size, "cpu_c": rc["cpu"], "maxrss_c_kb": rc["maxrss_kb"],
        "cpu_d": rd["cpu"], "maxrss_d_kb": rd["maxrss_kb"],
        "sha256_decoded": rd["sha256"], "roundtrip_ok": ok, "ts": time.time(),
    }
    append_jsonl(CLOG, rec)
    if not ok:
        raise RuntimeError("ROUND TRIP FAILED %s %s" % (be, sha_in))
    return rec


def sizes_for(lane, data, backends):
    """Compress bytes `data` with each back-end (cache by content hash).
    Must be called while holding the lane.  Returns {backend: record}."""
    sha_in = sha256(data)
    cache = load_cache()
    need = [be for be in backends if (sha_in, be) not in cache]
    res = {be: cache[(sha_in, be)] for be in backends if (sha_in, be) in cache}
    if need:
        inp = os.path.join(lane.dir, "in.bin")
        with open(inp, "wb") as f:
            f.write(data)
        for be in need:
            res[be] = compress_one(lane, be, sha_in, len(data))
        os.remove(inp)
    return res


def slim(rec):
    """Compact view of a compression record for per-experiment result rows."""
    return {"size": rec["size"], "cpu_c": rec["cpu_c"], "cpu_d": rec["cpu_d"],
            "maxrss_c_kb": rec["maxrss_c_kb"], "roundtrip_ok": rec["roundtrip_ok"]}
