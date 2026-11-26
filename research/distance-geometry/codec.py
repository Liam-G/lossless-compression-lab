"""Reconstruct a packed distance matrix from transmitted landmark columns and exact errors."""

import argparse
from functools import cache
import json
from math import isqrt
from pathlib import Path
import struct

import numpy as np
import zstandard as zstd

HEADER = struct.Struct(">4sQB")
PROFILES = ("direct", "rows", "two", "three", "joint", "sphere", "all")
RAW, ZSTD, ABOVE, LAND2, LAND3, SPHERE = range(6)
PRECISION = 20


def dimension(byte_count):
    if byte_count % 2:
        return None
    n = (1 + isqrt(1 + 4 * byte_count)) // 2
    return n if n * (n - 1) == byte_count else None


def column(words, n, vertex):
    indices = np.arange(n, dtype=np.int64)
    higher = np.maximum(indices, vertex)
    pos = higher * (higher - 1) // 2 + np.minimum(indices, vertex)
    pos[vertex] = 0
    out = words[pos].copy()
    out[vertex] = 0
    return out


def determinant(mat):
    if len(mat) == 1:
        return int(mat[0][0])
    if len(mat) == 2:
        return int(mat[0][0]) * int(mat[1][1]) - int(mat[0][1]) * int(mat[1][0])
    total = 0
    for i, x in enumerate(mat[0]):
        minor = [r[:i] + r[i + 1 :] for r in mat[1:]]
        total += (-1) ** i * int(x) * determinant(minor)
    return total


def gram(cols, vertices):
    origin = cols[0].astype(np.int64) ** 2
    return [
        [
            int(origin[v] + origin[u]) - int(cols[j + 1][v]) ** 2
            for j, u in enumerate(vertices[1:])
        ]
        for v in vertices[1:]
    ]


def landmarks(words, n, k):
    # Greedily maximize the squared simplex volume among 96 dispersed vertices.
    vertices = [0]
    cols = [column(words, n, 0)]
    for _ in range(k):
        best = 0
        chosen = None
        for c in np.linspace(0, n - 1, min(96, n), dtype=int):
            if c in vertices:
                continue
            # For the current simplex the new column needs distances only to its vertices.
            selected = [*vertices, int(c)]
            origin = cols[0]
            mat = []
            for i, v in enumerate(selected[1:]):
                row = []
                for j, u in enumerate(selected[1:]):
                    d = (
                        0
                        if v == u
                        else int(words[max(v, u) * (max(v, u) - 1) // 2 + min(v, u)])
                    )
                    row.append(int(origin[v]) ** 2 + int(origin[u]) ** 2 - d * d)
                mat.append(row)
            volume = determinant(mat)
            if volume > best:
                best, chosen = volume, int(c)
        if chosen is None:
            raise ValueError("Degenerate landmark simplex")
        vertices.append(chosen)
        cols.append(column(words, n, chosen))
    return vertices, cols


def coordinates(vertices, cols):
    k = len(vertices) - 1
    metric = gram(cols, vertices)
    det = determinant(metric)
    if det <= 0:
        raise ValueError("Degenerate landmark metric")
    adj = np.empty((k, k), object)
    for i in range(k):
        for j in range(k):
            sub = [r[:i] + r[i + 1 :] for idx, r in enumerate(metric) if idx != j]
            adj[i, j] = (-1) ** (i + j) * determinant(sub)
    radii = cols[0].astype(np.int64) ** 2
    dots = np.stack(
        [
            radii + int(radii[v]) - d.astype(np.int64) ** 2
            for v, d in zip(vertices[1:], cols[1:], strict=True)
        ],
        axis=1,
    )
    nums = dots.astype(object) @ adj
    weights = (nums * (1 << PRECISION) + det // 2) // det
    maxweight = max(abs(int(weights.min())), abs(int(weights.max())))
    if maxweight * int(np.abs(dots).max()) * k > 2**62:
        raise ValueError("Landmarks are numerically ill-conditioned")
    return radii, dots, weights.astype(np.int64)


def exact_root(squared):
    # Correct the floating seed with integer square comparisons, then round to nearest.
    squared = np.clip(squared, 0, 65535**2)
    root = np.sqrt(squared).astype(np.int64)
    root -= root * root > squared
    root += (root + 1) * (root + 1) <= squared
    return (root + (4 * squared > (2 * root + 1) ** 2)).astype("<u2")


@cache
def sphere_tables():
    # Fixed Q62 sine/cosine of pi/(2*65535) make the predictor reproducible.
    sine, cosine = 0, 1 << 62
    sin_step, cos_step = 110536651520310, 4611686017102671360
    table = np.empty(65536, dtype="<u2")
    for i in range(len(table)):
        table[i] = min(65535, (65535 * sine + (1 << 61)) >> 62)
        sine, cosine = (
            (sine * cos_step + cosine * sin_step + (1 << 61)) >> 62,
            (cosine * cos_step - sine * sin_step + (1 << 61)) >> 62,
        )
    values = np.arange(65536)
    first = np.searchsorted(table, values, side="left")
    last = np.searchsorted(table, values, side="right")
    inverse = np.minimum(65535, (first + last) // 2).astype("<u2")
    return table, inverse


def transform(words, n, vertices=None, cols=None, reverse=False, spherical=False):
    out = np.empty_like(words)
    if spherical:
        chord, angle = sphere_tables()
        cols = [chord[c] for c in cols]
    if vertices is not None:
        radii, dots, weights = coordinates(vertices, cols)
    previous = np.empty(0, dtype="<u2")
    for i in range(1, n):
        start = i * (i - 1) // 2
        row = words[start : start + i]
        if vertices is None:
            prediction = np.zeros(i, dtype="<u2")
            prediction[:-1] = previous
        else:
            paired = (dots[:i] @ weights[i] + (1 << (PRECISION - 1))) >> PRECISION
            prediction = exact_root(radii[:i] + radii[i] - paired)
            if spherical:
                prediction = angle[prediction]
        if reverse:
            delta = (row >> 1) ^ ((np.zeros_like(row)) - (row & 1))
            actual = out[start : start + i]
            np.add(prediction, delta, out=actual)
            previous = actual
        else:
            delta = row - prediction
            out[start : start + i] = (delta << 1) ^ (
                np.zeros_like(delta) - (delta >> 15)
            )
            previous = row
    return out


def plane_bytes(words):
    return words.view(np.uint8).reshape(-1, 2).T.copy().tobytes()


def unplanes(data):
    return np.frombuffer(data, np.uint8).reshape(2, -1).T.copy().ravel().view("<u2")


def encode(data, profile):
    coder = zstd.ZstdCompressor(level=3)
    best = (RAW, data)

    def offer(tag, blob):
        nonlocal best
        if len(blob) < len(best[1]):
            best = (tag, blob)

    offer(ZSTD, coder.compress(data))
    n = dimension(len(data))
    if n and n >= 5 and profile != "direct":
        words = np.frombuffer(data, "<u2")
        if profile in ("rows", "joint", "all"):
            offer(ABOVE, coder.compress(plane_bytes(transform(words, n))))
        for k, tag, profile_name in (
            (2, LAND2, "two"),
            (3, LAND3, "three"),
            (3, SPHERE, "sphere"),
        ):
            if (
                profile != profile_name
                and profile != "all"
                and (profile != "joint" or tag == SPHERE)
            ):
                continue
            try:
                if tag == SPHERE:
                    verts, _ = landmarks(sphere_tables()[0][words], n, k)
                    cols = [column(words, n, v) for v in verts]
                else:
                    verts, cols = landmarks(words, n, k)
                residual = transform(words, n, verts, cols, spherical=tag == SPHERE)
            except ValueError:
                continue
            header = struct.pack(">" + "I" * len(verts), *verts)
            body = b"".join(c.tobytes() for c in cols) + plane_bytes(residual)
            offer(tag, header + coder.compress(body))
    mode, payload = best
    return HEADER.pack(b"DGM1", len(data), mode) + payload, mode


def decode(archive):
    magic, size, mode = HEADER.unpack_from(archive)
    if magic != b"DGM1" or mode > SPHERE:
        raise ValueError("Invalid distance format")
    body = archive[HEADER.size :]
    if mode == RAW:
        result = body
    elif mode == ZSTD:
        result = zstd.ZstdDecompressor().decompress(body, max_output_size=size)
    else:
        n = dimension(size)
        if n is None or n < 5:
            raise ValueError("Invalid packed triangle")
        vertices = cols = None
        if mode == ABOVE:
            inner = zstd.ZstdDecompressor().decompress(body, max_output_size=size)
        else:
            count = 3 if mode == LAND2 else 4
            vertices = struct.unpack_from(">" + "I" * count, body)
            if len(set(vertices)) != count or max(vertices) >= n:
                raise ValueError("Invalid landmarks")
            extra = 2 * n * count
            raw = zstd.ZstdDecompressor().decompress(
                body[4 * count :], max_output_size=size + extra
            )
            if len(raw) != size + extra:
                raise ValueError("Invalid distance/residual stream")
            cols = np.frombuffer(raw[:extra], "<u2").reshape(count, n)
            inner = raw[extra:]
        if len(inner) != size:
            raise ValueError("Invalid residual size")
        result = transform(
            unplanes(inner), n, vertices, cols, True, spherical=mode == SPHERE
        ).tobytes()
    if len(result) != size:
        raise ValueError("Invalid decoded size")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("encode", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="joint")
    a = p.parse_args()
    with a.output.open("xb") as out:
        if a.action == "encode":
            archive, mode = encode(a.input.read_bytes(), a.profile)
            print(json.dumps({"mode": mode}))
            out.write(archive)
        else:
            out.write(decode(a.input.read_bytes()))
