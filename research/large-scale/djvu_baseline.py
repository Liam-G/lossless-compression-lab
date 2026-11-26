"""Lossless DjVu bitonal symbol coding for 1,728-bit rows, in bounded-height pages."""

import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--rows", type=int, default=8192)
    parser.add_argument("--separated", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory(dir=args.target.parent) as directory:
        scratch = Path(directory)
        if args.mode == "encode":
            pages = []
            with args.source.open("rb") as source:
                while rows := source.read(216 * args.rows):
                    height, tail = divmod(len(rows), 216)
                    if tail:
                        raise ValueError("Expected whole 1,728-bit scanlines")
                    bitmap = scratch / "input.pbm"
                    bitmap.write_bytes(f"P4\n1728 {height}\n".encode() + rows)
                    page = scratch / f"page-{len(pages)}.djvu"
                    if args.separated:
                        page = page.with_suffix(".rle")
                        with page.open("xb") as output:
                            subprocess.run(
                                ["pbmtodjvurle", bitmap], stdout=output, check=True
                            )
                    else:
                        subprocess.run(
                            ["cjb2", "-dpi", "300", bitmap, page], check=True
                        )
                    pages.append(page)
            if args.separated:
                subprocess.run(
                    ["csepdjvu", "-d", "300", *pages, args.target], check=True
                )
            else:
                subprocess.run(["djvm", "-c", args.target, *pages], check=True)
        else:
            subprocess.run(
                [
                    "ddjvu",
                    "-format=pbm",
                    "-eachpage",
                    args.source,
                    scratch / "page-%04d.pbm",
                ],
                check=True,
            )
            with args.target.open("xb") as target:
                for page in sorted(scratch.glob("page-*.pbm")):
                    with Image.open(page) as image:
                        if image.width != 1728 or image.mode != "1":
                            raise ValueError("Unexpected decoded raster")
                        target.write(image.tobytes("raw", "1;I"))


if __name__ == "__main__":
    main()
