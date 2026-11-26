"""Rice-code monotone locations separately for each nonzero correction byte."""

from io import BytesIO
import struct
import numpy as np

GROUP = struct.Struct(">BBII")


def take(stream, n):
    data = stream.read(n)
    if len(data) != n:
        raise ValueError("Truncated gap stream")
    return data


def pack_changes(raw):
    values = np.frombuffer(raw, np.uint8)
    positions = np.flatnonzero(values)
    hits = values[positions]
    # Pay neither a codebook nor a membership matrix for absent classes.
    groups = np.unique(hits)
    result = BytesIO()
    result.write(bytes([len(groups)]))
    for value in groups:
        at = positions[hits == value]
        gaps = np.diff(at, prepend=-1) - 1
        # The best integer Rice parameter is near log2(mean gap + 1).
        middle = max(0, int(np.log2(1 + gaps.mean())))
        choices = range(max(0, middle - 2), min(30, middle + 2) + 1)
        k = min(choices, key=lambda b: int(np.sum(gaps >> b)) + len(at) * (b + 1))
        ends = np.cumsum((gaps >> k) + 1) - 1
        unary = np.zeros(ends[-1] + 1, np.uint8)
        unary[ends] = 1
        upper = np.packbits(unary).tobytes()
        lower = np.packbits((gaps[:, None] >> np.arange(k)) & 1).tobytes()
        result.write(GROUP.pack(int(value), k, len(at), len(upper)))
        result.write(upper)
        result.write(lower)
    return result.getvalue()


def unpack_changes(payload, size):
    src = BytesIO(payload)
    out = np.zeros(size, np.uint8)
    count = take(src, 1)[0]
    last = 0
    for _ in range(count):
        value, k, n, nu = GROUP.unpack(take(src, GROUP.size))
        if value <= last or k > 30 or not 0 < n <= size:
            raise ValueError("Invalid gap class")
        last = value
        unary = np.unpackbits(np.frombuffer(take(src, nu), np.uint8))
        ends = np.flatnonzero(unary)
        if len(ends) != n:
            raise ValueError("Invalid unary length")
        upper = np.diff(ends, prepend=-1) - 1
        bits = np.unpackbits(
            np.frombuffer(take(src, (n * k + 7) // 8), np.uint8), count=n * k
        ).reshape(n, k)
        low = (bits.astype(np.int64) << np.arange(k)).sum(axis=1)
        at = np.cumsum((upper << k) + low + 1) - 1
        if at[-1] >= size or np.any(out[at]):
            raise ValueError("Overlapping or out-of-range correction")
        out[at] = value
    if src.read(1):
        raise ValueError("Trailing gap data")
    return out.tobytes()


def infer_unit_denominators(prediction, n):
    half = 1 << n
    first, second = np.frombuffer(prediction, np.uint8).reshape(2, half)
    plus_four = first.astype(np.uint16) + 4
    updated = np.minimum(second, np.where(plus_four <= n - 1, plus_four, 255)).astype(
        np.uint8
    )
    return first.tobytes() + updated.tobytes()
