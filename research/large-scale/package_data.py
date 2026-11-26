"""Recover complete raw tar byte streams from two locally cached revisions of each package."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PACKAGES = {
    "numpy-base": "python-numpy-2.5.4-1.1-x86_64_v3.pkg.tar.zst",
    "numpy-update": "python-numpy-2.5.5-1.1-x86_64_v3.pkg.tar.zst",
    "mesa-base": "mesa-3:26.2.6-1-x86_64_v3.pkg.tar.zst",
    "mesa-update": "mesa-3:26.3.1-4-x86_64_v3.pkg.tar.zst",
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=True, parents=True)
    result = {}
    for name, member in PACKAGES.items():
        src = a.cache / member
        target = a.out / name
        with target.open("xb") as out:
            subprocess.run(["zstd", "-dcq", src], stdout=out, check=True)
        result[name] = dict(
            bytes=target.stat().st_size,
            sha256=digest(target),
            package=member,
            package_sha256=digest(src),
        )
    (a.out / "packages.json").write_text(json.dumps(result, indent=2) + "\n")
