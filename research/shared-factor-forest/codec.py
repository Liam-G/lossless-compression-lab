"""Share a factor/split across words and encode recurring exact formula leaves once."""

import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import struct
import sys

import zstandard as zstd

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH / "whiteboard-trees"))
import factor_forest as forest
from tree import read_varint, varint, unit

HEADER = struct.Struct(">4sQ")
RECORD = struct.Struct(">BBBI")
BLOCK = 1 << 18
PRIMES = (1, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)
OFFSET = (0, 1, -1)
PROFILES = ("direct", "factor", "formula", "inline", "shared")
STORED, ZSTD, SPLIT, INLINE, SHARED = range(5)
ESCAPE = 255


def take(f, length):
    result = f.read(length)
    if len(result) != length:
        raise ValueError("Truncated record")
    return result


def components(value, width, prime):
    qbits = width if prime == 1 else (((1 << width) // prime).bit_length())
    low = qbits // 2
    for j, d in enumerate(OFFSET if prime != 1 else (0,)):
        q, r = divmod(value + d, prime)
        if q >= 0 and not r:
            return j, q >> low, q & ((1 << low) - 1)
    return None


def candidate_score(samples, width, prime, catalog):
    seen = hits = 0
    for value in samples:
        result = components(value, width, prime)
        if result is not None:
            seen += 1
            if catalog:
                hits += sum(v in catalog for v in result[1:])
    return hits, seen


def proposals(data, profile, catalog):
    for width in (16, 32, 64):
        total = len(data) // width
        if not total:
            continue
        indexes = sorted({j * (total - 1) // 31 for j in range(32)})
        samples = [
            int.from_bytes(data[i * width : (i + 1) * width], "big") for i in indexes
        ]
        scores = []
        for p in PRIMES:
            hits, seen = candidate_score(samples, 8 * width, p, catalog)
            if p == 1 or seen == len(samples) or hits >= max(2, len(samples) // 8):
                scores.append((hits, seen, -p))
        if profile == "formula":
            yield width, 1
        else:
            for _, _, neg in sorted(scores, reverse=True)[:2]:
                yield width, -neg


def decode_formula(wire):
    f = BytesIO(wire)
    tag, base, digit = take(f, 3)
    n = read_varint(f)
    db, dr = take(f, 2)
    if tag != forest.FORMULA or not (
        2 <= base <= 16 and 1 <= digit < base and 3 <= n <= 516
    ):
        raise ValueError("Invalid formula")
    if (db, dr) != (0, 0) and not (2 <= db <= 10 and 3 <= dr <= 12):
        raise ValueError("Invalid divisor")
    value, r = divmod(digit * unit(base, n), unit(db, dr) if db else 1)
    if r or f.read(1):
        raise ValueError("Invalid arithmetic leaf")
    return value


def transformed(block, width, prime, mode, catalog):
    n = len(block) // width
    qbits = 8 * width if prime == 1 else (((1 << (8 * width)) // prime).bit_length())
    low = qbits // 2
    lengths = ((qbits - low + 7) // 8, (low + 7) // 8)
    tags, refs = bytearray(), bytearray()
    literals = [bytearray(), bytearray()]
    escapes = bytearray()
    definitions = {}
    for pos in range(0, n * width, width):
        word = block[pos : pos + width]
        result = components(int.from_bytes(word, "big"), 8 * width, prime)
        if result is None:
            tags.append(ESCAPE)
            escapes.extend(word)
            continue
        correction, left, right = result
        mask = 0
        for i, value in enumerate((left, right)):
            wire = catalog.get(value)
            if wire:
                mask |= 1 << i
                if mode == SHARED:
                    idx = definitions.setdefault(wire, len(definitions))
                    refs.extend(varint(idx))
                else:
                    refs.extend(bytes([len(wire)]) + wire)
            else:
                literals[i].extend(value.to_bytes(lengths[i], "big"))
        tags.append(4 * correction + mask)
    book = b"".join(bytes([len(w)]) + w for w in definitions)
    head = varint(len(definitions)) + book + varint(len(refs))
    return b"".join((head, tags, refs, *literals, escapes, block[n * width :]))


def inverse(raw, size, width, prime, mode):
    f = BytesIO(raw)
    n = size // width
    qbits = 8 * width if prime == 1 else (((1 << (8 * width)) // prime).bit_length())
    low = qbits // 2
    lengths = ((qbits - low + 7) // 8, (low + 7) // 8)
    count = read_varint(f)
    if count > 2 * n or (mode != SHARED and count):
        raise ValueError("Invalid formula dictionary size")
    book = [decode_formula(take(f, take(f, 1)[0])) for _ in range(count)]
    refsize = read_varint(f)
    tags = take(f, n)
    refs = BytesIO(take(f, refsize))
    sizes = [
        sum(t != ESCAPE and not (t & (1 << i)) for t in tags) * lengths[i]
        for i in range(2)
    ]
    lanes = [BytesIO(take(f, k)) for k in sizes]
    out = bytearray()
    for tag in tags:
        if tag == ESCAPE:
            out.extend(take(f, width))
            continue
        correction, mask = divmod(tag, 4)
        if correction >= 3 or (prime == 1 and correction) or (mode == SPLIT and mask):
            raise ValueError("Invalid factor record")
        parts = []
        for i in range(2):
            if mask & (1 << i):
                if mode == SHARED:
                    idx = read_varint(refs)
                    if idx >= len(book):
                        raise ValueError("Invalid formula reference")
                    value = book[idx]
                else:
                    value = decode_formula(take(refs, take(refs, 1)[0]))
            else:
                value = int.from_bytes(take(lanes[i], lengths[i]), "big")
            if value.bit_length() > (low if i else qbits - low):
                raise ValueError("Factor child exceeds width")
            parts.append(value)
        value = prime * ((parts[0] << low) + parts[1]) - OFFSET[correction]
        out.extend(value.to_bytes(width, "big"))
    out.extend(take(f, size - len(out)))
    if f.read(1) or refs.read(1):
        raise ValueError("Trailing factor data")
    return out


def pack(src, dest, profile):
    dest.write(HEADER.pack(b"SFF1", src.seek(0, 2)))
    src.seek(0)
    coder = zstd.ZstdCompressor(level=3)
    catalog = forest.book() if profile not in ("direct", "factor") else {}
    hist = Counter()
    while data := src.read(BLOCK):
        options = [(len(data), STORED, 0, 0, data)]

        def offer(kind, w, p, payload):
            opts = (len(payload), kind, w, p, payload)
            if opts[:4] < options[0][:4]:
                options[0] = opts

        offer(ZSTD, 0, 0, coder.compress(data))
        if profile != "direct":
            for w, p in proposals(data, profile, catalog):
                modes = [SPLIT]
                if profile in ("formula", "inline", "shared"):
                    modes.append(INLINE)
                if profile == "shared":
                    modes.append(SHARED)
                for mode in modes:
                    transformed_bytes = transformed(
                        data, w, p, mode, catalog if mode != SPLIT else {}
                    )
                    offer(mode, w, p, coder.compress(transformed_bytes))
        length, mode, w, p, payload = options[0]
        hist[f"{mode}/{w}/{p}"] += 1
        dest.write(RECORD.pack(mode, w, p, length))
        dest.write(payload)
    return hist


def unpack(src, dest):
    magic, left = HEADER.unpack(take(src, HEADER.size))
    if magic != b"SFF1":
        raise ValueError("Invalid shared forest header")
    decoder = zstd.ZstdDecompressor()
    while left:
        size = min(BLOCK, left)
        mode, w, p, length = RECORD.unpack(take(src, RECORD.size))
        if length > size:
            raise ValueError("Invalid payload length")
        payload = take(src, length)
        if mode == STORED:
            block = payload
        elif mode == ZSTD:
            block = decoder.decompress(payload, max_output_size=size)
        elif mode in (SPLIT, INLINE, SHARED) and w in (16, 32, 64) and p in PRIMES:
            block = inverse(
                decoder.decompress(payload, max_output_size=4 * size + 1024),
                size,
                w,
                p,
                mode,
            )
        else:
            raise ValueError("Invalid mode")
        if len(block) != size:
            raise ValueError("Invalid output length")
        dest.write(block)
        left -= size
    if src.read(1):
        raise ValueError("Trailing file data")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("op", choices=("encode", "decode"))
    cli.add_argument("source", type=Path)
    cli.add_argument("dest", type=Path)
    cli.add_argument("--profile", choices=PROFILES, default="shared")
    a = cli.parse_args()
    with a.source.open("rb") as src, a.dest.open("xb") as dest:
        if a.op == "encode":
            print(json.dumps(pack(src, dest, a.profile)))
        else:
            unpack(src, dest)
