"""Regenerate the 28-bit census and retain only witnesses whose denominator exceeds one."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import numpy as np
from costs import EXE
from data import WITNESS


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def generate(dest):
    with TemporaryDirectory(dir=dest.parent) as temporary:
        prefix = Path(temporary) / "n28"
        summary = json.loads(subprocess.check_output([EXE, "28", "27", prefix]))
        path = prefix.with_suffix(".rec6.bin")
        records = np.memmap(path, mode="r", dtype="<u4").reshape(-1, 9)
        # R(c,b,r) = 1 exactly when c = 1 and r = 1.
        selected = records[(records[:, 5] != 1) | (records[:, 7] != 1)]
        with dest.open("xb") as stream:
            stream.write(WITNESS.pack(b"WIT1", 0, len(selected)))
            stream.write(selected.tobytes())
        return dict(
            bytes=dest.stat().st_size,
            sha256=digest(dest),
            bits=summary["N"],
            budget=summary["K"],
            original_records=len(records),
            selected_records=len(selected),
            complete_rec6_sha256=digest(path),
            complete_rec3_sha256=digest(prefix.with_suffix(".rec3.bin")),
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(json.dumps(generate(a.output), indent=2))
