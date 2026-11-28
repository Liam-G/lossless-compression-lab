"""Exhaustive check of the whiteboard idea.

d = R(c1,b1,r1) / R(c2,b2,r2),  R(c,b,r) = c*(b^r-1)/(b-1)  (digit c repeated r times in base b)

For every d < 2^N find the cheapest 6-tuple whose quotient is exactly d, under two cost models:
  free  : sum of bitlen of the six numbers (NOT decodable: no separators; deliberately generous)
  gamma : sum of Elias-gamma lengths 2*bitlen-1 (a real, parseable code)
and compare with bitlen(d), the cost of writing d itself.

Completeness: a tuple of total cost < N must have each triple cost <= N-1-min_triple_cost, so we
enumerate every triple up to that bound, keep the cheapest triple per distinct value R, then test
every ordered pair (R1, R2) with R1/R2 < 2^N for exact divisibility.
"""
import sys, math, json, bisect
from collections import defaultdict

def bl(x): return x.bit_length()

def costs(model):
    if model == 'free':
        return (lambda x: bl(x))
    return (lambda x: 2 * bl(x) - 1)

def enum_triples(max_cost, cost):
    """All (c,b,r), 1<=c<b, r>=1, with cost(c)+cost(b)+cost(r) <= max_cost.
    Returns dict R -> (min cost, triple)."""
    best = {}
    # enumerate by bit-lengths to stay complete and bounded
    for lb in range(2, 64):
        cb_min = cost(1 << (lb - 1))
        if cb_min + cost(1) + cost(1) > max_cost: break
        for lc in range(1, lb + 1):
            cc = cost(1 << (lc - 1))
            if cb_min + cc + cost(1) > max_cost: break
            for lr in range(1, 64):
                cr = cost(1 << (lr - 1))
                if cb_min + cc + cr > max_cost: break
                for b in range(1 << (lb - 1), 1 << lb):
                    if b < 2: continue
                    for c in range(1 << (lc - 1), min(1 << lc, b)):
                        k = cost(c) + cost(b)
                        for r in range(1 << (lr - 1), 1 << lr):
                            t = k + cost(r)
                            R = c * (b ** r - 1) // (b - 1)
                            old = best.get(R)
                            if old is None or t < old[0]:
                                best[R] = (t, (c, b, r))
    return best

def run(N, model):
    cost = costs(model)
    min_triple = cost(1) + cost(2) + cost(1)          # c=1, b=2, r=1  -> R=1
    max_triple = N - 1 - min_triple                    # total must be < N to beat bitlen(d) <= N
    trip = enum_triples(max_triple, cost)
    vals = sorted(trip)                                # distinct R values
    logs = [math.log2(v) for v in vals]
    bestd = {}                                         # d -> (cost, tuple)
    pairs = 0
    for i, R1 in enumerate(vals):
        c1, t1 = trip[R1]
        lo = bisect.bisect_left(logs, logs[i] - N - 1e-9)
        for j in range(lo, i + 1):
            R2 = vals[j]
            c2, t2 = trip[R2]
            tot = c1 + c2
            if tot >= N: continue
            pairs += 1
            q, rem = divmod(R1, R2)
            if rem or q >= (1 << N): continue
            if tot < bl(q):                            # strictly cheaper than writing d
                old = bestd.get(q)
                if old is None or tot < old[0]:
                    bestd[q] = (tot, t1 + t2)
    by_len = defaultdict(lambda: [0, 0, 0, 0])         # L -> [count d, any saving, >=8 bits, >=16 bits]
    for L in range(1, N + 1):
        by_len[L][0] = 1 << (L - 1)
    for d, (tot, _) in bestd.items():
        L = bl(d); s = L - tot
        by_len[L][1] += 1
        if s >= 8: by_len[L][2] += 1
        if s >= 16: by_len[L][3] += 1
    top = sorted(bestd.items(), key=lambda kv: (bl(kv[0]) - kv[1][0]), reverse=True)[:12]
    return {
        'N': N, 'model': model, 'triples': len(trip), 'pairs_tested': pairs,
        'total_d': (1 << N) - 1,
        'd_with_any_saving': sum(v[1] for v in by_len.values()),
        'd_saving_ge_8_bits': sum(v[2] for v in by_len.values()),
        'd_saving_ge_16_bits': sum(v[3] for v in by_len.values()),
        'by_len': {L: by_len[L] for L in sorted(by_len)},
        'top_savers': [{'d': d, 'bits_d': bl(d), 'cost': c, 'tuple': t} for d, (c, t) in top],
    }

if __name__ == '__main__':
    N = int(sys.argv[1]); model = sys.argv[2]
    res = run(N, model)
    print(json.dumps(res))
