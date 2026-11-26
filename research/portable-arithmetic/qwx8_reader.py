"""Restore the three fixed metadata lanes without a table of codec names."""

from io import BytesIO
import lzma


def restore_weight_lanes(encoded, model_start):
    source = BytesIO(encoded)
    runs = []
    for _ in range(int.from_bytes(source.read(1), "little")):
        width = 0
        for shift in (0, 7, 14):
            chunk = source.read(1)
            if not chunk:
                raise ValueError("truncated weight lane directory")
            width |= (chunk[0] & 127) << shift
            if chunk[0] < 128:
                break
        else:
            raise ValueError("oversized weight lane run")
        if not width:
            raise ValueError("empty weight lane run")
        runs.append(width)
    front = model_start - sum(runs)
    if not runs or not 0 < front < model_start < 4 << 20:
        raise ValueError("invalid weight lane sizes")
    rest = source.read()
    blocks = []
    for limit in (4 << 20, sum(runs[::2]) + 1):
        decoder = lzma.LZMADecompressor(
            format=lzma.FORMAT_RAW,
            filters=[{"id": lzma.FILTER_LZMA2, "dict_size": 1 << 18}],
        )
        blocks.append(decoder.decompress(rest, max_length=limit))
        if not decoder.eof:
            raise ValueError("invalid compressed weight lane")
        rest = decoder.unused_data
    primary, narrow = blocks
    if (
        not front < len(primary)
        or len(narrow) != sum(runs[::2])
        or len(rest) != sum(runs[1::2])
    ):
        raise ValueError("incorrect weight lane length")
    lanes = (BytesIO(narrow), BytesIO(rest))
    data = bytearray(primary[:front])
    for index, size in enumerate(runs):
        data.extend(lanes[index % 2].read(size))
    data.extend(primary[front:])
    return bytes(data)
