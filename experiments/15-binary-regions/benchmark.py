from regions import IDENT, ELF, constants


def datasets(codec, fixtures, rng):
    synthetic = IDENT + ELF.pack(2, 62, 1, 4194304, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    for i in range(16):
        synthetic += rng.randbytes(15) + constants()[i] + bytes(13)
    yield "generated-header-and-regions", synthetic, b""
    for name in ("rusage.elf", "scanner.elf"):
        yield name, (fixtures / name).read_bytes(), b""
