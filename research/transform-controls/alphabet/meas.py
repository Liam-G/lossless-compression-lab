#!/usr/bin/env python3
"""meas.py - run exactly ONE child process and report its CPU time and peak RSS.

Usage:
  python3 -I meas.py [--stdin FILE] [--stdout FILE | --sha256-stdout] -- cmd args...

Prints one JSON line on stdout:
  {"rc":..,"utime":..,"stime":..,"cpu":..,"maxrss_kb":..,"out_bytes":..,"sha256":..}

CPU time and peak memory come from resource.getrusage(RUSAGE_CHILDREN) deltas
around the single child this process runs (one child per measuring process, so
ru_maxrss is that child's own high-water mark).  With --sha256-stdout the child's
stdout is hashed inside this process (its CPU is RUSAGE_SELF, not charged to the
child) and nothing is written to disk.
"""
import sys, json, hashlib, resource, subprocess


def main():
    a = sys.argv[1:]
    stdin_path = None
    stdout_path = None
    hash_out = False
    while a and a[0] != "--":
        if a[0] == "--stdin":
            stdin_path = a[1]; a = a[2:]
        elif a[0] == "--stdout":
            stdout_path = a[1]; a = a[2:]
        elif a[0] == "--sha256-stdout":
            hash_out = True; a = a[1:]
        else:
            raise SystemExit("bad arg " + a[0])
    cmd = a[1:]
    if not cmd:
        raise SystemExit("no command")
    fin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    out_bytes = None
    digest = None
    if hash_out:
        h = hashlib.sha256()
        n = 0
        p = subprocess.Popen(cmd, stdin=fin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # stderr is small for the tools used here; read stdout fully first
        while True:
            b = p.stdout.read(1 << 20)
            if not b:
                break
            h.update(b)
            n += len(b)
        err = p.stderr.read()
        rc = p.wait()
        out_bytes = n
        digest = h.hexdigest()
    else:
        fout = open(stdout_path, "wb") if stdout_path else subprocess.PIPE
        p = subprocess.run(cmd, stdin=fin, stdout=fout, stderr=subprocess.PIPE)
        rc = p.returncode
        err = p.stderr
        if stdout_path:
            fout.close()
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    ut = r1.ru_utime - r0.ru_utime
    st = r1.ru_stime - r0.ru_stime
    res = {
        "rc": rc,
        "utime": ut,
        "stime": st,
        "cpu": ut + st,
        "maxrss_kb": r1.ru_maxrss,
        "out_bytes": out_bytes,
        "sha256": digest,
        "stderr_tail": err.decode("utf-8", "replace")[-400:] if rc != 0 else "",
    }
    sys.stdout.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
