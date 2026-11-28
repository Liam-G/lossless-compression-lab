"""Arena stage 1: every reshape chain (alone and in pairs) x every compressor, verbose, ranked.
usage:
  arena.py cheap  INPUT WORK OUT.jsonl            # all chains, cheap compressors (xz, bzip2, zstd)
  arena.py strong INPUT WORK CHEAP.jsonl OUT.jsonl N   # top N chains + baselines, slow compressors (ours, PPMd, brotli)
Every chain is decoded back and compared with the input (SHA-256); chains that fail or do not apply are logged and dropped.
"""
import hashlib, itertools, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
VIEW = os.path.join(HERE, '../build/view'); TF = os.path.join(HERE, '../text-views/textfront.py')
STATICO = os.path.join(HERE, '../statico/statico'); GBUILD = os.path.join(HERE, '../build/grammar-lab')
CAP = 100_000_000                       # skip chains whose data would grow past this
CPP = ['bwt', 'mtf', 'delta', 'xorprev', 'reverse', 'bitplanes', 'base2', 'base3', 'base4', 'transpose:4', 'transpose:16', 'transpose:80']
TEXT = ['caps', 'words', 'split']
FIRST = ['xz', 'zstd', 'bzip2', 'ppmd']
VIEWS = CPP + TEXT + FIRST
GROW = {'base2': 8, 'base3': 6, 'base4': 4}
lock = threading.Lock()

def sh(cmd, **kw): return subprocess.run(cmd, check=True, capture_output=True, **kw)
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def view(direction, v, src, dst):
    if v in CPP: sh([VIEW, direction, v, src, dst])
    elif v in TEXT:
        if direction == 'enc': sh([sys.executable, '-I', TF, 'enc', src, dst, v])
        else: sh([sys.executable, '-I', TF, 'dec', src, dst])
    elif v == 'xz': open(dst, 'wb').write(sh(['xz', '-c', '-9e', '-T1'] + (['-d'] if direction == 'dec' else []) + [src]).stdout)
    elif v == 'zstd': open(dst, 'wb').write(sh(['zstd', '-q', '-c', '-19', '--long=27'] + (['-d'] if direction == 'dec' else []) + [src]).stdout)
    elif v == 'bzip2': open(dst, 'wb').write(sh(['bzip2', '-c', '-9'] + (['-d'] if direction == 'dec' else []) + [src]).stdout)
    elif v == 'ppmd':
        if direction == 'enc':
            if os.path.exists(dst): os.remove(dst)
            sh(['7z', 'a', '-bd', '-bso0', '-t7z', '-m0=PPMd:mem=768m:o=10', dst + '.7z', src]); os.rename(dst + '.7z', dst)
        else: open(dst, 'wb').write(sh(['7z', 'e', '-so', '-t7z', src]).stdout)

def size_of(backend, p):
    if backend == 'xz': return len(sh(['xz', '-c', '-T1', '--lzma2=preset=9e,dict=128MiB', p]).stdout)
    if backend == 'bzip2': return len(sh(['bzip2', '-9', '-c', p]).stdout)
    if backend == 'zstd': return len(sh(['zstd', '-q', '-c', '-19', '--long=27', p]).stdout)
    if backend == 'brotli': return len(sh(['brotli', '-c', '-q', '11', '-w', '24', p]).stdout)
    if backend == 'ppmd':
        a = p + '.7z'
        if os.path.exists(a): os.remove(a)
        sh(['7z', 'a', '-bd', '-bso0', '-t7z', '-m0=PPMd:mem=768m:o=10', a, p]); n = os.path.getsize(a); os.remove(a); return n
    if backend == 'statico-M1':       # ours, as shipped (self-verifies before writing)
        a = p + '.stc'; sh([STATICO, 'c', p, a]); n = os.path.getsize(a); os.remove(a); return n
    if backend == 'statico-new':      # ours with GLZA-style rule picking (gbuild verifies the round trip)
        a = p + '.stc'; sh([GBUILD, p, a], env=dict(os.environ, GP_POWER='8', GP_SPACE='1')); n = os.path.getsize(a); os.remove(a); return n
    raise ValueError(backend)

def run_chain(chain, src, work, backends, n_in):
    tag = '+'.join(chain) if chain else 'none'
    d = os.path.join(work, tag.replace(':', '_')); os.makedirs(d, exist_ok=True)
    t0 = time.time(); r = {'chain': tag, 'steps': len(chain)}
    try:
        cur, size = src, n_in
        for i, v in enumerate(chain):
            if size * GROW.get(v, 1) > CAP: raise RuntimeError(f'would grow past {CAP:,} bytes')
            nxt = os.path.join(d, f's{i}'); view('enc', v, cur, nxt); cur = nxt; size = os.path.getsize(cur)
        r['reshaped'] = size; t_re = time.time() - t0
        back = cur
        for i, v in reversed(list(enumerate(chain))):
            out = os.path.join(d, f'b{i}'); view('dec', v, back, out); back = out
        r['roundtrip'] = sha(back) == REF
        if not r['roundtrip']: raise RuntimeError('ROUND TRIP FAILED')
        for b in backends: r[b] = size_of(b, cur)
        r['secs'] = round(time.time() - t0, 1)
        best = min(backends, key=lambda b: r[b])
        line = (f'{tag:28} {n_in:>12,} -> {size:>12,} (reshape {t_re:5.1f}s, round trip OK) | ' +
                '  '.join(f'{b} {r[b]:>11,}' for b in backends) + f'  | best {best} {r[best] * 8 / n_in:.3f} bits/byte  [{r["secs"]}s]')
    except Exception as e:
        msg = e.stderr.decode(errors='replace').strip().splitlines()[-1][:80] if isinstance(e, subprocess.CalledProcessError) and e.stderr else str(e)
        r['error'] = msg; line = f'{tag:28} DROPPED: {msg}'
    finally:
        subprocess.run(['rm', '-rf', d])
    return r, line

def main():
    global REF
    mode, src, work = sys.argv[1:4]; os.makedirs(work, exist_ok=True)
    REF = sha(src); n_in = os.path.getsize(src)
    if mode == 'cheap':
        out = sys.argv[4]; backends = ['zstd', 'bzip2', 'xz']
        chains = [()] + [(v,) for v in VIEWS] + list(itertools.product(VIEWS, VIEWS))
        par = 4
    else:
        cheap, out, N = sys.argv[4], sys.argv[5], int(sys.argv[6]); backends = ['statico-new', 'statico-M1', 'ppmd', 'brotli']
        rows = [json.loads(l) for l in open(cheap) if l.strip()]
        ok = [r for r in rows if 'error' not in r]
        ok.sort(key=lambda r: min(r['zstd'], r['bzip2'], r['xz']))
        pick = [r['chain'] for r in ok[:N]]
        for must in ['none', 'caps', 'words', 'split', 'caps+split', 'split+caps', 'bwt', 'xz', 'base2', 'bitplanes']:
            if must not in pick and any(r['chain'] == must for r in ok): pick.append(must)
        chains = [tuple() if c == 'none' else tuple(c.split('+')) for c in pick]
        par = 2
    print(f'ARENA {mode}: input {src} ({n_in:,} bytes), {len(chains)} chains x compressors {backends}, {par} at a time', flush=True)
    print(f'views: {VIEWS}', flush=True)
    done = 0
    with open(out, 'w') as f, ThreadPoolExecutor(par) as ex:
        futs = [ex.submit(run_chain, c, src, work, backends, n_in) for c in chains]
        for fu in futs:
            r, line = fu.result(); done += 1
            with lock:
                print(f'[{done:3d}/{len(chains)}] {line}', flush=True); f.write(json.dumps(r) + '\n'); f.flush()
    rows = [json.loads(l) for l in open(out) if l.strip()]
    ok = [r for r in rows if 'error' not in r]
    print(f'\nRANKING ({len(ok)} chains ran, {len(rows) - len(ok)} dropped); best compressor per chain, bits per input byte', flush=True)
    for b in backends:
        ok.sort(key=lambda r: r[b])
        base = next((r[b] for r in ok if r['chain'] == 'none'), None)
        print(f'\n  by {b}:' + (f' (no reshape = {base:,})' if base else ''))
        for i, r in enumerate(ok[:15]):
            rel = f'{100 * (r[b] - base) / base:+6.2f}%' if base else ''
            print(f'   {i + 1:2d}. {r["chain"]:28} {r[b]:>11,}  {r[b] * 8 / n_in:.3f} b/B  {rel}')
    print('ALLDONE', flush=True)

if __name__ == '__main__':
    main()
