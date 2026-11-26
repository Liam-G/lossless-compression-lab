"""Restore a computational cost-table package using its included enumerator."""

from pathlib import Path
import os
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 archive.pyz OUTPUT")
    with ZipFile(sys.argv[0]) as package, TemporaryDirectory() as tmp:
        work = Path(tmp)
        data = package.read("table")
        magic, size, mode, n, k = struct.unpack_from(">4sQBBB", data)
        body = data[15:]
        if magic != b"WCT1":
            raise ValueError("Invalid cost-table member")
        if mode == 0:
            raw = body
        elif mode == 1:
            from compression.zstd import decompress

            raw = decompress(body)
        else:
            if not 9 <= n <= 26 or size != 2 << n:
                raise ValueError("Invalid formula dimensions")
            if mode == 2:
                a = bytearray(1 << n)
                a[0] = 255
                for b in range(1, n + 1):
                    lower, upper = 1 << (b - 1), 1 << b
                    a[lower:upper] = bytes([2 * b + 1]) * (upper - lower)
                    a[upper - 1] += 1
                raw = bytes(a) + b"\xff" * (1 << n)
            elif mode == 3 and 8 <= k <= n - 1:
                exe = work / "enumerate"
                env = os.environ.copy()
                if "enumerate.c" in package.namelist():
                    src = work / "enumerate.c"
                    src.write_bytes(package.read("enumerate.c"))
                    subprocess.run(
                        ["cc", "-O3", "-std=gnu11", src, "-lgmp", "-lm", "-o", exe],
                        check=True,
                    )
                else:
                    exe.write_bytes(package.read("enumerate"))
                    exe.chmod(0o700)
                if "libgmp.so.10" in package.namelist():
                    (work / "libgmp.so.10").write_bytes(package.read("libgmp.so.10"))
                    env["LD_LIBRARY_PATH"] = str(work)
                subprocess.run(
                    [exe, str(n), str(k), work / "pred"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
                raw = (work / "pred.f3.u8").read_bytes() + (
                    work / "pred.f6.u8"
                ).read_bytes()
            else:
                raise ValueError("Invalid enumeration mode or budget")
            if body:
                from compression.zstd import decompress

                residual = decompress(body)
                raw = bytes(x ^ y for x, y in zip(raw, residual, strict=True))
        if len(raw) != size:
            raise ValueError("Incorrect cost-table size")
        with open(sys.argv[1], "xb") as out:
            out.write(raw)


if __name__ == "__main__":
    main()
