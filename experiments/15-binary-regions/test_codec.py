"""Algorithm-specific checks run by the repository test command."""


def verify(c):
    from regions import IDENT, ELF, elf_recipe, elf_header
    from wire import encode, decode

    hdr = IDENT + ELF.pack(2, 62, 1, 4194304, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    assert elf_header(elf_recipe(hdr)) == hdr
    source = hdr + bytes([33]) * 512
    archive, stats = encode(c, source, "combined")
    assert stats["covered_and_record_bytes"]["header"][0] == 64 and decode(c, archive)[0] == source
