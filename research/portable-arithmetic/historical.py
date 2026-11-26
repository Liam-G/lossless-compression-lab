"""Rebuild the QWX8 weight branch and verify the original complete V15 package under isolation."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from weight_branch import weight_branch

Q_SHA = "5f7921346a0b045f6196be84b1c794344455a47eaf84bf9ef81b8707559ca547"
V15_SHA = "b75a7dd33d17ce6004fdb98173e928f244fd155812e8fc9f2b8f9461c0729351"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify(workspace, report):
    folder = workspace / "lab/hutter/divisors"
    lanes = folder / "q-coda-ricerca"
    before = lanes / "qwx7/pesi.qwx7"
    after = lanes / "qwx8/pesi.qwx8"
    original = lanes / "qwx8/Q.portatile-v15.pyz"
    raw = folder / "work/cofattore-Q.base256"
    if sha(original) != V15_SHA or sha(raw) != Q_SHA:
        raise ValueError("Different source package or raw target")
    branch, old_dir, new_dir = weight_branch(before.read_bytes())
    if branch != after.read_bytes():
        raise ValueError("Weight branch differs from the recorded V15 input")
    with TemporaryDirectory(dir=report.parent) as tmp:
        reconstructed = Path(tmp) / "decoded"
        start = perf_counter()
        subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                original.resolve(),
                "decode",
                reconstructed.resolve(),
            ],
            cwd=tmp,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        seconds = perf_counter() - start
        subprocess.run(["cmp", raw, reconstructed], check=True)
        result = dict(
            package_bytes=original.stat().st_size,
            package_sha256=V15_SHA,
            input_bytes=raw.stat().st_size,
            input_sha256=Q_SHA,
            previous_weight_sha256=sha(before),
            recreated_weight_bytes=len(branch),
            recreated_weight_sha256=sha(after),
            old_directory_bytes=old_dir,
            new_directory_bytes=new_dir,
            decode_seconds=round(seconds, 3),
            byte_equal=True,
        )
    with report.open("x") as out:
        out.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace", type=Path)
    p.add_argument("report", type=Path)
    a = p.parse_args()
    verify(a.workspace, a.report)
