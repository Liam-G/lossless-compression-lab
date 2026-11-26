"""Rebuild the original three-lane model-weight branch and check both independent inverses."""

import argparse
from pathlib import Path
from struct import pack, unpack_from
from qwx7_reader import restore_weight_lanes as old_unpack
from qwx8_reader import restore_weight_lanes


def put_width(width):
    result = bytearray()
    while width >= 128:
        result.append((width & 127) | 128)
        width >>= 7
    result.append(width)
    return result


def weight_branch(original):
    size, mode, head, model = unpack_from("<IBII", original, 4)
    old = original[17 : size + 8]
    lanes, runs = unpack_from("<BH", old)
    end = 3 + 3 * runs
    lengths = unpack_from("<3I", old, end)
    if (
        original[:4] != b"QWX7"
        or lanes != 3
        or tuple(n >> 24 for n in lengths) != (9, 33, 0)
    ):
        raise ValueError("expected the three verified QWX7 lanes")
    entries = [int.from_bytes(old[at : at + 3], "little") for at in range(3, end, 3)]
    width = (1 << 21) - 1
    if (
        entries[0] >> 21
        or entries[-1] >> 21
        or entries[0] + sum(n & width for n in entries[1:-1]) != model
    ):
        raise ValueError("unexpected QWX7 first lane")
    descriptors = bytearray([len(entries) - 2])
    for index, entry in enumerate(entries[1:-1]):
        if (entry >> 21) != 1 + index % 2:
            raise ValueError("expected alternating QWX7 mantissas")
        descriptors.extend(put_width(entry & width))
    encoding = descriptors + old[end + 12 :]
    if restore_weight_lanes(encoding, model) != old_unpack(old):
        raise ValueError("QWX8 metadata differs after reconstruction")
    frame = pack("<4sIBII", b"QWX8", len(encoding) + 9, mode, head, model)
    return frame + encoding + original[size + 8 :], 3 + 3 * runs + 12, len(descriptors)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    result, old_length, new_length = weight_branch(a.source.read_bytes())
    with a.output.open("xb") as dst:
        dst.write(result)
    print(f"Directory {old_length} -> {new_length} bytes")
