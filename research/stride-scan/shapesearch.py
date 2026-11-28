"""Shape search spike: fold the data into shapes, walk them in formula-defined orders, and search for local rules
(contexts) that predict each cell. Score = exact code length of a sequential KT (adaptive) bitwise model, i.e. what
an arithmetic coder driven by that rule would emit. Plus NKS-style exact-program detectors.

usage: python3 -I shapesearch.py OUT.json FILE [FILE ...]   (env CAP=bytes per file, default 4 MiB)
"""
import json, lzma, math, os, sys, time
import numpy as np
from scipy.special import gammaln

LN2, LOGPI = math.log(2), math.log(math.pi)
M1, M2, M3 = np.uint64(0x9E3779B97F4A7C15), np.uint64(0xC2B2AE3D27D4EB4F), np.uint64(0x165667B19E3779F9)
U = np.uint64

# ---------------------------------------------------------------- coder model: sequential KT, bitwise, hashed contexts
def cost_bits(sym, nbits, ctx, tb=22):
    """exact code length (bits) of coding `sym` (nbits each, MSB first) with a KT estimator per (context, bit prefix)."""
    sym = sym.astype(U); c = ctx.astype(U) * M1
    size, sh, tot = 1 << tb, U(64 - tb), 0.0
    for b in range(nbits):
        partial = (sym >> U(nbits - b)) | U(1 << b)
        bit = ((sym >> U(nbits - 1 - b)) & U(1)).astype(np.float64)
        h = (((c ^ (partial * M2)) * M3) >> sh).astype(np.int64)
        n = np.bincount(h, minlength=size).astype(np.float64)
        n1 = np.bincount(h, weights=bit, minlength=size)
        n0 = n - n1; m = n > 0
        tot += float((gammaln(n[m] + 1) + LOGPI - gammaln(n0[m] + .5) - gammaln(n1[m] + .5)).sum()) / LN2
    return tot

def combine(feats):
    c = np.zeros(len(feats[0]) if feats else 0, U) if feats else None
    for f in feats: c = c * U(1000003) + f.astype(U) + U(1)
    return c

# ---------------------------------------------------------------- shapes: geometry (neighbour indices) + traversal order
class Shape:
    """m cells; for each cell: named neighbour index arrays (−1 = none) and coordinates; traversal perm (None = linear)."""
    def __init__(self, name, m, nbrs, coords, perm=None):
        self.name, self.m, self.nbrs, self.coords, self.perm = name, m, nbrs, coords, perm

def grid(dims, trav='raster'):
    m = int(np.prod(dims)); idx = np.arange(m)
    if len(dims) == 1: D, H, W = 1, 1, dims[0]
    elif len(dims) == 2: D, (H, W) = 1, dims
    else: D, H, W = dims
    w = idx % W; h = (idx // W) % H; d = idx // (W * H)
    def off(dd, dh, dw):
        ok = (w + dw >= 0) & (w + dw < W) & (h + dh >= 0) & (h + dh < H) & (d + dd >= 0) & (d + dd < D)
        return np.where(ok, idx + dd * H * W + dh * W + dw, -1)
    nb = {'W': off(0, 0, -1), 'WW': off(0, 0, -2), 'E': off(0, 0, 1), 'S': off(0, 1, 0), 'SW': off(0, 1, -1), 'SE': off(0, 1, 1)}
    if H > 1: nb.update(N=off(0, -1, 0), NW=off(0, -1, -1), NE=off(0, -1, 1), NN=off(0, -2, 0), NWW=off(0, -1, -2), NEE=off(0, -1, 2))
    if D > 1: nb.update(U=off(-1, 0, 0), UN=off(-1, -1, 0), UW=off(-1, 0, -1))
    perm = None
    if trav != 'raster':
        if D > 1: raise ValueError('traversals only for 2-D')
        r, c = h, w
        if trav == 'colmajor': key = c * H + r
        elif trav == 'snake': key = r * W + np.where(r % 2 == 0, c, W - 1 - c)
        elif trav == 'diagonal': key = (r + c).astype(np.int64) * (H + W) + r
        elif trav == 'spiral':
            k = np.minimum(np.minimum(r, c), np.minimum(H - 1 - r, W - 1 - c))
            h2, w2 = H - 2 * k, W - 2 * k; rr, cc = r - k, c - k
            pos = np.where(rr == 0, cc, np.where(cc == w2 - 1, w2 - 1 + rr,
                  np.where(rr == h2 - 1, (w2 - 1) + (h2 - 1) + (w2 - 1 - cc), 2 * (w2 - 1) + (h2 - 1) + (h2 - 1 - rr))))
            key = k.astype(np.int64) * (H * W) + pos
        elif trav == 'morton':
            key = np.zeros(m, np.int64)
            for b in range(16): key |= ((c >> b) & 1) << (2 * b) | ((r >> b) & 1) << (2 * b + 1)
        elif trav == 'hilbert':
            n = 1 << int(math.ceil(math.log2(max(H, W)))); x, y = c.copy(), r.copy(); key = np.zeros(m, np.int64); s = n // 2
            while s > 0:
                rx = (x & s) > 0; ry = (y & s) > 0
                key += s * s * ((3 * rx.astype(np.int64)) ^ ry.astype(np.int64))
                flip = (~ry) & rx
                x = np.where(flip, n - 1 - x, x); y = np.where(flip, n - 1 - y, y)
                sw = ~ry; x, y = np.where(sw, y, x), np.where(sw, x, y)
                s //= 2
        else: raise ValueError(trav)
        perm = np.argsort(key, kind='stable')
    return Shape(f'grid{dims}/{trav}', m, nb, {'x': w, 'y': h, 'z': d}, perm)

def ragged(n_cells, a, b):
    """rows of length L(r) = a + b*r (>=1), left aligned: b=1,a=1 is a triangle; b=0 is a rectangle."""
    lens, tot, r = [], 0, 0
    while tot < n_cells:
        L = max(1, a + b * r); L = min(L, n_cells - tot); lens.append(L); tot += L; r += 1
    lens = np.array(lens); start = np.concatenate([[0], np.cumsum(lens)[:-1]])
    idx = np.arange(n_cells); row = np.searchsorted(start, idx, side='right') - 1; col = idx - start[row]
    prevlen = np.where(row > 0, lens[np.maximum(row - 1, 0)], 0); pstart = start[np.maximum(row - 1, 0)]
    def up(dc):
        cc = col + dc; ok = (row > 0) & (cc >= 0) & (cc < prevlen)
        return np.where(ok, pstart + cc, -1)
    nb = {'W': np.where(col >= 1, idx - 1, -1), 'WW': np.where(col >= 2, idx - 2, -1), 'N': up(0), 'NW': up(-1), 'NE': up(1)}
    return Shape(f'rows L(r)={a}+{b}r', n_cells, nb, {'x': col, 'y': row, 'z': np.zeros(n_cells, np.int64)})

def modperm(m, a):
    """1-D formula permutation: visit position (a*i) mod m."""
    idx = np.arange(m)
    nb = {'W': np.where(idx >= 1, idx - 1, -1), 'E': np.where(idx + 1 < m, idx + 1, -1)}
    perm = (np.arange(m, dtype=np.int64) * a) % m
    return Shape(f'1d i->{a}i mod m', m, nb, {'x': idx, 'y': np.zeros(m, np.int64), 'z': np.zeros(m, np.int64)}, perm)

# ---------------------------------------------------------------- features on a shape
def features(shape, cells, nbits):
    """returns (sequence in traversal order, dict name -> feature array in traversal order, quantisable flag)."""
    m = shape.m; perm = shape.perm if shape.perm is not None else np.arange(m)
    rank = np.empty(m, np.int64); rank[perm] = np.arange(m)
    seq = cells[perm].astype(np.int64)
    vals = {}
    for k, nb in shape.nbrs.items():
        ok = nb >= 0
        ok[ok] &= rank[nb[ok]] < rank[np.nonzero(ok)[0]]          # only cells already decoded
        if not ok.any(): continue
        vals[k] = np.where(ok, cells[np.where(ok, nb, 0)].astype(np.int64), -1)[perm]
    t1 = np.concatenate([[-1], seq[:-1]]); t2 = np.concatenate([[-1, -1], seq[:-2]])
    vals['T1'], vals['T2'] = t1, t2
    co = {k: v[perm] for k, v in shape.coords.items()}
    return seq, vals, co

def med(W, N, NW):
    mx, mn = np.maximum(W, N), np.minimum(W, N)
    return np.where(NW >= mx, mn, np.where(NW <= mn, mx, W + N - NW))

def search_shape(shape, cells, nbits, sample, max_feats=4, log=None):
    """greedy rule search on the first `sample` cells (in traversal order); returns best config + bits on the sample."""
    seq, vals, co = features(shape, cells, nbits)
    S = min(sample, len(seq)); seq_s = seq[:S]; v = {k: a[:S] for k, a in vals.items()}; c = {k: a[:S] for k, a in co.items()}
    mask = (1 << nbits) - 1
    # prediction transforms (only for multi-bit cells)
    preds = {'none': None}
    if nbits > 1:
        z = lambda a: np.maximum(a, 0)
        for k in ('T1', 'W', 'N'):
            if k in v: preds[k] = z(v[k])
        if all(k in v for k in ('W', 'N', 'NW')): preds['MED'] = med(z(v['W']), z(v['N']), z(v['NW']))
    def residual(p):
        if p is None: return seq_s
        r = (seq_s - p) & mask
        return np.where(r & (1 << (nbits - 1)), 2 * (mask + 1 - r) - 1, 2 * r) & mask      # zigzag
    # candidate context features
    cand = {}
    for k, a in v.items():
        if nbits == 1: cand[k] = a + 1
        else:
            for q in (0, 3, 6) if nbits == 8 else (8, 11):
                cand[f'{k}>>{q}'] = np.where(a < 0, -1, a >> q) + 1
    if nbits > 1 and all(k in v for k in ('W', 'N', 'NW')):
        g = np.abs(np.maximum(v['W'], 0) - np.maximum(v['NW'], 0)) + np.abs(np.maximum(v['N'], 0) - np.maximum(v['NW'], 0))
        cand['act'] = np.floor(np.log2(g + 1)).astype(np.int64)
    x, y = c['x'], c['y']
    formulas = {'x': x, 'y': y, 'x^y': x ^ y, 'x+y': x + y, 'x-y': x - y, 'x*y>>3': (x * y) >> 3, '(x2+y2)>>6': (x * x + y * y) >> 6}
    if shape.name.startswith('grid') or shape.name.startswith('rows'):
        for k, f in formulas.items():
            cand['f:' + k] = (f & mask) if nbits > 1 else (f & 1)
    def greedy(sym, chosen, cur, limit):
        chosen = list(chosen)
        while len(chosen) < limit:
            trial = None
            for k, a in cand.items():
                if k in chosen: continue
                b = cost_bits(sym, nbits, combine([cand[j] for j in chosen] + [a]), tb=18)
                if trial is None or b < trial[0]: trial = (b, k)
            if trial is None or trial[0] > cur * 0.995: break
            cur = trial[0]; chosen.append(trial[1])
        return chosen, cur
    best = None
    for pname, p in preds.items():                     # every predictor gets a short search ...
        sym = residual(p)
        chosen, cur = greedy(sym, [], cost_bits(sym, nbits, np.zeros(S, U), tb=18), 2)
        if best is None or cur < best['bits']: best = {'pred': pname, 'feats': chosen, 'bits': cur}
    sym = residual(preds[best['pred']])                # ... the winner gets the full one
    chosen, cur = greedy(sym, best['feats'], best['bits'], max_feats)
    best = {'pred': best['pred'], 'feats': chosen, 'bits': cur}
    return best

def full_bits(shape, cells, nbits, cfg):
    seq, vals, co = features(shape, cells, nbits); mask = (1 << nbits) - 1
    z = lambda a: np.maximum(a, 0)
    p = {'none': None, 'T1': z(vals['T1']), 'W': z(vals.get('W', vals['T1'])), 'N': z(vals.get('N', vals['T1']))}.get(cfg['pred'])
    if cfg['pred'] == 'MED': p = med(z(vals['W']), z(vals['N']), z(vals['NW']))
    sym = seq if p is None else (lambda r: np.where(r & (1 << (nbits - 1)), 2 * (mask + 1 - r) - 1, 2 * r) & mask)((seq - p) & mask)
    feats = []
    x, y = co['x'], co['y']
    formulas = {'x': x, 'y': y, 'x^y': x ^ y, 'x+y': x + y, 'x-y': x - y, 'x*y>>3': (x * y) >> 3, '(x2+y2)>>6': (x * x + y * y) >> 6}
    for f in cfg['feats']:
        if f == 'act':
            g = np.abs(z(vals['W']) - z(vals['NW'])) + np.abs(z(vals['N']) - z(vals['NW'])); feats.append(np.floor(np.log2(g + 1)).astype(np.int64))
        elif f.startswith('f:'): fv = formulas[f[2:]]; feats.append((fv & mask) if nbits > 1 else (fv & 1))
        elif '>>' in f:
            k, q = f.split('>>'); a = vals[k]; feats.append(np.where(a < 0, -1, a >> int(q)) + 1)
        else: feats.append(vals[f] + 1)
    ctx = combine(feats) if feats else np.zeros(len(sym), U)
    bits = cost_bits(sym, nbits, ctx)
    # NKS view: how deterministic is the found rule?  fraction of cells equal to their context's majority symbol
    det = None
    if nbits == 1 and feats:
        key = np.unique(ctx, return_inverse=True)[1]
        n1 = np.bincount(key, weights=sym); n = np.bincount(key)
        det = float(np.maximum(n1, n - n1).sum() / len(sym))
    return bits, det

# ---------------------------------------------------------------- shape candidates
def stride_widths(a, maxw, k, quant):
    """top-k widths w minimising H(a[i] | a[i-w]) (quantised values), on a sample."""
    a = (a[: 1 << 20] >> quant).astype(np.int64); K = int(a.max()) + 1
    res = []
    for w in range(1, min(maxw, len(a) // 4)):
        if K == 2 and w > 2:   # bits: condition on the 3-cell neighbourhood above (what a cellular automaton reads)
            L = len(a) - w - 1
            ctx = a[0:L] << 2 | a[1:L + 1] << 1 | a[2:L + 2]; tgt = a[w + 1:w + 1 + L]
            j = np.bincount(ctx * 2 + tgt, minlength=16).astype(np.float64).reshape(8, 2)
            n = j.sum(); pb = j.sum(1)
            hj = -(j[j > 0] / n * np.log2(j[j > 0] / n)).sum(); hb = -(pb[pb > 0] / n * np.log2(pb[pb > 0] / n)).sum()
            res.append((hj - hb, w)); continue
        j = np.bincount(a[:-w] * K + a[w:], minlength=K * K).astype(np.float64).reshape(K, K)
        n = j.sum(); pb = j.sum(1)
        hj = -(j[j > 0] / n * np.log2(j[j > 0] / n)).sum(); hb = -(pb[pb > 0] / n * np.log2(pb[pb > 0] / n)).sum()
        res.append((hj - hb, w))
    res.sort(); out = []
    for h, w in res:
        if all(w % o and o % w for o in out) or not out: out.append(w)
        if len(out) == k: break
    return out

def candidates(cells, nbits, extra_widths=()):
    m = len(cells); shapes = [grid((m,))]
    q = 0 if nbits <= 8 else 8
    widths = stride_widths(cells, 4097 if nbits == 1 else 2049, 3, q) if m > 64 else []
    widths = [w for w in widths if w > 1 and m // w >= 4]
    widths += [w for w in extra_widths if w not in widths and w > 1 and m // w >= 4]
    for W in widths:
        H = m // W; shapes.append(grid((H, W)))
    if widths and nbits != 1:
        W = widths[0]; H = m // W
        for t in ('colmajor', 'snake', 'diagonal', 'spiral', 'morton', 'hilbert'): shapes.append(grid((H, W), t))
        rows = cells[: H * W].reshape(H, W)
        # 3-D: depth period over rows (H(row_i | row_{i-h}) proxy using one column sample)
        for h2 in stride_widths(rows[:, W // 2].copy(), 600, 2, q) if H > 64 else []:
            if h2 > 1 and H // h2 >= 4: shapes.append(grid((H // h2, h2, W)))
        shapes.append(ragged(m, W, 1)); shapes.append(ragged(m, W, -1 if W > 64 else 1))
    shapes.append(ragged(m, 1, 1))                         # the triangle
    if nbits == 1: return shapes
    shapes.append(ragged(m, 1, 2))
    for a in (int(m * 0.6180339887) | 1, 7919):
        if math.gcd(a, m) == 1: shapes.append(modperm(m, a))
    return shapes

# ---------------------------------------------------------------- NKS exact-program detectors
def berlekamp_massey(s):
    n = len(s); C = np.zeros(n + 1, np.uint8); B = np.zeros(n + 1, np.uint8); C[0] = B[0] = 1
    L, mm = 0, 1
    for i in range(n):
        d = int(s[i]) ^ (int(np.dot(C[1:L + 1], s[i - L:i][::-1]) & 1) if L else 0)
        if d == 0: mm += 1
        elif 2 * L <= i:
            T = C.copy(); C[mm:] ^= B[: n + 1 - mm]; L, B, mm = i + 1 - L, T, 1
        else: C[mm:] ^= B[: n + 1 - mm]; mm += 1
    return L, C[: L + 1]

FORMULAS = {
    'x': lambda x, y: x, 'y': lambda x, y: y, 'x+y': lambda x, y: x + y, 'x-y': lambda x, y: x - y, 'x^y': lambda x, y: x ^ y,
    'x&y': lambda x, y: x & y, 'x|y': lambda x, y: x | y, 'x*y': lambda x, y: x * y, '(x*y)>>3': lambda x, y: (x * y) >> 3,
    '(x*x+y*y)>>6': lambda x, y: (x * x + y * y) >> 6, '(x*x+y*y)>>4': lambda x, y: (x * x + y * y) >> 4,
    'x*x+y*y': lambda x, y: x * x + y * y, '(x+y)>>1': lambda x, y: (x + y) >> 1, 'x*y>>8': lambda x, y: (x * y) >> 8,
}

def formula_cost(raw, extra_widths=()):
    """exact 'simple program' search: data[r*W+c] == f(c, r) & 255 for some width W and formula f; exceptions charged."""
    n = len(raw); best = None
    widths = sorted(set([1 << k for k in range(3, 14)] + [int(round(math.sqrt(n)))] + list(extra_widths)))
    for W in widths:
        H = n // W
        if H < 2: continue
        y, x = np.mgrid[0:H, 0:W]; d = raw[:H * W].reshape(H, W).astype(np.int64)
        for name, f in FORMULAS.items():
            v = f(x, y) & 255
            exc = int((v != d).sum())
            if best is None or exc < best[0]: best = (exc, W, name)
    exc, W, name = best
    tail = n - (n // W) * W
    cost_bits = 64 + exc * (math.log2(n) + 8) + tail * 8
    return {'formula': name, 'width': W, 'exceptions': exc, 'bytes': math.ceil(cost_bits / 8) + 16}

def lfsr_cost(bits):
    L, C = berlekamp_massey(bits[:8192])
    if L > 256: return {'linear_complexity_8192': int(L), 'bytes': None}
    taps = [j for j in range(1, L + 1) if C[j]]
    pred = np.zeros(len(bits) - L, np.uint8)
    for j in taps: pred ^= bits[L - j: len(bits) - j]
    exc = int((pred != bits[L:]).sum())
    cost = 2 * L + exc * math.log2(len(bits)) + 64
    return {'linear_complexity_8192': int(L), 'taps': taps, 'exceptions': exc, 'bytes': math.ceil(cost / 8) + 16}

# ---------------------------------------------------------------- driver
def run_file(path, cap, log):
    raw = np.fromfile(path, np.uint8)[:cap]; n = len(raw)
    xz = len(lzma.compress(raw.tobytes(), preset=9 | lzma.PRESET_EXTREME))
    res = {'file': os.path.basename(path), 'bytes': n, 'xz': xz, 'runs': []}
    bits = np.unpackbits(raw)
    res['lfsr'] = lfsr_cost(bits)
    res['formula'] = formula_cost(raw)
    log(f"   formula search: best {res['formula']}")
    log(f"== {res['file']}  {n} B  xz={xz}  BM linear complexity(8192 bits)={res['lfsr']['linear_complexity_8192']}"
        + (f"  LFSR cost={res['lfsr']['bytes']} B" if res['lfsr'].get('bytes') else ''))
    views = [('u8', raw, 8)]
    def h0(a):
        c = np.bincount(a, minlength=256).astype(np.float64); p = c[c > 0] / c.sum(); return float(-(p * np.log2(p)).sum())
    he, ho = h0(raw[0::2]), h0(raw[1::2])
    if abs(he - ho) > 0.5:                     # 16-bit structure: one byte of each pair is much more predictable
        v = raw[: n - n % 2]
        views.append(('u16le' if ho < he else 'u16be', v.view('<u2' if ho < he else '>u2').astype(np.int64), 16))
    views.append(('bit', bits.astype(np.int64), 1))
    log(f"   views: {[v[0] for v in views]} (H0 even {he:.2f} odd {ho:.2f})")
    for vname, cells, nb in views:
        cells = cells.astype(np.int64)
        sample = {8: 1 << 18, 16: 1 << 17, 1: 1 << 20}[nb]
        scored = []
        for sh in candidates(cells, nb, [res['formula']['width']] if nb == 8 and res['formula']['exceptions'] < n // 2 else []):
            t = time.time()
            try: cfg = search_shape(sh, cells, nb, sample)
            except Exception as e: log(f"   {vname} {sh.name}: error {e}"); continue
            S = min(sample, sh.m); per = cfg['bits'] / S
            scored.append((per, sh, cfg)); log(f"   {vname:6} {sh.name:34} pred={cfg['pred']:5} rule={cfg['feats']}  {per * (8 / nb):.4f} bits/byte  ({time.time() - t:.0f}s)")
        scored.sort(key=lambda z: z[0])
        for per, sh, cfg in scored[:2]:
            b, det = full_bits(sh, cells, nb, cfg)
            tail = (n - sh.m * nb // 8) if nb != 1 else 0
            total = math.ceil(b / 8) + max(0, tail) + 16
            res['runs'].append({'view': vname, 'shape': sh.name, 'pred': cfg['pred'], 'rule': cfg['feats'], 'bytes': total, 'determinism': det})
            log(f"   -> FULL {vname} {sh.name} {cfg['pred']} {cfg['feats']}: {total} B (xz {xz}, {100 * (total / xz - 1):+.1f}%)" + (f"  rule determinism {det:.4f}" if det else ''))
    best = min(res['runs'], key=lambda r: r['bytes'])
    cands = [best['bytes'], res['formula']['bytes']] + ([res['lfsr']['bytes']] if res['lfsr'].get('bytes') else [])
    res['best'] = min(cands); res['best_run'] = best
    log(f"** {res['file']}: best {res['best']} B vs xz {xz} ({100 * (res['best'] / xz - 1):+.1f}%)   [{best['view']} {best['shape']} {best['pred']} {best['rule']}]")
    return res

if __name__ == '__main__':
    out = sys.argv[1]; cap = int(os.environ.get('CAP', 4 << 20)); results = []
    logf = open(out.replace('.json', '.log'), 'a')
    def log(s): print(s, flush=True); logf.write(s + '\n'); logf.flush()
    for f in sys.argv[2:]:
        results.append(run_file(f, cap, log)); json.dump(results, open(out, 'w'), indent=1)
