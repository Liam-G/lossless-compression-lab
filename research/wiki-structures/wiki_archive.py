"""Lossless Wikipedia views backed by the parallel cm3 container."""

import argparse
import json
from pathlib import Path
import shutil
import struct
from tempfile import TemporaryDirectory
from time import perf_counter

import cm3_parallel
import wiki_order
import wiki_templates


MAGIC = b"WCM1"
HEADER = struct.Struct("<4sB32s")
# View numbers are part of the file format. Add new entries at the end.
MODES = {
    "literal": (None, None),
    "template": (None, "template"),
    "arithmetic": (None, "arithmetic"),
    "title": ("title", None),
    "title-template": ("title", "template"),
    "similar": ("similar", None),
    "similar-template": ("similar", "template"),
}
MODE_NAMES = tuple(MODES)


def transform(data, mode):
    ordering, generator = MODES[mode]
    if ordering:
        data, stats = wiki_order.encode(data, ordering)
    else:
        stats = {}
    if generator:
        data, generation = wiki_templates.encode(data, generator == "arithmetic")
        stats.update(generation)
    return data, stats


def inverse(data, mode):
    ordering, generator = MODES[mode]
    if generator:
        data = wiki_templates.decode(data)
    return wiki_order.decode(data) if ordering else data


def compress(
    source,
    destination,
    binary,
    settings,
    mode,
    members,
    workers,
    notify=None,
    prime_bytes=0,
):
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output must be different files")
    started = perf_counter()
    digest = cm3_parallel.sha256(source)
    with TemporaryDirectory(prefix="wiki-cm3-", dir=destination.parent) as scratch:
        scratch = Path(scratch)
        view = source
        stats = {}
        if mode != "literal":
            data, stats = transform(source.read_bytes(), mode)
            view = scratch / "source-view"
            view.write_bytes(data)
            del data
        payload = scratch / "payload.c3p"
        cm3_parallel.compress(
            view, payload, binary, settings, members, workers, notify, prime_bytes
        )
        staged = scratch / "archive"
        with staged.open("wb") as output, payload.open("rb") as packed:
            output.write(
                HEADER.pack(MAGIC, MODE_NAMES.index(mode), bytes.fromhex(digest))
            )
            shutil.copyfileobj(packed, output)
        staged.replace(destination)
    return {
        "mode": mode,
        "source_bytes": source.stat().st_size,
        "archive_bytes": destination.stat().st_size,
        "sha256": digest,
        "encode_s": round(perf_counter() - started, 3),
        **stats,
    }


def decompress(source, destination, binary, settings, workers, notify=None):
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output must be different files")
    started = perf_counter()
    with TemporaryDirectory(prefix="wiki-cm3-", dir=destination.parent) as scratch:
        scratch = Path(scratch)
        payload = scratch / "payload.c3p"
        with source.open("rb") as archive, payload.open("wb") as packed:
            envelope = archive.read(HEADER.size)
            if len(envelope) != HEADER.size:
                raise ValueError("Truncated Wikipedia archive")
            magic, number, expected = HEADER.unpack(envelope)
            if magic != MAGIC or number >= len(MODE_NAMES):
                raise ValueError("Invalid Wikipedia archive format")
            shutil.copyfileobj(archive, packed)
        mode = MODE_NAMES[number]
        view = scratch / "source-view"
        cm3_parallel.decompress(payload, view, binary, settings, workers, notify)
        if mode == "literal":
            recovered = view
        else:
            recovered = scratch / "restored"
            recovered.write_bytes(inverse(view.read_bytes(), mode))
        digest = cm3_parallel.sha256(recovered)
        if bytes.fromhex(digest) != expected:
            raise ValueError("The reconstructed Wikipedia source has the wrong SHA-256")
        recovered.replace(destination)
    return {
        "mode": mode,
        "source_bytes": destination.stat().st_size,
        "sha256": digest,
        "decode_s": round(perf_counter() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("c", "d"))
    parser.add_argument("binary", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--mode", choices=MODE_NAMES, default="similar")
    parser.add_argument("--members", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--prime-bytes", type=int, default=0)
    args = parser.parse_args()
    settings = cm3_parallel.read_config(args.config)

    def progress(index, members, raw, packed, elapsed):
        print(
            f"{args.operation} {index}/{members} {raw} -> {packed} bytes in {elapsed:.2f}s",
            flush=True,
        )

    if args.operation == "c":
        result = compress(
            args.source,
            args.destination,
            args.binary,
            settings,
            args.mode,
            args.members,
            args.workers,
            progress,
            args.prime_bytes,
        )
    else:
        result = decompress(
            args.source, args.destination, args.binary, settings, args.workers, progress
        )
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
