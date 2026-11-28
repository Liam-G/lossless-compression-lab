// Block generator encoder (lab PoC): describe data block by block, each block by the cheapest GENERATOR (+ corrections).
// usage: blockgen DATA NBYTES BLOCK DIGITDIR MODE OUT.prog      MODE = math (only rule generators) | all (+ generators that reuse earlier data)
// Each block's line in OUT.prog is code that regenerates it. After encoding, every line is re-run and compared (round trip).
// Costs (bits): 4 (which family) + naming the candidate (log2 of the family's candidate count) + corrections.
//   bit corrections : log2(n+1) + log2 C(n, m)                          (m flipped bits among n)
//   byte corrections: log2(L+1) + log2 C(L, c) + 8 per replaced byte      (c replaced bytes among L)
#include <gmp.h>
#include <algorithm>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include "../statico/src/io.hpp"
using u64 = unsigned long long;
static double lg2C(double n, double m) { return (std::lgamma(n + 1) - std::lgamma(m + 1) - std::lgamma(n - m + 1)) / std::log(2.0); }
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

struct Bits { std::vector<u64> w; size_t n = 0;
    void push(int b) { if (n % 64 == 0) w.push_back(0); if (b) w[n / 64] |= 1ull << (63 - n % 64); n++; }
    void push_byte(int v) { for (int k = 7; k >= 0; k--) push(v >> k & 1); }
    int get(size_t i) const { return (int)(w[i / 64] >> (63 - i % 64) & 1); }
    u64 ext(size_t p) const { size_t q = p / 64, b = p % 64; u64 hi = q < w.size() ? w[q] : 0; if (!b) return hi; return (hi << b) | (q + 1 < w.size() ? w[q + 1] >> (64 - b) : 0); }
    void pad() { for (int k = 0; k < 128; k++) push(0); n -= 128; }
};
static std::vector<uint8_t> to_bytes(const Bits& b, size_t t, size_t L) { std::vector<uint8_t> o(L); for (size_t i = 0; i < L; i++) { int v = 0; for (int k = 0; k < 8; k++) v = v << 1 | b.get(t + 8 * i + k); o[i] = (uint8_t)v; } return o; }

// ---------- the block being described ----------
struct Tgt { const uint8_t* b; size_t L, n, KW; u64 mask; Bits bits; };
static Tgt make_tgt(const uint8_t* p, size_t L) { Tgt T; T.b = p; T.L = L; for (size_t i = 0; i < L; i++) T.bits.push_byte(p[i]); T.n = T.bits.n; T.KW = (T.n + 63) / 64;
    T.mask = T.n % 64 ? ~0ull << (64 - T.n % 64) : ~0ull; T.bits.pad(); return T; }
static long eval_bits(const Tgt& T, const Bits& S, size_t t, long bound, bool& comp) {
    long err = 0, cerr = 0;
    for (size_t k = 0; k < T.KW; k++) { u64 x = S.ext(t + 64 * k) ^ T.bits.w[k]; long wd = 64; if (k + 1 == T.KW) { x &= T.mask; wd = (long)(T.n - 64 * k); }
        long e = std::popcount(x); err += e; cerr += wd - e; if (err > bound && cerr > bound) return -1; }
    comp = cerr < err; return std::min(err, cerr);
}
static double bitfix_cost(size_t n, long m) { return std::log2((double)n + 1) + lg2C((double)n, (double)m); }
static double bytefix_cost(size_t L, long c) { return std::log2((double)L + 1) + lg2C((double)L, (double)c) + 8.0 * c; }

// ---------- a description ----------
enum Fam { RAW, STREAM, ROOT, PRNG, FORMULA, INTSEQ, PATTERN, COPY, LZP, ORDERK, NFAM };
static const char* FAMN[NFAM] = {"raw", "digits+sequences", "roots+fractions", "random generators", "formulas", "integer sequences", "repeats+cellular", "copy earlier data", "last follower", "most frequent follower"};
struct Desc { int fam = RAW; double bits = 1e300; long p[4] = {0, 0, 0, 0}; bool comp = false; bool bytefix = false; std::string code; };

// ---------- banks (built once) ----------
struct Named { std::string name; Bits bits; };
static std::vector<Named> STREAMS, ROOTS; static double STREAM_NAME, ROOT_NAME; static size_t STREAM_P;
static void build_streams(const std::string& dir) {
    const size_t N = (1 << 20) - 64;
    std::vector<std::pair<std::string, std::vector<uint8_t>>> dg;
    for (auto nm : {"pi", "e", "sqrt2", "sqrt3", "sqrt5", "phi", "sqrt2+sqrt3"}) { std::vector<uint8_t> d; read_all((dir + "/" + nm + ".dig").c_str(), d); dg.push_back({nm, d}); }
    size_t nc = dg.size();
    for (size_t i = 0; i < nc; i++) for (size_t j = i + 1; j < nc; j++) { std::vector<uint8_t> s(N); for (size_t k = 0; k < N; k++) s[k] = (uint8_t)((dg[i].second[k] + dg[j].second[k]) % 10); dg.push_back({dg[i].first + "+" + dg[j].first, s}); }
    std::vector<Named> base; const char* tn[8] = {"odd", "div3", "ge5", "bit1", "bit2", "bit3", "zero", "prime"};
    for (auto& [nm, d] : dg) for (int t = 0; t < 8; t++) { Named b; b.name = "digits(\"" + nm + "\", rule=\"" + tn[t] + "\""; for (size_t k = 0; k < N; k++) { int x = d[k], r = 0;
        switch (t) { case 0: r = x & 1; break; case 1: r = x % 3 == 0; break; case 2: r = x >= 5; break; case 3: r = x >> 1 & 1; break; case 4: r = x >> 2 & 1; break; case 5: r = x >> 3 & 1; break; case 6: r = x == 0; break; default: r = x == 2 || x == 3 || x == 5 || x == 7; }
        b.bits.push(r); } base.push_back(std::move(b)); }
    auto add = [&](const std::string& nm, auto f) { Named b; b.name = nm + "("; for (size_t k = 0; k < N; k++) b.bits.push(f(k)); base.push_back(std::move(b)); };
    add("thue_morse", [](size_t k) { return std::popcount(k) & 1; });
    { std::vector<int> a = {0}, bb = {0, 1}; while (bb.size() < N) { auto c = bb; c.insert(c.end(), a.begin(), a.end()); a = bb; bb = c; } add("fibonacci_word", [&](size_t k) { return bb[k]; }); }
    add("dragon_folds", [](size_t k) { size_t m = k + 1; while (!(m & 1)) m >>= 1; return (int)((m >> 1) & 1); });
    add("rudin_shapiro", [](size_t k) { int c = 0; for (size_t m = k; m; m >>= 1) if ((m & 3) == 3) c++; return c & 1; });
    add("period_doubling", [](size_t k) { return (int)(std::countr_zero(k + 1) & 1); });
    { std::vector<int> ch; for (size_t v = 1; ch.size() < N; v++) { int L = 64 - std::countl_zero(v); for (int i = L - 1; i >= 0; i--) ch.push_back(v >> i & 1); } add("champernowne", [&](size_t k) { return ch[k]; }); }
    STREAM_P = 1 << 18;
    for (auto& b : base) for (int s : {1, 2, 3, 4}) { Named d; d.name = b.name + ", step=" + std::to_string(s); for (int ph = 0; ph < s; ph++) for (size_t k = ph; k < b.bits.n; k += s) d.bits.push(b.bits.get(k));
        d.bits.pad(); STREAMS.push_back(std::move(d)); }
    STREAM_NAME = std::log2((double)STREAMS.size() * STREAM_P * 2);
    const size_t L = 8192; mpz_t x, f; mpz_init(x); mpz_init(f);
    auto frac = [&](const std::string& nm) { mpz_tdiv_r_2exp(f, x, L); std::vector<uint8_t> buf(L / 8 + 8, 0); size_t cnt = 0; mpz_export(buf.data(), &cnt, 1, 1, 1, 0, f);
        Named b; b.name = nm; for (size_t i = 0; i < L / 8 - cnt; i++) b.bits.push_byte(0); for (size_t i = 0; i < cnt; i++) b.bits.push_byte(buf[i]); b.bits.pad(); ROOTS.push_back(std::move(b)); };
    for (unsigned n = 2; n <= 4000; n++) { unsigned r = (unsigned)std::sqrt((double)n); if (r * r == n) continue; mpz_set_ui(x, n); mpz_mul_2exp(x, x, 2 * L); mpz_sqrt(x, x); frac("sqrt(" + std::to_string(n) + ")"); }
    for (unsigned n = 2; n <= 1000; n++) { unsigned r = (unsigned)std::cbrt((double)n + 0.5); if (r * r * r == n) continue; mpz_set_ui(x, n); mpz_mul_2exp(x, x, 3 * L); mpz_root(x, x, 3); frac("cbrt(" + std::to_string(n) + ")"); }
    for (unsigned q = 3; q <= 4095; q += 2) { mpz_set_ui(x, 1); mpz_mul_2exp(x, x, L); mpz_tdiv_q_ui(x, x, q); frac("1/" + std::to_string(q)); }
    mpz_clear(x); mpz_clear(f); ROOT_NAME = std::log2((double)ROOTS.size() * 6000 * 2);
}

// formulas: f(i) and x(k+1)=f(x(k),k), size <= 5, precomputed outputs
enum Op : uint8_t { I_, X_, C_, NEG, SQR, ISQ, POPC, DSUM, TRI, FIB, ADD, SUB, MUL, DIV, MOD, XOR, AND, OR, SHL, SHR, POW, GCD };
static const char* OPN[] = {"i", "x", "c", "-", "sq", "isqrt", "popcount", "digitsum", "tri", "fib", "+", "-", "*", "//", "%", "^", "&", "|", "<<", ">>", "**", "gcd"};
struct Node { uint8_t op; u64 c; int32_t a, b; };
static std::vector<Node> NODES; static u64 FIBT[94];
static u64 ev(int n, u64 i, u64 x) {
    const Node& N = NODES[n];
    switch (N.op) { case I_: return i; case X_: return x; case C_: return N.c; case NEG: return 0 - ev(N.a, i, x); case SQR: { u64 v = ev(N.a, i, x); return v * v; }
    case ISQ: { u64 v = ev(N.a, i, x); u64 r = (u64)std::sqrt((double)v); while (r && r * r > v) r--; while ((r + 1) * (r + 1) <= v && r < 0xFFFFFFFFull) r++; return r; }
    case POPC: return (u64)std::popcount(ev(N.a, i, x)); case DSUM: { u64 v = ev(N.a, i, x), s = 0; while (v) { s += v % 10; v /= 10; } return s; }
    case TRI: { u64 v = ev(N.a, i, x); return v * (v + 1) / 2; } case FIB: return FIBT[ev(N.a, i, x) % 94]; default: break; }
    u64 a = ev(N.a, i, x), b = ev(N.b, i, x);
    switch (N.op) { case ADD: return a + b; case SUB: return a - b; case MUL: return a * b; case DIV: return b ? a / b : 0; case MOD: return b ? a % b : 0; case XOR: return a ^ b; case AND: return a & b;
    case OR: return a | b; case SHL: return a << (b & 63); case SHR: return a >> (b & 63); case POW: { u64 r = 1, e = b & 63, p = a; while (e) { if (e & 1) r *= p; p *= p; e >>= 1; } return r; }
    case GCD: { while (b) { u64 t = a % b; a = b; b = t; } return a; } }
    return 0;
}
static std::string show(int n) { const Node& N = NODES[n]; if (N.op == I_) return "i"; if (N.op == X_) return "x"; if (N.op == C_) return std::to_string(N.c);
    if (N.op < ADD) return std::string(OPN[N.op]) + "(" + show(N.a) + ")"; return "(" + show(N.a) + " " + OPN[N.op] + " " + show(N.b) + ")"; }
struct Expr { int root; bool recur; u64 x0; };
static std::vector<Expr> EXPRS; static const int NMAP = 13;
static const char* MAPN[NMAP] = {"bit0", "bit1", "bit2", "bit3", "bit4", "bit5", "bit6", "bit7", "div3", "rising", "lowbyte", "letter", "printable"};
static std::vector<std::vector<u64>> EXV; static double EXPR_NAME;
static std::vector<u64> expr_values(const Expr& e, size_t cnt) { std::vector<u64> v(cnt); u64 x = e.x0; for (size_t i = 0; i < cnt; i++) v[i] = e.recur ? (x = ev(e.root, i, x)) : ev(e.root, i, 0); return v; }
static void build_formulas(size_t nvals) {
    FIBT[0] = 0; FIBT[1] = 1; for (int k = 2; k < 94; k++) FIBT[k] = FIBT[k - 1] + FIBT[k - 2];
    for (int recur = 0; recur < 2; recur++) {
        std::vector<std::vector<int>> bys(6); std::unordered_set<u64> seen;
        auto sig = [&](int n) { u64 h = 1469598103934665603ull, x = 1; for (u64 i = 0; i < 24; i++) { u64 v = recur ? (x = ev(n, i, x)) : ev(n, i, 0); h = (h ^ v) * 1099511628211ull; } return h; };
        auto add = [&](Node nd, int s) { NODES.push_back(nd); int id = (int)NODES.size() - 1; if (!seen.insert(sig(id)).second) { NODES.pop_back(); return; } bys[s].push_back(id);
            for (u64 x0 : recur ? std::vector<u64>{0, 1, 2, 3} : std::vector<u64>{0}) EXPRS.push_back({id, (bool)recur, x0}); };
        add({I_, 0, -1, -1}, 1); if (recur) add({X_, 0, -1, -1}, 1);
        for (u64 c : {1, 2, 3, 5, 7, 10, 26, 64, 255}) add({C_, c, -1, -1}, 1);
        for (int s = 2; s <= 5; s++) {
            for (int a : std::vector<int>(bys[s - 1])) for (uint8_t op = NEG; op <= FIB; op++) add({op, 0, a, -1}, s);
            for (int s1 = 1; s1 <= s - 2; s1++) for (int a : std::vector<int>(bys[s1])) for (int b : std::vector<int>(bys[s - 1 - s1])) for (uint8_t op = ADD; op <= GCD; op++) {
                bool cm = op == ADD || op == MUL || op == XOR || op == AND || op == OR || op == GCD; if (cm && s1 == s - 1 - s1 && a > b) continue; add({op, 0, a, b}, s); }
        }
    }
    EXV.resize(EXPRS.size());
    std::atomic<size_t> nx{0}; std::vector<std::thread> th;
    for (unsigned t = 0; t < 12; t++) th.emplace_back([&] { for (size_t i; (i = nx++) < EXPRS.size();) EXV[i] = expr_values(EXPRS[i], nvals + 1); });
    for (auto& t : th) t.join();
    EXPR_NAME = std::log2((double)EXPRS.size() * NMAP * 2);
}
static std::vector<Bits> FBITS; static std::vector<std::vector<uint8_t>> FCHARS;
static Bits formula_bits(const std::vector<u64>& v, int mp, size_t n) { Bits S;
    if (mp < 10) for (size_t i = 0; i < n; i++) S.push(mp < 8 ? (int)(v[i] >> mp & 1) : mp == 8 ? v[i] % 3 == 0 : v[i + 1] > v[i]);
    else for (size_t i = 0; i < n / 8; i++) S.push_byte(mp == 10 ? (int)(v[i] & 255) : mp == 11 ? 'a' + (int)(v[i] % 26) : 32 + (int)(v[i] % 95));
    S.pad(); return S; }

// integer sequences written out as text
static std::vector<std::pair<std::string, std::string>> TEXTS; static double TEXT_NAME;
static void build_texts() {
    const size_t M = 4000; std::vector<std::pair<std::string, std::vector<u64>>> Q;
    auto seq = [&](const std::string& nm, auto f) { std::vector<u64> v(M); for (size_t i = 0; i < M; i++) v[i] = f(i, v); Q.push_back({nm, v}); };
    std::vector<uint8_t> sv(100000, 1); sv[0] = sv[1] = 0; for (size_t i = 2; i * i < sv.size(); i++) if (sv[i]) for (size_t j = i * i; j < sv.size(); j += i) sv[j] = 0;
    std::vector<u64> pr; for (size_t i = 2; pr.size() < M; i++) if (sv[i]) pr.push_back(i);
    seq("naturals", [](size_t i, auto&) -> u64 { return i; }); seq("primes", [&](size_t i, auto&) -> u64 { return pr[i]; }); seq("squares", [](size_t i, auto&) -> u64 { return i * i; });
    seq("fibonacci", [](size_t i, auto& v) -> u64 { return i < 2 ? i : v[i - 1] + v[i - 2]; }); seq("powers_of_2", [](size_t i, auto&) -> u64 { return i < 64 ? 1ull << i : 0; });
    seq("triangular", [](size_t i, auto&) -> u64 { return i * (i + 1) / 2; }); seq("years_from_1900", [](size_t i, auto&) -> u64 { return 1900 + i; });
    seq("factorials", [](size_t i, auto& v) -> u64 { return i ? v[i - 1] * i : 1; }); seq("odd", [](size_t i, auto&) -> u64 { return 2 * i + 1; });
    seq("collatz_steps", [](size_t i, auto&) -> u64 { u64 n = i + 1, c = 0; while (n != 1) { n = n & 1 ? 3 * n + 1 : n / 2; c++; } return c; });
    const char* seps[6] = {"", " ", ",", ", ", "\n", "|"};
    for (auto& [nm, v] : Q) for (int s = 0; s < 6; s++) { std::string t; for (size_t i = 0; i < M && t.size() < 30000; i++) { t += std::to_string(v[i]); t += seps[s]; }
        std::string sn = s == 4 ? "\\n" : seps[s]; TEXTS.push_back({"\"" + sn + "\".join(str(v) for v in " + nm + ")", t}); }
    TEXT_NAME = std::log2((double)TEXTS.size() * 30000);
}

// ---------- per-block search ----------
static unsigned NT = std::max(1u, std::thread::hardware_concurrency() - 2);
struct Best { Desc d; std::mutex mu; void offer(const Desc& x) { std::lock_guard<std::mutex> g(mu); if (x.bits < d.bits) d = x; } };
template <class F> static void par(size_t N, F f) { std::atomic<size_t> nx{0}; std::vector<std::thread> th; for (unsigned t = 0; t < NT; t++) th.emplace_back([&] { for (size_t i; (i = nx++) < N;) f(i); }); for (auto& t : th) t.join(); }

static void search_math(const Tgt& T, Best& B) {
    // digits + sequences: every stream, every start < STREAM_P
    par(STREAMS.size(), [&](size_t s) { long bound = (long)T.n / 2 + 1; Desc loc; const Bits& S = STREAMS[s].bits;
        for (size_t t = 0; t < STREAM_P && t + T.n + 64 < S.n; t++) { bool c; long m = eval_bits(T, S, t, bound, c); if (m < 0) continue; bound = m;
            double cost = 4 + STREAM_NAME + bitfix_cost(T.n, m); if (cost < loc.bits) { loc.fam = STREAM; loc.bits = cost; loc.p[0] = (long)s; loc.p[1] = (long)t; loc.comp = c; } }
        B.offer(loc); });
    par(ROOTS.size(), [&](size_t s) { long bound = (long)T.n / 2 + 1; Desc loc; const Bits& S = ROOTS[s].bits;
        for (size_t t = 0; t < 6000 && t + T.n + 64 < S.n; t++) { bool c; long m = eval_bits(T, S, t, bound, c); if (m < 0) continue; bound = m;
            double cost = 4 + ROOT_NAME + bitfix_cost(T.n, m); if (cost < loc.bits) { loc.fam = ROOT; loc.bits = cost; loc.p[0] = (long)s; loc.p[1] = (long)t; loc.comp = c; } }
        B.offer(loc); });
    const size_t SEEDS = 1 << 22; double pn = std::log2(2.0 * SEEDS * 2);
    par(2 * SEEDS / 65536, [&](size_t ch) { long bound = (long)T.n / 2 + 1; Desc loc; Bits S; S.w.assign(T.KW + 2, 0); S.n = 64 * (T.KW + 1); int g = (int)(ch / (SEEDS / 65536));
        for (size_t s = (ch % (SEEDS / 65536)) * 65536; s < (ch % (SEEDS / 65536) + 1) * 65536; s++) {
            if (g == 0) { uint32_t x = (uint32_t)(s + 1); for (size_t k = 0; k < T.KW; k++) { u64 v = 0; for (int h = 0; h < 2; h++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; v = v << 32 | x; } S.w[k] = v; } }
            else { u64 x = s; for (size_t k = 0; k < T.KW; k++) { u64 z = (x += 0x9e3779b97f4a7c15ull); z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull; z = (z ^ (z >> 27)) * 0x94d049bb133111ebull; S.w[k] = z ^ (z >> 31); } }
            bool c; long m = eval_bits(T, S, 0, bound, c); if (m < 0) continue; bound = m;
            double cost = 4 + pn + bitfix_cost(T.n, m); if (cost < loc.bits) { loc.fam = PRNG; loc.bits = cost; loc.p[0] = g; loc.p[1] = (long)s; loc.comp = c; } }
        B.offer(loc); });
    par(EXPRS.size(), [&](size_t e) { Desc loc; long bound = (long)T.n / 2 + 1;
        for (int mp = 0; mp < 11; mp++) { const Bits& S = FBITS[e * 11 + mp]; bool c; long m = eval_bits(T, S, 0, bound, c); if (m < 0) continue; bound = m;
            double cost = 4 + EXPR_NAME + bitfix_cost(T.n, m); if (cost < loc.bits) { loc.fam = FORMULA; loc.bits = cost; loc.p[0] = (long)e; loc.p[1] = mp; loc.comp = c; loc.bytefix = false; } }
        for (int mp = 11; mp < 13; mp++) { long cc = 0; const uint8_t* fc = FCHARS[e].data() + (mp - 11) * T.L; for (size_t i = 0; i < T.L; i++) cc += fc[i] != T.b[i];
            double cost = 4 + EXPR_NAME + bytefix_cost(T.L, cc); if (cost < loc.bits) { loc.fam = FORMULA; loc.bits = cost; loc.p[0] = (long)e; loc.p[1] = mp; loc.comp = false; loc.bytefix = true; } }
        B.offer(loc); });
    par(TEXTS.size(), [&](size_t q) { Desc loc; const std::string& s = TEXTS[q].second;
        for (size_t t = 0; t + T.L <= s.size(); t++) { long cc = 0; size_t i = 0; for (; i < T.L && cc < (long)T.L / 2; i++) cc += (uint8_t)s[t + i] != T.b[i];
            if (i < T.L) continue;
            double cost = 4 + TEXT_NAME + bytefix_cost(T.L, cc); if (cost < loc.bits) { loc.fam = INTSEQ; loc.bits = cost; loc.p[0] = (long)q; loc.p[1] = (long)t; loc.bytefix = true; } }
        B.offer(loc); });
    { Desc loc;   // repeating bit pattern of period p (the pattern itself is part of the description); constant bytes
        for (size_t p = 1; p <= 64; p++) { long m = 0; for (size_t i = p; i < T.n; i++) m += T.bits.get(i) != T.bits.get(i % p);
            double cost = 4 + 6 + (double)p + bitfix_cost(T.n, m);
            if (cost < loc.bits) { u64 pv = 0; for (size_t i = 0; i < p; i++) pv = pv << 1 | (u64)T.bits.get(i); loc.fam = PATTERN; loc.bits = cost; loc.p[0] = (long)p; loc.p[1] = (long)pv; loc.bytefix = false; } }
        B.offer(loc); }
}
// generators that reuse the data already described (decoder has it)
struct History { const std::vector<uint8_t>* d; std::unordered_map<u64, long> last[9]; std::unordered_map<u64, std::vector<uint32_t>> cnt[4]; size_t upto = 0; };
static u64 ctxkey(const uint8_t* d, size_t pos, int k) { u64 h = (u64)k; for (int j = 1; j <= k; j++) h = h * 1315423911ull + d[pos - j] + 1; return h; }
static void hist_add(History& H, size_t pos) {   // byte at pos becomes known
    const auto& d = *H.d;
    for (int k = 1; k <= 8; k++) if (pos >= (size_t)k) H.last[k][ctxkey(d.data(), pos, k)] = (long)pos;
    for (int k = 1; k <= 3; k++) if (pos >= (size_t)k) { auto& v = H.cnt[k][ctxkey(d.data(), pos, k)]; if (v.empty()) v.assign(256, 0); v[d[pos]]++; }
}
static int lzp_pred(const History& H, const uint8_t* d, size_t pos, int k) { if (pos < (size_t)k) return ' '; auto it = H.last[k].find(ctxkey(d, pos, k)); return it == H.last[k].end() ? ' ' : d[it->second]; }
static int ord_pred(const History& H, const uint8_t* d, size_t pos, int k) { if (pos < (size_t)k) return ' '; auto it = H.cnt[k].find(ctxkey(d, pos, k)); if (it == H.cnt[k].end()) return ' ';
    return (int)(std::max_element(it->second.begin(), it->second.end()) - it->second.begin()); }
static void search_data(const Tgt& T, size_t pos, History& H, Best& B) {
    const uint8_t* d = H.d->data();
    { Desc loc; size_t lo = 0; double nb = std::log2((double)pos + 1);   // copy(from=s, len=L), source entirely before the block
        for (size_t s = lo; s + T.L <= pos; s++) { long cc = 0; size_t i = 0; for (; i < T.L && cc < (long)T.L / 2; i++) cc += d[s + i] != T.b[i];
            if (i < T.L) continue;
            double cost = 4 + nb + bytefix_cost(T.L, cc); if (cost < loc.bits) { loc.fam = COPY; loc.bits = cost; loc.p[0] = (long)s; loc.bytefix = true; } }
        B.offer(loc); }
    // predictors run through the block; bytes inside the block become history as the decoder fixes them
    History& Hm = H;
    for (int fam : {LZP, ORDERK}) for (int k = 1; k <= (fam == LZP ? 8 : 3); k++) {
        long cc = 0; std::vector<std::pair<u64, long>> undo_last; std::vector<std::pair<u64, int>> undo_cnt;
        for (size_t i = 0; i < T.L; i++) { size_t p = pos + i; int pr = fam == LZP ? lzp_pred(Hm, d, p, k) : ord_pred(Hm, d, p, k); cc += pr != d[p];
            // temporarily add byte p to history (only the structure used by this predictor)
            if (fam == LZP && p >= (size_t)k) { u64 key = ctxkey(d, p, k); auto it = Hm.last[k].find(key); undo_last.push_back({key, it == Hm.last[k].end() ? -1 : it->second}); Hm.last[k][key] = (long)p; }
            if (fam == ORDERK && p >= (size_t)k) { u64 key = ctxkey(d, p, k); auto& v = Hm.cnt[k][key]; if (v.empty()) v.assign(256, 0); v[d[p]]++; undo_cnt.push_back({key, d[p]}); } }
        for (auto it = undo_last.rbegin(); it != undo_last.rend(); ++it) { if (it->second < 0) Hm.last[k].erase(it->first); else Hm.last[k][it->first] = it->second; }
        for (auto& [key, b] : undo_cnt) Hm.cnt[k][key][b]--;
        Desc loc; loc.fam = fam; loc.bits = 4 + 3 + bytefix_cost(T.L, cc); loc.p[0] = k; loc.bytefix = true; B.offer(loc);
    }
}

// ---------- regenerate a block from its description (the decoder) ----------
static std::vector<uint8_t> generate(const Desc& D, size_t L, size_t pos, History& H, const std::vector<long>& fixpos, const std::vector<uint8_t>& fixval, std::vector<uint8_t>& out_all) {
    size_t n = 8 * L; std::vector<uint8_t> o(L, 0);
    auto from_bits = [&](const Bits& S, size_t t) { Bits c; for (size_t i = 0; i < n; i++) c.push(S.get(t + i) ^ (int)D.comp); c.pad(); return to_bytes(c, 0, L); };
    switch (D.fam) {
    case STREAM: o = from_bits(STREAMS[D.p[0]].bits, (size_t)D.p[1]); break;
    case ROOT: o = from_bits(ROOTS[D.p[0]].bits, (size_t)D.p[1]); break;
    case PRNG: { Bits S; size_t K = (n + 63) / 64; if (D.p[0] == 0) { uint32_t x = (uint32_t)(D.p[1] + 1); for (size_t k = 0; k < K; k++) for (int h = 0; h < 2; h++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; for (int b = 31; b >= 0; b--) S.push(x >> b & 1); } }
        else { u64 x = (u64)D.p[1]; for (size_t k = 0; k < K; k++) { u64 z = (x += 0x9e3779b97f4a7c15ull); z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull; z = (z ^ (z >> 27)) * 0x94d049bb133111ebull; z ^= z >> 31; for (int b = 63; b >= 0; b--) S.push(z >> b & 1); } }
        S.pad(); o = from_bits(S, 0); break; }
    case FORMULA: { auto v = expr_values(EXPRS[D.p[0]], n + 1); if (D.p[1] < 11) o = from_bits(formula_bits(v, (int)D.p[1], n), 0);
        else for (size_t i = 0; i < L; i++) o[i] = (uint8_t)(D.p[1] == 11 ? 'a' + (int)(v[i] % 26) : 32 + (int)(v[i] % 95)); break; }
    case INTSEQ: for (size_t i = 0; i < L; i++) o[i] = (uint8_t)TEXTS[D.p[0]].second[D.p[1] + i]; break;
    case PATTERN: { Bits S; long p = D.p[0]; for (size_t i = 0; i < n; i++) S.push((int)(((u64)D.p[1] >> (p - 1 - (long)(i % p))) & 1)); S.pad(); o = to_bytes(S, 0, L); break; }
    case COPY: for (size_t i = 0; i < L; i++) o[i] = out_all[D.p[0] + i]; break;
    default: break;
    }
    if (D.fam == LZP || D.fam == ORDERK) {   // sequential: predict, apply the fix if there is one, the byte becomes history
        size_t f = 0;
        for (size_t i = 0; i < L; i++) { size_t p = pos + i; int pr = D.fam == LZP ? lzp_pred(H, out_all.data(), p, (int)D.p[0]) : ord_pred(H, out_all.data(), p, (int)D.p[0]);
            uint8_t b = (uint8_t)pr; if (f < fixpos.size() && fixpos[f] == (long)i) b = fixval[f++]; out_all[p] = b; o[i] = b;
            int k = (int)D.p[0]; if (D.fam == LZP && p >= (size_t)k) H.last[k][ctxkey(out_all.data(), p, k)] = (long)p;
            if (D.fam == ORDERK && p >= (size_t)k) { auto& v = H.cnt[k][ctxkey(out_all.data(), p, k)]; if (v.empty()) v.assign(256, 0); v[b]++; } }
        return o;
    }
    return o;
}

int main(int argc, char** argv) {
    if (argc < 7) { std::fprintf(stderr, "usage: blockgen DATA NBYTES BLOCK DIGITDIR math|all OUT.prog\n"); return 1; }
    std::vector<uint8_t> data; read_all(argv[1], data); size_t NBY = std::min<size_t>(std::stoul(argv[2]), data.size()), BL = std::stoul(argv[3]);
    data.resize(NBY); std::string mode = argv[5]; bool use_data = mode == "all";
    double t0 = now();
    std::printf("BLOCK GENERATOR ENCODER: first %zu bytes of %s, blocks of %zu bytes (%zu bits), mode %s\n", NBY, argv[1], BL, 8 * BL, mode.c_str());
    build_streams(argv[4]); build_formulas(8 * BL); build_texts();
    FBITS.resize(EXPRS.size() * 11); FCHARS.resize(EXPRS.size());
    par(EXPRS.size(), [&](size_t e) { for (int mp = 0; mp < 11; mp++) FBITS[e * 11 + mp] = formula_bits(EXV[e], mp, 8 * BL);
        FCHARS[e].resize(2 * BL); for (size_t i = 0; i < BL; i++) { FCHARS[e][i] = (uint8_t)('a' + (int)(EXV[e][i] % 26)); FCHARS[e][BL + i] = (uint8_t)(32 + (int)(EXV[e][i] % 95)); } });
    std::printf("banks: %zu digit/sequence streams x %zu starts (name %.1f bits) | %zu roots/fractions x 6000 starts (name %.1f) | 2 random generators x 4.2M seeds | "
                "%zu formulas/recurrences x %d read-outs (name %.1f) | %zu integer-sequence texts (name %.1f) | repeating patterns | %s  [%.0fs]\n",
                STREAMS.size(), STREAM_P, STREAM_NAME, ROOTS.size(), ROOT_NAME, EXPRS.size(), NMAP, EXPR_NAME, TEXTS.size(), TEXT_NAME,
                use_data ? "copy earlier data, last follower (context 1-8), most frequent follower (context 1-3)" : "no data-reusing generators", now() - t0);
    std::fflush(stdout);
    FILE* prog = std::fopen(argv[6], "w");
    History H; H.d = &data; std::vector<Desc> chosen; std::vector<double> fam_bits(NFAM, 0); std::vector<long> fam_n(NFAM, 0); double total = 0;
    std::vector<std::vector<long>> FP; std::vector<std::vector<uint8_t>> FV;
    for (size_t pos = 0; pos < NBY; pos += BL) {
        size_t L = std::min(BL, NBY - pos); Tgt T = make_tgt(data.data() + pos, L);
        Best B; Desc raw; raw.fam = RAW; raw.bits = 4 + 8.0 * L; B.offer(raw);
        if (L == BL) { search_math(T, B); if (use_data) search_data(T, pos, H, B); }
        Desc D = B.d;
        // compute the corrections explicitly
        std::vector<long> fp; std::vector<uint8_t> fv; std::string fixs;
        if (D.fam != RAW && D.fam != LZP && D.fam != ORDERK) {
            std::vector<uint8_t> scratch = data; History Hc; Hc.d = &scratch; std::vector<long> nofp; std::vector<uint8_t> nofv;
            std::vector<uint8_t> g = generate(D, L, pos, Hc, nofp, nofv, scratch);
            if (D.bytefix) { for (size_t i = 0; i < L; i++) if (g[i] != T.b[i]) { fp.push_back((long)i); fv.push_back(T.b[i]); } }
            else for (size_t i = 0; i < 8 * L; i++) if (((g[i / 8] >> (7 - i % 8)) & 1) != T.bits.get(i)) { fp.push_back((long)i); }
        } else if (D.fam == LZP || D.fam == ORDERK) {
            for (size_t i = 0; i < L; i++) { size_t p = pos + i; int pr = D.fam == LZP ? lzp_pred(H, data.data(), p, (int)D.p[0]) : ord_pred(H, data.data(), p, (int)D.p[0]);
                if (pr != data[p]) { fp.push_back((long)i); fv.push_back(data[p]); }
                int k = (int)D.p[0]; if (D.fam == LZP && p >= (size_t)k) H.last[k][ctxkey(data.data(), p, k)] = (long)p;
                if (D.fam == ORDERK && p >= (size_t)k) { auto& v = H.cnt[k][ctxkey(data.data(), p, k)]; if (v.empty()) v.assign(256, 0); v[data[p]]++; } }
            // undo: history is rebuilt uniformly below
            for (size_t i = 0; i < L; i++) { size_t p = pos + i; int k = (int)D.p[0]; if (D.fam == ORDERK && p >= (size_t)k) H.cnt[k][ctxkey(data.data(), p, k)][data[p]]--; }
        }
        // code line
        char buf[512]; std::string code;
        switch (D.fam) {
        case RAW: { std::string s; for (size_t i = 0; i < L && i < 24; i++) { uint8_t c = data[pos + i]; s += (c >= 32 && c < 127 && c != '"' && c != '\\') ? (char)c : '.'; } code = "raw(\"" + s + (L > 24 ? "...\")" : "\")"); break; }
        case STREAM: std::snprintf(buf, sizeof buf, "%s)[%ld:%ld]%s", STREAMS[D.p[0]].name.c_str(), D.p[1], D.p[1] + (long)(8 * L), D.comp ? " inverted" : ""); code = buf; break;
        case ROOT: std::snprintf(buf, sizeof buf, "binary_digits(%s)[%ld:%ld]%s", ROOTS[D.p[0]].name.c_str(), D.p[1], D.p[1] + (long)(8 * L), D.comp ? " inverted" : ""); code = buf; break;
        case PRNG: std::snprintf(buf, sizeof buf, "%s(seed=%ld).bits(%zu)%s", D.p[0] ? "splitmix64" : "xorshift32", D.p[0] ? D.p[1] : D.p[1] + 1, 8 * L, D.comp ? " inverted" : ""); code = buf; break;
        case FORMULA: { const Expr& e = EXPRS[D.p[0]]; code = std::string(e.recur ? "x(k+1) = " : "f(i) = ") + show(e.root) + (e.recur ? ", x(0)=" + std::to_string(e.x0) : "") + " -> " + MAPN[D.p[1]] + (D.comp ? " inverted" : ""); break; }
        case INTSEQ: std::snprintf(buf, sizeof buf, "%s[%ld:%ld]", TEXTS[D.p[0]].first.c_str(), D.p[1], D.p[1] + (long)L); code = buf; break;
        case PATTERN: { std::string pat; for (long i = 0; i < D.p[0]; i++) pat += (char)('0' + T.bits.get(i)); code = "repeat_bits(\"" + pat + "\")"; break; }
        case COPY: std::snprintf(buf, sizeof buf, "copy(from=%ld, len=%zu)", D.p[0], L); code = buf; break;
        case LZP: std::snprintf(buf, sizeof buf, "predict(next = byte that followed the last %ld bytes the last time they appeared)", D.p[0]); code = buf; break;
        case ORDERK: std::snprintf(buf, sizeof buf, "predict(next = most frequent byte after the last %ld bytes so far)", D.p[0]); code = buf; break;
        }
        if (!fp.empty()) code += D.bytefix || D.fam == LZP || D.fam == ORDERK ? " fix[" + std::to_string(fp.size()) + " bytes]" : " flip[" + std::to_string(fp.size()) + " bits]";
        std::fprintf(prog, "@%zu %s", pos, code.c_str()); for (size_t i = 0; i < fp.size(); i++) std::fprintf(prog, " %ld%s", fp[i], i < fv.size() ? (":" + std::to_string(fv[i])).c_str() : ""); std::fprintf(prog, "\n");
        std::printf("@%-7zu %-24s %7.0f bits (raw %5zu)  %s\n", pos, FAMN[D.fam], D.bits, 8 * L, code.c_str()); std::fflush(stdout);
        chosen.push_back(D); FP.push_back(fp); FV.push_back(fv); fam_bits[D.fam] += D.bits; fam_n[D.fam]++; total += D.bits;
        if (use_data) for (size_t i = 0; i < L; i++) { size_t p = pos + i; for (int k = 1; k <= 8; k++) if (p >= (size_t)k) H.last[k][ctxkey(data.data(), p, k)] = (long)p;
            for (int k = 1; k <= 3; k++) if (p >= (size_t)k) { auto& v = H.cnt[k][ctxkey(data.data(), p, k)]; if (v.empty()) v.assign(256, 0); v[data[p]]++; } }
    }
    std::fclose(prog);
    // decoder: re-run every line in order and compare
    std::vector<uint8_t> out(NBY, 0); History HD; HD.d = &out; size_t bad = 0, bi = 0;
    for (size_t pos = 0; pos < NBY; pos += BL, bi++) {
        size_t L = std::min(BL, NBY - pos); const Desc& D = chosen[bi]; std::vector<uint8_t> blk;
        if (D.fam == RAW) blk.assign(data.begin() + pos, data.begin() + pos + L);
        else blk = generate(D, L, pos, HD, FP[bi], FV[bi], out);
        if (D.fam != LZP && D.fam != ORDERK) { if (D.bytefix) for (size_t f = 0; f < FP[bi].size(); f++) blk[FP[bi][f]] = FV[bi][f]; else for (long q : FP[bi]) blk[q / 8] ^= (uint8_t)(1 << (7 - q % 8)); }
        for (size_t i = 0; i < L; i++) out[pos + i] = blk[i];
        if (use_data && D.fam != LZP && D.fam != ORDERK) {}
        for (size_t i = 0; i < L; i++) { size_t p = pos + i; for (int k = 1; k <= 8; k++) if (p >= (size_t)k) HD.last[k][ctxkey(out.data(), p, k)] = (long)p;
            if (D.fam != ORDERK) for (int k = 1; k <= 3; k++) if (p >= (size_t)k) { auto& v = HD.cnt[k][ctxkey(out.data(), p, k)]; if (v.empty()) v.assign(256, 0); v[out[p]]++; } }
        if (D.fam == ORDERK) for (size_t i = 0; i < L; i++) { size_t p = pos + i; for (int k = 1; k <= 3; k++) if (p >= (size_t)k && k != D.p[0]) { auto& v = HD.cnt[k][ctxkey(out.data(), p, k)]; if (v.empty()) v.assign(256, 0); v[out[p]]++; } }
        if (!std::equal(blk.begin(), blk.end(), data.begin() + pos)) bad++;
    }
    std::printf("\nROUND TRIP: %s (%zu of %zu blocks differ)\n", bad ? "FAILED" : "OK, every line regenerates its block exactly", bad, chosen.size());
    std::printf("\nTOTAL %.0f bits = %.0f bytes for %zu bytes (raw %zu bits; %.3f bits per byte)  [%.0fs]\n", total, total / 8, NBY, 8 * NBY, total / NBY, now() - t0);
    for (int f = 0; f < NFAM; f++) if (fam_n[f]) std::printf("  %-24s %5ld blocks  %9.0f bits\n", FAMN[f], fam_n[f], fam_bits[f]);
    return 0;
}
