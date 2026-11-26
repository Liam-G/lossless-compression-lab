"""Reversible Wikipedia line templates with optional arithmetic slot predictors."""

import argparse
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import re
import zlib


MAGIC = b"WGF1"
SLOT = re.compile(rb"\[\[[^\[\]\n]{1,256}\]\]|[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?")
RAW, PREVIOUS, LINEAR, COPY, SUM, DIFFERENCE, PERCENT = range(7)
RULE_NAMES = ("literal", "previous", "linear", "copy", "sum", "difference", "percent")


def put_int(output, value):
    while value >= 128:
        output.append((value & 127) | 128)
        value >>= 7
    output.append(value)


def put_blob(output, data):
    put_int(output, len(data))
    output.extend(data)


class Reader:
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def take(self, length):
        end = self.offset + length
        if end > len(self.data):
            raise ValueError("Truncated template stream")
        value = self.data[self.offset : end]
        self.offset = end
        return value

    def integer(self):
        value = 0
        for shift in range(0, 70, 7):
            byte = self.take(1)[0]
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError("Oversized template integer")

    def blob(self):
        return self.take(self.integer())

    def done(self):
        return self.offset == len(self.data)


def line_form(line):
    if len(line) < 24 or len(line) > 16384:
        return (), ()
    parts, values = [], []
    end = 0
    for match in SLOT.finditer(line):
        parts.append(line[end : match.start()])
        values.append(match.group())
        end = match.end()
        if len(values) > 24:
            return (), ()
    parts.append(line[end:])
    if not values or sum(map(len, parts)) < 16:
        return (), ()
    return tuple(parts), values


def format_number(value, places, commas):
    whole, fraction = divmod(value, 10**places)
    base = f"{whole:,}" if commas else str(whole)
    return (base + (f".{fraction:0{places}d}" if places else "")).encode("ascii")


def numeric_column(column):
    places = len(column[0].partition(b".")[2])
    commas = any(b"," in item for item in column)
    if places > 6:
        return None
    values = []
    for item in column:
        digits = item.replace(b",", b"").replace(b".", b"")
        if len(digits) > 12 or not digits.isdigit():
            return None
        value = int(digits)
        if format_number(value, places, commas) != item:
            return None
        values.append(value)
    return values, places, commas


def predict(rule, position, columns, last, step, scale):
    mode, first, second = rule
    if mode == PREVIOUS:
        return last
    if mode == LINEAR:
        return last + step
    a = columns[first][position]
    if mode == COPY:
        return a
    b = columns[second][position]
    if mode == SUM:
        return a + b
    if mode == DIFFERENCE:
        return a - b
    return (200 * scale * a + b) // (2 * b) if b else 0


def encode_column(column, known, arithmetic):
    original = bytes((RAW,)) + b"\n".join(column)
    numeric = numeric_column(column) if arithmetic else None
    if numeric is None:
        return original, None
    values, places, commas = numeric
    scale = 10**places
    sources = [index for index, earlier in enumerate(known) if earlier is not None][-6:]
    rules = [(PREVIOUS, 0, 0), (LINEAR, 0, 0)]
    rules.extend((COPY, index, 0) for index in sources)
    for a, b in combinations(sources, 2):
        rules.extend(
            (
                (SUM, a, b),
                (DIFFERENCE, a, b),
                (DIFFERENCE, b, a),
                (PERCENT, a, b),
                (PERCENT, b, a),
            )
        )
    best, best_size = original, len(zlib.compress(original, 1))
    for mode, first, second in rules:
        encoded = bytearray((mode, places, int(commas), first, second))
        last = step = 0
        for position, value in enumerate(values):
            error = value - predict(
                (mode, first, second), position, known, last, step, scale
            )
            put_int(encoded, 2 * error if error >= 0 else -2 * error - 1)
            step, last = value - last, value
        size = len(zlib.compress(encoded, 1))
        if size < best_size:
            best, best_size = bytes(encoded), size
    return best, values


def decode_column(encoded, known, count):
    stream = Reader(encoded)
    mode = stream.take(1)[0]
    if mode == RAW:
        column = stream.take(len(encoded) - 1).split(b"\n")
        if len(column) != count:
            raise ValueError("Incorrect literal column length")
        numeric = numeric_column(column)
        return column, numeric[0] if numeric else None
    places, commas, first, second = stream.take(4)
    if mode > PERCENT or places > 6 or commas > 1:
        raise ValueError("Invalid numeric rule")
    needed = () if mode < COPY else (first,) if mode == COPY else (first, second)
    if any(index >= len(known) or known[index] is None for index in needed):
        raise ValueError("Numeric rule refers to an unavailable column")
    column, values = [], []
    last = step = 0
    scale = 10**places
    for position in range(count):
        residual = stream.integer()
        error = residual // 2 if residual % 2 == 0 else -(residual // 2) - 1
        value = (
            predict((mode, first, second), position, known, last, step, scale) + error
        )
        if value < 0:
            raise ValueError("Invalid reconstructed number")
        column.append(format_number(value, places, commas))
        values.append(value)
        step, last = value - last, value
    if not stream.done():
        raise ValueError("Unused numeric residuals")
    return column, values


def encode(data, arithmetic=False, minimum=8, limit=512):
    lines = data.split(b"\n")
    forms = [line_form(line) for line in lines]
    frequency = Counter(parts for parts, _ in forms if parts)
    ranking = sorted(
        (parts for parts in frequency if frequency[parts] >= minimum),
        key=lambda parts: frequency[parts] * (sum(map(len, parts)) - len(parts) - 1),
        reverse=True,
    )
    templates = ranking[:limit]
    ids = {parts: index for index, parts in enumerate(templates, 1)}
    schedule, literals = bytearray(), []
    rows = defaultdict(list)
    for line, (parts, values) in zip(lines, forms):
        code = ids.get(parts, 0)
        put_int(schedule, code)
        if code:
            rows[code].append(values)
        else:
            literals.append(line)

    output = bytearray(MAGIC)
    put_blob(output, schedule)
    put_blob(output, b"\n".join(literals))
    put_int(output, len(templates))
    rules = Counter()
    for code, parts in enumerate(templates, 1):
        put_int(output, len(parts))
        for part in parts:
            put_blob(output, part)
        known = []
        for column in zip(*rows[code]):
            encoded, values = encode_column(column, known, arithmetic)
            known.append(values)
            put_blob(output, encoded)
            rules[RULE_NAMES[encoded[0]]] += 1
    return bytes(output), {
        "templates": len(templates),
        "generated_lines": len(lines) - len(literals),
        "rules": dict(rules),
    }


def decode(data):
    stream = Reader(data)
    if stream.take(len(MAGIC)) != MAGIC:
        raise ValueError("Unknown Wikipedia template format")
    schedule = Reader(stream.blob())
    codes = []
    while not schedule.done():
        codes.append(schedule.integer())
    frequency = Counter(codes)
    literal_blob = stream.blob()
    literal_lines = literal_blob.split(b"\n") if frequency[0] else []
    if len(literal_lines) != frequency[0] or (not frequency[0] and literal_blob):
        raise ValueError("Incorrect number of literal lines")
    literal = iter(literal_lines)
    forms = [None]
    template_count = stream.integer()
    for code in range(1, template_count + 1):
        parts = [stream.blob() for _ in range(stream.integer())]
        known, columns = [], []
        if len(parts) < 2 or not frequency[code]:
            raise ValueError("Unused or invalid template")
        for _ in parts[1:]:
            column, values = decode_column(stream.blob(), known, frequency[code])
            columns.append(column)
            known.append(values)
        forms.append((parts, zip(*columns)))
    if not stream.done() or any(code > template_count for code in codes):
        raise ValueError("Invalid Wikipedia template stream")

    def lines():
        for code in codes:
            if code == 0:
                yield next(literal)
            else:
                parts, rows = forms[code]
                values = next(rows)
                line = bytearray(parts[0])
                for value, part in zip(values, parts[1:]):
                    line.extend(value)
                    line.extend(part)
                yield bytes(line)

    return b"\n".join(lines())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--arithmetic", action="store_true")
    args = parser.parse_args()
    source = args.source.read_bytes()
    if args.mode == "encode":
        transformed, summary = encode(source, args.arithmetic)
        print(summary)
    else:
        transformed = decode(source)
    args.destination.write_bytes(transformed)


if __name__ == "__main__":
    main()
