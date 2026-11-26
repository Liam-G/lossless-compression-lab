"""Round-trip edge cases through the real binaries.
usage: python3 -I tests/edge_cases.py BIN_DIR WORK_DIR
Checks: SHA-256 equality, archive <= input + 16 + input/10000, truncated archive -> unstatico exits 2."""
import hashlib, os, random, subprocess, sys

bindir, work = sys.argv[1], sys.argv[2]
os.makedirs(work, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
canterbury = os.path.join(here, '..', '..', 'corpus', 'canterbury')

rng = random.Random(11)
blk = bytes(rng.randrange(256) for _ in range(16))
flipped = bytearray(blk * 65536); flipped[len(flipped) // 3] ^= 0x10
cases = {
    'empty': b'',
    'one_byte': b'\x42',
    'all_256': bytes(range(256)),
    'zeros_10MB': bytes(10 * 2**20),
    'random_10MB': os.urandom(10 * 2**20),
    'block_x65536': blk * 65536,
    'block_x65536_bitflip': bytes(flipped),
}
if os.path.isdir(canterbury):
    for f in sorted(os.listdir(canterbury)):
        cases['cant_' + f] = open(os.path.join(canterbury, f), 'rb').read()

def run(*a):
    return subprocess.run(a, capture_output=True)

fails = 0
for name, data in cases.items():
    src, arc, back = (os.path.join(work, name + s) for s in ('.in', '.stc', '.out'))
    open(src, 'wb').write(data)
    r = run(os.path.join(bindir, 'statico'), 'c', src, arc)
    if r.returncode: print('FAIL compress', name, r.stderr.decode()); fails += 1; continue
    r = run(os.path.join(bindir, 'unstatico'), arc, back)
    ok = r.returncode == 0 and hashlib.sha256(open(back, 'rb').read()).digest() == hashlib.sha256(data).digest()
    size = os.path.getsize(arc)
    bound = len(data) + 16 + len(data) // 10000
    status = 'ok' if ok and size <= bound else 'FAIL'
    fails += status != 'ok'
    print(f'{status:4} {name:28} {len(data):>10} -> {size:>10}')
    for p in (src, back): os.remove(p)

# test_truncated: half an archive must be rejected with exit code 2
arc = os.path.join(work, 'cant_alice29.txt.stc') if 'cant_alice29.txt' in cases else os.path.join(work, 'block_x65536_bitflip.stc')
half = os.path.join(work, 'truncated.stc')
blob = open(arc, 'rb').read(); open(half, 'wb').write(blob[:len(blob) // 2])
r = run(os.path.join(bindir, 'unstatico'), half, os.path.join(work, 'truncated.out'))
ok = r.returncode == 2
fails += not ok
print(f"{'ok' if ok else 'FAIL':4} truncated archive -> exit {r.returncode}: {r.stderr.decode().strip()}")
# test_huge_size_header: a header claiming 2^39 bytes must be rejected with exit 2, not abort
bad = os.path.join(work, 'huge.stc')
vi = bytearray(); v = 1 << 39
while v >= 0x80: vi.append((v & 0x7F) | 0x80); v >>= 7
vi.append(v)
open(bad, 'wb').write(b'STC1\x02' + bytes(vi) + bytes(32) + b'\x00' * 64)
r = run(os.path.join(bindir, 'unstatico'), bad, os.path.join(work, 'huge.out'))
ok = r.returncode == 2; fails += not ok
print(f"{'ok' if ok else 'FAIL':4} huge size header -> exit {r.returncode}: {r.stderr.decode().strip()[:80]}")

# test_grammar_limit: input above the grammar size limit falls back to order-0 (mode byte 1) and round trips
src, arc, back = (os.path.join(work, 'limit' + s) for s in ('.in', '.stc', '.out'))
data = cases.get('cant_alice29.txt', blk * 1000); open(src, 'wb').write(data)
r1 = run(os.path.join(bindir, 'statico'), 'c', '--grammar-limit=1000', src, arc)
r2 = run(os.path.join(bindir, 'unstatico'), arc, back)
ok = r1.returncode == 0 and r2.returncode == 0 and open(arc, 'rb').read()[4] == 1 and open(back, 'rb').read() == data
fails += not ok
print(f"{'ok' if ok else 'FAIL':4} grammar limit -> order0 fallback ({r1.stderr.decode().strip()[:70]})")
print('edge cases:', 'all passed' if not fails else f'{fails} FAILED')
sys.exit(1 if fails else 0)
