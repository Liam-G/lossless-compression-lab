"""Expose sparse compressible spans with a single full-width arithmetic change of variables."""

import argparse
from bisect import bisect_right
import json
import lzma
from pathlib import Path
from io import BytesIO

import numpy as np
import zstandard as zstd
from arithmetic import transform
from sparse_reader import HEADER, RECORD, SCALES, ZSTD, NIBBLES, XZ, decode

PAGE = 8192
PROFILES = ("direct", "scale", "regions", "joint", "informed")


def nibble_lanes(data, reverse=False):
    a = np.frombuffer(data, np.uint8)
    n = len(a) // 2
    result = np.empty_like(a)
    if reverse:
        hi, lo = a[:n], a[n : 2 * n]
        result[: 2 * n : 2] = (hi & 240) | (lo >> 4)
        result[1 : 2 * n : 2] = (hi << 4) | (lo & 15)
    else:
        left, right = a[: 2 * n : 2], a[1 : 2 * n : 2]
        result[:n] = (left & 240) | (right >> 4)
        result[n : 2 * n] = ((left & 15) << 4) | (right & 15)
    if len(a) % 2:
        result[-1] = a[-1]
    return result.tobytes()


def representation(data, op):
    scale, inv = op
    return data if scale == 1 else transform(data, scale, inv)


def scales(data, profile):
    yield (1, False)
    if profile in ("direct", "regions") or not data:
        return
    ops = [(s, inv) for s in SCALES[1:] for inv in (False, True)]
    w = min(len(data), 32768)
    starts = {0, len(data) - w}
    starts.update(range(0, min(len(data) - w, 4 << 20), 262144))
    starts.update(int((len(data) - w) * j / 12) for j in range(1, 12))
    # Score snippets only. A full-width map preserves carries across every boundary.
    coder = zstd.ZstdCompressor(level=1)

    def proxy(op):
        cost = 0
        for start in starts:
            piece = representation(data[start : start + w], op)
            cost += min(
                len(piece),
                len(coder.compress(piece)),
                len(coder.compress(nibble_lanes(piece))),
            )
        return cost

    winner = sorted(ops, key=proxy)[:2]
    if profile == "informed" and (12, False) not in winner:
        winner.append((12, False))
    yield from winner


def intervals(data, coder):
    size = len(data)
    # One pilot compression per page suppresses expensive work over near-uniform runs.
    candidates = []
    interesting = []
    for off in range(0, size, PAGE):
        raw = data[off : off + PAGE]
        priced = min(len(coder.compress(raw)), len(coder.compress(nibble_lanes(raw))))
        interesting.append(priced + RECORD.size < len(raw))
    positions = set()
    for j, hit in enumerate(interesting):
        if hit:
            for span in (1, 4, 16, 64):
                start = j // span * span * PAGE
                positions.add((start, min(size, start + PAGE * span)))
    for end in (128, 256, 512, 1024, 2048, 4096, PAGE, 2 * PAGE):
        if end <= size:
            positions.add((0, end))
    for off, end in sorted(positions):
        raw = data[off:end]
        contenders = [
            (ZSTD, coder.compress(raw)),
            (NIBBLES, coder.compress(nibble_lanes(raw))),
            (XZ, lzma.compress(raw, preset=3)),
        ]
        kind, body = min(contenders, key=lambda p: len(p[1]))
        gain = len(raw) - len(body) - RECORD.size
        if gain > 0:
            candidates.append((end, off, kind, body, gain))
    # Weighted interval scheduling with actual records as edge prices.
    candidates.sort(key=lambda x: (x[0], x[1]))
    ends = [x[0] for x in candidates]
    gain = [0]
    back = []
    for i, (_, off, _, _, saving) in enumerate(candidates):
        pred = bisect_right(ends, off, 0, i)
        take = gain[pred] + saving
        if take > gain[-1]:
            back.append(pred)
            gain.append(take)
        else:
            back.append(None)
            gain.append(gain[-1])
    chosen = []
    i = len(candidates)
    while i:
        pred = back[i - 1]
        if pred is None:
            i -= 1
        else:
            chosen.append(candidates[i - 1])
            i = pred
    return list(reversed(chosen))


def encode(data, profile):
    coder = zstd.ZstdCompressor(level=9)
    best_cost = len(data)
    selected = (1, False, data, [])
    for scale, inv in scales(data, profile):
        transformed = representation(data, (scale, inv))
        # A global compressed frame is an independent baseline in every profile.
        body = coder.compress(transformed)
        if len(body) + RECORD.size < best_cost:
            selected = (scale, inv, transformed, [(len(data), 0, ZSTD, body, 0)])
            best_cost = len(body) + RECORD.size
        if profile in ("regions", "joint", "informed"):
            regions = intervals(transformed, coder)
            cost = len(data) - sum(r[4] for r in regions)
            if cost < best_cost:
                selected = scale, inv, transformed, regions
                best_cost = cost
    scale, inv, stream, records = selected
    out = BytesIO()
    out.write(HEADER.pack(b"SCL1", len(data), SCALES.index(scale), inv, len(records)))
    end = 0
    for until, off, kind, body, _ in records:
        out.write(RECORD.pack(off, until - off, kind, len(body)))
        out.write(stream[end:off])
        out.write(body)
        end = until
    out.write(stream[end:])
    if out.tell() != HEADER.size + best_cost:
        raise RuntimeError("Interval accounting mismatch")
    return out.getvalue(), dict(
        factor=scale,
        inverse=inv,
        records=len(records),
        coded_input_bytes=sum(e - o for e, o, *_ in records),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.destination.open("xb") as dst:
        if a.action == "encode":
            archive, stats = encode(a.source.read_bytes(), a.profile)
            dst.write(archive)
            print(json.dumps(stats))
        else:
            dst.write(decode(a.source.read_bytes()))
