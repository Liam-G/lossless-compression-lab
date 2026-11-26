"""Run an LCX1 experiment from any working directory."""

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import multiprocessing
import platform
import random
import resource
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from time import perf_counter

import wire

ROOT = Path(__file__).resolve().parent
SEED = 190732
LAUNCHER = """import sys, zipfile, codec, wire
with zipfile.ZipFile(sys.argv[0]) as bundle:
    data, _ = wire.decode(codec, bundle.read('archive'), bundle.read('reference'))
    sys.stdout.buffer.write(data)
"""


def load(number, name):
    (directory,) = (ROOT / "experiments").glob(f"{int(number):02d}-*")
    spec = importlib.util.spec_from_file_location(name, directory / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bundle(codec, archive, reference):
    result = io.BytesIO()
    files = {"__main__.py": LAUNCHER, "archive": archive, "reference": reference}
    for name in ("codec", "wire", *getattr(codec, "DEPENDENCIES", ())):
        source = Path(codec.__file__) if name == "codec" else ROOT / (name + ".py")
        files[name + ".py"] = source.read_bytes()
    with zipfile.ZipFile(result, "w") as output:
        for name, content in files.items():
            output.writestr(zipfile.ZipInfo(name), content)
    return result.getvalue()


def trial(job):
    number, profile, data, ref = job
    codec = load(number, "codec")
    start = perf_counter()
    archive, details = wire.encode(codec, data, profile, ref)
    encoded = perf_counter()
    restored, extra = wire.decode(codec, archive, ref)
    end = perf_counter()
    if restored != data:
        raise ValueError("Round trip failed")
    return dict(
        profile=profile,
        archive_bytes=len(archive),
        metadata_bytes=details.pop("metadata_bytes"),
        encode_ms=round(1000 * (encoded - start), 3),
        decode_ms=round(1000 * (end - encoded), 3),
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        verified=True,
        bundle_bytes=len(bundle(codec, archive, ref)),
        details=json.dumps(details | extra, sort_keys=True),
    ), archive


def decoder_memory(job):
    number, archive, reference, original = job
    decoded, _ = wire.decode(load(number, "codec"), archive, reference)
    if decoded != original:
        raise ValueError("Isolated decoder mismatch")
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def csv_file(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bench(number, codec, output):
    if sys.platform != "linux":
        raise ValueError("Benchmark memory measurement requires Linux")
    version = subprocess.check_output(["zstd", "--version"], text=True).strip()
    driver = load(number, "benchmark")
    cases = list(driver.datasets(codec, ROOT / "fixtures", random.Random(SEED)))
    name, planted, ref = cases[0]
    cases.insert(1, ("uniform", random.Random(SEED + 1).randbytes(len(planted)), ref))
    output.mkdir(parents=True, exist_ok=False)
    trials, comparisons = [], []
    collections = {}
    with multiprocessing.get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        for name, data, ref in cases:
            zstd = subprocess.check_output(["zstd", "-q3c"], input=data)
            if subprocess.check_output(["zstd", "-qdc"], input=zstd) != data:
                raise ValueError("Zstd round trip failed")
            row = dict(
                dataset=name,
                input_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                reference_bytes=len(ref),
                reference_sha256=hashlib.sha256(ref).hexdigest() if ref else "",
                zstd_bytes=len(zstd),
            )
            jobs = [(number, profile, data, ref) for profile in codec.PROFILES]
            results = pool.map(trial, jobs, chunksize=1)
            sizes = {}
            for measurement, archive in results:
                if number == 11:
                    measurement["decoder_peak_rss_kib"] = pool.apply(
                        decoder_memory, ((number, archive, ref, data),)
                    )
                trials.append(row | measurement)
                sizes[measurement["profile"]] = len(archive)
                if number == 15 and name.endswith(".elf"):
                    collections.setdefault(measurement["profile"], {})[name] = archive
                if number == 7:
                    dest = output / "archives"
                    dest.mkdir(exist_ok=True)
                    (dest / f"{name}.{measurement['profile']}.lcx").write_bytes(archive)
            best = min(sizes, key=sizes.get)
            comparison = (
                row
                | sizes
                | dict(
                    best=best,
                    best_vs_raw=len(data) - sizes[best],
                    best_vs_zstd=len(zstd) - sizes[best],
                    delivered_with_base=len(ref) + sizes[best],
                )
            )
            for label, a, b, both in getattr(codec, "CONTRASTS", ()):
                comparison[label] = min(sizes[a], sizes[b]) - sizes[both]
            comparisons.append(comparison)
    if collections:
        collection_rows = []
        originals = {name: data for name, data, ref in cases}
        with tempfile.TemporaryDirectory() as temporary:
            for profile, archives in collections.items():
                path = Path(temporary) / (profile + ".pyz")
                with (
                    zipfile.ZipFile(io.BytesIO(bundle(codec, b"", b""))) as template,
                    zipfile.ZipFile(path, "w") as delivery,
                ):
                    for name in template.namelist():
                        if name == "archive":
                            continue
                        content = template.read(name)
                        if name == "__main__.py":
                            content = content.replace(
                                b"bundle.read('archive')", b"bundle.read(sys.argv[1])"
                            )
                        delivery.writestr(zipfile.ZipInfo(name), content)
                    for name, archive in archives.items():
                        delivery.writestr(zipfile.ZipInfo(name), archive)
                for name in archives:
                    if (
                        subprocess.check_output([sys.executable, "-I", path, name])
                        != originals[name]
                    ):
                        raise ValueError("Collection decoder mismatch")
                collection_rows.append(
                    dict(
                        profile=profile,
                        files=len(archives),
                        archive_bytes=sum(map(len, archives.values())),
                        bundle_with_one_decoder_bytes=path.stat().st_size,
                    )
                )
        csv_file(output / "collection.csv", collection_rows)
    csv_file(output / "trials.csv", trials)
    csv_file(output / "comparison.csv", comparisons)
    manifest = dict(
        python=sys.version,
        platform=platform.platform(),
        zstd=version,
        seed=SEED,
        sources={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                Path(codec.__file__),
                Path(driver.__file__),
                Path(wire.__file__),
                Path(__file__),
                *(ROOT / (name + ".py") for name in getattr(codec, "DEPENDENCIES", ())),
            ]
        },
    )
    (output / "environment.json").write_text(json.dumps(manifest, indent=2) + "\n")


def check(number, codec):
    rng = random.Random(SEED)
    for size in (0, 1, 7, 16, 33, 97):
        data = rng.randbytes(size)
        ref = rng.randbytes(size + 2)
        for profile in codec.PROFILES:
            archive, _ = wire.encode(codec, data, profile, ref)
            if wire.decode(codec, archive, ref)[0] != data:
                raise AssertionError((number, profile, size))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "delivered.pyz"
        path.write_bytes(bundle(codec, archive, ref))
        if subprocess.check_output([sys.executable, "-I", path], cwd=directory) != data:
            raise AssertionError("Bundle failed isolated decoding")
    load(number, "test_codec").verify(codec)
    print(f"{number:02d} passed {6 * len(codec.PROFILES)} round trips and isolated bundle decoding")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=int, choices=range(2, 17))
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("encode", "decode"):
        cmd = sub.add_parser(action)
        cmd.add_argument("input", type=Path)
        cmd.add_argument("output", type=Path)
        cmd.add_argument("--reference", type=Path)
        if action == "encode":
            cmd.add_argument("--profile")
    sub.add_parser("benchmark").add_argument("output", type=Path)
    sub.add_parser("test")
    args = parser.parse_args()
    codec = load(args.experiment, "codec")
    if args.command == "benchmark":
        bench(args.experiment, codec, args.output)
    elif args.command == "test":
        check(args.experiment, codec)
    else:
        ref = args.reference.read_bytes() if args.reference else b""
        data = args.input.read_bytes()
        if args.command == "encode":
            profile = args.profile or codec.PROFILES[-1]
            if profile not in codec.PROFILES:
                parser.error("Available profiles: " + ", ".join(codec.PROFILES))
            result, _ = wire.encode(codec, data, profile, ref)
        else:
            result, _ = wire.decode(codec, data, ref)
        with args.output.open("xb") as out:
            out.write(result)


if __name__ == "__main__":
    main()
