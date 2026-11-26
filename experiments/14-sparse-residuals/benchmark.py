import zlib
from lab import load
from wire import Reader, blocks


def datasets(codec, fixtures, rng):
    for mode in ("isolated", "clustered", "row-pattern"):
        mask = bytearray(512)
        if mode == "isolated":
            positions = rng.sample(range(4096), 128)
        elif mode == "clustered":
            positions = [i + j for i in rng.sample(range(0, 4096, 32), 16) for j in range(8)]
        else:
            positions = range(3, 4096, 32)
        for pos in positions:
            mask[pos // 8] |= 1 << (pos % 8)
        yield mode, bytes(mask), b""
    factors, spectral = load(8, "codec"), load(9, "codec")
    for name in ("fax.bin", "fax-mid.bin", "medical.bin"):
        raw = (fixtures / name).read_bytes()
        yield name + "-GF2", b"".join(factors.approximate(b)[2] for b in blocks(raw, 16)), b""
        header, stream = spectral.pack(raw, "combined", b"", {})
        meta, body = Reader(header), Reader(stream)
        masks = []
        for block in blocks(raw, 32):
            for _ in range(meta.byte()):
                meta.var()
                meta.var()
            masks.append(zlib.decompress(body.take(meta.var())))
        yield name + "-Walsh", b"".join(masks), b""
    # Turn the alignment codec's literal gaps into a one-bit-per-target-byte mask.
    delta = load(12, "codec")
    target = (fixtures / "logo-new.png").read_bytes()
    base = (fixtures / "logo-old.png").read_bytes()
    header, _ = delta.pack(target, "alignment", base, {})
    meta = Reader(header[32:])
    mask = [1] * len(target)
    pos = 0
    while meta.tell() < len(header) - 32:
        pos += meta.var()
        meta.var()
        n = meta.var()
        mask[pos : pos + n] = [0] * n
        pos += n
    yield (
        "aligned-logo-exceptions",
        bytes(sum(b << i for i, b in enumerate(part)) for part in blocks(mask, 8)),
        b"",
    )
