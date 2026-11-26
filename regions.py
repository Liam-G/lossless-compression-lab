"""Frozen ELF64 and integer-constant generators shared by experiments 15 and 16."""

from functools import lru_cache
from math import isqrt
import struct
from wire import Reader, var

IDENT = b"\x7fELF\x02\x01\x01" + bytes(9)
ELF = struct.Struct("<HHIQQQIHHHHHH")


def elf_recipe(data):
    if len(data) < 64 or not data.startswith(IDENT):
        return None
    return b"".join(var(x) for x in ELF.unpack_from(data, 16))


def elf_header(recipe):
    src = Reader(recipe)
    values = [src.var() for _ in range(13)]
    src.end()
    return IDENT + ELF.pack(*values)


@lru_cache(maxsize=1)
def constants():
    mask = (1 << 64) - 1
    values = [(1 << 40) + (1 << 8) + 179]
    for d in range(2, 32):
        if isqrt(d) ** 2 != d:
            values.extend([isqrt(d << 128) & mask, (isqrt(d << 126) - (1 << 63)) & mask])
    return tuple(v.to_bytes(8, order) for v in values for order in ("little", "big"))
