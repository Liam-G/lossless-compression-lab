"""Serialize byte tokens, repeated adjacent pairs, or repeated expression subtrees."""

from collections import Counter
from wire import var

ID = 11
PROFILES = ("flat", "grammar", "dag")


def token_bytes(symbol):
    if symbol < 128:
        return bytes([symbol])
    if symbol < 256:
        return bytes([255, symbol])
    rule = symbol - 256
    return bytes([128 + rule]) if rule < 126 else bytes([254]) + var(rule)


def read_token(stream):
    tag = stream.byte()
    if tag == 255:
        return stream.byte()
    if tag == 254:
        return 256 + stream.var()
    return tag if tag < 128 else 256 + tag - 128


def substitute(sequence, target, token):
    out = []
    i = 0
    width = len(target)
    while i < len(sequence):
        if sequence[i : i + width] == target:
            out.append(token)
            i += width
        else:
            out.append(sequence[i])
            i += 1
    return out


def grammar(data):
    seq = list(data)
    rules = []
    while len(seq) >= 2:
        counts = Counter(zip(seq, seq[1:]))
        pair, n = counts.most_common(1)[0]
        if n < 3:
            break
        token = 256 + len(rules)
        replaced = substitute(seq, list(pair), token)
        savings = sum(len(token_bytes(x)) for x in seq) - sum(len(token_bytes(x)) for x in replaced)
        if savings <= 1 + sum(len(token_bytes(x)) for x in pair):
            break
        rules.append(pair)
        seq = replaced
    return rules, seq


def dag(data):
    # Parenthesis spans are complete subexpressions; emit shorter definitions first.
    opens = []
    counts = Counter()
    for i, c in enumerate(data):
        if c == 40:
            opens.append(i)
        elif c == 41 and opens:
            start = opens.pop()
            counts[data[start : i + 1]] += 1
    rules = []
    ids = {}

    def tokenize(chunk):
        seq = []
        i = 0
        while i < len(chunk):
            match = next((s for s in reversed(ids) if chunk.startswith(s, i)), None)
            if match is None:
                seq.append(chunk[i])
                i += 1
            else:
                seq.append(ids[match])
                i += len(match)
        return seq

    for expr, n in sorted(counts.items(), key=lambda item: (len(item[0]), item[0])):
        if n < 2:
            continue
        rule = tokenize(expr)
        cost = sum(len(token_bytes(x)) for x in rule)
        token = 256 + len(rules)
        if n * (cost - len(token_bytes(token))) > len(var(len(rule))) + cost:
            ids[expr] = token
            rules.append(rule)
    return rules, tokenize(data)


def pack(data, profile, ref, stats):
    rules, seq = (
        ([], list(data))
        if profile == "flat"
        else (grammar(data) if profile == "grammar" else dag(data))
    )
    meta = var(len(rules))
    for rule in rules:
        meta += var(len(rule)) + b"".join(token_bytes(i) for i in rule)
    stats.update(rule_count=len(rules), rule_bytes=len(meta), references=sum(x >= 256 for x in seq))
    return meta, b"".join(token_bytes(x) for x in seq)


def unpack(size, profile, meta, body, ref, stats):
    table = [bytes([x]) for x in range(256)]
    for _ in range(meta.var()):
        table.append(b"".join(table[read_token(meta)] for _ in range(meta.var())))
    stats["decoder_rule_content_bytes"] = sum(map(len, table[256:]))
    out = bytearray()
    while len(out) < size:
        out.extend(table[read_token(body)])
    return out
