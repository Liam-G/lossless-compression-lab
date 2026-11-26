"""Read SCL1 with the Python 3.14 standard library, or python-zstandard on older Python."""

from io import BytesIO
import lzma
import struct
from arithmetic import transform

try:
    from compression.zstd import decompress as zstd_decompress
except ImportError:
    from zstandard import ZstdDecompressor

    zstd_decompress = ZstdDecompressor().decompress

HEADER = struct.Struct(">4sQBBI")
RECORD = struct.Struct(">QIBI")
SCALES = (1, 3, 5, 7, 12, 13, 17, 31, 255, 257, 3072)
ZSTD, NIBBLES, XZ = 1, 2, 3


def unshuffle_nibbles(data):
    n = len(data) // 2
    out = bytearray(data)
    high, low = data[:n], data[n : 2 * n]
    out[: 2 * n : 2] = bytes((h & 240) | (l >> 4) for h, l in zip(high, low))
    out[1 : 2 * n : 2] = bytes(((h << 4) & 240) | (l & 15) for h, l in zip(high, low))
    return bytes(out)


def take(stream, n):
    data = stream.read(n)
    if len(data) != n:
        raise ValueError("Truncated record")
    return data


def decode(archive):
    src = BytesIO(archive)
    magic, size, op, inv, n = HEADER.unpack(take(src, HEADER.size))
    if magic != b"SCL1" or op >= len(SCALES) or inv > 1:
        raise ValueError("Invalid whole-file scale")
    out = BytesIO()
    for _ in range(n):
        pos, length, kind, count = RECORD.unpack(take(src, RECORD.size))
        if pos < out.tell() or pos + length > size or count > length:
            raise ValueError("Invalid interval")
        out.write(take(src, pos - out.tell()))
        body = take(src, count)
        if kind == XZ:
            result = lzma.decompress(body)
        elif kind in (ZSTD, NIBBLES):
            result = zstd_decompress(body)
            if kind == NIBBLES:
                result = unshuffle_nibbles(result)
        else:
            raise ValueError("Unknown interval coder")
        if len(result) != length:
            raise ValueError("Invalid restored interval")
        out.write(result)
    out.write(take(src, size - out.tell()))
    if src.read(1):
        raise ValueError("Trailing data")
    return transform(out.getvalue(), SCALES[op], not inv) if op else out.getvalue()
