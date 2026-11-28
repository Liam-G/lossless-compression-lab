"""Automatic knob search for cm2lab on a sample (coordinate descent, parallel). usage: tune.py SAMPLE BASECONFIG ROUNDS"""
import itertools, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sample, basecfg, rounds = sys.argv[1], open(sys.argv[2]).read().split(), int(sys.argv[3])
cfg = dict(kv.split('=', 1) for kv in basecfg)
cfg['CM_CTX'] = cfg['CM_CTX'] + ',wc,o7' if 'wc' not in cfg['CM_CTX'] else cfg['CM_CTX']
GRID = {'CM_LIM': ['127', '255', '511'], 'CM_LIMLO': ['255', '511', '1023'], 'CM_LR': ['0.015', '0.02', '0.025'], 'CM_LRD': ['80000', '150000', '300000'],
        'CM_LRMIN': ['0.0015', '0.002', '0.0025'], 'CM_MATCH': ['5', '6', '7', '8'], 'CM_APMR': ['0.01', '0.02', '0.03'], 'CM_FB': ['0.5', '0.75', '0.9'], 'CM_SSW': ['0.3', '0.5', '0.7']}
def run(c):
    env = dict(os.environ, **c); out = subprocess.run(['systemd-run', '--user', '--scope', '--slice=build.slice', '-q', '--', './cm2lab_tune', sample], env=env, capture_output=True, text=True).stdout
    m = re.search(r'^\s*(\d+) bytes', out, re.M); return int(m.group(1)) if m else 10**12
best = run(cfg); print(f'start: {best:,}  {" ".join(f"{k}={v}" for k, v in sorted(cfg.items()))}', flush=True)
for r in range(rounds):
    improved = False
    for k, vals in GRID.items():
        trials = [dict(cfg, **{k: v}) for v in vals if v != cfg.get(k)]
        with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, trials))
        for t, s in zip(trials, res):
            mark = ' <- better' if s < best else ''
            print(f'  round {r + 1} {k}={t[k]:8} {s:,}{mark}', flush=True)
        i = min(range(len(res)), key=lambda q: res[q])
        if res[i] < best: best, cfg, improved = res[i], trials[i], True
    print(f'after round {r + 1}: {best:,}', flush=True)
    if not improved: break
open(sys.argv[2].replace('.config', '_tuned.config'), 'w').write(' '.join(f'{k}={v}' for k, v in cfg.items()))
print(f'BEST {best:,}  {" ".join(f"{k}={v}" for k, v in sorted(cfg.items()))}')
