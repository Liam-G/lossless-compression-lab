"""Relative archives with a pinned external reference and compressed residual literals."""

from collections import defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
import zlib
from wire import var, xor

ID = 12
PROFILES = ("fixed-xor", "copies", "alignment")


def copy_matches(base, target):
    index = defaultdict(list)
    for i in range(len(base) - 3):
        index[base[i : i + 4]].append(i)
    pos = 0
    while pos < len(target):
        length = 0
        for offset in index.get(target[pos : pos + 4], ())[:64]:
            n = 4
            while (
                offset + n < len(base)
                and pos + n < len(target)
                and base[offset + n] == target[pos + n]
            ):
                n += 1
            if n > length:
                source, length = offset, n
        if length >= 5:
            yield pos, source, length
            pos += length
        else:
            pos += 1


def pack(data, profile, ref, stats):
    digest = sha256(ref).digest()
    if profile == "fixed-xor":
        residual = xor(data, ref[: len(data)].ljust(len(data), b"\0"))
        return digest, zlib.compress(residual)
    if profile == "alignment":
        matches = (
            (b, a, n)
            for a, b, n in SequenceMatcher(None, ref, data, autojunk=False).get_matching_blocks()
            if n >= 4
        )
    else:
        matches = copy_matches(ref, data)
    meta = bytearray(digest)
    literals = bytearray()
    pos = 0
    count = 0
    for begin, source, length in matches:
        meta.extend(var(begin - pos) + var(source) + var(length))
        literals.extend(data[pos:begin])
        pos = begin + length
        count += 1
    literals.extend(data[pos:])
    stats.update(copy_records=count, copied_bytes=len(data) - len(literals))
    return meta, zlib.compress(literals)


def unpack(size, profile, meta, body, ref, stats):
    if meta.take(32) != sha256(ref).digest():
        raise ValueError("Reference SHA-256 mismatch")
    residual = zlib.decompress(body.read())
    if profile == "fixed-xor":
        return xor(residual, ref[:size].ljust(size, b"\0"))
    pos = 0
    out = bytearray()
    while meta.tell() < meta.getbuffer().nbytes:
        gap, start, length = meta.var(), meta.var(), meta.var()
        out.extend(residual[pos : pos + gap])
        out.extend(ref[start : start + length])
        pos += gap
    return out + residual[pos:]
