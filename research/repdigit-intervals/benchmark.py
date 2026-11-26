"""Compare fixed and adaptive split boundaries on Q and two exact controls."""

from argparse import ArgumentParser
from hashlib import file_digest
import json
from pathlib import Path
from random import Random
from resource import RUSAGE_CHILDREN, getrusage
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from codec import HERE, HEADER, MATCH, MAX_WIDTH, ZERO, bank_file, encode, repdigit, select, zeroes


SCANNER = HERE.parent / "build/interval-scan"


def hash_file(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def generate_random(path, size):
    rng = Random(0xC01AB123)
    with path.open("xb") as stream:
        while size:
            width = min(1 << 20, size)
            stream.write(rng.randbytes(width))
            size -= width


def generate_planted(path):
    rng = Random(16)
    number = 0
    data = bytearray()
    denominator = repdigit((3, 3, 1))
    for index in range(4096):
        data.extend(rng.randbytes(rng.randrange(9, 28)))
        if index % 2:
            value = repdigit((2, (10 + index % 11) * 12, 1)) // denominator
        else:
            value = repdigit((5, 75 + index % 18, 3))
        width = (value.bit_length() + 7) // 8
        if index % 10 == 0:
            data.extend(rng.randbytes(-len(data) % MAX_WIDTH))
            width = MAX_WIDTH
        else:
            width = min(MAX_WIDTH, width + index % 4)
        data.extend(value.to_bytes(width, "big"))
        number += 1
    data.extend(rng.randbytes(37))
    path.write_bytes(data)
    return number


def bench(name, source, scanner, bank, wires, modes, widths, work, output):
    size = source.stat().st_size
    started = perf_counter()
    raw = subprocess.check_output([scanner, bank, source])
    matches = list(MATCH.iter_unpack(raw))
    scan_seconds = perf_counter() - started
    fixed = [m for m in matches if m[0] % MAX_WIDTH == 0 and m[1] == min(MAX_WIDTH, size - m[0])]
    direct = [m for m in matches if modes[m[2]] == 0]
    zeros = zeroes(source, size, len(wires) - 1)
    results = {}
    restored = work / "restored"
    for variant, choices in (("fixed-32", fixed), ("adaptive-direct", direct), ("adaptive-both", matches),
                             ("adaptive-zero", zeros), ("adaptive-zero-direct", zeros + direct),
                             ("adaptive-zero-both", zeros + matches)):
        archive = work / f"{name}.{variant}.rps"
        selected, saving = select(choices, wires)
        encode(source, archive, selected, wires)
        observed = archive.stat().st_size
        if observed != size + HEADER.size - saving:
            raise ValueError("Serialized archive disagrees with interval prices")
        subprocess.run([sys.executable, "-I", "-B", HERE / "codec.py", "decode", archive, restored], check=True)
        subprocess.run(["cmp", source, restored], check=True)
        restored.unlink()
        results[variant] = dict(
            archive_bytes=observed, savings_vs_literal_container=saving, savings_vs_input=size - observed,
            available_matches=len(choices), retained_recipes=len(selected),
            quotient_recipes=sum(modes[recipe] == 1 for _, _, recipe in selected),
            zero_recipes=sum(modes[recipe] == 2 for _, _, recipe in selected),
            unpadded_recipe_bytes=sum(widths[recipe] for _, _, recipe in selected),
            leading_zero_bytes=sum(width - widths[recipe] for _, width, recipe in selected),
            exact=True,
        )
        if variant == "adaptive-zero-both" and observed < size:
            archive.replace(output / archive.name)
        else:
            archive.unlink()
    all_selected, _ = select(zeros + matches, wires)
    selected, _ = select(matches, wires)
    return dict(input=name, input_bytes=size, sha256=hash_file(source), scan_seconds=round(scan_seconds, 3),
                literal_archive_bytes=size + HEADER.size, first_selected_intervals=[
                    dict(offset=start, width=width, significant_bytes=widths[recipe], mode=modes[recipe])
                    for start, width, recipe in selected[:16]],
                first_selected_with_zeros=[dict(offset=start, width=width,
                                                significant_bytes=widths[recipe], mode=modes[recipe])
                                           for start, width, recipe in all_selected[:16]],
                selected_after_1_mib=sum(start >= 1 << 20 for start, _, _ in selected), results=results)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", type=lambda path: Path(path).resolve())
    parser.add_argument("--q", type=lambda path: Path(path).resolve(), required=True)
    args = parser.parse_args()
    args.output.mkdir()
    began = perf_counter()
    with TemporaryDirectory(prefix="rps-trial-", dir=args.output) as temporary:
        work = Path(temporary)
        bank = work / "bank"
        wires, modes, widths, meta = bank_file(bank)
        wires.append(ZERO)
        modes.append(2)
        widths.append(0)
        print(json.dumps(dict(stage="enumerated", **meta)), flush=True)
        planted, uniform = work / "planted", work / "random"
        planted_count = generate_planted(planted)
        generate_random(uniform, args.q.stat().st_size)
        for name, data in (("planted", planted), ("Q", args.q), ("random", uniform)):
            result = bench(name, data, SCANNER, bank, wires, modes, widths, work, args.output)
            if name == "planted":
                result["planted_count"] = planted_count
            print(json.dumps(result), flush=True)
    print(json.dumps(dict(stage="complete", seconds=round(perf_counter() - began, 3),
                          child_peak_rss_kib=getrusage(RUSAGE_CHILDREN).ru_maxrss)), flush=True)


if __name__ == "__main__":
    main()
