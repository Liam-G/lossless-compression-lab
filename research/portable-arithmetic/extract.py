"""Extract this archive using only its bundled decoder and the Python standard library."""

import sys
from zipfile import ZipFile


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 archive.pyz OUTPUT")
    with ZipFile(sys.argv[0]) as package:
        mode = package.getinfo("payload").comment
        data = package.read("payload")
    if mode == b"SCL1":
        from sparse_reader import decode

        data = decode(data)
    elif mode == b"XZ":
        from lzma import decompress

        data = decompress(data)
    elif mode == b"ZSTD":
        from compression.zstd import decompress

        data = decompress(data)
    elif mode != b"RAW":
        raise ValueError("Unknown package encoding")
    with open(sys.argv[1], "xb") as result:
        result.write(data)


if __name__ == "__main__":
    main()
