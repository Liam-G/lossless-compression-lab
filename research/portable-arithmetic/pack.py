"""Choose the least expensive complete ZIP application, charging its decoder and directory."""

import argparse
from io import BytesIO
import json
import lzma
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
import zstandard as zstd

HERE = Path(__file__).resolve().parent
CARRY = HERE.parent / "carry-trees"
sys.path.insert(0, str(CARRY))
import sparse_scale


def member(name, mode=b""):
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.comment = mode
    return info


def application(data, mode):
    target = BytesIO()
    sources = {"__main__.py": HERE / "extract.py"}
    if mode == b"SCL1":
        sources.update({f: CARRY / f for f in ("arithmetic.py", "sparse_reader.py")})
    with ZipFile(target, "w") as bundle:
        for name, source in sources.items():
            bundle.writestr(
                member(name),
                source.read_bytes(),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )
        bundle.writestr(member("payload", mode), data, compress_type=ZIP_STORED)
    return target.getvalue()


def encode(src, dest, profile):
    data = src.read_bytes()
    best = application(data, b"RAW")
    stats = dict(
        method="RAW", payload_bytes=len(data), delivery_overhead=len(best) - len(data)
    )

    def consider(mode, payload):
        nonlocal best, stats
        candidate = application(payload, mode)
        if len(candidate) < len(best):
            best = candidate
            stats = dict(
                method=mode.decode(),
                payload_bytes=len(payload),
                delivery_overhead=len(best) - len(payload),
            )

    if profile != "literal":
        consider(b"ZSTD", zstd.ZstdCompressor(level=9).compress(data))
        # On essentially incompressible files a full extreme XZ trial is costly.
        # The fast profile admits XZ when its 1 MiB prefix proxy saves at least 1%.
        sample = data[: 1 << 20]
        if sample and len(lzma.compress(sample, preset=3)) < 0.99 * len(sample):
            consider(b"XZ", lzma.compress(data, preset=6))
    if profile in ("joint", "informed"):
        archive, _ = sparse_scale.encode(data, profile)
        consider(b"SCL1", archive)
    with dest.open("xb") as output:
        output.write(best)
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument(
        "--profile",
        choices=("literal", "standard", "joint", "informed"),
        default="joint",
    )
    a = p.parse_args()
    print(json.dumps(encode(a.source, a.output, a.profile)))
