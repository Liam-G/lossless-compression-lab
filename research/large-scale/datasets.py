"""Materialize fixed, disjoint corpus inputs. Every primary input is at least 20 MiB."""

import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MIB = 1 << 20
MINIMUM = 20 * MIB
CASES = {
    "wiki-dev": [("enwik8/enwik8", 0, 24 * MIB)],
    "wiki-transfer": [("enwik8/enwik8", 64 * MIB, 24 * MIB)],
    "numerical": [
        (name, 0, None) for name in ("silesia/mr", "silesia/x-ray", "silesia/sao")
    ],
    "nci": [("silesia/nci", 0, None)],
    "mozilla": [("silesia/mozilla", 0, None)],
    "samba": [("silesia/samba", 0, None)],
    "webster": [("silesia/webster", 0, None)],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    manifest = {}
    for name, members in CASES.items():
        target = args.output / name
        parts = []
        with target.open("xb") as stream:
            for rel, start, size in members:
                with (args.corpus / rel).open("rb") as source:
                    source.seek(start)
                    data = source.read() if size is None else source.read(size)
                if size is not None and len(data) != size:
                    raise ValueError(rel)
                stream.write(data)
                parts.append(
                    dict(
                        path=rel,
                        offset=start,
                        bytes=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),
                    )
                )
        if target.stat().st_size < MINIMUM:
            raise ValueError(f"Undersized corpus: {name}")
        with target.open("rb") as source:
            manifest[name] = dict(
                bytes=target.stat().st_size,
                sha256=hashlib.file_digest(source, "sha256").hexdigest(),
                members=parts,
            )
    noise = Random(0x5A39C121).randbytes(24 * MIB)
    with (args.output / "uniform").open("xb") as stream:
        stream.write(noise)
    manifest["uniform"] = dict(
        bytes=len(noise),
        sha256=hashlib.sha256(noise).hexdigest(),
        generator="Python Random(0x5A39C121).randbytes(24 << 20)",
    )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
