import struct


def datasets(codec, fixtures, rng):
    expr = b"((x*17)+(x*17))"
    for n in (1, 2, 3, 4, 8, 16):
        yield f"reuse-{n}", b"\n".join(expr for _ in range(n)), b""
    yield "distinct", bytes(range(128)), b""
    for name in ("affine-0.bin", "affine-1.bin"):
        ops = struct.iter_unpack(">hh", (fixtures / name).read_bytes())
        data = b"\n".join(f"((x*{a})+{c})".encode() for a, c in ops)
        yield name + "-expressions", data, b""
