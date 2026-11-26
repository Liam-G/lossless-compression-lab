"""Archive-level test of spatial neighborhoods on the full fax and frozen real slices."""

import argparse
import csv
import gzip
import hashlib
import lzma
from pathlib import Path
import random
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

ENGINE = Path(__file__).resolve().parents[1] / "build/shape"


def cases(root):
    rng = random.Random(48107)
    width = 257
    row = rng.getrandbits(width)
    mask = (1 << width) - 1
    rows = []
    for _ in range(2048):
        rows.append(format(row, f"0{width}b"))
        row = ((row << 1) ^ (row | (row >> 1))) & mask
    yield "rule30-open-257", int("".join(rows), 2).to_bytes(2048 * width // 8, "big")
    yield "noise", rng.randbytes(2048 * width // 8)
    for name in (
        "canterbury/ptt5",
        "canterbury/kennedy.xls",
        "silesia/mr",
        "silesia/x-ray",
        "enwik8/enwik8",
    ):
        with (root / name).open("rb") as f:
            yield name.split("/")[-1], f.read(1 << 20)


def font_cases(directory):
    """All unique decompressed PSF files, including their headers and Unicode tables."""
    hashes = set()
    for path in sorted(directory.glob("*.psf*.gz")):
        data = gzip.decompress(path.read_bytes())
        digest = hashlib.sha256(data).digest()
        if digest not in hashes:
            hashes.add(digest)
            yield path.stem, data
    if not hashes:
        raise ValueError("No compressed PSF fonts found")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corpus", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument(
        "--fonts",
        action="store_true",
        help="benchmark all unique PSF fonts in the input directory",
    )
    args = p.parse_args()
    args.output.mkdir(parents=True)
    rows = []
    for name, data in font_cases(args.corpus) if args.fonts else cases(args.corpus):
        xz = lzma.compress(data, preset=9 | lzma.PRESET_EXTREME)
        zstd = subprocess.check_output(["zstd", "-q3c"], input=data)
        assert (
            lzma.decompress(xz) == data
            and subprocess.check_output(["zstd", "-qdc"], input=zstd) == data
        )
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            inp = tmp / "input"
            inp.write_bytes(data)
            for mode in ("history", "encode"):
                arc, restored = tmp / mode, tmp / (mode + ".restored")
                start = perf_counter()
                subprocess.run([ENGINE, mode, inp, arc], check=True)
                middle = perf_counter()
                subprocess.run([ENGINE, "decode", arc, restored], check=True)
                end = perf_counter()
                if restored.read_bytes() != data:
                    raise ValueError("Spatial inverse mismatch")
                with arc.open("rb") as f:
                    header = f.read(15)
                rows.append(
                    dict(
                        dataset=name,
                        profile=mode,
                        input_bytes=len(data),
                        archive_bytes=arc.stat().st_size,
                        zstd3=len(zstd),
                        xz9e=len(xz),
                        row_bits=int.from_bytes(header[12:14], "big"),
                        model=header[14],
                        encode_s=round(middle - start, 4),
                        decode_s=round(end - middle, 4),
                        sha256=hashlib.sha256(data).hexdigest(),
                        verified=True,
                    )
                )
    with (args.output / "trials.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
