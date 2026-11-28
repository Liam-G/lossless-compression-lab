import sys, numpy as np, hashlib
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I drops the script dir
import tf
d = open(sys.argv[1], "rb").read(100003)
for lsb in (False, True):
    for k in range(1, 33):
        h, p, s = tf.regroup(d, k, lsb, want_symbols=True)
        assert tf.regroup_inv(h, p) == d, (k, lsb)
        assert len(p) == -(-len(d) * 8 // k) * ((k + 7) // 8)
        assert int(s.max()) < (1 << k)
        # independent check through Python big integers
        n = int.from_bytes(d, "big") if not lsb else None
        if not lsb:
            pad = h[3]; n <<= pad; cnt = (len(d) * 8 + pad) // k
            ref = [(n >> (k * (cnt - 1 - i))) & ((1 << k) - 1) for i in (0, 1, 2, cnt - 1)]
            assert ref == [int(s[0]), int(s[1]), int(s[2]), int(s[-1])], (k, ref)
h, p = tf.regroup(d, 8); assert p == d
h, p = tf.regroup(d[:100000], 16); assert p == d[:100000]
h, p = tf.regroup(d[:100000], 16, True); assert p == np.frombuffer(d[:100000], "<u2").astype(">u2").tobytes()
for B in (2, 3, 7, 10, 16, 255, 256, 257, 4096, 65521, 65536, 65537, 1000003):
    x = d[:5000]
    h, p = tf.basechange(x, B); assert tf.basechange_inv(h, p) == x, B
    n = int.from_bytes(x, "big"); ds = []
    while n: n, r = divmod(n, B); ds.append(r)
    w = tf._digit_width(B)
    assert p == b"".join(v.to_bytes(w, "big") for v in ds[::-1]), B
assert tf.basechange(d[:5000], 256)[1] == d[:5000]
print("selftest ok")
