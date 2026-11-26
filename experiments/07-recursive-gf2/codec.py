"""Recursive GF(2) factors with reversible transformations before or after splitting."""

from collections import Counter
from functools import cache
from math import comb
from io import BytesIO
import struct

ID = 7
PROFILES = ("post-1", "pre-1", "post-3", "pre-3")
CONTRASTS = [("combined_gain", "pre-1", "post-3", "pre-3")]


@cache
def width(n, k):
    return (comb(n, k) - 1).bit_length()


def subset(mask):
    """Colexicographic subset rank."""
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
        raise ValueError("Invalid subset index")
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
    return sum(row << (i * w) for i, row in enumerate(rows))


def split_rows(value, h, w):
    mask = (1 << w) - 1
    return tuple((value >> (i * w)) & mask for i in range(h))


def join(*fields):
    length = value = 0
    for size, field in fields:
        value = (value << size) | field
        length += size
    return length, value


def step(rows, w, reverse=False):
    """Checkerboard phases with column zero in the low bit."""
    h = len(rows)
    rows = list(rows)
    for phase in (1, 0) if reverse else (0, 1):
        for y in range(h):
            up = rows[y - 1] if y or h % 2 == 0 else 0
            down = rows[(y + 1) % h] if y + 1 < h or h % 2 == 0 else 0
            x = rows[y]
            left, right = x << 1, x >> 1
            if w % 2 == 0:
                left |= x >> (w - 1)
                right |= (x & 1) << (w - 1)
            color = 0xAAAA if phase ^ (y & 1) else 0x5555
            rows[y] ^= ((left & right) ^ (up | down)) & color & ((1 << w) - 1)
    return tuple(rows)


def factor(rows, w):
    """Return independent row indices, coordinates and two basis partitions."""
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
    return (
        r,
        indices,
        (
            (tuple(coeffs), r),
            (tuple(x & mask for x in selected), r),
            (tuple(x >> r for x in selected), w - r),
        ),
    )


def encode_block(original, profile, steps, depth, beam):
    use_factors = profile in ("factor-one", "factor", "post", "pre")
    use_ca = profile in ("automaton", "post", "pre") and steps > 0

    @cache
    def solve(rows, w, levels):
        h = len(rows)
        n = w * h
        value = flatten(rows, w)
        can_factor = use_factors and levels > 0 and min(h, w) >= 2
        pre = profile == "pre" and can_factor and use_ca
        weight = value.bit_count()
        best = (1 + n, value)  # prefix 0
        enum_len = 3 + n.bit_length() + width(n, weight)
        if enum_len < best[0]:
            best = join((3, 4), (n.bit_length(), weight), (width(n, weight), subset(value)))
        candidates = [(0, rows)]
        if use_ca:
            states = [rows]
            for _ in range(steps):
                previous = step(states[-1], w, reverse=True)
                if previous == rows:
                    break
                states.append(previous)
            count = len(states)
            short = []
            best_cost, leaf = best[0], None
            for t in range(1, count):
                state = states[t]
                weight = sum(row.bit_count() for row in state)
                cost = 3 + 7 + n.bit_length() + width(n, weight)
                if cost < best_cost:
                    best_cost, leaf = cost, t
                rank = factor(state, w)[0] if pre else 0
                if 0 < rank < min(h, w):
                    short.append((rank, min(weight, n - weight), t))
            if leaf is not None:
                state = states[leaf]
                weight = sum(row.bit_count() for row in state)
                value = flatten(state, w)
                best = join(
                    (3, 5), (7, leaf), (n.bit_length(), weight), (width(n, weight), subset(value))
                )
            candidates.extend((t, states[t]) for _, _, t in sorted(short)[:beam])
        if can_factor:
            for t, matrix in candidates:
                rank, indices, parts = factor(matrix, w)
                if not 0 < rank < min(h, w):
                    continue
                prefix = [(3, 7 if t else 6)]
                if t:
                    prefix.append((7, t))
                prefix.extend(
                    [((min(h, w) - 1).bit_length(), rank - 1), (width(h, rank), subset(indices))]
                )
                children = [solve(part, cols, levels - 1) for part, cols in parts]
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
            self.put(8 - self.bits, 0)


class Reader:
    def __init__(self, stream):
        self.stream, self.bits, self.value = stream, 0, 0

    def get(self, size):
        if size > self.bits:
            count = (size - self.bits + 7) // 8
            chunk = self.stream.read(count)
            if len(chunk) != count:
                raise ValueError("Truncated input")
            self.value = (self.value << (8 * count)) | int.from_bytes(chunk, "big")
            self.bits += count * 8
        self.bits -= size
        result = self.value >> self.bits
        self.value &= (1 << self.bits) - 1
        return result


def decode_node(reader, h, w, stats, depth=0):
    n = h * w
    if not reader.get(1):
        stats[f"literal@{depth}"] += 1
        return split_rows(reader.get(n), h, w)
    factor_mode, ca = reader.get(1), reader.get(1)
    t = reader.get(7) if ca else 0
    if ca and not 1 <= t <= 100:
        raise ValueError("Invalid step")
    label = "factor" if factor_mode else "enumerative"
    stats[f"{label}{'+CA' if ca else ''}@{depth}"] += 1
    if factor_mode:
        r = 1 + reader.get((min(h, w) - 1).bit_length())
        if not r < min(h, w):
            raise ValueError("Invalid rank")
        indices = unsubset(h, r, reader.get(width(h, r)))
        coeffs = iter(decode_node(reader, h - r, r, stats, depth + 1))
        low = decode_node(reader, r, r, stats, depth + 1)
        high = decode_node(reader, r, w - r, stats, depth + 1)
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


def pack(data, profile, ref, stats):
    placement, depth = profile.split("-")
    stream = BytesIO()
    writer = Writer(stream)
    for i in range(0, len(data) - 31, 32):
        rows = struct.unpack_from("<16H", data, i)
        writer.put(*encode_block(rows, placement, 4, int(depth), 2))
    writer.finish()
    tail = len(data) // 32 * 32
    payload = stream.getvalue() + data[tail:]
    if len(payload) >= len(data):
        return bytes([0]), data
    return bytes([1]), payload


def unpack(size, profile, meta, body, ref, stats):
    if meta.byte() == 0:
        stats["paths"] = {"literal-file": 1}
        return body.take(size)
    reader = Reader(body)
    counts = Counter()
    out = bytearray()
    for _ in range(size // 32):
        out.extend(struct.pack("<16H", *decode_node(reader, 16, 16, counts)))
    if reader.value:
        raise ValueError("Invalid padding")
    stats["paths"] = dict(counts)
    return out + body.take(size % 32)
