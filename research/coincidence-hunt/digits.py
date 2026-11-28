"""Write D decimal digits (after the point) of several constants as raw bytes 0..9, one file each.
usage: digits.py OUTDIR [D]
"""
import math, os, sys, time
sys.set_int_max_str_digits(0)
out = sys.argv[1]; D = int(sys.argv[2]) if len(sys.argv) > 2 else (1 << 20) + 64
G = 30                                   # guard digits
S = 10 ** (D + G)

def isqrt_scaled(k): return math.isqrt(k * S * S)          # floor(sqrt(k) * S)
def e_scaled():
    def bs(a, b):
        if b - a == 1: return 1, b
        m = (a + b) // 2; p1, q1 = bs(a, m); p2, q2 = bs(m, b); return p1 * q2 + p2, q1 * q2
    K = 2
    while math.lgamma(K + 1) / math.log(10) < D + 2 * G: K *= 2
    P, Q = bs(0, K); return S + P * S // Q
def pi_scaled():
    C3 = 10939058860032000
    def bs(a, b):
        if b - a == 1:
            if a == 0: P = Q = 1
            else: P = (6 * a - 5) * (2 * a - 1) * (6 * a - 1); Q = a * a * a * C3
            T = P * (13591409 + 545140134 * a); return P, Q, (-T if a & 1 else T)
        m = (a + b) // 2; P1, Q1, T1 = bs(a, m); P2, Q2, T2 = bs(m, b)
        return P1 * P2, Q1 * Q2, Q2 * T1 + P1 * T2
    terms = int((D + 2 * G) / 14.18) + 2
    P, Q, T = bs(0, terms); s = math.isqrt(10005 * S * S)
    return Q * 426880 * s // T

def frac_digits(x_scaled):     # x_scaled = floor(x * 10^(D+G)); keep D digits after the point
    s = str(x_scaled); ip = len(s) - (D + G); return bytes(int(c) for c in s[ip:ip + D])

t0 = time.time(); os.makedirs(out, exist_ok=True)
r2, r3, r5 = isqrt_scaled(2), isqrt_scaled(3), isqrt_scaled(5)
consts = {'pi': pi_scaled(), 'e': e_scaled(), 'sqrt2': r2, 'sqrt3': r3, 'sqrt5': r5, 'phi': (S + r5) // 2, 'sqrt2+sqrt3': r2 + r3}
for name, v in consts.items():
    d = frac_digits(v); open(os.path.join(out, name + '.dig'), 'wb').write(d)
    print(f'{name:12} {"".join(map(str, d[:20]))}...  ({len(d):,} digits, {time.time() - t0:.0f}s)', flush=True)
