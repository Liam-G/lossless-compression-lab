"""Measure empirical byte entropy and paired whole-stream backend sizes on a reversible preprocessor."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
import zstandard

from bench import MINIMUM
from preprocess import PROFILES, prepare, transcode

HERE = Path(__file__).resolve().parent
BACKENDS = {
    "zstd-3": (["zstd", "-q", "-3", "-T1", "-c"], ["zstd", "-q", "-dc"]),
    "gzip-6": (["gzip", "-n", "-6", "-c"], ["gzip", "-dc"]),
    "xz-6": (["xz", "-6", "-T1", "-c"], ["xz", "-dc"]),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entropy(counts):
    counts = counts[counts > 0]
    if not len(counts):
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def describe(data):
    values = np.frombuffer(data, np.uint8)
    histogram = np.zeros(256, np.int64)
    pairs = np.zeros(65536, np.int64)
    step = 1 << 20
    for pos in range(0, len(values), step):
        chunk = values[pos : pos + step]
        histogram += np.bincount(chunk, minlength=256)
        start = max(1, pos)
        stop = pos + len(chunk)
        codes = (
            values[start - 1 : stop - 1].astype(np.uint16) * 256 + values[start:stop]
        )
        pairs += np.bincount(codes, minlength=65536)
    # Weight by the observed predecessors. The first byte has no predecessor.
    h1 = entropy(pairs) - entropy(pairs.reshape(256, 256).sum(axis=1))
    return dict(
        bytes=len(data), sha256=sha(data), h0=entropy(histogram), h1=max(0.0, h1)
    )


def measure(raw_path, profile, native, work):
    if raw_path.stat().st_size < MINIMUM:
        raise ValueError("Primary inputs must contain at least 20 MiB")
    raw = raw_path.read_bytes()
    if native:
        sha_raw = sha(raw)
        receipt_path = HERE / "results/archives.jsonl"
        known = {
            r["archive_sha256"]
            for r in map(json.loads, receipt_path.read_text().splitlines())
            if r["codec"] == profile and r["input_sha256"] == sha_raw
        }
        # A shortcut must reproduce the already verified native encoder on this input.
        encoded = native.read_bytes()
        if sha(encoded) not in known:
            raise ValueError(
                "Native archive does not match the published profile and input"
            )
        prepared = transcode(encoded)[0]
    else:
        prepared = prepare(raw_path, profile, work)
    path = work / "prepared"
    path.write_bytes(prepared)
    restored = work / "original"
    subprocess.run(
        [sys.executable, HERE / "preprocess.py", "restore", path, restored], check=True
    )
    if restored.read_bytes() != raw:
        raise ValueError("Inverse preprocessing failed")
    row = dict(
        dataset=raw_path.name,
        profile=profile,
        raw=describe(raw),
        prepared=describe(prepared),
        backends={},
        verified=True,
        zstandard_version=zstandard.__version__,
    )
    for name, (encode, decode) in BACKENDS.items():
        version = subprocess.check_output(
            [encode[0], "--version"], text=True
        ).splitlines()[0]
        result = dict(version=version, encode=encode, decode=decode)
        for label, data in (("raw", raw), ("prepared", prepared)):
            archive = subprocess.run(
                encode, input=data, capture_output=True, check=True
            ).stdout
            restored_stream = subprocess.run(
                decode, input=archive, capture_output=True, check=True
            ).stdout
            if restored_stream != data:
                raise ValueError(f"{name} failed on {label}")
            result[label] = dict(bytes=len(archive), sha256=sha(archive))
        row["backends"][name] = result
    return row


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("profile", choices=PROFILES)
    p.add_argument("input", type=Path)
    p.add_argument("receipt", type=Path)
    p.add_argument(
        "--native",
        type=Path,
        help="Reuse a native encode matching its published SHA-256",
    )
    a = p.parse_args()
    with TemporaryDirectory(dir=a.receipt.parent) as tmp:
        row = measure(a.input, a.profile, a.native, Path(tmp))
    with a.receipt.open("x") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
