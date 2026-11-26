"""Compare complete image containers using the known 1,728-pixel fax width."""

import argparse
import csv
import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, __version__ as pillow_version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    height, tail = divmod(len(data) * 8, 1728)
    if tail or not height:
        raise ValueError("Expected whole 1,728-bit rows")
    # A zero source bit is white. Both containers describe their own geometry.
    bitmap = Image.frombytes("1", (1728, height), data, "raw", "1;I")
    rows = []
    for name, fmt, options in [
        ("CCITT Group 4 TIFF, default strips", "TIFF", {"compression": "group4"}),
        (
            "CCITT Group 4 TIFF, single strip, white zero",
            "TIFF",
            {"compression": "group4", "tiffinfo": {262: 0, 278: height}},
        ),
        ("1-bit PNG", "PNG", {"optimize": True}),
    ]:
        buf = BytesIO()
        bitmap.save(buf, format=fmt, **options)
        buf.seek(0)
        with Image.open(buf) as restored:
            if restored.mode != "1" or restored.tobytes("raw", "1;I") != data:
                raise ValueError(f"Inexact fax reconstruction with {name}")
        rows.append(
            dict(
                codec=name,
                input_bytes=len(data),
                width=1728,
                height=height,
                archive_bytes=len(buf.getvalue()),
                sha256=hashlib.sha256(data).hexdigest(),
                pillow=pillow_version,
                verified=True,
            )
        )
    with args.output.open("x", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
