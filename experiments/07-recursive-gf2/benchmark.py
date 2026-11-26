import struct


def datasets(codec, fixtures, rng):
    for name in ("matched-rule", "different-rule", "hierarchical"):
        data = bytearray()
        for _ in range(24):
            basis = [rng.getrandbits(16) for _ in range(3)]
            if name == "hierarchical":
                basis = [(x & 255) * 257 for x in basis]
            rows = tuple(
                (basis[0] if rng.getrandbits(1) else 0)
                ^ (basis[1] if rng.getrandbits(1) else 0)
                ^ (basis[2] if rng.getrandbits(1) else 0)
                for _ in range(16)
            )
            for _ in range(2):
                if name == "matched-rule":
                    rows = codec.step(rows, 16)
                elif name == "different-rule":
                    # Alternate nonlinear checkerboard phases with a different neighborhood.
                    rows = list(rows)
                    for phase in (0, 1):
                        for y, x in enumerate(rows):
                            color = 0xAAAA if (phase ^ (y & 1)) else 0x5555
                            rows[y] ^= color & (
                                (rows[y - 1] & rows[(y + 1) % 16]) ^ (x << 1 | x >> 15)
                            )
            data.extend(struct.pack("<16H", *rows))
        yield name, bytes(data), b""
    for name in ("fax.bin", "fax-mid.bin", "medical.bin"):
        source = (fixtures / name).read_bytes()
        for k in (0, 5):
            plane = bytes(
                sum(((v >> k) & 1) << j for j, v in enumerate(source[i : i + 8]))
                for i in range(0, len(source), 8)
            )
            yield f"{name}-plane{k}", plane, b""
