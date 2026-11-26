"""A grayscale video archive with tile motion, reversible spatial prediction and exact errors."""

import argparse
from collections import Counter
import ctypes as ct
from functools import cache
import json
from pathlib import Path
import struct
import numpy as np
import zstandard as zstd

HEADER = struct.Struct(">4sIII")
RECORD = struct.Struct(">BI")
TILE = 32
PROFILES = ("direct", "spatial", "time", "motion", "joint")
STORED = 255


@cache
def library():
    lib = ct.CDLL(str(Path(__file__).resolve().parents[1] / "build/motion.so"))
    ptr = ct.c_void_p
    lib.motion_vectors.argtypes = lib.warp.argtypes = [
        ptr,
        ptr,
        ptr,
        ct.c_int,
        ct.c_int,
        ct.c_int,
    ]
    lib.motion_vectors.restype = None
    lib.warp.restype = ct.c_int
    lib.spatial.argtypes = [ptr, ptr, ct.c_int, ct.c_int, ct.c_int, ct.c_bool]
    lib.spatial.restype = None
    return lib


def spatial(values, mode, reverse=False):
    if mode == 0:
        return values
    h, w = values.shape
    out = np.empty_like(values)
    library().spatial(values.ctypes.data, out.ctypes.data, w, h, mode, reverse)
    return out


def vector_size(h, w):
    return 2 * ((h + TILE - 1) // TILE) * ((w + TILE - 1) // TILE)


def warp(prev, vectors):
    h, w = prev.shape
    out = np.empty_like(prev)
    if library().warp(
        prev.ctypes.data, vectors.ctypes.data, out.ctypes.data, w, h, TILE
    ):
        raise ValueError("Motion vector leaves the previous frame")
    return out


def predictions(frame, prev, profile):
    yield 0, frame, b""
    if prev is None or profile not in ("time", "motion", "joint"):
        return
    yield 1, frame - prev, b""
    if profile in ("motion", "joint"):
        h, w = frame.shape
        vectors = np.empty(vector_size(h, w), np.int8)
        library().motion_vectors(
            frame.ctypes.data, prev.ctypes.data, vectors.ctypes.data, w, h, TILE
        )
        yield 2, frame - warp(prev, vectors), vectors.tobytes()


def pack(src, out, profile, w, h):
    size = src.seek(0, 2)
    if min(w, h) < 1 or size % (w * h):
        raise ValueError("Expected complete grayscale frames")
    src.seek(0)
    out.write(HEADER.pack(b"MVR1", w, h, size // (w * h)))
    prev = None
    coder = zstd.ZstdCompressor(level=3)
    counts = Counter()
    while data := src.read(w * h):
        frame = np.frombuffer(data, np.uint8).reshape(h, w)
        choice = (len(data), STORED, data)
        for temporal, delta, vectors in predictions(frame, prev, profile):
            for sp in (0, 1, 2) if profile in ("spatial", "joint") else (0,):
                field = spatial(delta, sp)
                if sp or temporal:
                    field = (field << 1) ^ (np.zeros_like(field) - (field >> 7))
                record = coder.compress(vectors + field.tobytes())
                if len(record) < choice[0]:
                    choice = len(record), 3 * temporal + sp, record
        length, mode, payload = choice
        out.write(RECORD.pack(mode, length))
        out.write(payload)
        counts[str(mode)] += 1
        prev = frame
    return counts


def unpack(src, out):
    magic, w, h, n = HEADER.unpack(src.read(HEADER.size))
    if magic != b"MVR1" or not (w and h):
        raise ValueError("Invalid grayscale sequence")
    prev = None
    for _ in range(n):
        mode, length = RECORD.unpack(src.read(RECORD.size))
        if (mode > 8 and mode != STORED) or length > w * h:
            raise ValueError("Invalid frame header")
        payload = src.read(length)
        if len(payload) != length:
            raise ValueError("Truncated frame")
        if mode == STORED:
            if len(payload) != w * h:
                raise ValueError("Invalid literal frame")
            frame = np.frombuffer(payload, np.uint8).reshape(h, w)
        else:
            temporal, sp = divmod(mode, 3)
            offset = vector_size(h, w) if temporal == 2 else 0
            field = zstd.ZstdDecompressor().decompress(
                payload, max_output_size=w * h + offset
            )
            if len(field) != w * h + offset:
                raise ValueError("Invalid residual length")
            values = np.frombuffer(field[offset:], np.uint8).reshape(h, w)
            if temporal or sp:
                values = (values >> 1) ^ (np.zeros_like(values) - (values & 1))
            frame = spatial(values, sp, True)
            if temporal:
                if prev is None:
                    raise ValueError("Missing previous frame")
                frame = frame + (
                    prev
                    if temporal == 1
                    else warp(prev, np.frombuffer(field[:offset], np.int8))
                )
        out.write(frame.tobytes())
        prev = frame
    if src.read(1):
        raise ValueError("Trailing frames")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("encode", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=360)
    a = p.parse_args()
    with a.input.open("rb") as src, a.output.open("xb") as out:
        if a.mode == "encode":
            print(json.dumps(pack(src, out, a.profile, a.width, a.height)))
        else:
            unpack(src, out)
