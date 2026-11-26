"""GFH1 with native orbit search and an independent Python decoder."""
import argparse
import ctypes as ct
import json
import os
import struct
import tempfile
from collections import Counter
from functools import cache
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER = struct.Struct(">4sQB")
PROFILES = ("direct", "automaton", "factor-one", "factors", "post", "full")
Row = ct.c_uint16 * 16


class State(ct.Structure):
    _fields_ = [("rows", Row), ("weight", ct.c_uint16), ("rank", ct.c_uint16)]


@cache
def native():
    lib = ct.CDLL(str(HERE.parent / "build/orbit.so"))
    lib.orbit.argtypes = [ct.POINTER(ct.c_uint16), ct.c_int, ct.c_int, ct.c_int,
                          ct.c_bool, ct.POINTER(State)]
    lib.orbit.restype = ct.c_int
    return lib


@cache
def width(n, k):
    return (comb(n, k) - 1).bit_length()


def subset(mask):
    """Colexicographic rank of the set bit positions."""
    rank = 0
    j = 1
    while mask:
        bit = mask & -mask
        rank += comb(bit.bit_length() - 1, j)
        mask ^= bit
        j += 1
    return rank


def unsubset(n, k, rank):
    if not 0 <= k <= n or rank >= comb(n, k):
        raise ValueError("Invalid subset rank")
    mask = 0
    pos = n - 1
    for j in range(k, 0, -1):
        while comb(pos, j) > rank:
            pos -= 1
        mask |= 1 << pos
        rank -= comb(pos, j)
        pos -= 1
    return mask


def flatten(rows, w):
    return sum(row << (i*w) for i, row in enumerate(rows))


def split_rows(value, h, w):
    mask = (1 << w) - 1
    return tuple((value >> (i*w)) & mask for i in range(h))


def join(*fields):
    length = value = 0
    for size, field in fields:
        value = (value << size) | field
        length += size
    return length, value


def step(rows, w):
    """Forward Checkerboard mix with column zero at the low bit."""
    h = len(rows)
    rows = list(rows)
    for phase in (0, 1):
        for y in range(h):
            up = rows[y-1] if y or h % 2 == 0 else 0
            down = rows[(y+1) % h] if y+1 < h or h % 2 == 0 else 0
            x = rows[y]
            left, right = x << 1, x >> 1
            if w % 2 == 0:
                left |= x >> (w-1)
                right |= (x & 1) << (w-1)
            color = 0xaaaa if phase ^ (y & 1) else 0x5555
            rows[y] ^= ((left & right) ^ (up | down)) & color & ((1 << w)-1)
    return tuple(rows)


def factor(rows, w):
    """Independent rows, remaining coordinates and the two basis partitions."""
    basis = {}
    selected = []
    coeffs = []
    indices = 0
    for y, original in enumerate(rows):
        row, coeff = original, 0
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row, coeff ^ (1 << len(selected))
                selected.append(original)
                indices |= 1 << y
                break
            pivot_row, pivot_coeff = basis[pivot]
            row ^= pivot_row
            coeff ^= pivot_coeff
        else:
            coeffs.append(coeff)
    r = len(selected)
    mask = (1 << r) - 1
    return r, indices, ((tuple(coeffs), r), (tuple(x & mask for x in selected), r),
                        (tuple(x >> r for x in selected), w-r))


def encode_block(original, profile, steps, depth, beam):
    use_factors = profile in ("factor-one", "factors", "post", "full")
    use_ca = profile in ("automaton", "post", "full") and steps > 0

    @cache
    def solve(rows, w, levels):
        h = len(rows)
        n = w*h
        value = flatten(rows, w)
        can_factor = use_factors and levels > 0 and min(h, w) >= 2
        pre = profile == "full" and can_factor and use_ca
        weight = value.bit_count()
        best = (1+n, value)  # prefix 0
        enum_len = 3 + n.bit_length() + width(n, weight)
        if enum_len < best[0]:
            best = join((3, 4), (n.bit_length(), weight), (width(n, weight), subset(value)))
        candidates = [(0, rows)]
        if use_ca:
            states = (State * (steps + 1))()
            count = native().orbit(Row(*rows), h, w, steps, pre, states)
            short = []
            best_cost, leaf = best[0], None
            for t in range(1, count):
                st = states[t]
                cost = 3 + 7 + n.bit_length() + width(n, st.weight)
                if cost < best_cost:
                    best_cost, leaf = cost, t
                if pre and 0 < st.rank < min(h, w):
                    short.append((st.rank, min(st.weight, n-st.weight), t))
            if leaf is not None:
                st = states[leaf]
                value = flatten(st.rows[:h], w)
                best = join((3, 5), (7, leaf), (n.bit_length(), st.weight),
                            (width(n, st.weight), subset(value)))
            candidates.extend((t, tuple(states[t].rows[:h])) for _, _, t in sorted(short)[:beam])
        if can_factor:
            for t, matrix in candidates:
                rank, indices, parts = factor(matrix, w)
                if not 0 < rank < min(h, w):
                    continue
                prefix = [(3, 7 if t else 6)]
                if t:
                    prefix.append((7, t))
                prefix.extend([((min(h,w)-1).bit_length(), rank-1),
                               (width(h, rank), subset(indices))])
                children = [solve(part, cols, levels-1) for part, cols in parts]
                option = join(*prefix, *children)
                if option[0] < best[0]:
                    best = option
        return best

    try:
        return solve(original, 16, min(depth, 1) if profile == "factor-one" else depth)
    finally:
        solve.cache_clear()


class Writer:
    def __init__(self, stream):
        self.stream, self.bits, self.value = stream, 0, 0

    def put(self, size, value):
        self.value = (self.value << size) | value
        self.bits += size
        count, self.bits = divmod(self.bits, 8)
        self.stream.write((self.value >> self.bits).to_bytes(count, "big"))
        self.value &= (1 << self.bits) - 1

    def finish(self):
        if self.bits:
            self.put(8-self.bits, 0)


class Reader:
    def __init__(self, stream):
        self.stream, self.bits, self.value = stream, 0, 0

    def get(self, size):
        if size > self.bits:
            count = (size - self.bits + 7)//8
            chunk = self.stream.read(count)
            if len(chunk) != count:
                raise ValueError("Truncated file")
            self.value = (self.value << (8*count)) | int.from_bytes(chunk, "big")
            self.bits += count*8
        self.bits -= size
        result = self.value >> self.bits
        self.value &= (1 << self.bits) - 1
        return result


def decode_node(reader, h, w, stats, depth=0):
    n = h*w
    if not reader.get(1):
        stats[f"literal@{depth}"] += 1
        return split_rows(reader.get(n), h, w)
    factor_mode, ca = reader.get(1), reader.get(1)
    t = reader.get(7) if ca else 0
    if ca and not 1 <= t <= 100:
        raise ValueError("Invalid step")
    label = "factors" if factor_mode else "enumerative"
    stats[f"{label}{'+CA' if ca else ''}@{depth}"] += 1
    if factor_mode:
        r = 1 + reader.get((min(h, w)-1).bit_length())
        if not r < min(h, w):
            raise ValueError("Invalid rank")
        indices = unsubset(h, r, reader.get(width(h, r)))
        coeffs = iter(decode_node(reader, h-r, r, stats, depth+1))
        low = decode_node(reader, r, r, stats, depth+1)
        high = decode_node(reader, r, w-r, stats, depth+1)
        selected = [a | (b << r) for a, b in zip(low, high)]
        independent = iter(selected)
        rows = []
        for y in range(h):
            if indices >> y & 1:
                rows.append(next(independent))
            else:
                row, coeff = 0, next(coeffs)
                for j, base in enumerate(selected):
                    if coeff >> j & 1:
                        row ^= base
                rows.append(row)
        rows = tuple(rows)
    else:
        k = reader.get(n.bit_length())
        if k > n:
            raise ValueError("Invalid weight")
        rows = split_rows(unsubset(n, k, reader.get(width(n, k))), h, w)
    for _ in range(t):
        rows = step(rows, w)
    return rows


def literal_copy(src, dst, size):
    while size:
        buf = src.read(min(size, 1 << 20))
        if not buf:
            raise ValueError("Truncated literal body")
        dst.write(buf)
        size -= len(buf)


def pack(src, dst, profile, steps, depth, beam):
    size = os.fstat(src.fileno()).st_size
    dst.write(HEADER.pack(b"GFH1", size, 1))
    writer = Writer(dst)
    tree_bits = 0
    for _ in range(size//32):
        rows = struct.unpack("<16H", src.read(32))
        bits, val = encode_block(rows, profile, steps, depth, beam)
        writer.put(bits, val)
        tree_bits += bits
    tail = src.read()
    writer.put(8*len(tail), int.from_bytes(tail, "big"))
    writer.finish()
    literal = dst.tell() >= HEADER.size + size
    if literal:
        dst.seek(0)
        dst.write(HEADER.pack(b"GFH1", size, 0))
        src.seek(0)
        literal_copy(src, dst, size)
        dst.truncate()
    return dict(byte=dst.tell(), literal_body=literal, candidate_node_bits=tree_bits)


def unpack(src, dst):
    header = src.read(HEADER.size)
    if len(header) != HEADER.size:
        raise ValueError("Truncated header")
    magic, size, mode = HEADER.unpack(header)
    if magic != b"GFH1" or mode > 1:
        raise ValueError("Unknown header")
    counts = Counter()
    if mode == 0:
        literal_copy(src, dst, size)
    else:
        reader = Reader(src)
        for _ in range(size//32):
            dst.write(struct.pack("<16H", *decode_node(reader, 16, 16, counts)))
        tail = size % 32
        dst.write(reader.get(8*tail).to_bytes(tail, "big"))
        if reader.value:
            raise ValueError("Nonzero padding")
    if src.read(1):
        raise ValueError("Trailing bytes")
    return dict(byte=size, nodes=counts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    enc = sub.add_parser("pack")
    enc.add_argument("--profile", choices=PROFILES, default="full")
    enc.add_argument("--steps", type=int, choices=range(101), metavar="0..100", default=100)
    enc.add_argument("--depth", type=int, choices=range(16), metavar="0..15", default=3)
    enc.add_argument("--beam", type=int, choices=range(1, 101), metavar="1..100", default=2)
    for parser in (enc, sub.add_parser("unpack")):
        parser.add_argument("input", type=Path)
        parser.add_argument("output", type=Path)
    a = p.parse_args()
    if a.input.resolve() == a.output.resolve():
        p.error("Source and destination must differ")
    with a.input.open("rb") as src, tempfile.NamedTemporaryFile(dir=a.output.parent, delete=False) as dst:
        try:
            result = (pack(src, dst, a.profile, a.steps, a.depth, a.beam) if a.cmd == "pack"
                      else unpack(src, dst))
            dst.close()
            os.replace(dst.name, a.output)
        finally:
            Path(dst.name).unlink(missing_ok=True)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
