"""Count and price exact integer repdigits and repdigit quotients."""

import json
from math import ceil


def repdigit(parameters):
    base, repeats, digit = parameters
    if base < 2 or repeats < 3 or not 0 < digit < base:
        raise ValueError("Invalid repdigit parameters")
    return digit * (base**repeats - 1) // (base - 1)


def gamma(value):
    word = f"{value:b}"
    return "0" * (len(word) - 1) + word


def describe(numerator, denominator=None):
    def record(parameters):
        base, repeats, digit = parameters
        return gamma(base - 1) + gamma(repeats - 2) + gamma(digit)

    if denominator is None:
        return "00" + record(numerator)
    return "01" + record(numerator) + record(denominator)


def describe_factor(split, prefix, suffix, cofactor):
    def literal(value):
        width = value.bit_length()
        return gamma(width + 1) + (f"{value:b}" if width else "")

    return "10" + gamma(split) + literal(prefix) + literal(suffix) + literal(cofactor)


def reconstruct(wire):
    bits = "".join(f"{value:08b}" for value in wire)
    mode = bits[:2]
    if mode not in ("00", "01", "10"):
        raise ValueError("Invalid arithmetic record mode")
    position = 2

    def take():
        nonlocal position
        start = bits.index("1", position)
        stop = start + (start - position) + 1
        if stop > len(bits):
            raise ValueError("Truncated repdigit parameters")
        position = stop
        return int(bits[start:stop], 2)

    def value():
        return repdigit((take() + 1, take() + 2, take()))

    def literal():
        nonlocal position
        width = take() - 1
        end = position + width
        if end > len(bits):
            raise ValueError("Truncated integer literal")
        result = int(bits[position:end], 2) if width else 0
        position = end
        return result

    if mode == "10":
        split = take()
        prefix, suffix, cofactor = literal(), literal(), literal()
        radix = 10**split
        if not prefix or suffix >= radix or cofactor < 2:
            raise ValueError("Invalid gapped factor")
        target = (prefix * radix + suffix) * cofactor
    else:
        numerator = value()
        denominator = value() if mode == "01" else 1
        target, remainder = divmod(numerator, denominator)
        if remainder:
            raise ValueError("Nonintegral quotient")
    if len(bits) - position >= 8 or "1" in bits[position:]:
        raise ValueError("Invalid padding")
    return target


def pack(bits):
    return int(bits.ljust(8 * ceil(len(bits) / 8), "0"), 2).to_bytes(ceil(len(bits) / 8), "big")


def trial():
    bank = []
    for base in range(2, 17):
        for repeats in range(3, 13):
            for digit in range(1, base):
                params = (base, repeats, digit)
                record = describe(params)[2:]
                bank.append((repdigit(params), base, record))
    targets = ({}, {})

    def retain(table, value, bits):
        if value not in table or (len(bits), bits) < (len(table[value]), table[value]):
            table[value] = bits

    direct, ratios = targets
    for numerator, base, first in bank:
        if numerator <= 10_000:
            retain(direct, numerator, "00" + first)
        for denominator, other_base, second in bank:
            if base == other_base or not denominator <= numerator <= 10_000 * denominator:
                continue
            quotient, remainder = divmod(numerator, denominator)
            if not remainder:
                retain(ratios, quotient, "01" + first + second)

    summaries = []
    for table in targets:
        for target, bits in table.items():
            if reconstruct(pack(bits)) != target:
                raise ValueError("Minimum-cost record did not reconstruct the target")
        summaries.append(dict(covered=len(table), cheaper_than_binary_bits=sum(
            len(bits) < target.bit_length() for target, bits in table.items()),
            cheaper_than_canonical_bytes=sum(
                len(pack(bits)) < ceil(target.bit_length() / 8) for target, bits in table.items())))

    example = ((2, 120, 1), (3, 3, 1))
    bits = describe(*example)
    packed = pack(bits)
    value = reconstruct(packed)
    if value * repdigit(example[1]) != repdigit(example[0]):
        raise ValueError("Example ratio is not exact")
    return dict(bank_parameters=len(bank), maximum_target=10_000, direct=summaries[0],
                quotient=summaries[1], union_coverage=len(direct.keys() | ratios.keys()),
                exact_records_checked=len(direct) + len(ratios),
                example=dict(parameters=example, target=str(value), literal_bits=value.bit_length(),
                             payload_bits=len(bits), stored_bytes=len(packed), stored_hex=packed.hex()))


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "decode":
        print(reconstruct(bytes.fromhex(sys.argv[2])))
    elif len(sys.argv) == 1:
        print(json.dumps(trial(), indent=2))
    else:
        sys.exit("Pass no arguments for the trial or 'decode HEX' for reconstruction")
