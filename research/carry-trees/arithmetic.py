"""Fixed-width invertible multiplication and rotation with exact modular carries."""

from functools import cache


@cache
def reciprocal_carry(odd, bits):
    return pow(pow(2, bits, odd), -1, odd)


def transform(data, factor, inverse):
    if not data:
        return data
    bits = 8 * len(data)
    mask = (1 << bits) - 1
    shift = (factor & -factor).bit_length() - 1
    odd = factor >> shift
    shift %= bits
    x = int.from_bytes(data, "big")
    if inverse:
        if shift:
            x = (x >> shift) | ((x & ((1 << shift) - 1)) << (bits - shift))
        if odd > 1:
            carry = (-x * reciprocal_carry(odd, bits)) % odd
            x = (x + (carry << bits)) // odd
    else:
        x = (x * odd) & mask
        if shift:
            x = ((x << shift) & mask) | (x >> (bits - shift))
    return x.to_bytes(len(data), "big")
