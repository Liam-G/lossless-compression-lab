"""Render distinct manual pages as one stream of MSB-first, black-one, 1,728-bit rows."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from PIL import Image


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manual_directory", type=Path)
    p.add_argument("output_directory", type=Path)
    p.add_argument(
        "--transfer",
        type=Path,
        help="Render the first 64 pages of an independent PDF instead",
    )
    p.add_argument(
        "--name",
        default="manual-transfer",
        help="Dataset name for an independent manual",
    )
    a = p.parse_args()
    a.output_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = a.output_directory / "documents.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    groups = {
        "manual-graphs": ["dotguide", "neatoguide"],
        "manual-library": ["libguide"],
    }
    if a.transfer:
        groups = {a.name: [a.transfer.stem]}
    for name, manuals in groups.items():
        out = a.output_directory / name
        books = []
        with out.open("xb") as raw:
            for manual in manuals:
                pdf = a.transfer or a.manual_directory / (manual + ".pdf")
                with TemporaryDirectory() as tmp:
                    prefix = Path(tmp) / "p"
                    subprocess.run(
                        [
                            "pdftoppm",
                            *(["-l", "64"] if a.transfer else []),
                            "-mono",
                            "-scale-to-x",
                            "1728",
                            "-scale-to-y",
                            "-1",
                            pdf,
                            prefix,
                        ],
                        check=True,
                    )
                    bitmaps = sorted(
                        Path(tmp).glob("p-*.pbm"),
                        key=lambda f: int(f.stem.rsplit("-", 1)[1]),
                    )
                    heights = []
                    for page in bitmaps:
                        with Image.open(page) as im:
                            if im.width != 1728 or im.mode != "1":
                                raise ValueError("Unexpected document raster geometry")
                            raw.write(im.tobytes("raw", "1;I"))
                            heights.append(im.height)
                    books.append(
                        dict(source=pdf.name, sha256=digest(pdf), page_heights=heights)
                    )
        manifest[name] = dict(
            bytes=out.stat().st_size, sha256=digest(out), width_bits=1728, books=books
        )
    (a.output_directory / "documents.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
