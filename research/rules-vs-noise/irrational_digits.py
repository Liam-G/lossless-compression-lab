"""Can digits of sqrt(2), sqrt(3), sqrt(5), e, pi (and their digit-wise sums, i.e. XOR in base 2) recreate a target?
For each target we find the longest prefix that appears ANYWHERE in the digit streams, and compare it with
the bits needed to say where it is (log2 of the number of start positions searched).
"""
import math, os, sys, time

NB = 1 << 22                          # bits per constant
G = 64                                # guard bits

def sqrt_bits(k): return math.isqrt(k << (2 * (NB + G))) >> G

def e_bits():
    def bs(a, b):
        if b - a == 1: return 1, b
        m = (a + b) // 2; p1, q1 = bs(a, m); p2, q2 = bs(m, b); return p1 * q2 + p2, q1 * q2
    K = 2
    while math.lgamma(K + 1) / math.log(2) < NB + 2 * G: K *= 2
    P, Q = bs(0, K)
    return ((1 << (NB + G)) + (P << (NB + G)) // Q) >> G

def pi_bits():
    C3 = 10939058860032000
    def bs(a, b):
        if b - a == 1:
            P = Q = 1 if a == 0 else None
            if a: P = (6 * a - 5) * (2 * a - 1) * (6 * a - 1); Q = a * a * a * C3
            T = P * (13591409 + 545140134 * a)
            return P, Q, (-T if a & 1 else T)
        m = (a + b) // 2; P1, Q1, T1 = bs(a, m); P2, Q2, T2 = bs(m, b)
        return P1 * P2, Q1 * Q2, Q2 * T1 + P1 * T2
    terms = int((NB + 2 * G) * math.log10(2) / 14.18) + 2
    P, Q, T = bs(0, terms)
    s = math.isqrt(10005 << (2 * (NB + G)))
    return (Q * 426880 * s // T) >> G

def frac_bits(x, intbits):
    b = format(x, 'b'); return b[intbits:intbits + NB]          # drop the integer part

def longest_prefix(target, streams):
    k = 1
    while k <= len(target) and any(target[:k] in s for s in streams): k += 1
    return k - 1

if __name__ == '__main__':
    t0 = time.time()
    st = {'sqrt2': frac_bits(sqrt_bits(2), 1), 'sqrt3': frac_bits(sqrt_bits(3), 1), 'sqrt5': frac_bits(sqrt_bits(5), 2),
          'e': frac_bits(e_bits(), 2), 'pi': frac_bits(pi_bits(), 2)}
    print(f'digits ready [{time.time() - t0:.0f}s]  check: pi starts 0x{int(st["pi"][:32], 2):08x} (expect 243f6a88), '
          f'e starts 0x{int(st["e"][:32], 2):08x} (expect b7e15162)', flush=True)
    names = list(st)
    xor = lambda a, b: format(int(a, 2) ^ int(b, 2), f'0{NB}b')
    combos = dict(st)
    for i in range(len(names)):
        for j in range(i + 1, len(names)): combos[f'{names[i]}+{names[j]}'] = xor(st[names[i]], st[names[j]])
    combos['sum of all five'] = format(int(st['sqrt2'], 2) ^ int(st['sqrt3'], 2) ^ int(st['sqrt5'], 2) ^ int(st['e'], 2) ^ int(st['pi'], 2), f'0{NB}b')
    bits = lambda bs: ''.join(format(c, '08b') for c in bs)
    targets = {'enwik8 text (start)': bits(open(sys.argv[1], 'rb').read(16)),
               'xz output of enwik8 text': bits(open(sys.argv[2], 'rb').read(80)[64:]),
               'seeded random bytes': bits(__import__('random').Random(20261128).randbytes(16)),
               'CONTROL: a piece of sqrt(2) itself': st['sqrt2'][3_000_000:3_000_128]}
    print(f'{len(combos)} digit streams ({len(st)} constants + {len(combos) - len(st)} digit-wise sums), {NB:,} bits each')
    for sizes in (1 << 16, 1 << 18, 1 << 20, NB):
        sub = [s[:sizes] for s in combos.values()]
        name_cost = math.log2(len(sub) * sizes)
        row = '  '.join(f'{k.split(" (")[0][:26]:26} {longest_prefix(v, sub):3d}' for k, v in targets.items())
        print(f'search {len(sub)} streams x {sizes:>9,} start positions -> cost to name the spot {name_cost:5.1f} bits | bits recreated: {row}', flush=True)
    print(f'[{time.time() - t0:.0f}s]')
