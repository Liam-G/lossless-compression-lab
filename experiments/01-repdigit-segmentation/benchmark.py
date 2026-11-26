"""Run the four RPS1 profiles on held-out controls and real TZif files (Linux)."""

import argparse
import csv
import hashlib
import io
import json
import multiprocessing
import platform
import random
import resource
import subprocess
import sys
import zipfile
from pathlib import Path
from time import perf_counter

import codec

HERE = Path(__file__).resolve().parent
SIZE = 4096
WIDTHS = (8, 9, 10, 12, 16, 24, 32)
DENSITIES = (25, 75)
SEED = 703921
RUNNER = """import sys
import zipfile
from codec import decode
with zipfile.ZipFile(sys.argv[0]) as bundle:
    sys.stdout.buffer.write(decode(bundle.read('payload.rps')))
"""


def package(archive):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, data in (("__main__.py", RUNNER), ("codec.py", (HERE / "codec.py").read_bytes()),
                           ("payload.rps", archive)):
            bundle.writestr(zipfile.ZipInfo(name), data)
    return buffer.getvalue()


def planted(width, density):
    """Use one random background and evenly spaced plants with alternating operators."""
    data = bytearray(random.Random(SEED).randbytes(SIZE))
    count = SIZE * density // (100 * width)
    for i in range(count):
        start = 3 + i * SIZE // count
        if i % 2:
            exponent = 12 * (8 * width // 12)
            number = ((1 << exponent) - 1) // 13
        else:
            number = (1 << (8 * width)) - 1
        data[start:start + width] = number.to_bytes(width, "big")
    assert len(data) == SIZE
    return bytes(data), count


def measure(job):
    data, profile = job
    start = perf_counter()
    table = codec.catalog(profile.endswith("ratios"))
    built = perf_counter()
    archive, stats = codec.encode(data, profile, table)
    encoded = perf_counter()
    restored = codec.decode(archive)
    decoded = perf_counter()
    if restored != data:
        raise ValueError(f"Round trip failed for {profile}")
    return dict(profile=profile, archive_bytes=len(archive), **stats,
                catalog_ms=round(1000 * (built - start), 3),
                search_and_encode_ms=round(1000 * (encoded - built), 3),
                decode_ms=round(1000 * (decoded - encoded), 3),
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                bundle_bytes=len(package(archive)), round_trip=True)


def datasets(zones):
    for width in WIDTHS:
        for density in DENSITIES:
            data, count = planted(width, density)
            yield f"plant-w{width}-d{density}", data, width, density, count
    yield "random", random.Random(SEED).randbytes(SIZE), "", "", 0
    for name in ("London", "Paris", "Zurich"):
        data = (zones / "Europe" / name).read_bytes()
        if not data.startswith(b"TZif"):
            raise ValueError(f"Expected TZif input for {name}")
        yield f"Europe/{name}", data, "", "", 0


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory for this run")
    parser.add_argument("--zoneinfo", type=Path, default=HERE / "fixtures/zoneinfo")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("The peak RSS measurement requires Linux")
    zstd = subprocess.check_output(["zstd", "--version"], text=True).strip()
    inputs = list(datasets(args.zoneinfo))
    args.output.mkdir(parents=True)
    rows, summary = [], []
    # One fresh worker per measurement keeps peak RSS local to the trial.
    with multiprocessing.get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        for name, data, width, density, count in inputs:
            compressed = subprocess.check_output(["zstd", "-q", "-3", "-c"], input=data)
            if subprocess.check_output(["zstd", "-qdc"], input=compressed) != data:
                raise ValueError("Zstd round trip failed")
            trials = pool.map(measure, [(data, p) for p in codec.PROFILES], chunksize=1)
            meta = dict(dataset=name, sha256=hashlib.sha256(data).hexdigest(), raw_bytes=len(data),
                        width=width, target_density_pct=density, plant_count=count)
            rows.extend(dict(**meta, **trial) for trial in trials)
            sizes = {t["profile"]: t["archive_bytes"] for t in trials}
            gain = min(sizes["adaptive-direct"], sizes["fixed-ratios"]) - sizes["adaptive-ratios"]
            best = min(sizes.values())
            summary.append(dict(**meta, **sizes, combined_gain_bytes=gain, zstd_bytes=len(compressed),
                                best_vs_raw_bytes=len(data) - best, best_vs_zstd_bytes=len(compressed) - best))
    write_csv(args.output / "trials.csv", rows)
    write_csv(args.output / "comparison.csv", summary)
    manifest = dict(python=sys.version, platform=platform.platform(), zstd=zstd, seed=SEED,
                    decoder_sha256=hashlib.sha256((HERE / "codec.py").read_bytes()).hexdigest())
    (args.output / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
