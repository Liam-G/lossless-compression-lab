#!/usr/bin/env python3
"""p234.py - PART 2 (hidden alphabets), PART 3 (whole-number base change),
PART 4 (relabeling control).

  python3 -I p234.py --corpus /path/to/corpus --lane 1 --part 4|2|3

One JSON line per experiment is appended to raw/p{2,3,4}_rows.jsonl.  All
compressions go through common.sizes_for (content-addressed cache, SHA-256
round trip of every codec run), so re-running is cheap and resumable.
"with" = len(recipe header) + compressed size of the re-alphabeted file,
"without" = compressed size of the file as given; identical command lines.
"""
import os, sys, time, argparse
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I drops the script dir
import numpy as np
import common as C
import tf

MIB4 = 4 * 1024 * 1024
PPMD = ["ppmd_o4", "ppmd_o8", "ppmd_o16"]


def rd(corpus, rel, limit=None):
    with open(os.path.join(corpus, rel), "rb") as f:
        return f.read() if limit is None else f.read(limit)


def compare(lane, part, name, given, header, alt, regen_ok, backends, extra=None, done=None):
    """given = file as handed to us; alt = re-alphabeted file; header = recipe."""
    t0 = time.time()
    with lane:
        a = C.sizes_for(lane, given, backends)
    with lane:
        b = C.sizes_for(lane, alt, backends)
    row = {"part": part, "name": name, "n_given": len(given), "sha256_given": C.sha256(given),
           "n_alt": len(alt), "sha256_alt": C.sha256(alt), "header_hex": header.hex() if len(header) <= 16 else header[:16].hex() + "...",
           "header_len": len(header), "regenerated_byte_exact": bool(regen_ok), "backends": {}, "ts": time.time()}
    if extra:
        row.update(extra)
    for be in backends:
        row["backends"][be] = {
            "cmd": a[be]["cmd"], "without": a[be]["size"], "alt_payload": b[be]["size"],
            "with": b[be]["size"] + len(header), "delta": b[be]["size"] + len(header) - a[be]["size"],
            "ratio_with_over_without": (b[be]["size"] + len(header)) / a[be]["size"],
            "cpu_c_without": a[be]["cpu_c"], "cpu_c_with": b[be]["cpu_c"],
            "maxrss_c_kb_without": a[be]["maxrss_c_kb"], "maxrss_c_kb_with": b[be]["maxrss_c_kb"],
            "accepted": bool(a[be]["roundtrip_ok"] and b[be]["roundtrip_ok"] and regen_ok)}
    pp = [be for be in PPMD if be in backends]
    if pp:
        # the PPMd order is a searched option: charge 1 byte for it on both sides
        wo = min(a[be]["size"] for be in pp) + 1
        wi = min(b[be]["size"] for be in pp) + 1 + len(header)
        row["backends"]["ppmd_best_plus1"] = {
            "without": wo, "with": wi, "delta": wi - wo, "ratio_with_over_without": wi / wo,
            "order_without": min(pp, key=lambda be: a[be]["size"]), "order_with": min(pp, key=lambda be: b[be]["size"]),
            "accepted": bool(regen_ok)}
    row["wall_s"] = time.time() - t0
    C.append_jsonl(os.path.join(C.RAW, "p%d_rows.jsonl" % part), row)
    print("P%d %-28s given=%d alt=%d hdr=%d regen=%s | " % (part, name, len(given), len(alt), len(header), regen_ok) +
          " ".join("%s:%d->%d" % (be, v["without"], v["with"]) for be, v in row["backends"].items()) +
          "  [%.0fs]" % row["wall_s"], flush=True)
    return row


def part4(corpus, lane):
    perm = np.random.default_rng(20261118).permutation(256).astype(np.uint8)
    for name, rel, lim in (("dickens_4MiB", "silesia/dickens", MIB4), ("x-ray_whole", "silesia/x-ray", None)):
        data = rd(corpus, rel, lim)
        header, payload = tf.relabel(data, perm)
        ok = tf.relabel_inv(header, payload) == data
        compare(lane, 4, "relabel|" + name, data, header, payload, ok, C.B_FULL,
                {"seed": 20261118, "rng": "numpy.random.default_rng(seed).permutation(256)",
                 "note": "given = original, alt = relabeled; header = 1 id byte + 256-byte table"})


def part2(corpus, lane):
    B = C.B_FULL
    raw = rd(corpus, "enwik8/enwik8", MIB4)
    # a. base64
    for nm, ll, eol in (("a_base64_nolf", 0, b""), ("a_base64_76col_LF", 76, b"\n")):
        enc = tf.b64_make(raw, ll, eol)
        header, dec = tf.b64_decode(enc)
        ok = (tf.b64_encode_from(header, dec) == enc) and dec == raw
        compare(lane, 2, nm, enc, header, dec, ok, B, {"source": "enwik8 first 4194304 bytes"})
    # b. hex
    enc = raw.hex().encode()
    header, dec = tf.hex_decode(enc)
    ok = (tf.hex_encode_from(header, dec) == enc) and dec == raw
    compare(lane, 2, "b_hex_lower", enc, header, dec, ok, B, {"source": "enwik8 first 4194304 bytes"})
    # c. UTF-16LE
    enc = raw.decode("utf-8").encode("utf-16-le")
    header, dec = tf.utf16_decode(enc)
    ok = (tf.utf16_encode_from(header, dec) == enc) and dec == raw
    compare(lane, 2, "c_utf16le", enc, header, dec, ok, B, {"source": "enwik8 first 4194304 bytes (valid UTF-8 at the cut)"})
    del raw, enc, dec
    # d. x-ray bit depth
    xr = rd(corpus, "silesia/x-ray")
    HL = 240
    s = np.frombuffer(xr[HL:], dtype="<u2")
    sb = np.frombuffer(xr[HL:], dtype=">u2")
    depth = {"file_len": len(xr), "raw_header_len": HL, "n_samples": int(s.size),
             "le_min": int(s.min()), "le_max": int(s.max()), "le_or_mask": int(np.bitwise_or.reduce(s)),
             "le_distinct": int(np.unique(s).size), "be_max": int(sb.max()), "be_or_mask": int(np.bitwise_or.reduce(sb)),
             "le_mean_abs_diff": float(np.abs(np.diff(s.astype(np.int64))).mean()),
             "be_mean_abs_diff": float(np.abs(np.diff(sb.astype(np.int64))).mean()),
             "bits_used": int(int(s.max()).bit_length())}
    bits = depth["bits_used"]
    for lsb in (False, True):
        packed = tf.bitpack_make(xr, HL, bits, lsb)
        header, unp = tf.bitpack_unpack(packed, HL, bits, lsb)
        ok = (tf.bitpack_pack_from(header, unp) == packed) and unp == xr
        compare(lane, 2, "d_xray_pack%d_%s" % (bits, "lsbfirst" if lsb else "msbfirst"), packed, header, unp, ok, B,
                {"depth": depth, "note": "given = 240 header bytes + samples packed at %d bits; alt = 16-bit LE samples (= the original x-ray file)" % bits})
    # e. numbers as text
    W = 1900
    rows = (2 * 1024 * 1024 // 2) // W          # whole image rows inside a 2 MiB portion of samples
    samp = s[:rows * W]
    text = tf.numtext_make(samp, W)
    for variant, vn in ((0, "binary16le"), (1, "binary16le_delta"), (2, "binary16le_delta_zigzag")):
        header, body = tf.numtext_parse(text, variant)
        ok = tf.numtext_format_from(header, body) == text
        compare(lane, 2, "e_numtext_" + vn, text, header, body, ok, B,
                {"rows": rows, "row_width": W, "n_samples": int(samp.size), "binary_bytes_equiv": int(samp.size) * 2,
                 "note": "given = decimal ASCII, comma separated, LF after every row; samples = first %d rows of x-ray" % rows})
    # e2. packed 12-bit binary as the alt (parse + tight pack), for reference
    header0, body0 = tf.numtext_parse(text, 0)
    b12 = tf.bitpack_make(body0, 0, 12, False)
    h5, unp = tf.bitpack_unpack(b12, 0, 12, False)
    ok = unp == body0 and tf.numtext_format_from(header0, unp) == text
    compare(lane, 2, "e_numtext_binary12packed", text, header0 + h5, b12, ok, B,
            {"rows": rows, "row_width": W, "note": "alt = parsed then tightly packed at 12 bits (two recipe headers charged)"})


def part3(corpus, lane):
    BASES = [256, 2, 16, 4096, 65536, 255, 257, 3, 7, 10, 65521, 65537, 1000003]
    BE = ["xz9e", "ppmd_o4", "ppmd_o8", "ppmd_o16"]
    N = 256 * 1024
    for name, rel in (("dickens_256KiB", "silesia/dickens"), ("x-ray_256KiB", "silesia/x-ray")):
        data = rd(corpus, rel, N)
        for Bv in BASES:
            t0 = time.process_time()
            header, payload = tf.basechange(data, Bv)
            t1 = time.process_time()
            back = tf.basechange_inv(header, payload)
            t2 = time.process_time()
            ok = (C.sha256(back) == C.sha256(data)) and len(back) == len(data)
            w = tf._digit_width(Bv)
            dig = np.frombuffer(payload, dtype=np.uint8).reshape(-1, w)
            v = np.zeros(dig.shape[0], np.int64)
            for i in range(w):
                v = (v << 8) | dig[:, i]
            cnt = np.bincount(v)
            cnt = cnt[cnt > 0]
            p = cnt / cnt.sum()
            H = float(-(p * np.log2(p)).sum())
            compare(lane, 3, "base%d|%s" % (Bv, name), data, header, payload, ok, BE,
                    {"base": Bv, "digit_bytes": w, "n_digits": int(dig.shape[0]), "sample_raw_bytes": len(data),
                     "payload_raw_bytes": len(payload), "identity": payload == data,
                     "digit_order0_entropy_bits": H, "digit_plugin_bytes": H * dig.shape[0] / 8.0,
                     "distinct_digits": int(cnt.size),
                     "cpu_convert_s": t1 - t0, "cpu_invert_s": t2 - t1})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--lane", type=int, required=True)
    ap.add_argument("--part", type=int, required=True)
    a = ap.parse_args()
    lane = C.Lane(a.lane)
    {2: part2, 3: part3, 4: part4}[a.part](a.corpus, lane)
    print("part %d finished" % a.part, flush=True)


if __name__ == "__main__":
    main()
