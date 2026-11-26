#!/usr/bin/env python3
# naive_check.py N K F6_FILE F3_FILE OUT_JSON [f3mode]
# Independent brute force with Python big integers.  NO logarithm/magnitude filter, NO r=1 dedupe:
# every triple (c,b,r), b>=2, 1<=c<b, r>=1 with bl(c)+bl(b)+bl(r) <= K-4 is built exactly, and every ordered pair of
# triples with total cost <= K is tested with exact big-int division.  Result is compared byte for byte with the
# F6 array written by rep_fast (255 = no tuple of cost <= K).
# f3mode = "full": F3 fully naive (all b up to 2^N, all c<b, all r, including r=1 with every b>c).
# f3mode = "r1closed": as above but r=1 handled as cost bl(c)+bl(c+1)+1 (the b=c+1 choice), r>=2 fully naive.
import sys, json, time

N, K = int(sys.argv[1]), int(sys.argv[2])
f6file, f3file, outp = sys.argv[3], sys.argv[4], sys.argv[5]
f3mode = sys.argv[6] if len(sys.argv) > 6 else "full"
LIM = 1 << N
S = K - 4
t0 = time.time()
by_cost = {s: [] for s in range(4, S + 1)}
ntrip = 0
for lb in range(2, S - 1):
    for b in range(1 << (lb - 1), 1 << lb):
        for c in range(1, b):
            lc = c.bit_length()
            if lc + lb + 1 > S:
                break
            rmax = (1 << (S - lc - lb)) - 1
            rep = 0
            for r in range(1, rmax + 1):
                rep = rep * b + 1  # 1 + b + ... + b^(r-1)
                by_cost[lc + lb + r.bit_length()].append(c * rep)
                ntrip += 1
F6 = bytearray([255]) * LIM
npairs = 0
nhit = 0
for s1 in range(4, S + 1):
    A = by_cost[s1]
    for s2 in range(4, K - s1 + 1):
        B = by_cost[s2]
        s = s1 + s2
        npairs += len(A) * len(B)
        for v1 in A:
            for v2 in B:
                if v1 % v2 == 0:
                    d = v1 // v2
                    if d < LIM:
                        nhit += 1
                        if s < F6[d]:
                            F6[d] = s
ref6 = open(f6file, "rb").read()
assert len(ref6) == LIM
# index 0 is unused (d >= 1); both must agree on 1..LIM-1
mism6 = sum(1 for d in range(1, LIM) if F6[d] != ref6[d])
# ---- F3 ----
F3 = [10**9] * LIM
if f3mode == "full":
    for b in range(2, LIM + 1):
        lb = b.bit_length()
        for c in range(1, min(b, LIM)):
            cost = c.bit_length() + lb + 1
            if cost < F3[c]:
                F3[c] = cost
else:
    for c in range(1, LIM):
        F3[c] = c.bit_length() + (c + 1).bit_length() + 1
for b in range(2, LIM):
    lb = b.bit_length()
    rep = 1
    r = 1
    while True:
        r += 1
        rep = rep * b + 1
        if rep >= LIM:
            break
        lr = r.bit_length()
        for c in range(1, b):
            v = c * rep
            if v >= LIM:
                break
            cost = c.bit_length() + lb + lr
            if cost < F3[v]:
                F3[v] = cost
ref3 = open(f3file, "rb").read()
mism3 = sum(1 for d in range(1, LIM) if F3[d] != ref3[d])
res = {
    "N": N,
    "K": K,
    "f3mode": f3mode,
    "naive_triples": ntrip,
    "naive_pairs_tested": npairs,
    "naive_integer_quotients_in_range": nhit,
    "naive_distinct_d_cost_le_K": sum(1 for d in range(1, LIM) if F6[d] != 255),
    "F6_mismatches": mism6,
    "F3_mismatches": mism3,
    "d_compared": LIM - 1,
    "seconds": time.time() - t0,
}
json.dump(res, open(outp, "w"))
print(json.dumps(res))
