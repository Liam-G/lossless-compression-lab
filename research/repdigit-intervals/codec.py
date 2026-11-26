"""Split a binary integer at byte boundaries and price exact repdigit recipes."""

from argparse import ArgumentParser
from bisect import bisect_right
from collections import defaultdict
from itertools import count
from mmap import ACCESS_READ, mmap
from pathlib import Path
import re
import struct
import subprocess
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from repdigits import gamma, pack, reconstruct, repdigit


BUDGET = 28
MAX_WIDTH = 32
HEADER = struct.Struct(">4sII")
PATCH = struct.Struct(">IBB")
MATCH = struct.Struct("<IBI")
MAGIC = b"RPS1"
ZERO = b"\xc0"


def gamma_bits(number):
    return 2 * number.bit_length() - 1


def descriptors(limit):
    for base in count(2):
        first = gamma(base - 1)
        if len(first) + 2 > limit:
            return
        for repeats in count(3):
            prefix = first + gamma(repeats - 2)
            if len(prefix) + 1 > limit:
                break
            unit = repdigit((base, repeats, 1))
            for digit in range(1, base):
                if len(prefix) + gamma_bits(digit) > limit:
                    break
                yield base, unit * digit, prefix + gamma(digit)


def bank_file(path, max_width=MAX_WIDTH):
    tables = ({}, {})
    groups = defaultdict(list)
    admitted = [0, 0]
    candidate_count = 0

    def retain(mode, target, data):
        if target.bit_length() > max_width * 8:
            return
        admitted[mode] += 1
        previous = tables[mode].get(target)
        if previous is None or (len(data), data) < (len(previous), previous):
            tables[mode][target] = data

    for base, value, code in descriptors(BUDGET - 2):
        retain(0, value, "00" + code)
        if len(code) <= BUDGET - 5:
            groups[len(code)].append((base, value, code))
    for first_size, first in groups.items():
        for second_size, second in groups.items():
            if first_size + second_size > BUDGET - 2:
                continue
            for base, numerator, a in first:
                for other, denominator, b in second:
                    if base == other:
                        continue
                    candidate_count += 1
                    if numerator < denominator or (numerator >> (8 * max_width)) >= denominator:
                        continue
                    quotient, remainder = divmod(numerator, denominator)
                    if not remainder:
                        retain(1, quotient, "01" + a + b)

    wires, modes, widths = [], [], []
    with path.open("xb") as stream:
        for mode, table in enumerate(tables):
            for target, code in sorted(table.items()):
                width = (target.bit_length() + 7) // 8
                wire = pack(code)
                stream.write(bytes((width, len(wire))))
                stream.write(target.to_bytes(width, "big"))
                stream.write(wire)
                wires.append(wire)
                modes.append(mode)
                widths.append(width)
    report = dict(budget_bits=BUDGET, maximum_width_bytes=max_width, direct_entries=len(tables[0]),
                  quotient_entries=len(tables[1]), ordered_different_base_pairs=candidate_count,
                  representations_admitted=admitted)
    return wires, modes, widths, report


def select(matches, wires):
    """Maximize the exact byte saving with weighted interval scheduling."""
    intervals = sorted((start + width, start, width, code) for start, width, code in matches)
    ends = [entry[0] for entry in intervals]
    total = [0]
    decisions = []
    for index, (_, start, width, code) in enumerate(intervals):
        parent = bisect_right(ends, start, 0, index)
        saved = total[parent] + width - PATCH.size - len(wires[code])
        chosen = saved > total[-1]
        total.append(saved if chosen else total[-1])
        decisions.append((chosen, parent))
    result = []
    index = len(intervals)
    while index:
        chosen, parent = decisions[index - 1]
        if chosen:
            result.append(intervals[index - 1][1:])
        index = parent if chosen else index - 1
    return list(reversed(result)), total[-1]


def zeroes(source, size, zero_id, max_width=MAX_WIDTH):
    if size < 8:
        return []
    with source.open("rb") as stream, mmap(stream.fileno(), length=0, access=ACCESS_READ) as data:
        return [(start, width, zero_id)
                for run in re.finditer(rb"\x00{8,}", data)
                for start in range(run.start(), run.end() - 7)
                for width in range(8, min(max_width, run.end() - start) + 1)]


def copy(source, target, count):
    while count:
        block = source.read(min(count, 1 << 20))
        if not block:
            raise ValueError("Truncated literal data")
        target.write(block)
        count -= len(block)


def encode(source, output, matches, wires, magic=MAGIC):
    size = source.stat().st_size
    with source.open("rb") as origin, output.open("xb") as archive:
        archive.write(HEADER.pack(magic, size, len(matches)))
        for start, width, code in matches:
            wire = wires[code]
            archive.write(PATCH.pack(start, width, len(wire)))
            archive.write(wire)
        pos = 0
        for start, width, _ in matches:
            copy(origin, archive, start - pos)
            pos = start + width
            origin.seek(pos)
        copy(origin, archive, size - pos)


def decode(source, output):
    with source.open("rb") as archive:
        magic, size, count = HEADER.unpack(archive.read(HEADER.size))
        if magic != MAGIC or count > min(size // 8, source.stat().st_size // (PATCH.size + 1)):
            raise ValueError("Invalid split archive header")
        recipes = []
        previous = 0
        for _ in range(count):
            start, width, code_size = PATCH.unpack(archive.read(PATCH.size))
            if start < previous or not 1 <= width <= MAX_WIDTH or start + width > size or not 1 <= code_size <= 4:
                raise ValueError("Invalid formula interval")
            code = archive.read(code_size)
            if len(code) != code_size or (code != ZERO and code[0] >> 6 not in (0, 1)):
                raise ValueError("Invalid formula record")
            contents = bytes(width) if code == ZERO else reconstruct(code).to_bytes(width, "big")
            recipes.append((start, contents))
            previous = start + width
        with output.open("xb") as restored:
            pos = 0
            for start, contents in recipes:
                copy(archive, restored, start - pos)
                restored.write(contents)
                pos = start + len(contents)
            copy(archive, restored, size - pos)
            if archive.read(1):
                raise ValueError("Trailing archive data")


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for command in ("encode", "decode"):
        mode = commands.add_parser(command)
        mode.add_argument("source", type=Path)
        mode.add_argument("output", type=Path)
        if command == "encode":
            mode.add_argument("--scanner", required=True, type=lambda path: Path(path).resolve())
    args = parser.parse_args()
    if args.operation == "decode":
        decode(args.source, args.output)
        return

    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="rps-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        bank = work / "bank"
        wires, _, _, _ = bank_file(bank)
        raw = subprocess.check_output([args.scanner, bank, args.source])
        matches = list(MATCH.iter_unpack(raw))
        matches.extend(zeroes(args.source, args.source.stat().st_size, len(wires)))
        wires.append(ZERO)
        chosen, _ = select(matches, wires)
        encode(args.source, args.output, chosen, wires)


if __name__ == "__main__":
    main()
