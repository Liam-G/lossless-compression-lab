#!/usr/bin/env python3
"""tf.py - the alphabet transforms and their inverses.

Every forward transform returns (header_bytes, payload_bytes).  Every inverse
takes ONLY (header_bytes, payload_bytes) and returns the original bytes, so the
header provably carries every parameter the decoder needs.  Header length is
what gets charged in the size accounting.

Header layouts (first byte = transform id):
  0x01 regroup   : [01][k][flags bit0=LSB-first][pad_bits]                      4 bytes
  0x02 base64    : [02][alphabet 0=RFC4648 std][line_len][eol 0=none 1=LF 2=CRLF]
                   [final_eol 0/1][pad '=' 0/1]                                 6 bytes
  0x03 hex       : [03][case 0=lower 1=upper]                                   2 bytes
  0x04 utf16     : [04][flags bit0=1 little-endian, bit1=BOM]                   2 bytes
  0x05 bitpack   : [05][bits][container_bytes][flags bit0=1 LE container,
                   bit1=1 LSB-first packing][raw_header_len u16 LE]             6 bytes
  0x06 numtext   : [06][variant 0=plain 1=delta mod 2^16][sep][eol][row_w u16 LE]
                   [int_bytes]                                                  7 bytes
  0x07 basechange: [07][B u32 LE][orig_len u32 LE]                              9 bytes
  0x08 relabel   : [08][256-byte forward table]                               257 bytes
"""
import base64 as _b64
import binascii
import numpy as np


# ---------------------------------------------------------------- 0x01 regroup
def regroup(data, k, lsb=False, want_symbols=False):
    """Re-read bytes as k-bit symbols.  MSB-first: bit string = bits of each byte
    from the most significant; first bit of a symbol is its most significant bit.
    LSB-first: bits of each byte from the least significant; first bit of a symbol
    is its least significant bit.  Each symbol is stored big-endian in ceil(k/8)
    bytes.  The last symbol is zero-padded (pad_bits recorded in the header)."""
    arr = np.frombuffer(data, dtype=np.uint8)
    bits = np.unpackbits(arr, bitorder="little" if lsb else "big")
    nbits = bits.size
    n = -(-nbits // k)
    pad = n * k - nbits
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, np.uint8)])
    rows = bits.reshape(n, k)
    if lsb:
        rows = rows[:, ::-1]
    w = (k + 7) // 8
    sym = None
    if k <= 8:
        out = np.zeros(n, np.uint8)
        for j in range(k):
            out |= (rows[:, j] << np.uint8(k - 1 - j)).astype(np.uint8)
        payload = out.tobytes()
        if want_symbols:
            sym = out
    else:
        lead = 8 * w - k
        if lead:
            full = np.zeros((n, 8 * w), np.uint8)
            full[:, lead:] = rows
        else:
            full = np.ascontiguousarray(rows)
        packed = np.packbits(full, axis=1)
        del full
        payload = packed.tobytes()
        if want_symbols:
            sym = np.zeros(n, np.uint32)
            for i in range(w):
                sym |= packed[:, i].astype(np.uint32) << np.uint32(8 * (w - 1 - i))
    header = bytes([0x01, k, 1 if lsb else 0, pad])
    if want_symbols:
        return header, payload, sym
    return header, payload


def regroup_inv(header, payload):
    assert header[0] == 0x01 and len(header) == 4
    k = header[1]
    lsb = header[2] & 1
    pad = header[3]
    w = (k + 7) // 8
    arr = np.frombuffer(payload, dtype=np.uint8)
    assert arr.size % w == 0
    n = arr.size // w
    if k <= 8:
        bits = np.empty((n, k), np.uint8)
        for j in range(k):
            bits[:, j] = (arr >> np.uint8(k - 1 - j)) & np.uint8(1)
    else:
        bits = np.unpackbits(arr.reshape(n, w), axis=1)[:, 8 * w - k:]
    if lsb:
        bits = bits[:, ::-1]
    flat = np.ascontiguousarray(bits).reshape(-1)
    if pad:
        assert not flat[-pad:].any()
        flat = flat[:-pad]
    assert flat.size % 8 == 0
    return np.packbits(flat, bitorder="little" if lsb else "big").tobytes()


# ---------------------------------------------------------------- 0x02 base64
def b64_make(raw, line_len=0, eol=b""):
    """Build the 'encoded file' from raw bytes (used to create the test file)."""
    s = _b64.b64encode(raw)
    if line_len:
        s = b"".join(s[i:i + line_len] + eol for i in range(0, len(s), line_len))
    return s


def b64_decode(encoded):
    """Forward transform at compress time: encoded file -> (header, raw bytes).
    Detects the layout from the data, then proves it by exact regeneration."""
    eol = b""
    line_len = 0
    final_eol = 0
    if b"\r\n" in encoded[:200]:
        eol = b"\r\n"
    elif b"\n" in encoded[:200]:
        eol = b"\n"
    if eol:
        line_len = encoded.index(eol)
        final_eol = 1 if encoded.endswith(eol) else 0
    body = encoded.replace(eol, b"") if eol else encoded
    raw = _b64.b64decode(body, validate=True)
    padflag = 1 if (len(raw) % 3 == 0 or body.endswith(b"=")) else 0
    header = bytes([0x02, 0, line_len, {b"": 0, b"\n": 1, b"\r\n": 2}[eol], final_eol, padflag])
    assert b64_encode_from(header, raw) == encoded
    return header, raw


def b64_encode_from(header, raw):
    """Inverse at decode time: (header, raw) -> encoded file, byte exact."""
    assert header[0] == 0x02 and len(header) == 6 and header[1] == 0
    line_len = header[2]
    eol = {0: b"", 1: b"\n", 2: b"\r\n"}[header[3]]
    final_eol = header[4]
    s = _b64.b64encode(raw)
    if not header[5]:
        s = s.rstrip(b"=")
    if line_len:
        parts = [s[i:i + line_len] for i in range(0, len(s), line_len)]
        s = eol.join(parts) + (eol if final_eol else b"")
    return s


# ---------------------------------------------------------------- 0x03 hex
def hex_decode(encoded):
    raw = binascii.unhexlify(encoded)
    case = 0 if encoded == binascii.hexlify(raw) else 1
    header = bytes([0x03, case])
    assert hex_encode_from(header, raw) == encoded
    return header, raw


def hex_encode_from(header, raw):
    assert header[0] == 0x03 and len(header) == 2
    s = binascii.hexlify(raw)
    return s.upper() if header[1] else s


# ---------------------------------------------------------------- 0x04 utf16
def utf16_decode(encoded):
    """UTF-16LE (no BOM) file -> (header, UTF-8 bytes)."""
    text = encoded.decode("utf-16-le", errors="strict")
    raw = text.encode("utf-8")
    header = bytes([0x04, 1])
    assert utf16_encode_from(header, raw) == encoded
    return header, raw


def utf16_encode_from(header, raw):
    assert header[0] == 0x04 and len(header) == 2 and header[1] == 1
    return raw.decode("utf-8", errors="strict").encode("utf-16-le")


# ---------------------------------------------------------------- 0x05 bitpack
def bitpack_make(unpacked, raw_header_len, bits, lsb=False):
    """Build the tightly packed test file: raw header bytes verbatim, then each
    16-bit little-endian sample written with `bits` bits."""
    hdr = unpacked[:raw_header_len]
    s = np.frombuffer(unpacked[raw_header_len:], dtype="<u2")
    assert int(s.max()) < (1 << bits)
    if lsb:
        b = np.unpackbits(s.view(np.uint8).reshape(-1, 2), axis=1, bitorder="little")[:, :bits]
        return hdr + np.packbits(b.reshape(-1), bitorder="little").tobytes()
    be = s.astype(">u2").view(np.uint8).reshape(-1, 2)
    b = np.unpackbits(be, axis=1)[:, 16 - bits:]
    return hdr + np.packbits(b.reshape(-1)).tobytes()


def bitpack_unpack(packed, raw_header_len, bits, lsb=False):
    """Forward transform at compress time: packed file -> (header, unpacked file
    = raw header + 16-bit LE samples)."""
    hdr = packed[:raw_header_len]
    body = np.frombuffer(packed[raw_header_len:], dtype=np.uint8)
    n = (body.size * 8) // bits
    if lsb:
        b = np.unpackbits(body, bitorder="little")[:n * bits].reshape(n, bits)
        full = np.zeros((n, 16), np.uint8)
        full[:, :bits] = b
        s = np.packbits(full, axis=1, bitorder="little").tobytes()
    else:
        b = np.unpackbits(body)[:n * bits].reshape(n, bits)
        full = np.zeros((n, 16), np.uint8)
        full[:, 16 - bits:] = b
        s = np.packbits(full, axis=1).view(">u2").astype("<u2").tobytes()
    header = bytes([0x05, bits, 2, 1 | (2 if lsb else 0)]) + int(raw_header_len).to_bytes(2, "little")
    unpacked = hdr + s
    assert bitpack_pack_from(header, unpacked) == packed
    return header, unpacked


def bitpack_pack_from(header, unpacked):
    """Inverse at decode time: (header, unpacked) -> packed file, byte exact."""
    assert header[0] == 0x05 and len(header) == 6 and header[2] == 2 and header[3] & 1
    bits = header[1]
    lsb = bool(header[3] & 2)
    rhl = int.from_bytes(header[4:6], "little")
    return bitpack_make(unpacked, rhl, bits, lsb)


# ---------------------------------------------------------------- 0x06 numtext
def numtext_make(samples_u16, row_w):
    """Decimal ASCII, comma separated, one image row per line, LF after each row."""
    s = np.asarray(samples_u16, dtype=np.uint16).reshape(-1, row_w)
    lines = [b",".join(b"%d" % v for v in row) for row in s.tolist()]
    return b"\n".join(lines) + b"\n"


def numtext_parse(text, variant=0):
    """Forward at compress time: text -> (header, binary).  variant 0: 16-bit LE
    integers; variant 1: 16-bit LE differences to the previous sample (mod 2^16,
    first sample kept, raster order); variant 2: zig-zag coded differences."""
    lines = text.split(b"\n")
    assert lines[-1] == b""
    lines = lines[:-1]
    row_w = lines[0].count(b",") + 1
    vals = np.array([int(x) for ln in lines for x in ln.split(b",")], dtype=np.int64)
    assert vals.size == row_w * len(lines) and vals.min() >= 0 and vals.max() < 65536
    s = vals.astype(np.uint16)
    if variant == 0:
        body = s.astype("<u2").tobytes()
    else:
        d = np.empty_like(s)
        d[0] = s[0]
        d[1:] = s[1:] - s[:-1]          # uint16 arithmetic wraps mod 2^16
        if variant == 2:
            sd = d.astype(np.int16).astype(np.int32)
            d = ((sd << 1) ^ (sd >> 15)).astype(np.uint16)
        body = d.astype("<u2").tobytes()
    header = bytes([0x06, variant, ord(","), ord("\n")]) + int(row_w).to_bytes(2, "little") + bytes([2])
    assert numtext_format_from(header, body) == text
    return header, body


def numtext_format_from(header, body):
    """Inverse at decode time: (header, binary) -> text, byte exact."""
    assert header[0] == 0x06 and len(header) == 7 and header[6] == 2
    variant = header[1]
    sep = bytes([header[2]])
    eol = bytes([header[3]])
    row_w = int.from_bytes(header[4:6], "little")
    d = np.frombuffer(body, dtype="<u2").astype(np.uint16)
    if variant == 2:
        z = d.astype(np.int32)
        d = ((z >> 1) ^ -(z & 1)).astype(np.int16).astype(np.uint16)
    if variant in (1, 2):
        s = np.cumsum(d, dtype=np.uint16)   # wraps mod 2^16
    else:
        s = d
    rows = s.reshape(-1, row_w).tolist()
    return eol.join(sep.join(b"%d" % v for v in row) for row in rows) + eol


# ---------------------------------------------------------------- 0x07 base change
def _digit_width(B):
    w = 1
    while (1 << (8 * w)) < B:
        w += 1
    return w


def _to_digits(n, B):
    """Most-significant-first list of base-B digits of n (divide and conquer)."""
    if n == 0:
        return [0]
    LEAF = 32
    pows = [B ** LEAF]           # pows[j] = B^(LEAF * 2^j)
    while pows[-1] * pows[-1] <= n:
        pows.append(pows[-1] * pows[-1])

    def leaf(x, cnt):
        out = [0] * cnt
        i = cnt - 1
        while x:
            x, r = divmod(x, B)
            out[i] = r
            i -= 1
        return out

    def rec(x, j):
        # exactly LEAF * 2^(j+1) digits, zero padded on the left
        if j < 0:
            return leaf(x, LEAF)
        hi, lo = divmod(x, pows[j])
        return rec(hi, j - 1) + rec(lo, j - 1)

    digs = rec(n, len(pows) - 1)
    i = 0
    while digs[i] == 0:
        i += 1
    return digs[i:]


def _from_digits(digs, B):
    """Inverse of _to_digits (pairwise divide and conquer)."""
    vals = list(digs)
    p = B
    while len(vals) > 1:
        if len(vals) & 1:
            vals.insert(0, 0)
        vals = [vals[i] * p + vals[i + 1] for i in range(0, len(vals), 2)]
        p = p * p
    return vals[0]


def basechange(data, B):
    """File = one big-endian base-256 integer; write its base-B digits, most
    significant first, each digit big-endian in the fewest whole bytes."""
    n = int.from_bytes(data, "big")
    digs = _to_digits(n, B)
    w = _digit_width(B)
    if w == 1:
        payload = bytes(digs)
    else:
        payload = b"".join(d.to_bytes(w, "big") for d in digs)
    header = bytes([0x07]) + int(B).to_bytes(4, "little") + len(data).to_bytes(4, "little")
    return header, payload


def basechange_inv(header, payload):
    assert header[0] == 0x07 and len(header) == 9
    B = int.from_bytes(header[1:5], "little")
    L = int.from_bytes(header[5:9], "little")
    w = _digit_width(B)
    assert len(payload) % w == 0
    if w == 1:
        digs = list(payload)
    else:
        digs = [int.from_bytes(payload[i:i + w], "big") for i in range(0, len(payload), w)]
    assert max(digs) < B
    n = _from_digits(digs, B)
    return n.to_bytes(L, "big")


# ---------------------------------------------------------------- 0x08 relabel
def relabel(data, table):
    t = np.asarray(table, dtype=np.uint8)
    assert sorted(t.tolist()) == list(range(256))
    payload = t[np.frombuffer(data, dtype=np.uint8)].tobytes()
    return bytes([0x08]) + t.tobytes(), payload


def relabel_inv(header, payload):
    assert header[0] == 0x08 and len(header) == 257
    t = np.frombuffer(header[1:], dtype=np.uint8)
    inv = np.empty(256, np.uint8)
    inv[t] = np.arange(256, dtype=np.uint8)
    return inv[np.frombuffer(payload, dtype=np.uint8)].tobytes()
