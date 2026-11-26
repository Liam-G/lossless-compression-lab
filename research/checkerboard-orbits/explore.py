"""Inspect the original checkerboard torus and compare entropy with complete packet size."""

import argparse
from dataclasses import dataclass
from math import comb, log2
from pathlib import Path
from random import Random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wire import Reader, var


def step(state, h, w, inverse=False):
    if min(h, w) < 2 or h % 2 or w % 2 or len(state) != h * w:
        raise ValueError("Expected a complete even-sided torus")
    cells = list(state)
    for parity in (1, 0) if inverse else (0, 1):
        for y in range(h):
            for x in range((parity - y) % 2, w, 2):
                horizontal = cells[y * w + (x - 1) % w] & cells[y * w + (x + 1) % w]
                vertical = cells[((y - 1) % h) * w + x] | cells[((y + 1) % h) * w + x]
                cells[y * w + x] ^= horizontal ^ vertical
    return bytes(cells)


def shape(state):
    n = len(state)
    ones = sum(state)
    k = min(ones, n - ones)
    tag = 1 + 2 * k + (ones > n // 2)
    size = ((comb(n, k) - 1).bit_length() + 7) // 8
    if len(var(tag)) + size < 1 + (n + 7) // 8:
        return tag, size
    return 0, (n + 7) // 8


def pack(state, h, w, t):
    tag, width = shape(state)
    if tag:
        minority = tag % 2
        positions = (i for i, value in enumerate(state) if value == minority)
        rank = sum(comb(i, j) for j, i in enumerate(positions, 1))
    else:
        rank = 0
        for value in state:
            rank = (rank << 1) | value
    return bytes([h, w]) + var(t) + var(tag) + rank.to_bytes(width, "big")


def unpack(packet):
    source = Reader(packet)
    h, w = source.byte(), source.byte()
    if min(h, w) < 2 or h % 2 or w % 2:
        raise ValueError("Invalid torus")
    t, tag = source.var(), source.var()
    n = h * w
    k = (tag - 1) // 2 if tag else 0
    if k > n // 2:
        raise ValueError("Invalid minority population")
    limit = comb(n, k) if tag else 1 << n
    rank = int.from_bytes(source.take(((limit - 1).bit_length() + 7) // 8), "big")
    source.end()
    if rank >= limit:
        raise ValueError("Invalid enumerative seed")
    if tag:
        state = bytearray([1 - tag % 2]) * n
        pos = n - 1
        for j in range(k, 0, -1):
            while comb(pos, j) > rank:
                pos -= 1
            state[pos] = tag % 2
            rank -= comb(pos, j)
            pos -= 1
    else:
        state = bytes((rank >> (n - 1 - i)) & 1 for i in range(n))
    for _ in range(t):
        state = step(state, h, w)
    return bytes(state), h, w


@dataclass(frozen=True)
class Candidate:
    steps: int
    state: bytes
    packet_bytes: int


def search(original, h, w, limit):
    state = original
    entropy = smallest = None
    for t in range(limit + 1):
        tag, width = shape(state)
        size = 2 + len(var(t)) + len(var(tag)) + width
        candidate = Candidate(t, state, size)
        minority = min(sum(state), len(state) - sum(state))
        if entropy is None or minority < entropy[0]:
            entropy = (minority, candidate)
        if smallest is None or size < smallest.packet_bytes:
            smallest = candidate
        if t < limit:
            state = step(state, h, w, True)
    return entropy[1], smallest


def show(state, w):
    return "\n".join(
        "".join("█" if bit else "·" for bit in state[i : i + w])
        for i in range(0, len(state), w)
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=int, default=255)
    p.add_argument("--height", type=int, default=8)
    p.add_argument("--width", type=int, default=8)
    source = p.add_mutually_exclusive_group()
    source.add_argument("--seed", type=int)
    source.add_argument("--recorded", action="store_true", help="Original 8 by 8 crop")
    source.add_argument("--open", type=Path, help="Decode a saved packet")
    p.add_argument(
        "--save", type=Path, help="Write the smallest candidate to a new packet"
    )
    a = p.parse_args()
    if a.open:
        state, h, w = unpack(a.open.read_bytes())
        print(show(state, w))
    else:
        h, w = (8, 8) if a.recorded else (a.height, a.width)
        if min(h, w) < 2 or max(h, w) > 254 or h % 2 or w % 2 or a.steps < 0:
            p.error("Choose even sides from 2 to 254 and nonnegative steps")
        rng = Random(a.seed)
        state = (
            bytes(int(i) for i in f"{0xD76C3E682E181590:064b}")
            if a.recorded
            else bytes(rng.randrange(2) for _ in range(h * w))
        )
        entropy, best = search(state, h, w, a.steps)
        for label, item in (
            ("Initial", Candidate(0, state, len(pack(state, h, w, 0)))),
            ("Minimum entropy", entropy),
            ("Fewest bytes", best),
        ):
            probability = sum(item.state) / len(state)
            H = (
                0
                if probability in (0, 1)
                else -probability * log2(probability)
                - (1 - probability) * log2(1 - probability)
            )
            print(
                f"{label} | step {item.steps} | {H:.6f} bits/cell | {item.packet_bytes} bytes"
            )
            print(show(item.state, w))
        blob = pack(best.state, h, w, best.steps)
        if unpack(blob)[0] != state:
            raise RuntimeError("Original grid was not reconstructed")
        if a.save:
            with a.save.open("xb") as out:
                out.write(blob)
