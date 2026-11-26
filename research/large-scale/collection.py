"""Stream the original experiment codecs in independent 32 KiB chunks of one file."""

import argparse
from contextlib import nullcontext
from pathlib import Path
from functools import lru_cache
import importlib.util
import json
from multiprocessing import get_context
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import lab
import wire

HEADER = struct.Struct(">4sBBQ")
LENGTH = struct.Struct(">I")
CHUNK = 32768


STUDIES = {
    17: "formula-factor-grammar",
    18: "automaton-factor-residual",
    19: "reference-formula-intervals",
}


def module_for(number):
    if number not in STUDIES:
        return lab.load(number, "codec")
    src = ROOT / "studies" / STUDIES[number] / "benchmark.py"
    spec = importlib.util.spec_from_file_location(
        "collection_study_" + str(number), src
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup(number, profile, native):
    global active_module, active_table, active_profile
    active_module = module_for(number)
    active_table = (
        active_module.catalog(profile.endswith("ratios")) if number == 1 else None
    )
    active_profile = profile
    if number == 7:
        original = active_module.encode_block
        if native:
            engine_path = ROOT / "research/hierarchical-gf2/codec.py"
            spec = importlib.util.spec_from_file_location(
                "gfh_collection_accelerator", engine_path
            )
            engine = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(engine)

            def original(rows, placement, steps, depth, beam):
                return engine.encode_block(
                    rows,
                    "full" if placement == "pre" else placement,
                    steps,
                    depth,
                    beam,
                )

        active_module.encode_block = lru_cache(maxsize=8192)(original)


def encode_chunk(pair):
    block, reference = pair
    if active_table is not None:
        return active_module.encode(block, active_profile, active_table)[0], False
    archive, stats = wire.encode(active_module, block, active_profile, reference)
    return archive, active_module.ID == 12 or bool(stats.get("uses_base"))


def encode(src, out, number, profile, base=None, workers=1, native=False):
    module = module_for(number)
    if workers < 1:
        raise ValueError("Expected a positive worker count")
    size = src.seek(0, 2)
    src.seek(0)
    out.write(HEADER.pack(b"LCP1", number, module.PROFILES.index(profile), size))

    def chunks():
        while block := src.read(CHUNK):
            yield block, base.read(CHUNK) if base else b""

    if workers == 1:
        setup(number, profile, native)
        pool = nullcontext()
    else:
        pool = get_context("fork").Pool(
            workers, initializer=setup, initargs=(number, profile, native)
        )
    with pool as group:
        records = (
            group.imap(encode_chunk, chunks(), chunksize=2)
            if group
            else map(encode_chunk, chunks())
        )
        needed = False
        for inner, uses_ref in records:
            needed |= uses_ref
            out.write(LENGTH.pack(len(inner)))
            out.write(inner)
    return {"reference_used": needed}


def decode(src, out, base=None):
    magic, number, profile, size = HEADER.unpack(src.read(HEADER.size))
    if magic != b"LCP1":
        raise ValueError("Invalid collection header")
    module = module_for(number)
    if profile >= len(module.PROFILES):
        raise ValueError("Unknown collection profile")
    while size:
        count = LENGTH.unpack(src.read(LENGTH.size))[0]
        data = src.read(count)
        if len(data) != count:
            raise ValueError("Truncated chunk")
        ref = base.read(CHUNK) if base else b""
        if number == 1:
            block = module.decode(data)
        else:
            if data[5] != profile:
                raise ValueError("Mismatched chunk profile")
            block = wire.decode(module, data, ref)[0]
        if len(block) != min(CHUNK, size):
            raise ValueError("Incorrect chunk width")
        out.write(block)
        size -= len(block)
    if src.read(1):
        raise ValueError("Unexpected trailing data")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="op", required=True)
    enc = sub.add_parser("encode")
    enc.add_argument("number", type=int)
    enc.add_argument("profile")
    enc.add_argument("--workers", type=int, default=1)
    enc.add_argument("--native-gf2", action="store_true")
    for part in (enc, sub.add_parser("decode")):
        part.add_argument("source", type=Path)
        part.add_argument("dest", type=Path)
        part.add_argument("--reference", type=Path)
    a = p.parse_args()
    with (
        a.source.open("rb") as src,
        a.dest.open("xb") as out,
        a.reference.open("rb") if a.reference else nullcontext() as ref,
    ):
        if a.op == "encode":
            print(
                json.dumps(
                    encode(src, out, a.number, a.profile, ref, a.workers, a.native_gf2)
                )
            )
        else:
            decode(src, out, ref)
