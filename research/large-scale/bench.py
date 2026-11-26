"""Run one codec on a complete input. Store only a verified result line and hashes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
CM = RESEARCH / "build/cm3"
MINIMUM = 20 << 20


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


PROFILE_ENGINES = {
    "regenerate": "whiteboard-census/regenerate.py",
    "census": "whiteboard-census/costs.py",
    "witness": "whiteboard-census/witnesses.py",
    "learned": "learned-cellular-rules/codec.py",
    "wiki": "wiki-structures/codec.py",
    "glyph": "glyph-residuals/codec.py",
    "scale": "carry-trees/sparse_scale.py",
    "motion": "motion-residuals/codec.py",
    "distance": "distance-geometry/codec.py",
    "four": "four-dimensional-factors/codec.py",
    "views": "text-views/codec.py",
    "carry": "carry-trees/codec.py",
    "checker": "checkerboard-orbits/codec.py",
    "wavelet": "reversible-wavelets/codec.py",
    "lattice": "lattice-prediction/codec.py",
    "shared": "shared-factor-forest/codec.py",
    "forest": "whiteboard-trees/factor_forest.py",
    "tensor": "tensor-orbits/codec.py",
}


def commands(codec, src, arc, dest, scratch, reference=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CM3_")}
    family, _, profile = codec.partition("-")
    if family in PROFILE_ENGINES:
        engine = [sys.executable, RESEARCH / PROFILE_ENGINES[family]]
        return (
            engine + ["encode", src, arc, "--profile", profile],
            engine + ["decode", arc, dest],
            env,
            {},
        )
    if codec in ("ffv1", "h264lossless"):
        engine = [sys.executable, HERE / "video_baseline.py"]
        return engine + [codec, src, arc], engine + ["decode", arc, dest], env, {}
    if family in ("censusapp", "witnessapp"):
        packer = (
            RESEARCH
            / "whiteboard-census"
            / ("bundle.py" if family == "censusapp" else "witness_app.py")
        )
        return (
            [sys.executable, packer, src, arc, "--delivery", profile],
            [sys.executable, "-I", "-S", arc, dest],
            env,
            {},
        )
    if codec.startswith("portable-"):
        packer = RESEARCH / "portable-arithmetic/pack.py"
        encode = [sys.executable, packer, src, arc, "--profile", codec[9:]]
        return encode, [sys.executable, "-I", "-S", arc, dest], env, {}
    if codec.startswith("relative-"):
        engine = [sys.executable, RESEARCH / "arithmetic-references/codec.py"]
        base = reference or Path(os.environ["COMPRESSION_REFERENCE"])
        knobs = dict(
            reference=base.name,
            reference_bytes=base.stat().st_size,
            reference_sha256=digest(base),
        )
        flags = ["--reference", base]
        return (
            engine + ["encode", src, arc, "--profile", codec[9:], *flags],
            engine + ["decode", arc, dest, *flags],
            env,
            knobs,
        )
    if codec.startswith("sum-"):
        folder = RESEARCH / "generator-sums"
        return (
            [sys.executable, folder / "encode.py", src, arc, "--block", codec[4:]],
            [sys.executable, folder / "decoder.py", arc, dest],
            env,
            {},
        )
    if codec.startswith("decimal-"):
        exe = RESEARCH / "build/decimal-blocks"
        return (
            [exe, "split", src, arc, scratch / "blocks.tsv", codec[8:]],
            [exe, "join", arc, dest],
            env,
            {},
        )
    if codec in ("djvu", "djvu-wide", "djvu-multi"):
        engine = [sys.executable, HERE / "djvu_baseline.py"]
        flags = (
            ["--rows", "32760"]
            if codec == "djvu-wide"
            else (["--separated"] if codec == "djvu-multi" else [])
        )
        return (
            engine + ["encode", src, arc, *flags],
            engine + ["decode", arc, dest],
            env,
            {},
        )
    if codec in ("group4", "png1", "jbig"):
        engine = [sys.executable, HERE / "document_baseline.py"]
        return (
            engine + [codec, src, arc],
            engine + ["unjbig" if codec == "jbig" else "decode", arc, dest],
            env,
            {},
        )
    if codec.startswith("integer-"):
        engine = [
            os.environ.get("GMP_PYTHON", sys.executable),
            RESEARCH / "integer-formulas/run.py",
        ]
        return engine + [codec[8:], src, arc], engine + ["decode", arc, dest], env, {}
    if codec == "jxl":
        return (
            ["cjxl", src, arc, "-d", "0", "-e", "7", "--num_threads=2", "--quiet"],
            ["djxl", arc, dest, "--output_format", "ppm", "--num_threads=2", "--quiet"],
            env,
            {},
        )
    if codec in ("png", "webp"):
        engine = [sys.executable, HERE / "image_baseline.py"]
        return engine + [codec, src, arc], engine + ["decode", arc, dest], env, {}
    if codec.startswith("prime-"):
        exe = RESEARCH / "build/prime-indices"
        return [exe, codec[6:], src, arc], [exe, "decode", arc, dest], env, {}
    if codec == "quartic":
        exe = [sys.executable, RESEARCH / "quartic-trees/codec.py"]
        return exe + ["encode", src, arc], exe + ["decode", arc, dest], env, {}
    if codec == "whiteboard":
        exe = [sys.executable, RESEARCH / "whiteboard-trees/tree.py"]
        return exe + ["encode", src, arc], exe + ["decode", arc, dest], env, {}
    if codec in ("qrt-binary", "qrt-seeded"):
        exe = RESEARCH / "build/factor-tree"
        mode, arity, param = (
            ("split-mixed", "2", "0")
            if codec == "qrt-binary"
            else ("split-seeded", "128", "2")
        )
        return (
            [exe, mode, src, arc, scratch / "levels.tsv", "1048576", arity, param],
            [exe, "join", arc, dest],
            env,
            {},
        )
    if codec.startswith("gfh-"):
        exe = [sys.executable, RESEARCH / "hierarchical-gf2/codec.py"]
        parameters = codec.split("-")
        steps = parameters[1]
        depth = parameters[2] if len(parameters) > 2 else "3"
        return (
            exe
            + [
                "pack",
                "--profile",
                "full",
                "--steps",
                steps,
                "--depth",
                depth,
                src,
                arc,
            ],
            exe + ["unpack", arc, dest],
            env,
            {},
        )
    if codec in ("rps32", "qft255"):
        name, scanner = (
            ("codec.py", "interval-scan")
            if codec == "rps32"
            else ("quotient_trial.py", "product-scan")
        )
        engine = [sys.executable, RESEARCH / "repdigit-intervals" / name]
        return (
            engine + ["encode", src, arc, "--scanner", RESEARCH / "build" / scanner],
            engine + ["decode", arc, dest],
            env,
            {},
        )
    if codec.startswith(("pilot", "study")):
        number, profile = codec[5:].split("-", 1)
        engine = [sys.executable, HERE / "collection.py"]
        knobs = {}
        flags = []
        if int(number) in (12, 19):
            base = reference or src.parent / "wiki-dev"
            knobs = dict(
                reference=base.name,
                reference_bytes=base.stat().st_size,
                reference_sha256=digest(base),
            )
            flags = ["--reference", base]
        workers = os.environ.get("PILOT_WORKERS", "1")
        acceleration = (
            ["--native-gf2"]
            if int(number) == 7 and os.environ.get("PILOT_NATIVE_GF2") == "1"
            else []
        )
        knobs.update(workers=int(workers), native_gf2=bool(acceleration))
        return (
            engine
            + [
                "encode",
                number,
                profile,
                src,
                arc,
                *flags,
                "--workers",
                workers,
                *acceleration,
            ],
            engine + ["decode", arc, dest, *flags],
            env,
            knobs,
        )
    if codec.startswith("wcm-"):
        folder = RESEARCH / "wiki-structures"
        args = [sys.executable, folder / "wiki_archive.py"]
        fixed = [CM, folder / "context.config"]
        prime = 65536 if codec.endswith("-primed") else 0
        mode = codec[4:].removesuffix("-primed")
        options = [
            "--mode",
            mode,
            "--members",
            "4",
            "--workers",
            "2",
            "--prime-bytes",
            str(prime),
        ]
        return (
            args + ["c", *fixed, src, arc, *options],
            args + ["d", *fixed, arc, dest, "--workers", "2"],
            env,
            dict(
                members=4,
                workers=2,
                prime_bytes=prime,
                CM3_BITS="16",
                binary_sha256=digest(CM),
            ),
        )
    if codec.startswith("cm3-"):
        pipeline = codec[4:]
        knobs = {"CM3_BITS": "16", "CM3_MCAND": "32", "CM3_M2": "1", "CM3_L2": "6"}
        if pipeline == "context":
            knobs = {"CM3_BITS": "16"}
        elif pipeline == "lstm32":
            knobs["CM3_LSTM"] = "32"
            knobs["CM3_LSTM2"] = "1"
        elif pipeline != "mix":
            raise ValueError(codec)
        env.update(knobs)
        return [CM, "c", src, arc], [CM, "d", arc, dest], env, knobs
    if codec in ("zstd3", "zstd19"):
        level = codec[4:]
        return (
            ["zstd", "-T1", "-" + level, "-q", src, "-o", arc],
            ["zstd", "-dq", arc, "-o", dest],
            env,
            {},
        )
    if codec == "xz9e":
        return (
            ["xz", "-9e", "--threads=1", "--stdout", src],
            ["xz", "-dc", arc],
            env,
            {},
        )
    if codec == "statico":
        return (
            [RESEARCH / "statico/statico", "c", src, arc],
            [RESEARCH / "statico/unstatico", arc, dest],
            env,
            {},
        )
    if codec == "shape":
        engine = RESEARCH / "build/shape"
        return [engine, "encode", src, arc], [engine, "decode", arc, dest], env, {}
    raise ValueError(f"Unknown codec {codec}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("codec", nargs="+")
    parser.add_argument(
        "--reference", type=Path, help="External reference used for conditional coding"
    )
    args = parser.parse_args()
    if args.input.stat().st_size < MINIMUM:
        parser.error("Primary benchmark input must contain at least 20 MiB")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    source_sha = digest(args.input)
    with args.result.open("x", buffering=1) as log:
        for name in args.codec:
            with TemporaryDirectory(dir=args.result.parent) as td:
                tmp = Path(td)
                arc, restored = tmp / "archive", tmp / "restored"
                enc, dec, env, knobs = commands(
                    name, args.input, arc, restored, tmp, args.reference
                )
                start = perf_counter()

                def run(command, output, stage, statistics=False):
                    usage = tmp / (stage + ".rss")
                    timed = [sys.executable, HERE / "measure.py", usage, *command]
                    if name == "xz9e":
                        with output.open("xb") as stream:
                            subprocess.run(timed, stdout=stream, env=env, check=True)
                        details = None
                    else:
                        completed = subprocess.run(
                            timed,
                            stdout=subprocess.PIPE
                            if statistics
                            else subprocess.DEVNULL,
                            env=env,
                            check=True,
                        )
                        details = json.loads(completed.stdout) if statistics else None
                    return details, int(usage.read_text())

                selections, encode_peak = run(
                    enc,
                    arc,
                    "encode",
                    name.startswith(
                        (
                            "lattice-",
                            "shared-",
                            "wavelet-",
                            "checker-",
                            "views-",
                            "four-",
                            "relative-",
                            "distance-",
                            "motion-",
                            "scale-",
                            "glyph-",
                            "portable-",
                            "witnessapp-",
                            "regenerate-",
                            "censusapp-",
                            "census-",
                            "witness-",
                            "wiki-",
                            "learned-",
                            "pilot12-",
                            "study19-",
                        )
                    ),
                )
                middle = perf_counter()
                decoded_stats, decode_peak = run(
                    dec, restored, "decode", name.startswith("carry-")
                )
                end = perf_counter()
                subprocess.run(["cmp", args.input, restored], check=True)
                record = dict(
                    dataset=args.input.name,
                    codec=name,
                    input_bytes=args.input.stat().st_size,
                    input_sha256=source_sha,
                    archive_bytes=arc.stat().st_size,
                    archive_sha256=digest(arc),
                    encode_peak_kib=encode_peak,
                    decode_peak_kib=decode_peak,
                    encode_s=round(middle - start, 3),
                    decode_s=round(end - middle, 3),
                    knobs=knobs,
                    verified=True,
                )
                if decoded_stats is not None:
                    record["decoded_nodes"] = decoded_stats
                if selections is not None:
                    record["selections"] = selections
                print(json.dumps(record), file=log)
                print(name, args.input.name, record["archive_bytes"], flush=True)


if __name__ == "__main__":
    main()
