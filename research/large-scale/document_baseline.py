"""Encode 1,728-bit packed rows in a conventional monochrome image container."""

import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from PIL import Image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("group4", "png1", "decode", "jbig", "unjbig"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    # The benchmark source geometry is known; each bundle contains about 200 M pixels.
    Image.MAX_IMAGE_PIXELS = 400_000_000
    with a.output.open("xb") as out:
        if a.mode == "jbig":
            height, tail = divmod(a.input.stat().st_size, 216)
            if tail:
                raise ValueError("Expected whole rows")
            with TemporaryDirectory(dir=a.output.parent) as directory:
                pbm = Path(directory) / "input.pbm"
                with pbm.open("xb") as f:
                    f.write(f"P4\n1728 {height}\n".encode())
                    f.write(a.input.read_bytes())
                packed = Path(directory) / "image.jbg"
                subprocess.run(["pbmtojbg", "-q", pbm, packed], check=True)
                out.write(packed.read_bytes())
        elif a.mode == "unjbig":
            with TemporaryDirectory(dir=a.output.parent) as directory:
                pbm = Path(directory) / "decoded.pbm"
                subprocess.run(["jbgtopbm", a.input, pbm], check=True)
                with Image.open(pbm) as im:
                    if im.mode != "1" or im.width != 1728:
                        raise ValueError("Unexpected document raster")
                    out.write(im.tobytes("raw", "1;I"))
        elif a.mode == "decode":
            with Image.open(a.input) as im:
                if im.mode != "1" or im.width != 1728:
                    raise ValueError("Invalid packed-page geometry")
                out.write(im.tobytes("raw", "1;I"))
        else:
            data = a.input.read_bytes()
            height, tail = divmod(len(data), 216)
            if tail:
                raise ValueError("Expected complete 1,728-bit rows")
            im = Image.frombytes("1", (1728, height), data, "raw", "1;I")
            if a.mode == "group4":
                im.save(out, "TIFF", compression="group4", tiffinfo={262: 0})
            else:
                im.save(out, "PNG", optimize=True)


if __name__ == "__main__":
    main()
