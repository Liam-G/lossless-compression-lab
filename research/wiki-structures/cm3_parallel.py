"""Parallel container for independent cm3 members."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time


MAGIC = b"C3P1"
PREFIX = struct.Struct("<4sI")
LENGTH = struct.Struct("<Q")
BUFFER_SIZE = 1 << 20
MAX_HEADER = 1 << 20


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_config(path):
    config = dict(field.split("=", 1) for field in path.read_text().split())
    if (
        not config
        or "CM3_PRIME_PATH" in config
        or any(not name.startswith("CM3_") for name in config)
    ):
        raise ValueError("Expected a cm3 configuration")
    return config


def copy_exact(source, target, count):
    while count:
        data = source.read(min(count, BUFFER_SIZE))
        if not data:
            raise ValueError("Truncated archive or input")
        target.write(data)
        count -= len(data)


def slice_file(source, target, offset, length):
    with source.open("rb") as stream, target.open("wb") as output:
        stream.seek(offset)
        copy_exact(stream, output, length)


def run_members(jobs, operation, workers, notify, first=0):
    if workers < 1:
        raise ValueError("At least one worker is required")
    results = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
        tasks = {
            pool.submit(operation, index + first, *job): index
            for index, job in enumerate(jobs)
        }
        for done in as_completed(tasks):
            index = tasks[done]
            results[index] = done.result()
            if notify:
                notify(index + first + 1, len(jobs) + first, *results[index])
    return results


def run_cm3(binary, config, mode, source, destination, primer=None):
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("CM3_")
    }
    env.update(config)
    if primer is not None:
        env["CM3_PRIME_PATH"] = str(primer.resolve())
    result = subprocess.run(
        [str(binary.resolve()), mode, str(source), str(destination)],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode or not destination.is_file():
        raise RuntimeError(
            f"cm3 {mode} failed for {source.name}: {result.stderr.strip()}"
        )


def compress(
    source, archive, binary, config, members, workers, notify=None, prime_bytes=0
):
    if members < 1:
        raise ValueError("At least one member is required")
    if source.resolve() == archive.resolve():
        raise ValueError("Input and output must be different files")
    size = source.stat().st_size
    if prime_bytes < 0 or (prime_bytes and prime_bytes >= size):
        raise ValueError("The primer must be shorter than the input")
    body_size = size - prime_bytes
    members = min(members, max(1, body_size))
    boundaries = [
        prime_bytes + index * body_size // members for index in range(members + 1)
    ]
    if prime_bytes:
        boundaries.insert(0, 0)
    jobs = [(start, stop - start) for start, stop in zip(boundaries, boundaries[1:])]
    with tempfile.TemporaryDirectory(prefix="cm3p-", dir=archive.parent) as temporary:
        work = Path(temporary)
        primer = None
        if prime_bytes:
            primer = work / "primer"
            slice_file(source, primer, 0, prime_bytes)

        def encode(index, offset, raw_size):
            start = time.perf_counter()
            raw, packed = work / f"{index}.in", work / f"{index}.cm"
            slice_file(source, raw, offset, raw_size)
            run_cm3(binary, config, "c", raw, packed, primer if index else None)
            raw.unlink()
            with packed.open("rb") as stream:
                if stream.read(LENGTH.size) != LENGTH.pack(raw_size):
                    raise ValueError(f"Incorrect raw length in member {index}")
            return raw_size, packed.stat().st_size, time.perf_counter() - start

        results = run_members(jobs, encode, workers, notify)
        header = {
            "config": config,
            "sha256": sha256(source),
            "binary_sha256": sha256(binary),
            "members": [
                [raw_size, packed_size] for raw_size, packed_size, _ in results
            ],
        }
        if prime_bytes:
            header["prime_bytes"] = prime_bytes
        metadata = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
        if len(metadata) > MAX_HEADER:
            raise ValueError("Archive header is too large")
        staged = work / "archive"
        with staged.open("wb") as output:
            output.write(PREFIX.pack(MAGIC, len(metadata)))
            output.write(metadata)
            for index in range(len(results)):
                with (work / f"{index}.cm").open("rb") as member:
                    shutil.copyfileobj(member, output, BUFFER_SIZE)
        staged.replace(archive)
    return header


def read_header(archive):
    with archive.open("rb") as stream:
        prefix = stream.read(PREFIX.size)
        if len(prefix) != PREFIX.size:
            raise ValueError("Truncated archive header")
        magic, metadata_size = PREFIX.unpack(prefix)
        if magic != MAGIC or not 1 <= metadata_size <= MAX_HEADER:
            raise ValueError("Invalid archive header")
        header = json.loads(stream.read(metadata_size))
    offset = PREFIX.size + metadata_size
    jobs = []
    for raw_size, packed_size in header["members"]:
        if (
            type(raw_size) is not int
            or raw_size < 0
            or type(packed_size) is not int
            or packed_size < 12
        ):
            raise ValueError("Invalid member lengths")
        jobs.append((offset, raw_size, packed_size))
        offset += packed_size
    if not jobs or offset != archive.stat().st_size:
        raise ValueError("Archive length does not match its members")
    prime_bytes = header.get("prime_bytes", 0)
    if (
        type(prime_bytes) is not int
        or prime_bytes < 0
        or (prime_bytes and (len(jobs) < 2 or prime_bytes != jobs[0][1]))
    ):
        raise ValueError("Invalid primer length")
    return header, jobs


def decompress(archive, destination, binary, config, workers, notify=None):
    if archive.resolve() == destination.resolve():
        raise ValueError("Input and output must be different files")
    header, jobs = read_header(archive)
    if config != header["config"] or sha256(binary) != header["binary_sha256"]:
        raise ValueError(
            "The archive requires the cm3 binary and configuration used to create it"
        )
    with tempfile.TemporaryDirectory(
        prefix="cm3p-", dir=destination.parent
    ) as temporary:
        work = Path(temporary)
        primer = work / "0.out" if header.get("prime_bytes", 0) else None

        def decode(index, offset, raw_size, packed_size):
            start = time.perf_counter()
            packed, raw = work / f"{index}.cm", work / f"{index}.out"
            slice_file(archive, packed, offset, packed_size)
            with packed.open("rb") as stream:
                if stream.read(LENGTH.size) != LENGTH.pack(raw_size):
                    raise ValueError(f"Incorrect raw length in member {index}")
            run_cm3(binary, config, "d", packed, raw, primer if index else None)
            if raw.stat().st_size != raw_size:
                raise ValueError(f"Wrong decoded length in member {index}")
            return raw_size, packed_size, time.perf_counter() - start

        if primer is None:
            run_members(jobs, decode, workers, notify)
        else:
            first_member = decode(0, *jobs[0])
            if notify:
                notify(1, len(jobs), *first_member)
            run_members(jobs[1:], decode, workers, notify, first=1)
        staged = work / "decoded"
        with staged.open("wb") as output:
            for index in range(len(jobs)):
                with (work / f"{index}.out").open("rb") as member:
                    shutil.copyfileobj(member, output, BUFFER_SIZE)
        if sha256(staged) != header["sha256"]:
            raise ValueError("SHA-256 verification failed")
        staged.replace(destination)
    return header


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("c", "d"))
    parser.add_argument("binary", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--members", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--prime-bytes",
        type=int,
        default=0,
        help="encode this shared prefix once, then prime each remaining member",
    )
    args = parser.parse_args()
    config = read_config(args.config)

    def progress(index, members, raw, packed, elapsed):
        print(
            f"{args.mode} member {index}/{members}: {raw} -> {packed} bytes in {elapsed:.2f} s",
            flush=True,
        )

    if args.mode == "c":
        result = compress(
            args.source,
            args.destination,
            args.binary,
            config,
            args.members,
            args.workers,
            progress,
            prime_bytes=args.prime_bytes,
        )
    else:
        result = decompress(
            args.source, args.destination, args.binary, config, args.workers, progress
        )
    print(
        json.dumps(
            {
                "path": str(args.destination),
                "sha256": result["sha256"],
                "bytes": args.destination.stat().st_size,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
