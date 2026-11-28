"""Article-order experiment on enwik8: same bytes, different page order, same compressors.
Inverse is free if page <id>s increase in file order (decoder sorts pages by id) - checked here.
Writes work/order_<name>.bin for each order and verifies the inverse by SHA-256."""
import re, sys, hashlib, numpy as np

src = sys.argv[1]
data = open(src, 'rb').read()
last_end = data.rfind(b'</page>') + len(b'</page>\n')      # enwik8 is cut mid-page: the partial page stays in the tail
starts = [m.start() for m in re.finditer(rb'  <page>', data) if m.start() < last_end]
head = data[:starts[0]]
ends = starts[1:] + [last_end]
pages = [data[s:e] for s, e in zip(starts, ends)]
tail = data[ends[-1]:]
assert head + b''.join(pages) + tail == data
ids = [int(re.search(rb'<id>(\d+)</id>', p).group(1)) for p in pages]
print('pages', len(pages), ' ids strictly increasing in file order:', all(a < b for a, b in zip(ids, ids[1:])),
      ' head', len(head), 'tail', len(tail), ' last page complete:', pages[-1].rstrip().endswith(b'</page>'))

def title(p): return re.search(rb'<title>(.*?)</title>', p).group(1)
def text(p):
    m = re.search(rb'<text[^>]*>(.*?)</text>', p, re.S); return m.group(1) if m else b''
def is_redirect(p): return text(p)[:9].lower() == b'#redirect'
def first_cat(p):
    m = re.search(rb'\[\[Category:([^\]|]+)', text(p)); return m.group(1) if m else b'\xff'

# MinHash signatures over word 3-shingles of the text (first 4000 bytes), 32 hashes
rng = np.random.default_rng(1)
A = rng.integers(1, 2**61 - 1, 32, dtype=np.uint64); B = rng.integers(0, 2**61 - 1, 32, dtype=np.uint64)
def sig(p):
    w = re.findall(rb'[A-Za-z]{3,}', text(p)[:4000].lower())
    sh = {hash(b' '.join(w[i:i + 3])) & 0xFFFFFFFF for i in range(max(0, len(w) - 2))} or {0}
    h = np.array(sorted(sh), dtype=np.uint64)
    return ((h[:, None] * A[None, :] + B[None, :]) % np.uint64(2**61 - 1)).min(0)

def greedy_similarity(idx):
    """nearest-neighbour chain by MinHash agreement, starting from the first page"""
    S = np.stack([sig(pages[i]) for i in idx])
    left = np.ones(len(idx), bool); cur = 0; out = [idx[0]]; left[0] = False
    for _ in range(len(idx) - 1):
        sim = (S == S[cur]).sum(1).astype(np.int32); sim[~left] = -1
        cur = int(sim.argmax()); out.append(idx[cur]); left[cur] = False
    return out

n = len(pages); allidx = list(range(n))
red = [i for i in allidx if is_redirect(pages[i])]; art = [i for i in allidx if not is_redirect(pages[i])]
print('redirects', len(red), 'articles', len(art))
orders = {
    'original': allidx,
    'random': list(np.random.default_rng(7).permutation(n)),
    'title': sorted(allidx, key=lambda i: title(pages[i])),
    'category': sorted(allidx, key=lambda i: (is_redirect(pages[i]), first_cat(pages[i]), ids[i])),
    'redirects_first+similarity': red + greedy_similarity(art),
}
h = hashlib.sha256(data).hexdigest()
for name, o in orders.items():
    body = b''.join(pages[i] for i in o)
    blob = head + body + tail
    # inverse: split again, sort by id
    bend = len(blob) - len(tail)
    st = [m.start() for m in re.finditer(rb'  <page>', blob) if m.start() < bend]
    ps = [blob[s:e] for s, e in zip(st, st[1:] + [bend])]
    back = head + b''.join(sorted(ps, key=lambda p: int(re.search(rb'<id>(\d+)</id>', p).group(1)))) + tail
    assert hashlib.sha256(back).hexdigest() == h, name
    open(f'work/order_{name}.bin', 'wb').write(blob)
    print('wrote', name, len(blob), 'inverse ok')
