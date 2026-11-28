#!/usr/bin/env python3
"""make_results.py - merge raw/*.jsonl into results.json and print compact tables.
  python3 -I make_results.py
Numbers are copied, never rounded, into results.json; only the printed tables round."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def last_by(rows, keyf):
    d = {}
    for r in rows:
        d[keyf(r)] = r
    return list(d.values())

p1 = last_by(C.read_jsonl(os.path.join(C.RAW, "p1_rows.jsonl")), lambda r: (r["file"], r["k"], r["bitorder"]))
p2 = last_by(C.read_jsonl(os.path.join(C.RAW, "p2_rows.jsonl")), lambda r: r["name"])
p3 = last_by(C.read_jsonl(os.path.join(C.RAW, "p3_rows.jsonl")), lambda r: r["name"])
p4 = last_by(C.read_jsonl(os.path.join(C.RAW, "p4_rows.jsonl")), lambda r: r["name"])
clog = C.read_jsonl(C.CLOG)
FILES = ["ptt5", "dickens", "x-ray", "mr", "sao", "random"]
BE1 = C.B_P1

res = {
    "meta": {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "backend_commands": {be: {"compress": C.cmd_str(be), "decode": " ".join(C.BACKENDS[be]["d"])} for be in C.BACKENDS},
        "accounting": "with = recipe header bytes + compressed size of transformed file; without = compressed size of the file as given; same command line; every codec run decoded and SHA-256 compared; every transform inverted from (header, payload) only and compared.",
        "container_note": "7z sizes include the .7z container (member name in.bin, attributes), identical on both sides; xz/zstd/bzip2 sizes are whole-stream sizes.",
        "part1_samples": "ptt5 whole (513216 B); first 4194304 B of silesia/dickens, x-ray, mr, sao (SHRUNK from whole files for x-ray/mr/sao to fit the time budget); random = numpy.random.default_rng(12345).bytes(4194304)",
        "part1_k_grid": "MSB-first k in {1,2,3,4,5,6,7,8,10,12,14,16,20,24,32} for all six samples; LSB-first k in {4,12,16}; plus whatever of the full 1..32 grid finished for ptt5 (see rows)",
        "n_codec_runs": len(clog), "n_codec_runs_roundtrip_ok": sum(1 for r in clog if r.get("roundtrip_ok")),
        "total_cpu_compress_s": sum(r["cpu_c"] for r in clog), "total_cpu_decompress_s": sum(r["cpu_d"] for r in clog),
        "max_child_rss_kb": max([r["maxrss_c_kb"] for r in clog] + [0]),
    },
    "part1_symbol_width": p1, "part2_hidden_alphabets": p2, "part3_base_change": p3, "part4_relabel": p4,
}
all_ok = (all(v["accepted"] for r in p1 for v in r["backends"].values())
          and all(v["accepted"] for r in p2 + p3 + p4 for v in r["backends"].values()))
res["meta"]["all_rows_accepted"] = all_ok

# ---- derived summaries
summ = {}
base1 = {}
for r in p1:
    if r["k"] == 8 and r["bitorder"] == "msb":
        base1[r["file"]] = {be: r["backends"][be]["size_orig"] for be in BE1}
        base1[r["file"]]["n"] = r["n_orig"]
summ["part1_baseline_sizes"] = base1
best = {}
for f in FILES:
    for be in BE1:
        cand = [(r["backends"][be]["total_with"], r["k"], r["bitorder"]) for r in p1 if r["file"] == f and not r["identity"]]
        if cand:
            m = min(cand)
            best["%s|%s" % (f, be)] = {"best_non_identity_total_with": m[0], "k": m[1], "bitorder": m[2],
                                         "without": base1.get(f, {}).get(be), "delta": m[0] - base1[f][be] if f in base1 else None}
summ["part1_best_non_identity"] = best
res["summary"] = summ
with open(os.path.join(C.HERE, "results.json"), "w") as f:
    json.dump(res, f, indent=1, sort_keys=True)

# ---- printed tables
def pct(a, b):
    return "%+.2f%%" % (100.0 * (a - b) / b)

print("rows: p1=%d p2=%d p3=%d p4=%d  codec runs=%d all_ok=%s  cpu_c=%.0fs cpu_d=%.0fs maxrss=%d kB" % (
    len(p1), len(p2), len(p3), len(p4), len(clog), all_ok, res["meta"]["total_cpu_compress_s"], res["meta"]["total_cpu_decompress_s"], res["meta"]["max_child_rss_kb"]))
print("\nPART 1 baselines:", json.dumps(base1))
for f in FILES:
    rows = sorted([r for r in p1 if r["file"] == f], key=lambda r: (r["bitorder"], r["k"]))
    if not rows:
        continue
    print("\n### %s (n=%d)" % (f, rows[0]["n_orig"]))
    print("| k | order | H/bit | plug-in B | two-part B | distinct | xz9e | zstd22 | ppmd_o8 | ppmd_o16 | best vs orig best |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    ob = min(base1[f][be] for be in BE1) if f in base1 else None
    for r in rows:
        e = r["entropy"]
        b = r["backends"]
        bw = min(b[be]["total_with"] for be in BE1)
        print("| %d | %s | %.4f | %.0f | %.0f | %d | %d | %d | %d | %d | %s |" % (
            r["k"], r["bitorder"], e["H_bits_per_orig_bit"], e["plugin_bytes"], e["twopart_bytes"], e["distinct"],
            b["xz9e"]["total_with"], b["zstd22"]["total_with"], b["ppmd_o8"]["total_with"], b["ppmd_o16"]["total_with"],
            pct(bw, ob) if ob else "?") + (" id" if r["identity"] else ""))
for title, rows in (("PART 2", p2), ("PART 3", p3), ("PART 4", p4)):
    print("\n### %s" % title)
    for r in rows:
        print("%-34s given=%d alt=%d hdr=%d regen=%s" % (r["name"], r["n_given"], r["n_alt"], r["header_len"], r["regenerated_byte_exact"]))
        print("     " + "  ".join("%s %d->%d (%s)" % (be, v["without"], v["with"], pct(v["with"], v["without"])) for be, v in r["backends"].items()))
