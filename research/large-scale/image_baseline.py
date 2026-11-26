"""Standard lossless image containers on canonical 8-bit PPM input."""

import argparse
from pathlib import Path
from PIL import Image

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("op", choices=("png", "webp", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    with Image.open(a.input) as im, a.output.open("xb") as out:
        if a.op == "decode":
            rgb = im.convert("RGB")
            w, h = rgb.size
            out.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
            out.write(rgb.tobytes())
        elif a.op == "png":
            im.save(out, "PNG", optimize=True)
        else:
            im.save(out, "WEBP", lossless=True, method=6)
