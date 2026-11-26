"""Select a numeral base by empirical entropy or transmitted byte cost."""

from collections import Counter
from math import log2
from wire import blocks, var

ID = 5
PROFILES = ("global-entropy", "local-entropy", "global-bytes", "local-bytes")
CONTRASTS = [("combined_gain", "local-entropy", "global-bytes", "local-bytes")]
BASES = (2, 3, 4, 5, 7, 8, 10, 16, 31, 64, 128, 256, 257)


def candidate(value, base):
    digits = []
    while value or not digits:
        value, d = divmod(value, base)
        digits.append(d)
    counts = Counter(digits)
    dominant = max(counts, key=counts.get)
    exceptions = [(i, d) for i, d in enumerate(digits) if d != dominant]
    record = var(len(digits)) + var(dominant) + var(len(exceptions))
    record += b"".join(var(i) + var(d) for i, d in exceptions)
    entropy = sum(n / len(digits) * log2(len(digits) / n) for n in counts.values())
    return entropy, record


def pack(data, profile, ref, stats):
    scope, rule = profile.split("-")
    words = list(blocks(data, 16))
    options = [[candidate(int.from_bytes(w, "big"), base) for base in BASES] for w in words]

    # A literal escape is always available at the block's actual width.
    def choose(rule):
        totals = [0] * len(BASES)
        local = []
        for word, row in zip(words, options):
            costs = [item[0] if rule == "entropy" else min(len(word), len(item[1])) for item in row]
            local.append(min(range(len(BASES)), key=costs.__getitem__))
            totals = [a + b for a, b in zip(totals, costs)]
        global_choice = min(range(len(BASES)), key=totals.__getitem__)
        return local if scope == "local" else [global_choice] * len(words)

    entropy, actual = choose("entropy"), choose("bytes")
    selected = entropy if rule == "entropy" else actual
    meta = bytearray([selected[0] if selected else 0]) if scope == "global" else bytearray()
    body = bytearray()
    for word, row, i in zip(words, options, selected):
        candidate_bytes = row[i][1]
        if len(candidate_bytes) < len(word):
            meta.append(i if scope == "local" else 0)
            body.extend(candidate_bytes)
        else:
            meta.append(255)
            body.extend(word)
    stats.update(
        changed_base_blocks=sum(a != b for a, b in zip(entropy, actual)), selector_bytes=len(meta)
    )
    return meta, body


def unpack(size, profile, meta, body, ref, stats):
    global_base = meta.byte() if profile.startswith("global") else None
    out = bytearray()
    while len(out) < size:
        width, tag = min(16, size - len(out)), meta.byte()
        if tag == 255:
            out.extend(body.take(width))
            continue
        base = BASES[tag if global_base is None else global_base]
        count = body.var()
        digits = [body.var()] * count
        for _ in range(body.var()):
            i = body.var()
            digits[i] = body.var()
        value = sum(d * base**i for i, d in enumerate(digits))
        out.extend(value.to_bytes(width, "big"))
    return out
