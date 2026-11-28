"""Expose the complete reversible representation before the chosen block compressor."""

import argparse
import struct
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import zstandard as zstd
from bench import commands

# Each specification mirrors the original decoder's record header and stored mode.
# The last field in every record is the body length. Only backend frames are removed.
FORMATS = {
    b"SFF1": (">BBBI", 3, "shared-shared"),
    b"LTP1": (">BBBHI", 3, "lattice-joint"),
    b"MKR1": (">BBII", 5, "modular-joint"),
    b"TVW1": (">BBI", 3, "views-bwt"),
    b"F4D1": (">BBI", 3, "four-joint"),
    b"LCA1": (">BBI", 6, "learned-coupled"),
}
PROFILES = (
    "pilot01-fixed-direct",
    "pilot01-adaptive-ratios",
    "shared-shared",
    "lattice-joint",
    *(
        "lattice-rows-" + mode
        for mode in (
            "literal",
            "framed",
            "above",
            "delta",
            "columns",
            "joint",
            "select",
            "fields",
            "positions",
            "field-positions",
            "route-select",
            "prefix",
            "field-prefix",
        )
    ),
    *(
        "checker-bitmap-" + name
        for name in (
            *(
                p + "-" + form
                for p in ("direct", "xor", "orbit")
                for form in ("flat", "tree", "book", "planes", "hot", "hotplanes")
            ),
            "rotated-book",
            "select",
        )
    ),
    "modular-joint",
    "views-bwt",
    "views-mtf",
    "four-direct",
    "four-rank",
    "four-equivalent",
    "four-orbit",
    "four-joint",
    "learned-coupled",
    "witness-joint",
    "pilot06-checker-3-fixed",
    "pilot07-pre-1",
    "pilot10-fixed",
    "pilot10-conditional",
    "pilot11-dag",
)


def take(source, size):
    data = source.read(size)
    if len(data) != size:
        raise ValueError("Truncated representation")
    return data


def frame_offset(magic, fields):
    """Bytes preceding the frame, or None for a literal body."""
    if magic == b"SFF1" and fields[0] == 0:
        return None
    if magic == b"LTP1" and fields[1] == 255:
        return None
    if magic == b"MKR1" and fields[0] == 0:
        return None
    if magic == b"TVW1" and fields[1] == 3:
        return None
    if magic == b"F4D1" and fields[0] & 3 == 2:
        return None
    if magic == b"LCA1":
        if fields[0] == 255:
            return None
        return 32 * (fields[0] >= 2) + 8 * bool(fields[1] & 2)
    return 0


def witness_body(src, dst, transform):
    size_mode = take(src, 9)
    dst.write(size_mode)
    mode = size_mode[-1]
    if mode <= 1:
        body = src.read()
        dst.write(transform(body) if mode else body)
        return
    if mode not in (2, 3, 4):
        raise ValueError("Unknown witness mode")
    for columns in (6, 9):
        dst.write(take(src, 4))  # Number of witnesses in this group.
        for _ in range(1 if mode == 3 else columns):
            compressed = True
            if mode != 3:
                kind = take(src, 1)
                dst.write(kind)
                compressed = kind != b"\0"  # All-zero column has no body.
            length = int.from_bytes(take(src, 4), "big")
            data = take(src, length)
            if compressed:
                data = transform(data)
            dst.write(len(data).to_bytes(4, "big"))
            dst.write(data)
    if src.read(1):
        raise ValueError("Trailing witness data")


def transcode(data, restore=False):
    src = BytesIO(data)
    tag = take(src, 4)
    for outer, prepared, decoder in (
        (b"RGR1", b"RGP1", "lattice-rows-select"),
        (b"CBZ1", b"CBP1", "checker-bitmap-select"),
    ):
        if tag == outer and not restore:
            stream = zstd.ZstdDecompressor().decompress(src.read())
            if not stream.startswith(prepared):
                raise ValueError("Invalid prepared representation")
            return stream, decoder
        if tag == prepared and restore:
            return outer + zstd.ZstdCompressor(level=3).compress(data), decoder
    if tag == b"LCP1" and len(data) >= 14 and data[4] in (1, 6, 7, 10, 11):
        # These five formats serialize their records without a terminal general compressor.
        return data, "collection"
    magic = tag[:3] + b"1" if restore and tag.endswith(b"P") else tag
    if magic not in FORMATS and magic != b"WFW1":
        raise ValueError(f"Unsupported format {tag!r}")
    if restore != (tag != magic):
        raise ValueError("Incorrect direction for this stream")
    dst = BytesIO()
    dst.write(magic if restore else magic[:3] + b"P")
    level = 9 if magic == b"WFW1" else FORMATS[magic][1]
    convert = (
        zstd.ZstdCompressor(level=level).compress
        if restore
        else zstd.ZstdDecompressor().decompress
    )
    if magic == b"WFW1":
        witness_body(src, dst, convert)
        return dst.getvalue(), "witness-joint"
    record_format, _, codec = FORMATS[magic]
    record = struct.Struct(record_format)
    dst.write(take(src, 16 if magic == b"LCA1" else 8))
    while header := src.read(record.size):
        *fields, length = record.unpack(header)
        body = take(src, length)
        offset = frame_offset(magic, fields)
        if offset is not None:
            body = body[:offset] + convert(body[offset:])
        dst.write(record.pack(*fields, len(body)))
        dst.write(body)
    return dst.getvalue(), codec


def prepare(source, profile, work):
    native = work / "selected"
    enc, _, env, _ = commands(profile, source, native, work / "unused", work)
    subprocess.run(enc, env=env, check=True, stdout=subprocess.DEVNULL)
    return transcode(native.read_bytes())[0]


def restore(data, output, work):
    native, codec = transcode(data, restore=True)
    archive = work / "selected"
    archive.write_bytes(native)
    if codec == "collection":
        dec = [
            sys.executable,
            Path(__file__).with_name("collection.py"),
            "decode",
            archive,
            output,
        ]
        env = None
    else:
        _, dec, env, _ = commands(codec, work / "unused", archive, output, work)
    subprocess.run(dec, env=env, check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    enc = sub.add_parser("prepare")
    enc.add_argument("profile", choices=PROFILES)
    for command in (enc, sub.add_parser("restore")):
        command.add_argument("source", type=Path)
        command.add_argument("output", type=Path)
    a = parser.parse_args()
    with TemporaryDirectory(dir=a.output.parent) as tmp:
        if a.action == "prepare":
            prepared = prepare(a.source, a.profile, Path(tmp))
            with a.output.open("xb") as dest:
                dest.write(prepared)
        else:
            restore(a.source.read_bytes(), a.output, Path(tmp))
