#!/usr/bin/env python3
# q1_analyze.py N PREFIX REP_FAST_STDOUT_JSON OUT_JSON
# Turns the F6/F3 arrays written by rep_fast into the per-bit-length tables, verifies every saver record
# with exact Python big integers, and extracts the biggest savers.
import sys, json
import numpy as np

N = int(sys.argv[1])
prefix = sys.argv[2]
runinfo = json.load(open(sys.argv[3]))
outp = sys.argv[4]
K = runinfo["K"]
LIM = 1 << N
assert runinfo["N"] == N and K == N - 1
f6 = np.fromfile(prefix + ".f6.u8", dtype=np.uint8)
f3 = np.fromfile(prefix + ".f3.u8", dtype=np.uint8)
assert len(f6) == LIM and len(f3) == LIM
dt6 = np.dtype(
    [
        ("d", "<u8"),
        ("c1", "<u4"),
        ("b1", "<u4"),
        ("r1", "<u4"),
        ("c2", "<u4"),
        ("b2", "<u4"),
        ("r2", "<u4"),
        ("cost", "<u4"),
    ]
)
dt3 = np.dtype(
    [("d", "<u8"), ("c", "<u4"), ("b", "<u4"), ("r", "<u4"), ("cost", "<u4")]
)
rec6 = np.fromfile(prefix + ".rec6.bin", dtype=dt6)
rec3 = np.fromfile(prefix + ".rec3.bin", dtype=dt3)


def R(c, b, r):
    return c * (b**r - 1) // (b - 1)


def bl(x):
    return int(x).bit_length()


# ---- exact verification of every record (soundness of the fast search) ----
CH = 100000
bad6 = 0
for i in range(0, len(rec6), CH):
    for d, c1, b1, r1, c2, b2, r2, cost in rec6[i : i + CH].tolist():
        ok = (
            b1 >= 2
            and b2 >= 2
            and 1 <= c1 < b1
            and 1 <= c2 < b2
            and r1 >= 1
            and r2 >= 1
            and R(c1, b1, r1) == d * R(c2, b2, r2)
            and cost == bl(c1) + bl(b1) + bl(r1) + bl(c2) + bl(b2) + bl(r2)
        )
        if not ok:
            bad6 += 1


def last_index(
    dcol,
):  # records for one d are appended in strictly decreasing cost order: the last one is the best
    n = len(dcol)
    u, first_in_rev = np.unique(dcol[::-1], return_index=True)
    return u, (n - 1 - first_in_rev)


u6, li6 = last_index(rec6["d"])
bad6_final = int((rec6["cost"][li6] != f6[u6]).sum())
bad3 = 0
for i in range(0, len(rec3), CH):
    for d, c, b, r, cost in rec3[i : i + CH].tolist():
        ok = (
            b >= 2
            and 1 <= c < b
            and r >= 1
            and R(c, b, r) == d
            and cost == bl(c) + bl(b) + bl(r)
        )
        if not ok:
            bad3 += 1
u3, li3 = last_index(rec3["d"])
bad3_final = int((rec3["cost"][li3] != f3[u3]).sum())


def get6(d):
    j = np.searchsorted(u6, d)
    return rec6[li6[j]].tolist() if j < len(u6) and u6[j] == d else None


def get3(d):
    j = np.searchsorted(u3, d)
    return rec3[li3[j]].tolist() if j < len(u3) and u3[j] == d else None


# ---- per-class counts (chunked to keep memory small) ----
models = ["free", "gamma", "best_case"]
per_L = []
tot = {m: {"lt_L": 0, "le_L_minus_8": 0, "le_L_minus_16": 0} for m in models}
hist_free_saving = {}
cand = []
candc = []
n_den1_savers = 0
n_free_savers = 0
f6hist = np.zeros(256, dtype=np.int64)
CHUNK = 1 << 22
for L in range(1, N + 1):
    lo, hi = 1 << (L - 1), 1 << L
    row = {"L": L, "count_d": hi - lo}
    for m in models:
        row[m] = {"lt_L": 0, "le_L_minus_8": 0, "le_L_minus_16": 0}
    for clo in range(lo, hi, CHUNK):
        chi = min(hi, clo + CHUNK)
        a = f6[clo:chi].astype(np.int16)
        t3 = f3[clo:chi].astype(np.int16)
        cost = {
            "free": a,
            "gamma": 2 * a - 6,
            "best_case": 1 + np.minimum(a, t3),
        }  # a == 255 means "> K" (censored); never < L
        for m in models:
            c = cost[m]
            row[m]["lt_L"] += int((c < L).sum())
            row[m]["le_L_minus_8"] += int((c <= L - 8).sum())
            row[m]["le_L_minus_16"] += int((c <= L - 16).sum())
        h = np.bincount(f6[clo:chi], minlength=256)
        f6hist += h
        for vv in np.nonzero(h)[0].tolist():
            if vv <= K:
                hist_free_saving[L - vv] = hist_free_saving.get(L - vv, 0) + int(h[vv])
        sav = L - a
        idx = np.nonzero(sav > 0)[0]
        n_free_savers += len(idx)
        n_den1_savers += int((t3[idx] + 4 == a[idx]).sum())
        if len(idx):
            o = idx[np.argsort(-sav[idx], kind="stable")[:20]]
            cand += [(int(sav[i]), clo + int(i)) for i in o]
        savc = L - cost["best_case"]
        idx = np.nonzero(savc > 0)[0]
        if len(idx):
            o = idx[np.argsort(-savc[idx], kind="stable")[:20]]
            candc += [(int(savc[i]), clo + int(i)) for i in o]
    for m in models:
        for k in row[m]:
            tot[m][k] += row[m][k]
    per_L.append(row)
cand.sort(key=lambda x: (-x[0], x[1]))
candc.sort(key=lambda x: (-x[0], x[1]))


def describe(d):
    L = bl(d)
    F6 = int(f6[d])
    F3 = int(f3[d])
    e = {
        "d": d,
        "hex": hex(d),
        "L": L,
        "free_cost": F6 if F6 <= K else None,
        "gamma_cost": 2 * F6 - 6 if F6 <= K else None,
        "triple_only_free_cost_F3": F3,
        "best_case_cost": 1 + min(F3, F6),
    }
    t = get6(d)
    if t is not None:
        e["tuple6"] = {
            "c1": t[1],
            "b1": t[2],
            "r1": t[3],
            "c2": t[4],
            "b2": t[5],
            "r2": t[6],
        }
    t = get3(d)
    if t is not None:
        e["triple"] = {"c": t[1], "b": t[2], "r": t[3]}
    e["saving_free"] = L - F6 if F6 <= K else None
    e["saving_gamma"] = L - (2 * F6 - 6) if F6 <= K else None
    e["saving_best_case"] = L - (1 + min(F3, F6))
    return e


raw = {int(k): v for k, v in runinfo["triples_raw_by_cost_no_r1_dedupe"].items()}
tuples_raw = sum(raw[s1] * raw[s2] for s1 in raw for s2 in raw if s1 + s2 <= K)
# gamma is a prefix code over tuples; distinct d need distinct tuples, so the number of d with gamma cost <= m is <= 2^m
# and the Kraft sum over distinct d is <= 1.  (index 0 of the arrays is unused and holds 255.)
g_le = {}
cum = 0
prefix_ok = True
kraft_gamma = 0.0
for F in range(0, K + 1):
    if f6hist[F]:
        g = 2 * F - 6
        cum += int(f6hist[F])
        g_le[g] = cum
        kraft_gamma += int(f6hist[F]) * 2.0 ** (-g)
        if cum > 2**g:
            prefix_ok = False
res = {
    "N": N,
    "K_cost_cap_free_bits": K,
    "d_range": [1, LIM - 1],
    "records_checked_exact": {
        "rec6": int(len(rec6)),
        "rec6_bad": bad6,
        "rec6_final_cost_mismatch_vs_F6": bad6_final,
        "rec3": int(len(rec3)),
        "rec3_bad": bad3,
        "rec3_final_cost_mismatch_vs_F3": bad3_final,
    },
    "six_tuples_with_free_cost_le_K_raw_count": tuples_raw,
    "integer_quotients_in_range_after_r1_dedupe": runinfo["integer_quotients_in_range"],
    "distinct_d_with_any_tuple_cost_le_K": runinfo["distinct_d_with_tuple_cost_le_K"],
    "per_L": per_L,
    "overall": {"count_d": LIM - 1, **tot},
    "free_savers_total": n_free_savers,
    "free_savers_whose_best_tuple_cost_equals_F3_plus_4_ie_denominator_1_suffices": n_den1_savers,
    "hist_L_minus_free_cost_for_d_with_cost_le_K": {
        str(k): hist_free_saving[k] for k in sorted(hist_free_saving)
    },
    "gamma_kraft_sum_over_distinct_d": kraft_gamma,
    "gamma_count_le_m_never_exceeds_2pow_m": prefix_ok,
    "gamma_cum_count_by_cost": {str(k): v for k, v in g_le.items()},
    "free_cost_histogram_for_cost_le_K": {
        str(F): int(f6hist[F]) for F in range(K + 1) if f6hist[F]
    },
    "top20_free": [describe(d) for _, d in cand[:20]],
    "top20_best_case": [describe(d) for _, d in candc[:20]],
}
json.dump(res, open(outp, "w"), indent=1)
print(
    json.dumps(
        {
            k: res[k]
            for k in [
                "N",
                "records_checked_exact",
                "six_tuples_with_free_cost_le_K_raw_count",
                "integer_quotients_in_range_after_r1_dedupe",
                "distinct_d_with_any_tuple_cost_le_K",
                "overall",
                "free_savers_total",
                "free_savers_whose_best_tuple_cost_equals_F3_plus_4_ie_denominator_1_suffices",
                "gamma_kraft_sum_over_distinct_d",
                "gamma_count_le_m_never_exceeds_2pow_m",
            ]
        },
        indent=1,
    )
)
for e in res["top20_free"][:20]:
    print(
        e["d"],
        e["hex"],
        e["L"],
        e["free_cost"],
        e["gamma_cost"],
        e["best_case_cost"],
        e.get("tuple6"),
        e.get("triple"),
    )
