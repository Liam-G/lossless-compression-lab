"""Rebuild a saved arithmetic witness computation and apply its lossless correction."""

import hashlib
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import zlib

HEADER = struct.Struct(">4sBBBBQ")
COUNTS = struct.Struct("<4sII")
ROW = struct.Struct("<9I")


def assemble(prefix, subset):
    three = b"" if subset else prefix.with_suffix(".rec3.bin").read_bytes()
    six = prefix.with_suffix(".rec6.bin").read_bytes()
    if subset:
        retained = bytearray()
        for record in ROW.iter_unpack(six):
            if record[5] != 1 or record[7] != 1:
                retained.extend(ROW.pack(*record))
        six = retained
    return COUNTS.pack(b"WIT1", len(three) // 24, len(six) // 36) + three + six


def extract(package, output):
    with ZipFile(package) as archive, TemporaryDirectory(dir=output.parent) as tmp:
        info = archive.read("model")
        magic, mode, n, budget, flags, size = HEADER.unpack_from(info)
        patch = info[HEADER.size :]
        if magic != b"WRP1" or mode > 2 or flags > 3:
            raise ValueError("Invalid witness package")
        if mode == 0:
            raw = zlib.decompress(patch)
        else:
            if not 9 <= n <= 28 or not 8 <= budget < n:
                raise ValueError("Invalid enumeration dimensions")
            root = Path(tmp)
            exe = root / "enumerate"
            if "enumerate" in archive.namelist():
                exe.write_bytes(archive.read("enumerate"))
                exe.chmod(0o700)
            else:
                src = root / "enumerate.c"
                src.write_bytes(archive.read("enumerate.c"))
                build = ["cc", "-O3", "-std=gnu11"]
                if flags & 2:
                    build.append("-march=native")
                subprocess.run([*build, src, "-lgmp", "-lm", "-o", exe], check=True)
            prefix = root / "run"
            subprocess.run(
                [exe, str(n), str(budget), prefix],
                stdout=subprocess.DEVNULL,
                check=True,
            )
            raw = assemble(prefix, flags & 1)
            if len(raw) != size or hashlib.sha256(raw).digest() != patch[:32]:
                raise ValueError("Witness enumeration differs on this build")
            if mode == 2:
                delta = zlib.decompress(patch[32:])
                raw = bytes(a ^ b for a, b in zip(raw, delta, strict=True))
            elif len(patch) != 32:
                raise ValueError("Unexpected residual")
        if len(raw) != size:
            raise ValueError("Invalid reconstructed length")
        with output.open("xb") as out:
            out.write(raw)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 archive.pyz OUTPUT")
    extract(Path(sys.argv[0]), Path(sys.argv[1]))
