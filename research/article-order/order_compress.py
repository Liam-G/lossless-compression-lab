import sys, subprocess, hashlib, os, json, resource
from concurrent.futures import ThreadPoolExecutor
names = ['original', 'random', 'title', 'category', 'redirects_first+similarity']
TOOLS = {
    'xz':   (['xz', '-T1', '--lzma2=preset=9e,dict=128MiB', '-c'], ['xz', '-dc']),
    'zstd': (['zstd', '--ultra', '-22', '--long=27', '--single-thread', '-c'], ['zstd', '-dc', '--long=27']),
    'ppmd': None,
}
def job(name, tool):
    f = f'work/order_{name}.bin'
    h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
    if tool == 'ppmd':
        out = f'work/order_{name}.7z'
        if os.path.exists(out): os.remove(out)
        subprocess.run(['7z', 'a', '-t7z', '-m0=PPMd:o=12:mem=768m', '-mmt=1', '-bd', '-y', out, f], capture_output=True, check=True)
        size = os.path.getsize(out)
        back = subprocess.run(['7z', 'x', '-so', out], capture_output=True, check=True).stdout
        os.remove(out)
    else:
        c, d = TOOLS[tool]
        z = subprocess.run(c + [f], capture_output=True, check=True).stdout
        size = len(z)
        back = subprocess.run(d, input=z, capture_output=True, check=True).stdout
    ok = hashlib.sha256(back).hexdigest() == h
    print(json.dumps({'order': name, 'tool': tool, 'bytes': size, 'roundtrip': ok}), flush=True)
    return name, tool, size, ok
with ThreadPoolExecutor(3) as ex:
    res = list(ex.map(lambda a: job(*a), [(n, t) for t in ['ppmd', 'xz', 'zstd'] for n in names]))
json.dump(res, open('order_results.json', 'w'))
