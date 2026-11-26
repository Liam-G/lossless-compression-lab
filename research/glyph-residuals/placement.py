"""Encode learned per-shape baselines, exact line membership and horizontal positioning."""

from collections import Counter, defaultdict
from itertools import groupby
import lzma
import struct
import zstandard as zstd
from wire import Reader, var, zig, signed


def baseline_offsets(events, bank):
    histogram = Counter(y + bank[i][1] for _, y, i in events)
    votes = [Counter() for _ in bank]
    # Vote for nearby strong text baselines. A distance penalty resolves dense tables.
    for _, y, i in events:
        bottom = y + bank[i][1]
        reach = min(9, bank[i][1] // 2)
        best = max(
            range(-reach, reach + 1),
            key=lambda d: (5 * histogram[bottom + d] - abs(d), -abs(d)),
        )
        votes[i][best] += 1
    return [v.most_common(1)[0][0] if v else 0 for v in votes]


def symbol(cache, previous, actual, reverse):
    recent = cache[previous]
    if reverse:
        token = recent[actual] if actual < len(recent) else actual - 4
    else:
        token = actual
    encoded = recent.index(token) if token in recent else token + 4
    if reverse and actual != encoded:
        raise ValueError("Invalid symbol prediction")
    if token in recent:
        recent.remove(token)
    recent.insert(0, token)
    del recent[4:]
    return token if reverse else encoded


def encode(events, bank):
    dic = var(len(bank)) + b"".join(bytes([w, h]) + pattern for w, h, pattern in bank)
    learned = baseline_offsets(events, bank)
    coder = zstd.ZstdCompressor(level=15)
    finalists = []
    for offsets in ([0] * len(bank), learned):
        lines = sorted((y + bank[i][1] + offsets[i], x, i) for x, y, i in events)
        wire_y = bytearray()
        ids = [bytearray(), bytearray()]
        gaps = [bytearray(), bytearray()]
        previous_line = 0
        previous_first = 0
        prediction = {}
        cache = defaultdict(list)
        for baseline, line in groupby(lines, key=lambda v: v[0]):
            line = list(line)
            wire_y.extend(var(baseline - previous_line) + var(len(line)))
            previous_line = baseline
            previous = -1
            end = 0
            for _, x, i in line:
                gap = x - end
                key = (previous, i)
                estimate = prediction.get(key, 0) if previous != -1 else previous_first
                ids[0].extend(var(i))
                ids[1].extend(var(symbol(cache, previous, i, False)))
                gaps[0].extend(var(zig(gap)))
                gaps[1].extend(var(zig(gap - estimate)))
                prediction[key] = gap
                if previous == -1:
                    previous_first = gap
                previous = i
                end = x + bank[i][0]
        # Price the four possible combinations with the same compressor.
        prefix = dic + b"".join(var(zig(offset)) for offset in offsets)
        for use_cache, id_stream in enumerate(ids):
            for use_prediction, gap_stream in enumerate(gaps):
                header = struct.pack(
                    ">BIII",
                    2 * use_cache + use_prediction,
                    len(wire_y),
                    len(id_stream),
                    len(gap_stream),
                )
                payload = prefix + header + wire_y + id_stream + gap_stream
                finalists.append((len(coder.compress(payload)), payload))
    size, payload = min(finalists, key=lambda item: item[0])
    z = coder.compress(payload)
    x = lzma.compress(payload, preset=6)
    return min((b"Z" + z, b"X" + x), key=len)


def decode(side):
    if side[:1] == b"Z":
        data = zstd.ZstdDecompressor().decompress(side[1:])
    elif side[:1] == b"X":
        data = lzma.decompress(side[1:])
    else:
        raise ValueError("Unknown placement compression")
    source = Reader(data)
    count = source.var()
    if count > 4096:
        raise ValueError("Oversized dictionary")
    bank = []
    for _ in range(count):
        w, h = source.byte(), source.byte()
        if not (2 <= w <= 64 and 3 <= h <= 72):
            raise ValueError("Invalid glyph dimensions")
        bank.append((w, h, source.take((w * h + 7) // 8)))
    shifts = [signed(source.var()) for _ in bank]
    flags, ny, ni, nx = struct.unpack(">BIII", source.take(13))
    if flags > 3:
        raise ValueError("Unknown glyph positioning rule")
    lines = Reader(source.take(ny))
    ids = Reader(source.take(ni))
    gaps = Reader(source.take(nx))
    source.end()
    events = []
    y = 0
    previous_first = 0
    cache = defaultdict(list)
    pred = {}
    while lines.tell() < ny:
        y += lines.var()
        n = lines.var()
        if not n:
            raise ValueError("Empty glyph line")
        previous = -1
        end = 0
        for _ in range(n):
            val = ids.var()
            i = symbol(cache, previous, val, True) if flags & 2 else val
            if not 0 <= i < count:
                raise ValueError("Missing glyph")
            key = (previous, i)
            estimate = pred.get(key, 0) if previous != -1 else previous_first
            gap = signed(gaps.var()) + (estimate if flags & 1 else 0)
            x = end + gap
            events.append((x, y - bank[i][1] - shifts[i], i))
            pred[key] = gap
            if previous == -1:
                previous_first = gap
            previous = i
            end = x + bank[i][0]
    ids.end()
    gaps.end()
    return events, bank
