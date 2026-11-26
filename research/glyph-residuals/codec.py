"""Transmit repeated bitmap components, their positions, and an exact residual raster."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
from scipy import ndimage
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from wire import Reader, var, zig, signed
import placement

HEADER = struct.Struct(">4sIIBII")
PROFILES = ("direct", "jbig", "glyphs", "fuzzy", "joint", "position")
RAW, ZSTD, JBIG, EXACT_Z, EXACT_J, FUZZY_Z, FUZZY_J = range(7)
POSITION_Z, POSITION_J = 7, 8
STRIPE = 512
BUDGET = 4096


def components(bitmap):
    h, w = bitmap.shape
    for y0 in range(0, h, STRIPE):
        slab = np.unpackbits(bitmap[y0 : y0 + STRIPE], axis=1)
        label, _ = ndimage.label(slab, np.ones((3, 3), np.uint8))
        for tag, box in enumerate(ndimage.find_objects(label), 1):
            ys, xs = box
            height, width = ys.stop - ys.start, xs.stop - xs.start
            if not (2 <= width <= 64 and 3 <= height <= 72):
                continue
            stamp = label[box] == tag
            if stamp.sum() < 8:
                continue
            yield (width, height, np.packbits(stamp).tobytes()), xs.start, y0 + ys.start


def jbig(data, w, h, reverse=False):
    with TemporaryDirectory() as directory:
        pbm = Path(directory) / "bitmap.pbm"
        packed = Path(directory) / "raster.jbg"
        if reverse:
            packed.write_bytes(data)
            subprocess.run(
                ["jbgtopbm", packed, pbm], check=True, stdout=subprocess.DEVNULL
            )
            from PIL import Image

            Image.MAX_IMAGE_PIXELS = 400_000_000
            with Image.open(pbm) as im:
                if im.size != (w, h) or im.mode != "1":
                    raise ValueError("Incorrect JBIG geometry")
                return im.tobytes("raw", "1;I")
        with pbm.open("wb") as f:
            f.write(f"P4\n{w} {h}\n".encode())
            f.write(data)
        subprocess.run(
            ["pbmtojbg", "-q", pbm, packed], check=True, stdout=subprocess.DEVNULL
        )
        return packed.read_bytes()


def texture(key):
    w, h, data = key
    return np.unpackbits(np.frombuffer(data, np.uint8), count=w * h).reshape(h, w)


def apply(bitmap, events, bank):
    result = bitmap.copy()
    # Each bounding box lies wholly in one encoder stripe. Decode in stripes to
    # keep unpacked memory bounded, even when events were coded in baseline order.
    groups = defaultdict(list)
    for x, y, s in events:
        groups[y // STRIPE].append((x, y, s))
    glyphs = [texture(key) for key in bank]
    for stripe, entries in groups.items():
        y0 = stripe * STRIPE
        dst = result[y0 : y0 + STRIPE]
        field = np.unpackbits(dst, axis=1)
        for x, y, s in entries:
            g = glyphs[s]
            h, w = g.shape
            local = y - y0
            if min(x, local) < 0 or local + h > len(field) or x + w > field.shape[1]:
                raise ValueError("Glyph leaves its stripe")
            field[local : local + h, x : x + w] ^= g
        dst[:] = np.packbits(field, axis=1)
    return result.tobytes()


def dictionary(events):
    freq = Counter(k for k, _, _ in events)
    return [k for k, n in freq.most_common() if n >= 3 and (n - 1) * len(k[2]) > 4 * n][
        :BUDGET
    ]


def classify(events, bank, fuzzy):
    ids = {key: i for i, key in enumerate(bank)}
    by_size = defaultdict(list)
    for i, (w, h, pattern) in enumerate(bank):
        if len(by_size[w, h]) < 24:
            by_size[w, h].append((int.from_bytes(pattern), i))
    out = []
    for key, x, y in events:
        i = ids.get(key)
        if i is None and fuzzy:
            w, h, pattern = key
            options = by_size.get((w, h), ())
            if options:
                value = int.from_bytes(pattern)
                err, nearest = min(((value ^ v).bit_count(), idx) for v, idx in options)
                if err <= max(1, value.bit_count() // 12):
                    i = nearest
        if i is not None:
            out.append((x, y, i))
    return out


def event_bytes(events, bank, bottom):
    ordered = sorted(events, key=lambda e: (e[1] + bottom * bank[e[2]][1], e[0], e[2]))
    ids = bytearray()
    dx = bytearray()
    dy = bytearray()
    previous_y = previous_end = 0
    for x, y, i in ordered:
        w, h, _ = bank[i]
        key = y + bottom * h
        dy.extend(var(key - previous_y))
        dx.extend(var(zig(x - (previous_end if key == previous_y else 0))))
        ids.extend(var(i))
        previous_y, previous_end = key, x + w
    return (
        bytes([bottom])
        + var(len(ordered))
        + var(len(ids))
        + var(len(dx))
        + ids
        + dx
        + dy
    )


def metadata(events, bank, coder):
    dic = var(len(bank)) + b"".join(bytes([w, h]) + pattern for w, h, pattern in bank)
    return min(
        (coder.compress(dic + event_bytes(events, bank, align)) for align in (0, 1)),
        key=len,
    )


def read_metadata(data):
    stream = Reader(data)
    count = stream.var()
    if count > BUDGET:
        raise ValueError("Dictionary exceeds budget")
    bank = []
    for _ in range(count):
        w, h = stream.byte(), stream.byte()
        if not (2 <= w <= 64 and 3 <= h <= 72):
            raise ValueError("Invalid glyph")
        bank.append((w, h, stream.take((w * h + 7) // 8)))
    bottom = stream.byte()
    if bottom > 1:
        raise ValueError("Invalid scan order")
    n, ni, nx = stream.var(), stream.var(), stream.var()
    ids = Reader(stream.take(ni))
    dx = Reader(stream.take(nx))
    events = []
    key = last = 0
    for _ in range(n):
        token = ids.var()
        if token >= count:
            raise ValueError("Missing glyph")
        step = stream.var()
        x = (0 if step else last) + signed(dx.var())
        key += step
        w, h, _ = bank[token]
        events.append((x, key - bottom * h, token))
        last = x + w
    ids.end()
    dx.end()
    stream.end()
    return events, bank


def encode(raw, w, profile):
    if w < 8 or w % 8 or len(raw) % (w // 8):
        raise ValueError("Expected complete packed rows")
    h = len(raw) // (w // 8)
    bitmap = np.frombuffer(raw, np.uint8).reshape(h, w // 8)
    coder = zstd.ZstdCompressor(level=9)
    best = (len(raw), RAW, b"", raw, {})

    def offer(mode, side, body, stats):
        nonlocal best
        size = len(side) + len(body)
        if size < best[0]:
            best = (size, mode, side, body, stats)

    offer(ZSTD, b"", coder.compress(raw), {})
    if h and profile in ("jbig", "joint", "position"):
        offer(JBIG, b"", jbig(raw, w, h), {})
    if profile in ("glyphs", "fuzzy", "joint", "position"):
        entries = list(components(bitmap))
        bank = dictionary(entries)
        for fuzzy in (
            (False, True) if profile in ("fuzzy", "joint", "position") else (False,)
        ):
            events = classify(entries, bank, fuzzy)
            if not events:
                continue
            diff = apply(bitmap, events, bank)
            side = metadata(events, bank, coder)
            stats = dict(
                dictionary=len(bank), placements=len(events), side_bytes=len(side)
            )
            offer(FUZZY_Z if fuzzy else EXACT_Z, side, coder.compress(diff), stats)
            if profile in ("joint", "position"):
                raster = jbig(diff, w, h)
                offer(FUZZY_J if fuzzy else EXACT_J, side, raster, stats)
                if profile == "position":
                    positional = placement.encode(events, bank)
                    adjusted = dict(stats, side_bytes=len(positional), fuzzy=fuzzy)
                    offer(POSITION_J, positional, raster, adjusted)
                    offer(POSITION_Z, positional, coder.compress(diff), adjusted)
    _, mode, side, body, stats = best
    return HEADER.pack(b"GLR1", w, h, mode, len(side), len(body)) + side + body, dict(
        mode=mode, **stats
    )


def decode(data):
    w0, w, h, mode, ns, nb = HEADER.unpack_from(data)
    if (
        w0 != b"GLR1"
        or not w
        or w % 8
        or mode > POSITION_J
        or len(data) != HEADER.size + ns + nb
    ):
        raise ValueError("Invalid glyph archive")
    side = data[HEADER.size : HEADER.size + ns]
    body = data[HEADER.size + ns :]
    size = w // 8 * h
    if mode == RAW:
        plane = body
    elif mode in (JBIG, EXACT_J, FUZZY_J, POSITION_J):
        plane = jbig(body, w, h, True)
    else:
        plane = zstd.ZstdDecompressor().decompress(body, max_output_size=size)
    if len(plane) != size:
        raise ValueError("Unexpected raster length")
    if mode >= EXACT_Z:
        events, bank = (
            placement.decode(side)
            if mode in (POSITION_J, POSITION_Z)
            else read_metadata(zstd.ZstdDecompressor().decompress(side))
        )
        plane = apply(np.frombuffer(plane, np.uint8).reshape(h, w // 8), events, bank)
    elif ns:
        raise ValueError("Unexpected dictionary")
    return plane


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--width", type=int, default=1728)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.output.open("xb") as out:
        if a.mode == "encode":
            data, stats = encode(a.source.read_bytes(), a.width, a.profile)
            out.write(data)
            print(json.dumps(stats))
        else:
            out.write(decode(a.source.read_bytes()))
