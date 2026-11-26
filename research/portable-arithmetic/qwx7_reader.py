"""Read the branching representation of the QWX6 metadata."""

import lzma


def restore_weight_lanes(encoded):
    import bz2
    import zlib
    from struct import unpack_from

    lanes, count = unpack_from("<BH", encoded)
    if not 1 <= lanes <= 8:
        raise ValueError("invalid weight lane count")
    end = 3 + count * 3
    if end + 4 * lanes > len(encoded):
        raise ValueError("truncated weight lane directory")
    runs, sizes = [], [0] * lanes
    for offset in range(3, end, 3):
        item = int.from_bytes(encoded[offset : offset + 3], "little")
        lane, size = item >> 21, item & ((1 << 21) - 1)
        if lane >= lanes or not size:
            raise ValueError("invalid weight lane run")
        runs.append((lane, size))
        sizes[lane] += size
    if sum(sizes) > 4 << 20:
        raise ValueError("oversized weight lanes")
    lengths = unpack_from(f"<{lanes}I", encoded, end)
    offset = end + 4 * lanes
    blocks = []
    for length, size in zip(lengths, sizes, strict=True):
        codec, length = length >> 24, length & 0xFFFFFF
        if offset + length > len(encoded):
            raise ValueError("truncated weight lane block")
        block = encoded[offset : offset + length]
        offset += length
        if codec == 1:
            decoder = bz2.BZ2Decompressor()
        elif codec == 2:
            decoder = zlib.decompressobj(-15)
        elif codec >= 8:
            pb, context = divmod(codec - 8, 25)
            lp, lc = divmod(context, 5)
            decoder = lzma.LZMADecompressor(
                format=lzma.FORMAT_RAW,
                filters=[
                    {
                        "id": lzma.FILTER_LZMA2,
                        "dict_size": 1 << 18,
                        "lc": lc,
                        "lp": lp,
                        "pb": pb,
                    }
                ],
            )
        elif codec != 0:
            raise ValueError("invalid weight lane codec")
        if codec:
            block = decoder.decompress(block, size + 1)
            if not decoder.eof or decoder.unused_data:
                raise ValueError("invalid compressed weight lane")
        if len(block) != size:
            raise ValueError("incorrect weight lane length")
        blocks.append(block)
    if offset != len(encoded):
        raise ValueError("unexpected data after weight lanes")

    output = bytearray()
    offsets = [0] * lanes
    for lane, width in runs:
        start = offsets[lane]
        offsets[lane] = start + width
        output.extend(blocks[lane][start : offsets[lane]])
    return bytes(output)
