"""Bounded exact formula search on variable-width binary split trees, including the root."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from math import floor, log2
from mmap import mmap, ACCESS_READ
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)


def copy(source, target, count):
    while count:
        data = source.read(min(count, 1 << 20))
        if not data:
            raise ValueError("Truncated literal")
        target.write(data)
        count -= len(data)

MODS = (1000000007, 1000000009)
NUM_BASES = (*range(2, 17), 31, 64, 128, 256, 257)
DEN_BASES = (2, 3, 4, 5, 7, 10, 16, 31, 64, 256)
HEADER = struct.Struct('>4sQ')
MAGIC = b'QBT1'
LITERAL, SPLIT, FORMULA, UNEQUAL = 0, 1, 2, 3


def varint(n):
    result = bytearray()
    while n >= 128:
        result.append(128 + n % 128)
        n //= 128
    result.append(n)
    return bytes(result)


def read_varint(f):
    n = 0
    for shift in range(0, 70, 7):
        b = f.read(1)
        if not b:
            raise ValueError('truncated parameter')
        n |= (b[0] & 127) << shift
        if b[0] < 128:
            return n
    raise ValueError('parameter too long')


def unit(b, r):
    return (pow(b, r) - 1) // (b - 1)


def exact(wire):
    p, b, r, c, d, t, e = wire
    if p not in (1, *PRIMES) or not 0 < c < b or r < 3:
        raise ValueError('invalid numerator or multiplier')
    denominator = 1
    if d:
        if b == d or not 0 < e < d or t < 3:
            raise ValueError('invalid denominator')
        denominator = e * unit(d, t)
    elif t or e:
        raise ValueError('invalid direct record')
    leaf, remainder = divmod(c * unit(b, r), denominator)
    if remainder:
        return None
    return p * leaf


def recipe(wire):
    return bytes([FORMULA]) + b''.join(map(varint, wire))


@lru_cache(maxsize=None)
def scales(base):
    table = {}
    for p in (1, *PRIMES):
        for c in range(1, base):
            table.setdefault(p*c, []).append((p, c))
    return table


def describe_node(data, start, end):
    first = start
    while first < end and data[first] == 0:
        first += 1
    stop = min(first + 7, end)
    head = int.from_bytes(data[first:stop], 'big')
    if not head:
        return None
    modulus = MODS[0] * MODS[1]
    residue = 0
    chunk = 65536
    shift = pow(256, chunk, modulus)
    for i in range(first, end, chunk):
        n = min(end - i, chunk)
        residue = (residue * (shift if n == chunk else pow(256, n, modulus))
                   + int.from_bytes(data[i:i+n], 'big')) % modulus
    return (log2(head) + 8*(end-stop), head.bit_length()+8*(end-stop), residue)


@lru_cache(maxsize=120000)
def unit_mod(base, repeats, mod):
    return (pow(base, repeats, mod) - 1) * pow(base-1, -1, mod) % mod


@lru_cache(maxsize=120000)
def inverse_unit(base, repeats, mod):
    a = unit_mod(base, repeats, mod)
    return pow(a, -1, mod) if a else 0


def denominators(bit_length):
    yield 0, 0, 0, 0.0, (1, 1)
    for b in DEN_BASES:
        k = bit_length / log2(b)
        for r in sorted({3, 4, 6, 8, 12, 16, 31, 64, max(3, int(k/2)), max(3, int(k))}):
            # log2(1-b**(-r)) is negligible once r*log2(b) exceeds 55.
            correction = log2(1 - b**(-r)) if r*log2(b) < 55 else 0.0
            log_unit = r*log2(b) - log2(b-1) + correction
            residues = [unit_mod(b, r, m) for m in MODS]
            for e in sorted({1, min(2, b-1), b-1}):
                yield b, r, e, log_unit+log2(e), tuple(e*v % m for v, m in zip(residues, MODS))


def search(data, start, end, stats):
    info = describe_node(data, start, end)
    if info is None:
        return None, None
    log_n, bit_length, residue = info
    # Independent necessary condition for ANY even bases <=256 and r1,r2 >=64.
    low = int.from_bytes(data[max(start,end-8):end], 'big')
    mask = (1 << 64) - 1
    modular_bound = any(0 < (low * k & mask) <= 53*255*255 for k in range(1, 255*255+1))
    if not modular_bound:
        stats['even_family_excluded'] += 1
    best = None
    actual = None
    for d, t, e, log_den, den_mod in denominators(bit_length):
        targets = [residue * v % m for v, m in zip(den_mod, MODS)]
        for b in NUM_BASES:
            if b == d:
                continue
            # b**r = 1 + N * denominator * (b-1) / (p*c).
            # Bound using 1 <= p*c <= 53*(b-1); extra endpoints cover rounding.
            high = log_n + log_den + log2(b - 1)
            lo = max(3, floor((high - log2(53*(b-1))) / log2(b)) - 1)
            hi = floor((high + 1) / log2(b)) + 1
            stats['numerator_exponents_tested'] += hi-lo+1
            for r in range(lo, hi+1):
                inv = inverse_unit(b, r, MODS[0])
                if inv:
                    s = targets[0] * inv % MODS[0]
                    if s not in scales(b) or s * unit_mod(b,r,MODS[1]) % MODS[1] != targets[1]:
                        continue
                    possible = [s]
                elif targets[0]:
                    continue
                else:
                    inv2 = inverse_unit(b, r, MODS[1])
                    if inv2:
                        possible = [targets[1] * inv2 % MODS[1]]
                    else:
                        possible = [] if targets[1] else scales(b)
                for s in possible:
                    for p, c in scales(b).get(s, ()):
                        wire = (p,b,r,c,d,t,e)
                        if actual is None:
                            actual = int.from_bytes(data[start:end], 'big')
                        stats['exact_candidate_checks'] += 1
                        if exact(wire) != actual:
                            continue
                        encoded = recipe(wire)
                        if best is None or (len(encoded), encoded) < (len(best), best):
                            best = encoded
    return best, not modular_bound


def compress(source, archive):
    size = source.stat().st_size
    stats = Counter()
    upper = []
    alternate_cuts = []
    anchors = (0, size//2, size-1)
    with source.open('rb') as f:
        if not size:
            with archive.open('xb') as out:
                out.write(HEADER.pack(MAGIC, 0) + bytes([LITERAL]))
            return dict(source_bytes=0, archive_bytes=archive.stat().st_size)
        with mmap(f.fileno(), 0, access=ACCESS_READ) as data:
            @lru_cache(maxsize=None)
            def leaf(start, end):
                width = end-start
                stats['nodes'] += 1
                form, even_excluded = search(data, start, end, stats)
                best = (1+width, (LITERAL,start,end))
                if form is not None:
                    stats['exact_formula_nodes'] += 1
                    if len(form) < best[0]:
                        best = (len(form), (FORMULA,form))
                return best, form is not None, even_excluded

            def visit(start, end, depth):
                width = end-start
                best, matched, even_excluded = leaf(start, end)
                if depth < 2:
                    upper.append(dict(depth=depth, start=start, width=width,
                                      exact_formula=matched, even_family_excluded=even_excluded))
                if width >= 512 and (depth < 3 or any(start <= i < end for i in anchors)):
                    mid = start+width//2
                    lc, left = visit(start, mid, depth+1)
                    rc, right = visit(mid, end, depth+1)
                    if 1+lc+rc < best[0]:
                        best = (1+lc+rc, (SPLIT,left,right))
                return best
            cost, tree = visit(0, size, 0)
            # Price each alternate root cut as two independent literal/formula leaves.
            for a, b in [(1,8), (1,4), (1,3), (2,3), (3,4), (7,8)]:
                mid = size*a//b
                if not 0 < mid < size or mid == size//2:
                    continue
                (lc,left), lm, _ = leaf(0,mid)
                (rc,right), rm, _ = leaf(mid,size)
                candidate = 1 + len(varint(mid)) + lc + rc
                alternate_cuts.append(dict(offset=mid, fraction=[a,b], left_match=lm, right_match=rm,
                                           archive_bytes=HEADER.size+candidate))
                if candidate < cost:
                    cost, tree = candidate, (UNEQUAL,mid,left,right)
            tags = Counter()
            with archive.open('xb') as out:
                out.write(HEADER.pack(MAGIC,size))
                def write(node):
                    tag = node[0]
                    tags[tag] += 1
                    if tag == FORMULA:
                        out.write(node[1])
                    else:
                        out.write(bytes([tag]))
                        if tag == UNEQUAL:
                            out.write(varint(node[1]))
                            write(node[2])
                            write(node[3])
                        elif tag == SPLIT:
                            write(node[1])
                            write(node[2])
                        else:
                            for pos in range(node[1], node[2], 1 << 20):
                                out.write(data[pos:min(pos+(1 << 20), node[2])])
                write(tree)
            assert HEADER.size + cost == archive.stat().st_size
    return dict(source_bytes=size, archive_bytes=HEADER.size+cost, selected_tags=dict(tags),
                top_nodes=upper, alternate_cuts=alternate_cuts, stats=dict(stats))


def decode(archive, dest):
    with archive.open('rb') as f, dest.open('xb') as out:
        magic, width = HEADER.unpack(f.read(HEADER.size))
        if magic != MAGIC:
            raise ValueError('bad header')
        def visit(w):
            tag = f.read(1)
            if tag == bytes([LITERAL]):
                copy(f,out,w)
            elif tag == bytes([SPLIT]) and w >= 2:
                visit(w//2)
                visit(w - w//2)
            elif tag == bytes([UNEQUAL]):
                mid = read_varint(f)
                if not 0 < mid < w:
                    raise ValueError('invalid split position')
                visit(mid)
                visit(w-mid)
            elif tag == bytes([FORMULA]):
                wire = [read_varint(f) for _ in range(7)]
                n = exact(wire)
                if n is None:
                    raise ValueError('inexact quotient')
                out.write(n.to_bytes(w,'big'))
            else:
                raise ValueError('bad tag')
        visit(width)
        if f.read(1):
            raise ValueError('trailing data')


def bench(q, output):
    output.mkdir(exist_ok=True)
    reports = {}
    with TemporaryDirectory(dir=output) as tmp:
        tmp = Path(tmp)
        width = 786432
        a = exact((31,2,8*width-12,1,3,3,1))
        r = 6 * int((8*width-8)/log2(3)/6)
        b = exact((47,3,r,1,2,3,1))
        planted = tmp/'planted'
        planted.write_bytes(a.to_bytes(width,'big') + b.to_bytes(width,'big'))
        for name, source in [('Q', q), ('planted', planted)]:
            arc, restored = tmp/'tree', tmp/'decoded'
            report = compress(source, arc)
            subprocess.run([sys.executable, '-B', __file__, 'decode', arc, restored], check=True)
            subprocess.run(['cmp', source, restored], check=True)
            with source.open('rb') as f:
                report['sha256'] = hashlib.file_digest(f,'sha256').hexdigest()
            reports[name] = report
            print(name, json.dumps(report), flush=True)
            if name == 'planted':
                arc.replace(output/'planted-big.qbt')
            else:
                arc.unlink()
            restored.unlink()
    (output/'big-results.json').write_text(json.dumps(reports,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bench','encode','decode'])
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.command == 'bench':
        bench(args.source,args.destination)
    elif args.command == 'encode':
        print(json.dumps(compress(args.source,args.destination)))
    else:
        decode(args.source,args.destination)
