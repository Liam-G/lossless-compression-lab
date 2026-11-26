"""Corpus bench: size, compress/decompress time, decode MB/s, peak RSS, SHA-256 round-trip check.
usage: python3 -I bench/bench.py FILE... --out bench/results/<tag>.json [--args "--prod-cost=6"]
Each binary runs in a fresh child (via a tiny wrapper) so per-run peak RSS is measured separately."""
import glob, hashlib, json, os, subprocess, sys, time

REF_ENWIK8 = {'xz (LTCB best)': 24_703_772, 'GLZA 0.12': 20_068_917}
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
historical = os.path.join(here, 'results', 'm1_silesia.json')

def measure(cmd):
    """run cmd in a child that reports its own peak RSS (KB) and CPU seconds."""
    code = ("import resource,subprocess,sys,json,time;t=time.time();r=subprocess.run(sys.argv[1:],capture_output=True);"
            "u=resource.getrusage(resource.RUSAGE_CHILDREN);"
            "print(json.dumps({'rc':r.returncode,'err':r.stderr.decode()[-400:],'wall':time.time()-t,'cpu':u.ru_utime+u.ru_stime,'rss_mb':u.ru_maxrss/1024}))")
    out = subprocess.run([sys.executable, '-I', '-c', code] + cmd, capture_output=True, text=True).stdout
    return json.loads(out)

def xz_ref(name):
    with open(historical) as reference:
        for row in json.load(reference)['rows']:
            if row['file'] == name:
                return row.get('xz_ref')
    return None

def main():
    args = sys.argv[1:]
    out = args[args.index('--out') + 1]; extra = []
    if '--args' in args: extra = args[args.index('--args') + 1].split()
    files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--out', '--args'))]
    work = os.path.join(root, 'work', 'bench'); os.makedirs(work, exist_ok=True)
    rows = []
    for f in files:
        name = os.path.basename(f); arc = os.path.join(work, name + '.stc'); back = os.path.join(work, name + '.out')
        n = os.path.getsize(f)
        c = measure([os.path.join(root, 'statico'), 'c'] + extra + [f, arc])
        d = measure([os.path.join(root, 'unstatico'), arc, back]) if c['rc'] == 0 else {'rc': -1, 'wall': 0, 'cpu': 0, 'rss_mb': 0, 'err': ''}
        ok = d['rc'] == 0 and hashlib.sha256(open(back, 'rb').read()).digest() == hashlib.sha256(open(f, 'rb').read()).digest()
        size = os.path.getsize(arc) if c['rc'] == 0 else None
        row = {'file': name, 'bytes': n, 'statico': size, 'roundtrip': ok, 'xz_ref': REF_ENWIK8['xz (LTCB best)'] if name == 'enwik8' else xz_ref(name),
               'c_wall': round(c['wall'], 2), 'c_rss_mb': round(c['rss_mb']), 'd_wall': round(d['wall'], 3), 'd_rss_mb': round(d['rss_mb']),
               'd_MBps': round(n / 1e6 / d['wall'], 1) if d['wall'] else None, 'err': (c['err'] + d['err']).strip()[-300:]}
        rows.append(row)
        print(json.dumps(row), flush=True)
        for p in (arc, back):
            if os.path.exists(p): os.remove(p)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump({'args': extra, 'rows': rows, 'ref_enwik8': REF_ENWIK8}, open(out, 'w'), indent=1)
    print(f"\n{'file':<14}{'bytes':>12}{'statico':>12}{'xz':>12}{'vs xz':>8}{'comp s':>9}{'dec MB/s':>9}{'dec MB':>8}  rt")
    for r in rows:
        vs = f"{100 * (r['statico'] / r['xz_ref'] - 1):+.1f}%" if r['statico'] and r['xz_ref'] else ''
        print(f"{r['file']:<14}{r['bytes']:>12,}{(r['statico'] or 0):>12,}{(r['xz_ref'] or 0):>12,}{vs:>8}{r['c_wall']:>9.1f}{(r['d_MBps'] or 0):>9.1f}{r['d_rss_mb']:>8}  {'ok' if r['roundtrip'] else 'FAIL'}")
    sys.exit(0 if all(r['roundtrip'] for r in rows) else 1)

main()
