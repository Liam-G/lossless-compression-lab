"""Combinatorial number system for a fixed-weight bit mask (colex order)."""

from math import comb


def rank(mask):
    value, index = 0, 1
    while mask:
        bit = mask & -mask
        value += comb(bit.bit_length() - 1, index)
        mask ^= bit
        index += 1
    return value


def unrank(length, count, value):
    if not 0 <= count <= length or not 0 <= value < comb(length, count):
        raise ValueError("Invalid subset rank")
    mask = 0
    pos = length - 1
    for k in range(count, 0, -1):
        while comb(pos, k) > value:
            pos -= 1
        mask |= 1 << pos
        value -= comb(pos, k)
        pos -= 1
    return mask


def bits_needed(length, count):
    return (comb(length, count) - 1).bit_length()
