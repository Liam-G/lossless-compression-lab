"""Can a big list of simple rules (and combinations of rules) recreate noise?

Program family: elementary cellular automaton (rule 0..255), ring of width w (8..71), single 1 in the middle,
read one column c over time starting at step t0 (0..255). Each program prints a bit stream.
For each target we find the program whose stream reproduces the longest exact prefix of the target,
and compare that with the bits needed just to say which program it is (log2 of the family size).
Pairs: two programs XORed together (the 'combination' of rules), searched by sorting 64-bit prefixes.
Linear rules: Berlekamp-Massey finds the shortest XOR (LFSR) rule over ALL possible tap sets exactly.
"""
import math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python -I drops the script dir
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stride-scan'))
from shapesearch import berlekamp_massey

T0, L, WIDTHS = 256, 64, range(8, 72)
T = T0 + L

def eca_history(w):
    """history[t, rule, cell] for all 256 rules at once, ring of width w, single seed in the middle."""
    S = np.zeros((256, w), np.uint8); S[:, w // 2] = 1
    rules = np.arange(256, dtype=np.uint16)[:, None]
    H = np.empty((T, 256, w), np.uint8)
    for t in range(T):
        H[t] = S
        idx = (np.roll(S, 1, 1) << 2) | (S << 1) | np.roll(S, -1, 1)
        S = ((rules >> idx) & 1).astype(np.uint8)
    return H

def bits_of(path, skip=64, n=8192):
    raw = np.frombuffer(open(path, 'rb').read(), np.uint8)[skip:]
    return np.unpackbits(raw)[:n]

def search(targets):
    best = {k: (0, None) for k in targets}
    pref = []                                               # 64-bit prefixes of the t0 < 4 subfamily, for the pair search
    count = 0
    for w in WIDTHS:
        H = eca_history(w)
        count += 256 * w * T0
        win = np.lib.stride_tricks.sliding_window_view(H, L, axis=0)[:T0]   # [t0, rule, cell, j]
        p = np.packbits(win[:4], axis=-1).reshape(-1, 8)
        pref.append(p.view('>u8').ravel())
        for k, tg in targets.items():
            eq = win == tg[:L].astype(np.uint8)              # [t0, rule, cell, j]
            run = np.where(eq.all(-1), L, np.argmin(eq, -1))  # length of exact prefix match per program
            m = int(run.max())
            if m > best[k][0]:
                t0, r, c = np.unravel_index(int(run.argmax()), run.shape)
                best[k] = (m, f'rule {r}, width {w}, column {c}, start step {t0}')
    return best, count, np.concatenate(pref)

def pair_search(pref, tg):
    """max common prefix of a1 and (target ^ a2) over all pairs: sort both lists together, compare neighbours."""
    t = int(np.packbits(tg[:64].astype(np.uint8)).view('>u8')[0])
    A = np.unique(pref)
    B = A ^ np.uint64(t)
    allv = np.concatenate([A, B]); lab = np.concatenate([np.zeros(len(A), np.int8), np.ones(len(B), np.int8)])
    o = np.argsort(allv, kind='stable'); v = allv[o]; lb = lab[o]
    x = v[1:] ^ v[:-1]; ok = lb[1:] != lb[:-1]
    x = x[ok]
    lcp = np.where(x == 0, 64, 63 - np.floor(np.log2(np.maximum(x, 1).astype(np.float64))).astype(int))
    return int(lcp.max()), len(A)

if __name__ == '__main__':
    t_start = time.time()
    tg = {'xz output of enwik8 text': bits_of(sys.argv[1]), 'PPMd output of enwik8 text': bits_of(sys.argv[2]),
          'seeded random bytes': np.unpackbits(np.random.default_rng(20261128).integers(0, 256, 1024, dtype=np.uint8))}
    H = eca_history(61)
    ctrl = np.concatenate([H[:, 30, 30], np.zeros(0, np.uint8)])          # rule 30 noise, made by a member of the family
    tg['CONTROL: rule 30 noise (made by a rule)'] = ctrl
    best, count, pref = search(tg)
    print(f'single programs tried: {count:,} (= 2^{math.log2(count):.1f})   [{time.time() - t_start:.0f}s]')
    for k, (m, how) in best.items():
        cap = ' (checked up to 64)' if m == L else ''
        print(f'  {k:42} longest exact prefix recreated: {m} bits{cap}   by {how}')
    print()
    for k, v in tg.items():
        m, nA = pair_search(pref, v)
        print(f'  pairs XORed  {k:42} best prefix {m} bits   from {nA:,} distinct programs -> {nA * (nA - 1) // 2:,} pairs (= 2^{math.log2(nA * (nA - 1) / 2):.1f})')
    print()
    for k, v in tg.items():
        n = 8192 if len(v) >= 8192 else len(v)
        Lc, _ = berlekamp_massey(v[:n].astype(np.uint8))
        print(f'  linear rules {k:42} shortest XOR rule recreating {n} bits needs {Lc} taps + {Lc} seed bits = {2 * Lc} bits')
    print(f'[{time.time() - t_start:.0f}s]')
