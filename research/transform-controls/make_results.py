#!/usr/bin/env python3
"""Aggregate the three controls into results.json and print compact tables.

usage: python3 -I make_results.py --dir LAB_CONTROLS_DIR --session-start EPOCH
Reads part1_stats_*.json, part1_selection_*.json, part1_runs.jsonl, part2.json, part3_runs.jsonl.
"""
import argparse, json, math, os, sys

GRID = [(lc, lp, pb) for lc in (0, 3, 4) for lp in (0, 1, 2) for pb in (0, 1, 2) if lc + lp <= 4]
FILES = ["dickens", "mozilla", "mr", "nci", "ooffice", "osdb", "reymont",
         "samba", "sao", "webster", "x-ray", "xml"]


def jsonl(path):
    rows = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def part1(d):
    out = {}
    runs = jsonl(os.path.join(d, "part1_runs.jsonl"))
    for name in ("rand", "dickens_xz"):
        sp = os.path.join(d, "part1_stats_%s.json" % name)
        if not os.path.exists(sp):
            continue
        st = json.load(open(sp))
        sel = json.load(open(os.path.join(d, "part1_selection_%s.json" % name)))
        n = st["n"]
        cands = st["candidates"]
        byidx = {c["idx"]: c for c in cands}
        rr = [r for r in runs if r["target"] == name]
        act = {}
        for r in rr:
            act[(r["idx"], r["backend"])] = r

        def actual(idx):
            return {b: (act[(idx, b)]["size"] if (idx, b) in act else None) for b in ("xz", "zstd")}

        def describe(c, key):
            est = c[key]
            return dict(idx=c["idx"], transform="%s(%d)" % (c["kind"], c["param"]), estimator=key,
                        estimate_bits=est, estimate_bytes=est / 8,
                        promised_saving_bytes=n - est / 8,
                        promised_saving_pct=100 * (1 - est / (8.0 * n)),
                        actual_container_bytes=actual(c["idx"]),
                        actual_minus_raw_bytes={b: (v - n if v is not None else None)
                                                for b, v in actual(c["idx"]).items()})

        res = dict(n=n, sha256=st["sha256"], n_candidates=len(cands))
        best_any = min(cands, key=lambda c: (min(c["h0_bits"], c["h1_bits"]), c["idx"]))
        res["best_by_plugin_estimate"] = describe(
            best_any, "h0_bits" if best_any["h0_bits"] <= best_any["h1_bits"] else "h1_bits")
        res["best_by_plugin_h0"] = describe(min(cands, key=lambda c: (c["h0_bits"], c["idx"])), "h0_bits")
        res["best_by_plugin_h1"] = describe(min(cands, key=lambda c: (c["h1_bits"], c["idx"])), "h1_bits")
        byte_c = [c for c in cands if c["kind"] in ("delta", "shuffle")]
        res["best_bytelevel_by_plugin_h0"] = describe(min(byte_c, key=lambda c: (c["h0_bits"], c["idx"])), "h0_bits")
        res["best_bytelevel_by_plugin_h1"] = describe(min(byte_c, key=lambda c: (c["h1_bits"], c["idx"])), "h1_bits")
        res["best_by_adaptive_kt0"] = describe(min(cands, key=lambda c: (c["kt0_bits"], c["idx"])), "kt0_bits")
        res["best_by_adaptive_kt1"] = describe(min(cands, key=lambda c: (c["kt1_bits"], c["idx"])), "kt1_bits")
        for key in ("h0_bits", "h1_bits", "kt0_bits", "kt1_bits"):
            res["n_candidates_with_%s_below_raw" % key] = sum(1 for c in cands if c[key] < 8 * n)
        # spread of the plug-in order-1 estimate over the 2048 byte-level candidates
        h1s = sorted(c["h1_bits"] for c in byte_c)
        h0s = sorted(c["h0_bits"] for c in byte_c)
        res["bytelevel_h1_promised_saving_bytes_min_median_max"] = [
            n - h1s[-1] / 8, n - h1s[len(h1s) // 2] / 8, n - h1s[0] / 8]
        res["bytelevel_h0_promised_saving_bytes_min_median_max"] = [
            n - h0s[-1] / 8, n - h0s[len(h0s) // 2] / 8, n - h0s[0] / 8]
        res["bits_k_table"] = [dict(k=c["param"], n_sym=c["n_sym"], h0_bytes=c["h0_bits"] / 8,
                                    h1_bytes=c["h1_bits"] / 8, kt0_bytes=c["kt0_bits"] / 8,
                                    kt1_bytes=c["kt1_bits"] / 8, distinct_pairs=c["distinct_pairs"],
                                    actual_container_bytes=actual(c["idx"]))
                               for c in cands if c["kind"] == "bits"]
        plain = {r["backend"]: r["size"] for r in rr if r["idx"] == -1}
        res["plain_backend_bytes_no_transform_no_header"] = plain
        tested = [r for r in rr if r["idx"] >= 0]
        res["n_actual_runs"] = len(tested)
        res["n_candidates_tested"] = len(set(r["idx"] for r in tested))
        res["n_selected"] = len(sel["order"])
        res["all_selected_done"] = all((i, b) in act for i in sel["order"] for b in ("xz", "zstd"))
        res["all_rt_ok"] = all(r["rt_ok"] for r in rr)
        res["header_bytes"] = 2
        res["naming_cost_bits_exact"] = math.log2(len(cands))
        res["naming_cost_bits_charged"] = 16
        if tested:
            for b in ("xz", "zstd"):
                tb = [r for r in tested if r["backend"] == b]
                if tb:
                    m = min(tb, key=lambda r: (r["size"], r["idx"]))
                    res["best_actual_%s" % b] = dict(idx=m["idx"], transform="%s(%d)" % (m["kind"], m["param"]),
                                                     container_bytes=m["size"], minus_raw_bytes=m["size"] - n,
                                                     minus_plain_backend_bytes=m["size"] - plain.get(b, 0) if b in plain else None)
                    w = max(tb, key=lambda r: (r["size"], r["idx"]))
                    res["worst_actual_%s" % b] = dict(idx=w["idx"], transform="%s(%d)" % (w["kind"], w["param"]),
                                                      container_bytes=w["size"], minus_raw_bytes=w["size"] - n)
            m = min(tested, key=lambda r: (r["size"], r["idx"]))
            res["best_actual_overall"] = dict(idx=m["idx"], transform="%s(%d)" % (m["kind"], m["param"]),
                                              backend=m["backend"], container_bytes=m["size"],
                                              minus_raw_bytes=m["size"] - n)
            res["any_candidate_beats_raw"] = any(r["size"] < n for r in tested)
            res["n_runs_beating_raw"] = sum(1 for r in tested if r["size"] < n)
            res["n_runs_beating_plain_backend"] = sum(1 for r in tested if r["backend"] in plain and r["size"] < plain[r["backend"]])
            res["cpu_s_total_backend"] = sum(r.get("cpu_s", 0) for r in rr)
            res["max_backend_rss_kb"] = max(r.get("maxrss_kb", 0) for r in rr)
        out[name] = res
    return out


def part3(d, t0):
    rows = [r for r in jsonl(os.path.join(d, "part3_runs.jsonl")) if r.get("rt_ok") and r["t_end"] >= t0]
    bad = [r for r in jsonl(os.path.join(d, "part3_runs.jsonl")) if not r.get("rt_ok")]
    by = {}
    for r in rows:
        by[(r["file"], r["bcj"], (r["lc"], r["lp"], r["pb"]))] = r
    per = []
    tot = dict(n=0, default=0, best_lclppb=0, best_incl_bcj=0)
    for f in FILES:
        g0 = {g: by[(f, False, g)]["size"] for g in GRID if (f, False, g) in by}
        g1 = {g: by[(f, True, g)]["size"] for g in GRID if (f, True, g) in by}
        if (3, 0, 2) not in g0:
            continue
        n = by[(f, False, (3, 0, 2))]["n"]
        dflt = g0[(3, 0, 2)]
        bg = min(g0, key=lambda g: (g0[g], g))
        rec = dict(file=f, n=n, default_9e=dflt, grid_points_done=len(g0), grid_points_total=len(GRID),
                   best_size=g0[bg], best_opts="lc=%d,lp=%d,pb=%d" % bg, gain_bytes=dflt - g0[bg],
                   gain_pct=100.0 * (dflt - g0[bg]) / dflt,
                   worst_size=max(g0.values()), worst_opts="lc=%d,lp=%d,pb=%d" % max(g0, key=lambda g: (g0[g], g)),
                   missing=["lc=%d,lp=%d,pb=%d" % g for g in GRID if g not in g0])
        best_all = g0[bg]
        if g1:
            bb = min(g1, key=lambda g: (g1[g], g))
            rec.update(x86_grid_points_done=len(g1), x86_default_lclppb=g1.get((3, 0, 2)),
                       x86_best_size=g1[bb], x86_best_opts="x86 + lc=%d,lp=%d,pb=%d" % bb,
                       x86_only_gain_pct=(100.0 * (dflt - g1[(3, 0, 2)]) / dflt) if (3, 0, 2) in g1 else None,
                       x86_best_gain_pct=100.0 * (dflt - g1[bb]) / dflt,
                       x86_missing=["lc=%d,lp=%d,pb=%d" % g for g in GRID if g not in g1])
            best_all = min(best_all, g1[bb])
        rec["best_incl_bcj"] = best_all
        rec["gain_incl_bcj_pct"] = 100.0 * (dflt - best_all) / dflt
        per.append(rec)
        tot["n"] += n
        tot["default"] += dflt
        tot["best_lclppb"] += g0[bg]
        tot["best_incl_bcj"] += best_all
    res = dict(per_file=per, n_ok_runs=len(rows), n_failed_runs=len(bad), files_reported=len(per))
    if per:
        tot["gain_lclppb_bytes"] = tot["default"] - tot["best_lclppb"]
        tot["gain_lclppb_pct"] = 100.0 * tot["gain_lclppb_bytes"] / tot["default"]
        tot["gain_incl_bcj_bytes"] = tot["default"] - tot["best_incl_bcj"]
        tot["gain_incl_bcj_pct"] = 100.0 * tot["gain_incl_bcj_bytes"] / tot["default"]
        res["total"] = tot
        # single global setting: grid points completed on every file (no BCJ)
        glob = {}
        for g in GRID:
            if all((f, False, g) in by for f in FILES):
                glob["lc=%d,lp=%d,pb=%d" % g] = sum(by[(f, False, g)]["size"] for f in FILES)
        res["corpus_total_per_single_setting_no_bcj"] = glob
        res["cpu_s_total_compress"] = sum(r["cpu_s"] for r in rows)
        res["max_compress_rss_kb"] = max(r["maxrss_kb"] for r in rows)
        res["full_grid_files"] = [p["file"] for p in per if p["grid_points_done"] == len(GRID)
                                  and (p["file"] not in ("mozilla", "ooffice") or p.get("x86_grid_points_done") == len(GRID))]
        res["partial_grid_files"] = [p["file"] for p in per if p["file"] not in res["full_grid_files"]]
    res["grid"] = ["lc=%d,lp=%d,pb=%d" % g for g in GRID]
    res["all_sizes"] = {"%s|%s|lc=%d,lp=%d,pb=%d" % (f, "x86" if b else "nobcj", g[0], g[1], g[2]): r["size"]
                        for (f, b, g), r in sorted(by.items())}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--session-start", type=float, default=0.0)
    a = ap.parse_args()
    d = a.dir
    res = dict(session_start_epoch=a.session_start)
    res["part1"] = part1(d)
    p2 = os.path.join(d, "part2.json")
    if os.path.exists(p2):
        res["part2"] = json.load(open(p2))
    res["part3"] = part3(d, a.session_start)
    with open(os.path.join(d, "results.json.tmp"), "w") as fh:
        json.dump(res, fh, indent=1)
    os.replace(os.path.join(d, "results.json.tmp"), os.path.join(d, "results.json"))

    # compact printout
    for name, r in res["part1"].items():
        print("== part1", name, "n=%d" % r["n"])
        for k in ("best_by_plugin_estimate", "best_by_plugin_h0", "best_bytelevel_by_plugin_h0",
                  "best_bytelevel_by_plugin_h1", "best_by_adaptive_kt0", "best_by_adaptive_kt1"):
            b = r[k]
            print("  %-30s %-13s %-8s est=%.1f B promise=%.1f B (%.4f%%) actual=%s" % (
                k, b["transform"], b["estimator"], b["estimate_bytes"], b["promised_saving_bytes"],
                b["promised_saving_pct"], b["actual_container_bytes"]))
        for k in ("plain_backend_bytes_no_transform_no_header", "best_actual_xz", "best_actual_zstd",
                  "worst_actual_xz", "worst_actual_zstd", "best_actual_overall", "any_candidate_beats_raw",
                  "n_runs_beating_raw", "n_runs_beating_plain_backend", "n_actual_runs", "n_candidates_tested",
                  "n_selected", "all_selected_done", "all_rt_ok",
                  "n_candidates_with_h0_bits_below_raw", "n_candidates_with_h1_bits_below_raw",
                  "n_candidates_with_kt0_bits_below_raw", "n_candidates_with_kt1_bits_below_raw",
                  "bytelevel_h1_promised_saving_bytes_min_median_max",
                  "bytelevel_h0_promised_saving_bytes_min_median_max", "cpu_s_total_backend", "max_backend_rss_kb"):
            print("  ", k, r.get(k))
        for b in r["bits_k_table"]:
            print("   bits k=%2d h0=%.0f h1=%.0f kt0=%.0f kt1=%.0f pairs=%d actual=%s" % (
                b["k"], b["h0_bytes"], b["h1_bytes"], b["kt0_bytes"], b["kt1_bytes"], b["distinct_pairs"],
                b["actual_container_bytes"]))
    p3 = res["part3"]
    print("== part3 ok_runs=%d failed=%d" % (p3["n_ok_runs"], p3["n_failed_runs"]))
    for p in p3["per_file"]:
        print("  %-8s n=%9d def=%9d best=%9d %-16s gain=%.3f%% pts=%d/%d" % (
            p["file"], p["n"], p["default_9e"], p["best_size"], p["best_opts"], p["gain_pct"],
            p["grid_points_done"], p["grid_points_total"])
              + ("  x86: pts=%d dflt=%s best=%d %s (%.3f%%)" % (
                  p["x86_grid_points_done"], p["x86_default_lclppb"], p["x86_best_size"], p["x86_best_opts"],
                  p["x86_best_gain_pct"]) if "x86_best_size" in p else ""))
    for k in ("total", "corpus_total_per_single_setting_no_bcj", "full_grid_files", "partial_grid_files",
              "cpu_s_total_compress", "max_compress_rss_kb"):
        print("  ", k, p3.get(k))


if __name__ == "__main__":
    main()
