"""Sample exact repeated substrings using the most recent equal four-byte prefix."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

WINDOW = 32768
STRIDE = 97
LIMIT = 64


def measure(data, stride=STRIDE, window=WINDOW, limit=LIMIT):
    if stride < 1 or window < 1 or limit < 4:
        raise ValueError("Invalid match probe dimensions")
    count = max(0, len(data) - limit + 1)
    lengths = np.zeros((count + stride - 1) // stride, np.int32)
    if count:
        values = np.frombuffer(data, np.uint8)
        keys = np.ndarray((len(data) - 3,), dtype="<u4", buffer=data, strides=(1,))
        columns = np.arange(limit)
        for start in range(0, count, 1 << 17):
            left, stop = max(0, start - window), min(start + (1 << 17), count)
            # Stable ordering puts the most recent earlier equal prefix immediately
            # before its successor. Include the full lookback at a chunk boundary.
            indices = left + np.argsort(keys[left:stop], kind="stable")
            prev, pos = indices[:-1], indices[1:]
            valid = (
                (pos >= start)
                & (pos % stride == 0)
                & (pos - prev <= window)
                & (keys[pos] == keys[prev])
            )
            pos, prev = pos[valid], prev[valid]
            unequal = values[pos[:, None] + columns] != values[prev[:, None] + columns]
            lengths[pos // stride] = np.where(
                unequal.any(axis=1), unequal.argmax(axis=1), limit
            )
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "stride": stride,
        "window": window,
        "cap": limit,
        "samples": len(lengths),
        "matched_bytes": int(lengths.sum()),
        "at_least_4": int(np.sum(lengths >= 4)),
        "at_least_16": int(np.sum(lengths >= 16)),
        "at_cap": int(np.sum(lengths == limit)),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    a = p.parse_args()
    print(json.dumps(measure(a.input.read_bytes()), sort_keys=True))
