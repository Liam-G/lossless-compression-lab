"""Price text tokenization, cyclic-context sorting and move-to-front in bytes."""

import argparse
from collections import Counter
import ctypes as ct
from pathlib import Path
import json
import struct
import zstandard as zstd
import textfront

LIB = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/text-views.so"))
U8 = ct.POINTER(ct.c_ubyte)
I32 = ct.POINTER(ct.c_int32)
LIB.libsais_bwt.argtypes = [U8, U8, I32, ct.c_int32, ct.c_int32, I32]
LIB.libsais_unbwt.argtypes = [U8, U8, I32, ct.c_int32, I32, ct.c_int32]
LIB.move_front.argtypes = [U8, ct.c_size_t, ct.c_int]
LIB.move_front.restype = None
BLOCK = 2 << 20
RECORD = struct.Struct(">BBI")
TEXT = (
    (),
    ("caps",),
    ("words",),
    ("split",),
    ("caps", "words"),
    ("split", "caps", "words"),
)
PROFILES = ("direct", "text", "bwt", "mtf", "joint")


def sort_context(data, inverse=False):
    if inverse:
        if len(data) < 4:
            raise ValueError("Missing primary index")
        (primary,) = struct.unpack_from(">I", data)
        data = data[4:]
    n = len(data)
    buf = (ct.c_ubyte * n).from_buffer_copy(data)
    out = (ct.c_ubyte * n)()
    work = (ct.c_int32 * (n + 1))()
    if inverse:
        status = LIB.libsais_unbwt(buf, out, work, n, None, primary)
        if status < 0:
            raise ValueError("Invalid BWT index")
        return bytes(out)
    primary = LIB.libsais_bwt(buf, out, work, n, 0, None)
    if primary < 0:
        raise ValueError("BWT construction failed")
    return struct.pack(">I", primary) + bytes(out)


def mtf(data, inverse=False):
    buf = (ct.c_ubyte * len(data)).from_buffer_copy(data)
    LIB.move_front(buf, len(data), inverse)
    return bytes(buf)


def representations(block, profile):
    for text_mode, pieces in enumerate(TEXT):
        if text_mode and profile not in ("text", "joint"):
            break
        if pieces:
            try:
                base = textfront.encode(block, pieces)
            except ValueError:
                continue
            if textfront.decode(base) != block:
                continue
        else:
            base = block
        yield text_mode, 0, base
        if profile in ("bwt", "mtf", "joint"):
            sorted_bytes = sort_context(base)
            yield text_mode, 1, sorted_bytes
            if profile in ("mtf", "joint"):
                yield text_mode, 2, mtf(sorted_bytes)


def encode(source, out, profile):
    size = source.seek(0, 2)
    source.seek(0)
    out.write(struct.pack(">4sQ", b"TVW1", size))
    coder = zstd.ZstdCompressor(level=3)
    counts = Counter()
    while block := source.read(BLOCK):
        best = (len(block), 0, 3, block)
        for text_mode, view, trial in representations(block, profile):
            compressed = coder.compress(trial)
            if len(compressed) < best[0]:
                best = (len(compressed), text_mode, view, compressed)
        length, text_mode, view, payload = best
        out.write(RECORD.pack(text_mode, view, length))
        out.write(payload)
        counts[f"{text_mode}/{view}"] += 1
    return counts


def decode(source, out):
    magic, remain = struct.unpack(">4sQ", source.read(12))
    if magic != b"TVW1":
        raise ValueError("Invalid text-view header")
    while remain:
        text_mode, view, length = RECORD.unpack(source.read(RECORD.size))
        expected = min(BLOCK, remain)
        if text_mode >= len(TEXT) or view > 3 or length > expected:
            raise ValueError("Invalid text-view record")
        payload = source.read(length)
        if len(payload) != length:
            raise ValueError("Truncated payload")
        if view != 3:
            payload = zstd.ZstdDecompressor().decompress(payload)
            if view == 2:
                payload = mtf(payload, True)
            if view:
                payload = sort_context(payload, True)
            if text_mode:
                payload = textfront.decode(payload)
        if len(payload) != expected:
            raise ValueError("Unexpected decoded size")
        out.write(payload)
        remain -= expected
    if source.read(1):
        raise ValueError("Trailing data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.input.open("rb") as src, a.output.open("xb") as out:
        if a.mode == "encode":
            print(json.dumps(encode(src, out, a.profile)))
        else:
            decode(src, out)
