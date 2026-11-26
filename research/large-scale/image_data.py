"""Materialize three independent RGB rasters from locally installed Hyprland wallpapers."""

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("images", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    manifest = {}
    for name in ("wall0", "wall1", "wall2"):
        path = a.images / (name + ".png")
        with Image.open(path) as original:
            image = original.convert("RGB")
            w, h = image.size
            target = a.output / (name + ".ppm")
            with target.open("xb") as out:
                out.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
                out.write(image.tobytes())
        with target.open("rb") as f:
            manifest[target.name] = dict(
                width=w,
                height=h,
                bytes=target.stat().st_size,
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                sha256=hashlib.file_digest(f, "sha256").hexdigest(),
            )
    (a.output / "images.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
