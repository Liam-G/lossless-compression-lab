"""Reversible text front end: a reversible rewrite of enwik8-style XML text, so known back ends
(xz, PPMd, bzip2) and statico's grammar all read the same rewritten file.

Pieces (each can be switched on alone):
  split : article bodies are cut out of the XML; the remaining page headers become a skeleton of tags
          plus one column per field (ids stored as differences).
  caps  : 'Word' -> CAP + 'word', 'WORD' -> ALLCAP + 'word'.
  words : frequent (lower-cased) words -> 1..3 byte codes made only of byte values the input never uses.
The output is ONE file (dictionary included), so one size per variant covers everything.

usage: textfront.py enc IN OUT split,caps,words   |   textfront.py dec IN OUT
"""

import collections, re, struct, sys

TEXT_OPEN = re.compile(rb"<text\b[^>]*>")
TAG = re.compile(rb"<[^>]*>")
WORD = re.compile(rb"[A-Za-z]+")
NUM = re.compile(rb"0|[1-9][0-9]*")
N1, N2, N3 = (
    12,
    28,
    8,
)  # spare bytes used as 1-byte codes / first byte of 2-byte / of 3-byte codes


def pack(*blobs):
    return b"".join(struct.pack(">I", len(b)) + b for b in blobs)


def unpack(buf, pos, n):
    out = []
    for _ in range(n):
        (k,) = struct.unpack_from(">I", buf, pos)
        pos += 4
        out.append(buf[pos : pos + k])
        pos += k
    return out, pos


# ---------- split: bodies out, headers as columns ----------
def split_bodies(d):
    meta, bodies, pos = bytearray(), [], 0
    while True:
        m = TEXT_OPEN.search(d, pos)
        if not m:
            meta += d[pos:]
            break
        meta += d[pos : m.end()]
        if m.group().endswith(b"/>"):
            pos = m.end()
            continue
        e = d.find(b"</text>", m.end())
        if e < 0:
            bodies.append(d[m.end() :])
            pos = len(d)
            break  # enwik8 ends mid-article
        bodies.append(d[m.end() : e])
        pos = e
    return bytes(meta), bodies


def join_bodies(meta, bodies):
    out, pos, it = bytearray(), 0, iter(bodies)
    for m in TEXT_OPEN.finditer(meta):
        out += meta[pos : m.end()]
        pos = m.end()
        if not m.group().endswith(b"/>"):
            out += next(it)
    out += meta[pos:]
    return bytes(out)


def _keys(tags):
    """deterministic column key for the gap after each tag, computed from the skeleton alone."""
    stack, keys = [], [b"^"]
    for t in tags:
        name = re.match(rb"</?([^\s/>]*)", t).group(1)
        if t.startswith(b"</"):
            if stack:
                stack.pop()
            kind = b"/" + name
        elif t.endswith(b"/>"):
            kind = name + b"/"
        else:
            stack.append(name)
            kind = name
        keys.append(b"/".join(stack[-3:]) + b"|" + kind)
    return keys


def meta_encode(meta, sep):
    tags = TAG.findall(meta)
    vals = TAG.split(meta)  # len(tags) + 1 gaps
    cols = collections.OrderedDict()
    for k, v in zip(_keys(tags), vals):
        cols.setdefault(k, []).append(v)
    blobs = []
    for k, vs in cols.items():
        delta = len(vs) > 1 and all(NUM.fullmatch(v) for v in vs)
        if delta:
            prev, out = 0, []
            for v in vs:
                x = int(v)
                out.append(str(x - prev).encode())
                prev = x
            vs = out
        blobs += [k, b"D" if delta else b"R", bytes([sep]).join(vs)]
    return pack(b"".join(tags), struct.pack(">I", len(cols))) + pack(*blobs)


def meta_decode(buf, sep):
    (skel, ncol), pos = unpack(buf, 0, 2)
    (ncol,) = struct.unpack(">I", ncol)
    blobs, _ = unpack(buf, pos, 3 * ncol)
    cols = {}
    for i in range(ncol):
        k, flag, data = blobs[3 * i : 3 * i + 3]
        vs = data.split(bytes([sep]))
        if flag == b"D":
            prev, out = 0, []
            for v in vs:
                prev += int(v)
                out.append(str(prev).encode())
            vs = out
        cols[k] = iter(vs)
    tags = TAG.findall(skel)
    out = bytearray()
    for i, k in enumerate(_keys(tags)):
        out += next(cols[k])
        if i < len(tags):
            out += tags[i]
    return bytes(out)


# ---------- caps + words ----------
def code_table(spare):
    one, two, three = spare[:N1], spare[N1 : N1 + N2], spare[N1 + N2 : N1 + N2 + N3]
    codes = [bytes([a]) for a in one]
    codes += [bytes([a, b]) for a in two for b in spare]
    codes += [bytes([a, b, c]) for a in three for b in spare for c in spare]
    return codes, one, two, three


def fold(w, caps):
    if caps:
        if w[:1].isupper() and (len(w) == 1 or w[1:].islower()):
            return CAP_B, w.lower()
        if len(w) > 1 and w.isupper():
            return ALLCAP_B, w.lower()
    return b"", w


def words_encode(body, caps, words, spare):
    dict_words, table = [], {}
    if words:
        cnt = collections.Counter(fold(w, caps)[1] for w in WORD.findall(body))
        codes, *_ = code_table(spare)
        ci = 0
        for w, _ in cnt.most_common():
            if ci >= len(codes):
                break
            if len(w) > len(codes[ci]):
                table[w] = codes[ci]
                dict_words.append(w)
                ci += 1

    def rep(m):
        flag, w = fold(m.group(), caps)
        return flag + table.get(w, w)

    return b"\n".join(dict_words), WORD.sub(rep, body)


def words_decode(dict_blob, body, spare):
    dict_words = dict_blob.split(b"\n") if dict_blob else []
    codes, one, two, three = code_table(spare)
    inv = {c: w for c, w in zip(codes, dict_words)}
    cls = lambda bs: re.escape(bytes(bs)).join([b"[", b"]"]) if bs else b"(?!)"
    S = cls(spare)
    pat = re.compile(
        b"(["
        + re.escape(CAP_B + ALLCAP_B)
        + b"]?)("
        + cls(one)
        + b"|"
        + cls(two)
        + S
        + b"|"
        + cls(three)
        + S
        + S
        + b"|[A-Za-z]+)"
    )

    def rep(m):
        flag, tok = m.group(1), m.group(2)
        w = inv.get(tok, tok)
        if flag == CAP_B:
            return w[:1].upper() + w[1:]
        if flag == ALLCAP_B:
            return w.upper()
        return w

    return pat.sub(rep, body)


# ---------- container ----------
def encode(d, pieces):
    global CAP_B, ALLCAP_B
    used = set(d) | set(
        b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-\n"
    )
    unused = [b for b in range(256) if b not in used]
    if len(unused) < 3 + N1 + N2 + N3:
        raise ValueError(f"only {len(unused)} unused byte values")
    sep, CAP_B, ALLCAP_B, spare = (
        unused[0],
        bytes([unused[1]]),
        bytes([unused[2]]),
        unused[3 : 3 + N1 + N2 + N3],
    )
    flags = sum(1 << i for i, p in enumerate(("split", "caps", "words")) if p in pieces)
    hdr = b"TF1" + bytes([flags, sep, unused[1], unused[2]]) + bytes(spare)
    if "split" in pieces:
        meta, bodies = split_bodies(d)
        dict_blob, body = words_encode(
            bytes([sep]).join(bodies), "caps" in pieces, "words" in pieces, spare
        )
        return hdr + pack(
            meta_encode(meta, sep), struct.pack(">I", len(bodies)), dict_blob, body
        )
    dict_blob, body = words_encode(d, "caps" in pieces, "words" in pieces, spare)
    return hdr + pack(dict_blob, body)


def decode(buf):
    global CAP_B, ALLCAP_B
    assert buf[:3] == b"TF1"
    flags, sep = buf[3], buf[4]
    CAP_B, ALLCAP_B = bytes([buf[5]]), bytes([buf[6]])
    spare = list(buf[7 : 7 + N1 + N2 + N3])
    pos = 7 + N1 + N2 + N3
    if flags & 1:
        (mblob, nb, dict_blob, body), _ = unpack(buf, pos, 4)
        body = words_decode(dict_blob, body, spare)
        bodies = body.split(bytes([sep])) if struct.unpack(">I", nb)[0] else []
        assert len(bodies) == struct.unpack(">I", nb)[0]
        return join_bodies(meta_decode(mblob, sep), bodies)
    (dict_blob, body), _ = unpack(buf, pos, 2)
    return words_decode(dict_blob, body, spare)


CAP_B = ALLCAP_B = b""
if __name__ == "__main__":
    mode, src, dst = sys.argv[1:4]
    data = open(src, "rb").read()
    if mode == "enc":
        pieces = set(p for p in sys.argv[4].split(",") if p and p != "none")
        open(dst, "wb").write(encode(data, pieces))
    else:
        open(dst, "wb").write(decode(data))
