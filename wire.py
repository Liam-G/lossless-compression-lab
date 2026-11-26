"""Binary framing shared by experiments 02–16. All integers are unsigned LEB128 unless specified."""

import io
import struct


def var(n):
    if n < 0:
        raise ValueError("Expected unsigned integer")
    result = bytearray()
    while n >= 128:
        result.append(128 | (n & 127))
        n >>= 7
    result.append(n)
    return bytes(result)


def zig(n):
    return 2 * n if n >= 0 else -2 * n - 1


def signed(n):
    return -(n // 2) - 1 if n & 1 else n // 2


class Reader(io.BytesIO):
    def take(self, n):
        data = self.read(n)
        if len(data) != n:
            raise ValueError("Truncated stream")
        return data

    def byte(self):
        return self.take(1)[0]

    def var(self):
        result = shift = 0
        while True:
            b = self.byte()
            result |= (b & 127) << shift
            if b < 128:
                return result
            shift += 7

    def end(self):
        if self.read(1):
            raise ValueError("Trailing bytes")


def blocks(data, width):
    for i in range(0, len(data), width):
        yield data[i : i + width]


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b, strict=True))


def encode(module, data, profile, reference=b""):
    stats = {}
    metadata, body = module.pack(data, profile, reference, stats)
    header = struct.pack(">4sBB", b"LCX1", module.ID, module.PROFILES.index(profile))
    prefix = header + var(len(data)) + struct.pack(">I", len(metadata)) + metadata
    return prefix + body, stats | {"metadata_bytes": len(prefix)}


def decode(module, archive, reference=b""):
    stream = Reader(archive)
    if stream.take(5) != b"LCX1" + bytes([module.ID]):
        raise ValueError("Wrong experiment or archive version")
    profile = module.PROFILES[stream.byte()]
    size = stream.var()
    (meta_size,) = struct.unpack(">I", stream.take(4))
    metadata = Reader(stream.take(meta_size))
    stats = {}
    data = module.unpack(size, profile, metadata, stream, reference, stats)
    metadata.end()
    stream.end()
    if len(data) != size:
        raise ValueError("Incorrect reconstructed size")
    return bytes(data), stats
