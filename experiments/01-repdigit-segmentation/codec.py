"""Encode or decode an RPS1 archive using exact repdigit recipes."""

import argparse
import struct
from pathlib import Path

HEADER = struct.Struct(">4sII")
PATCH = struct.Struct(">IBB")
WIDTH = 32
BUDGET = 28
PROFILES = ("fixed-direct", "adaptive-direct", "fixed-ratios", "adaptive-ratios")


def repdigit(base, repeats, digit):
    return digit * (base**repeats - 1) // (base - 1)


def gamma(number):
    word = f"{number:b}"
    return "0" * (len(word) - 1) + word


def arguments(base, repeats, digit):
    return gamma(base - 1) + gamma(repeats - 2) + gamma(digit)


def catalog(include_ratios):
    """Keep the shortest bit recipe per integer across all enabled operators."""
    table = {}
    divisors = []
    if include_ratios:
        for base in range(2, 6):
            for repeats in range(3, 6):
                divisors.append((base, repdigit(base, repeats, 1), arguments(base, repeats, 1)))

    def retain(number, bits):
        if len(bits) <= BUDGET and number.bit_length() <= WIDTH * 8:
            old = table.get(number)
            if old is None or (len(bits), bits) < (len(old), old):
                table[number] = bits

    for base in range(2, 11):
        for repeats in range(3, 257):
            unit = repdigit(base, repeats, 1)
            for digit in range(1, base):
                number = digit * unit
                args = arguments(base, repeats, digit)
                retain(number, "00" + args)
                for other, divisor, suffix in divisors:
                    if other != base and number % divisor == 0:
                        retain(number // divisor, "01" + args + suffix)
    return {number: int(bits.ljust((len(bits) + 7) // 8 * 8, "0"), 2)
            .to_bytes((len(bits) + 7) // 8, "big") for number, bits in table.items()}


def encode(data, profile, table):
    """Choose disjoint intervals by exact serialized cost, including each patch header."""
    size = len(data)
    fixed = profile.startswith("fixed")
    choices = {}
    best = [0] * (size + 1)
    for start in range(size - 1, -1, -1):
        best[start] = best[start + 1]
        if fixed and start % WIDTH:
            continue
        limit = min(WIDTH, size - start)
        widths = (limit,) if fixed else range(PATCH.size + 2, limit + 1)
        for width in widths:
            end = start + width
            recipe = table.get(int.from_bytes(data[start:end], "big"))
            if recipe is None:
                continue
            saving = width - PATCH.size - len(recipe) + best[end]
            if saving > best[start]:
                choices[start] = (end, recipe)
                best[start] = saving

    patches = bytearray()
    literals = bytearray()
    pos = count = covered = 0
    while pos < size:
        if pos in choices:
            end, recipe = choices[pos]
            patches.extend(PATCH.pack(pos, end - pos, len(recipe)) + recipe)
            count += 1
            covered += end - pos
            pos = end
        else:
            literals.append(data[pos])
            pos += 1
    archive = HEADER.pack(b"RPS1", size, count) + patches + literals
    assert len(archive) == HEADER.size + size - best[0]
    return archive, dict(records=count, metadata_bytes=HEADER.size + len(patches),
                         literal_bytes=len(literals), regenerated_bytes=covered)


def reconstruct(wire):
    if wire == b"\xc0":  # RPS1 also defines a zero-run record.
        return 0
    bits = "".join(f"{byte:08b}" for byte in wire)
    mode = bits[:2]
    pos = 2

    def take():
        nonlocal pos
        first = bits.index("1", pos)
        end = first + 1 + first - pos
        if end > min(len(bits), BUDGET):
            raise ValueError("Truncated gamma field")
        pos = end
        return int(bits[first:end], 2)

    def value():
        base, repeats, digit = take() + 1, take() + 2, take()
        if digit >= base:
            raise ValueError("Invalid repdigit")
        return repdigit(base, repeats, digit)

    if mode not in ("00", "01"):
        raise ValueError("Unknown operator")
    numerator = value()
    divisor = value() if mode == "01" else 1
    result, remainder = divmod(numerator, divisor)
    if remainder or len(bits) - pos > 7 or "1" in bits[pos:]:
        raise ValueError("Invalid arithmetic recipe")
    return result


def decode(archive):
    magic, size, count = HEADER.unpack_from(archive)
    if magic != b"RPS1" or count > size // 8:
        raise ValueError("Invalid archive header")
    pos = HEADER.size
    patches = []
    end = covered = 0
    for _ in range(count):
        start, width, length = PATCH.unpack_from(archive, pos)
        pos += PATCH.size
        if start < end or not 1 <= width <= WIDTH or start + width > size:
            raise ValueError("Invalid interval")
        if not 1 <= length <= 4 or pos + length > len(archive):
            raise ValueError("Invalid recipe size")
        content = reconstruct(archive[pos:pos + length]).to_bytes(width, "big")
        patches.append((start, content))
        pos += length
        covered += width
        end = start + width
    if len(archive) - pos != size - covered:
        raise ValueError("Literal stream has the wrong length")
    output = bytearray()
    for start, content in patches:
        gap = start - len(output)
        output.extend(archive[pos:pos + gap])
        output.extend(content)
        pos += gap
    output.extend(archive[pos:])
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("encode", "decode"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("output", type=Path)
        if name == "encode":
            command.add_argument("--profile", choices=PROFILES, default="adaptive-ratios")
    args = parser.parse_args()
    source = args.source.read_bytes()
    if args.command == "decode":
        output = decode(source)
    else:
        output, _ = encode(source, args.profile, catalog(args.profile.endswith("ratios")))
    with args.output.open("xb") as stream:
        stream.write(output)


if __name__ == "__main__":
    main()
