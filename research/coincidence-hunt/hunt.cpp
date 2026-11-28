// Coincidence hunter (lab PoC): look for ANY simple rule whose output matches ONE small target, with corrections.
// usage: hunt TARGET DIGITDIR
// A candidate's cost = bits to name it (log2 of how many candidates its family tried, +3 for the family)
//                    + corrections: number of wrong bits, then which ones (log2 C(n, m))   [bit-level families]
//                      or wrong characters: which positions + 8 bits each                    [character-level families]
// "longest exact run" = how many target bits, from the start, the candidate reproduces with no correction at all.
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
#include <numeric>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>
#include "../statico/src/io.hpp"
using u64 = unsigned long long; using i64 = long long;
static uint32_t bitrev32(uint32_t v) { uint32_t r = 0; for (int k = 0; k < 32; k++) { r = r << 1 | (v & 1); v >>= 1; } return r; }

struct Bits { std::vector<u64> w; size_t n = 0;
    void push(int b) { if (n % 64 == 0) w.push_back(0); if (b) w[n / 64] |= 1ull << (63 - n % 64); n++; }
    void push_byte(int v) { for (int k = 7; k >= 0; k--) push(v >> k & 1); }
    int get(size_t i) const { return (int)(w[i / 64] >> (63 - i % 64) & 1); }
    u64 ext(size_t p) const { size_t q = p / 64, b = p % 64; u64 hi = q < w.size() ? w[q] : 0; if (!b) return hi;
        return (hi << b) | (q + 1 < w.size() ? w[q + 1] >> (64 - b) : 0); }
    void pad() { for (int k = 0; k < 128; k++) push(0); n -= 128; }
};
static double lg2C(double n, double m) { return (std::lgamma(n + 1) - std::lgamma(m + 1) - std::lgamma(n - m + 1)) / std::log(2.0); }
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

// ---------------- target ----------------
static std::vector<uint8_t> TB; static Bits TGT; static size_t NB; static size_t KW; static u64 LASTMASK;
static long width_of(size_t k) { return k + 1 < KW ? 64 : (long)(NB - 64 * (KW - 1)); }

// errors of S (from bit t) against the target, complement allowed; -1 once both exceed bound. prefix = exact run.
static long eval_bits(const Bits& S, size_t t, long bound, bool& comp, long& prefix) {
    long err = 0, cerr = 0; prefix = -1;
    for (size_t k = 0; k < KW; k++) {
        u64 x = S.ext(t + 64 * k) ^ TGT.w[k]; if (k + 1 == KW) x &= LASTMASK;
        if (prefix < 0 && x) prefix = 64 * (long)k + std::countl_zero(x);
        long e = std::popcount(x); err += e; cerr += width_of(k) - e;
        if (err > bound && cerr > bound) { if (prefix < 0) prefix = 64 * (long)(k + 1); return -1; }
    }
    if (prefix < 0) prefix = (long)NB;
    comp = cerr < err; return std::min(err, cerr);
}
static double bit_cost_span(double name, long m, size_t span) { return name + std::log2((double)span + 1) + lg2C((double)span, (double)m); }
static double bit_cost(double name, long m) { return bit_cost_span(name, m, NB); }
static double char_cost(double name, long c) { double n = (double)TB.size(); return name + std::log2(n + 1) + lg2C(n, (double)c) + 8.0 * c; }

struct Hit { double cost = 1e300; long wrong = -1; std::string unit, desc; };
struct Fam { std::string name; double candidates = 0, name_bits = 0, secs = 0; Hit best; long prefix = 0; std::string prefix_desc; };
static std::vector<Hit> GLOBAL; static std::mutex GMU;
struct Local { Hit best; long prefix = 0; std::string prefix_desc; long bound; };
static void offer(Local& L, double cost, long wrong, const char* unit, const std::function<std::string()>& desc) {
    if (cost < L.best.cost) { L.best.cost = cost; L.best.wrong = wrong; L.best.unit = unit; L.best.desc = desc(); }
}
static void offer_prefix(Local& L, long p, const std::function<std::string()>& desc) { if (p > L.prefix) { L.prefix = p; L.prefix_desc = desc(); } }
static void merge(Fam& F, std::vector<Local>& locs) {
    for (auto& L : locs) { if (L.best.cost < F.best.cost) F.best = L.best; if (L.prefix > F.prefix) { F.prefix = L.prefix; F.prefix_desc = L.prefix_desc; } }
}
static unsigned NT = std::max(1u, std::thread::hardware_concurrency() - 2);
template <class F> static void par_for(size_t N, std::vector<Local>& locs, F f) {
    std::atomic<size_t> next{0}; std::vector<std::thread> th; locs.assign(NT, Local{}); for (auto& L : locs) L.bound = (long)NB / 2 + 1;
    for (unsigned t = 0; t < NT; t++) th.emplace_back([&, t]() { for (size_t i; (i = next.fetch_add(1)) < N;) f(i, locs[t]); });
    for (auto& x : th) x.join();
}
// check a bit stream at every start in [t0, t1)
static void scan_stream(const Bits& S, size_t t0, size_t t1, double name, Local& L, const std::function<std::string(size_t)>& what) {
    for (size_t t = t0; t < t1; t++) {
        bool comp; long pre; long m = eval_bits(S, t, L.bound, comp, pre);
        if (pre > L.prefix) offer_prefix(L, pre, [&] { return what(t); });
        if (m >= 0) { if (m < L.bound) L.bound = m; offer(L, bit_cost(name, m), m, "bits", [&] { return what(t) + (comp ? " (inverted)" : ""); }); }
    }
}
static void report(Fam& F) {
    std::printf("  -> %.3g candidates (naming one costs %.1f bits), %.1fs\n", F.candidates, F.name_bits, F.secs);
    std::printf("     best: %.0f bits = %s, %ld wrong %s\n", F.best.cost, F.best.desc.c_str(), F.best.wrong, F.best.unit.c_str());
    std::printf("     longest exact run from the start: %ld bits (%s)\n", F.prefix, F.prefix_desc.c_str());
    std::fflush(stdout); GLOBAL.push_back(F.best); GLOBAL.back().desc = F.name + ": " + F.best.desc;
}
static void start(const char* name, const char* what) { std::printf("\n=== %s: %s\n", name, what); std::fflush(stdout); }

// ---------------- family: digits of constants + famous 0/1 sequences, every step and start ----------------
static void fam_streams(const std::string& dir) {
    start("digits+sequences", "digits of pi, e, sqrt2, sqrt3, sqrt5, phi, sqrt2+sqrt3 and their 21 digit-wise sums, each digit -> bit by 8 rules "
          "(odd, div3, >=5, bit1..3, zero, prime); Thue-Morse, Fibonacci word, dragon folds, Rudin-Shapiro, period-doubling, Baum-Sweet, Cantor, "
          "Sierpinski rows, primes, squares, Champernowne; every 1st..10th element; every start position");
    double t0 = now(); const size_t N = (1 << 20) - 64;
    std::vector<std::pair<std::string, std::vector<uint8_t>>> dg;
    for (auto nm : {"pi", "e", "sqrt2", "sqrt3", "sqrt5", "phi", "sqrt2+sqrt3"}) { std::vector<uint8_t> d; read_all((dir + "/" + nm + ".dig").c_str(), d); dg.push_back({nm, d}); }
    size_t nc = dg.size();
    for (size_t i = 0; i < nc; i++) for (size_t j = i + 1; j < nc; j++) { std::vector<uint8_t> s(N); for (size_t k = 0; k < N; k++) s[k] = (uint8_t)((dg[i].second[k] + dg[j].second[k]) % 10); dg.push_back({dg[i].first + "(+)" + dg[j].first, s}); }
    std::vector<std::pair<std::string, Bits>> base;
    const char* tn[8] = {"odd", "div3", ">=5", "bit1", "bit2", "bit3", "zero", "prime"};
    for (auto& [nm, d] : dg) for (int t = 0; t < 8; t++) { Bits b; for (size_t k = 0; k < N; k++) { int x = d[k], r = 0;
        switch (t) { case 0: r = x & 1; break; case 1: r = x % 3 == 0; break; case 2: r = x >= 5; break; case 3: r = x >> 1 & 1; break;
                     case 4: r = x >> 2 & 1; break; case 5: r = x >> 3 & 1; break; case 6: r = x == 0; break; default: r = x == 2 || x == 3 || x == 5 || x == 7; }
        b.push(r); } base.push_back({"digits of " + nm + " -> " + tn[t], b}); }
    auto add = [&](const std::string& nm, auto f) { Bits b; for (size_t k = 0; k < N; k++) b.push(f(k)); base.push_back({nm, b}); };
    add("Thue-Morse", [](size_t k) { return std::popcount(k) & 1; });
    { std::vector<int> a = {0}, bb = {0, 1}; while (bb.size() < N) { auto c = bb; c.insert(c.end(), a.begin(), a.end()); a = bb; bb = c; } add("Fibonacci word", [&](size_t k) { return bb[k]; }); }
    add("dragon-curve folds", [](size_t k) { size_t m = k + 1; while (!(m & 1)) m >>= 1; return (int)((m >> 1) & 1); });
    add("Rudin-Shapiro", [](size_t k) { int c = 0; for (size_t m = k; m; m >>= 1) if ((m & 3) == 3) c++; return c & 1; });
    add("period-doubling", [](size_t k) { return (int)(std::countr_zero(k + 1) & 1); });
    add("Baum-Sweet", [](size_t k) { if (!k) return 1; size_t m = k; while (m) { int z = 0; while (m && !(m & 1)) { z++; m >>= 1; } if (z & 1) return 0; while (m & 1) m >>= 1; } return 1; });
    add("Cantor set", [](size_t k) { for (size_t m = k; m; m /= 3) if (m % 3 == 1) return 0; return 1; });
    { std::vector<int> pas, row = {1}; while (pas.size() < N) { pas.insert(pas.end(), row.begin(), row.end()); std::vector<int> nx(row.size() + 1, 1); for (size_t i = 1; i < row.size(); i++) nx[i] = row[i - 1] ^ row[i]; row = nx; }
      add("Sierpinski (Pascal mod 2) rows", [&](size_t k) { return pas[k]; }); }
    { std::vector<uint8_t> sv(N + 1, 1); sv[0] = sv[1] = 0; for (size_t i = 2; i * i <= N; i++) if (sv[i]) for (size_t j = i * i; j <= N; j += i) sv[j] = 0; add("primes indicator", [&](size_t k) { return (int)sv[k]; }); }
    { std::vector<int> ch; for (size_t v = 1; ch.size() < N; v++) { int L = 64 - std::countl_zero(v); for (int i = L - 1; i >= 0; i--) ch.push_back(v >> i & 1); } add("Champernowne (1,2,3,... in binary)", [&](size_t k) { return ch[k]; }); }
    std::vector<std::pair<std::string, Bits>> S; const int steps[] = {1, 2, 3, 4, 5, 7, 8, 10}; double total = 0;
    for (auto& [nm, b] : base) for (int s : steps) { Bits d; for (int ph = 0; ph < s; ph++) for (size_t k = ph; k < b.n; k += s) d.push(b.get(k)); d.pad();
        total += (double)(d.n - NB); S.push_back({nm + (s > 1 ? ", every " + std::to_string(s) + "th" : ""), std::move(d)}); }
    Fam F; F.name = "digits+sequences"; F.candidates = total * 2; F.name_bits = std::log2(F.candidates) + 3;
    std::printf("  %zu base sequences x 8 steps = %zu streams of ~1M bits\n", base.size(), S.size()); std::fflush(stdout);
    std::vector<Local> locs;
    par_for(S.size(), locs, [&](size_t i, Local& L) { scan_stream(S[i].second, 0, S[i].second.n - NB, F.name_bits, L, [&](size_t t) { return S[i].first + ", from position " + std::to_string(t); }); });
    merge(F, locs); F.secs = now() - t0; report(F);
}

// ---------------- family: binary digits of sqrt(n), cbrt(n), 1/q (GMP) ----------------
static void fam_roots() {
    start("roots+fractions", "binary digits of sqrt(n) for n<=4000, cube root of n for n<=1000, 1/q for odd q<=4095; 8192 bits each, every start");
    double t0 = now(); const size_t L = 8192; std::vector<std::pair<std::string, Bits>> S;
    auto frac_bits = [&](mpz_t x, const std::string& nm) { mpz_t f; mpz_init(f); mpz_tdiv_r_2exp(f, x, L); std::vector<uint8_t> buf(L / 8 + 8, 0); size_t cnt = 0;
        mpz_export(buf.data(), &cnt, 1, 1, 1, 0, f); Bits b; for (size_t i = 0; i < L / 8 - cnt; i++) b.push_byte(0); for (size_t i = 0; i < cnt; i++) b.push_byte(buf[i]); b.pad(); S.push_back({nm, std::move(b)}); mpz_clear(f); };
    mpz_t x; mpz_init(x);
    for (unsigned n = 2; n <= 4000; n++) { unsigned r = (unsigned)std::sqrt((double)n); if (r * r == n) continue; mpz_set_ui(x, n); mpz_mul_2exp(x, x, 2 * L); mpz_sqrt(x, x); frac_bits(x, "sqrt(" + std::to_string(n) + ")"); }
    for (unsigned n = 2; n <= 1000; n++) { unsigned r = (unsigned)std::cbrt((double)n + 0.5); if (r * r * r == n) continue; mpz_set_ui(x, n); mpz_mul_2exp(x, x, 3 * L); mpz_root(x, x, 3); frac_bits(x, "cbrt(" + std::to_string(n) + ")"); }
    for (unsigned q = 3; q <= 4095; q += 2) { mpz_set_ui(x, 1); mpz_mul_2exp(x, x, L); mpz_tdiv_q_ui(x, x, q); frac_bits(x, "1/" + std::to_string(q)); }
    mpz_clear(x);
    Fam F; F.name = "roots+fractions"; F.candidates = (double)S.size() * (L - NB) * 2; F.name_bits = std::log2(F.candidates) + 3;
    std::vector<Local> locs;
    par_for(S.size(), locs, [&](size_t i, Local& Lc) { scan_stream(S[i].second, 0, L - NB, F.name_bits, Lc, [&](size_t t) { return "binary digits of " + S[i].first + " from bit " + std::to_string(t); }); });
    merge(F, locs); F.secs = now() - t0; report(F);
}

// ---------------- family: random-number generators, every seed ----------------
static void fam_prng() {
    start("random generators", "xorshift32 with every seed (2^32), splitmix64 with seeds 0..2^30, 8 classic LCGs x 2^24 seeds (top byte per step)");
    double t0 = now(); Fam F; F.name = "random generators"; F.candidates = 4294967295.0 + 1073741824.0 + 8.0 * 16777216; F.name_bits = std::log2(F.candidates * 2) + 3;
    std::vector<Local> locs; const size_t CH = 1 << 20;
    auto run = [&](size_t nseeds, auto gen_word, auto desc) {   // gen_word(seed, state&, k) -> 64 bits
        par_for((nseeds + CH - 1) / CH, locs, [&](size_t c, Local& L) {
            Bits S; S.w.resize(KW + 2); S.n = 64 * (KW + 1);
            for (size_t s = c * CH; s < std::min(nseeds, (c + 1) * CH); s++) {
                gen_word(s, S.w.data(), KW);
                bool comp; long pre; long m = eval_bits(S, 0, L.bound, comp, pre);
                if (pre > L.prefix) offer_prefix(L, pre, [&] { return desc(s); });
                if (m >= 0) { if (m < L.bound) L.bound = m; offer(L, bit_cost(F.name_bits, m), m, "bits", [&] { return desc(s) + (comp ? " (inverted)" : ""); }); }
            }
        });
        merge(F, locs);
    };
    run(4294967295ull, [](size_t s, u64* w, size_t K) { uint32_t x = (uint32_t)(s + 1); for (size_t k = 0; k < K; k++) { u64 v = 0; for (int h = 0; h < 2; h++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; v = v << 32 | x; } w[k] = v; } },
        [](size_t s) { return "xorshift32 seed " + std::to_string(s + 1); });
    std::printf("  xorshift32 done (%.0fs)\n", now() - t0); std::fflush(stdout);
    run(1ull << 30, [](size_t s, u64* w, size_t K) { u64 x = s; for (size_t k = 0; k < K; k++) { u64 z = (x += 0x9e3779b97f4a7c15ull); z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull; z = (z ^ (z >> 27)) * 0x94d049bb133111ebull; w[k] = z ^ (z >> 31); } },
        [](size_t s) { return "splitmix64 seed " + std::to_string(s); });
    const uint32_t A[8] = {1664525, 22695477, 1103515245, 214013, 134775813, 69069, 1140671485, 16843009}, C[8] = {1013904223, 1, 12345, 2531011, 1, 1, 12820163, 826366247};
    for (int g = 0; g < 8; g++) {
        uint32_t a = A[g], cc = C[g];
        run(1ull << 24, [a, cc](size_t s, u64* w, size_t K) { uint32_t x = (uint32_t)s; for (size_t k = 0; k < K; k++) { u64 v = 0; for (int h = 0; h < 8; h++) { x = a * x + cc; v = v << 8 | (x >> 24); } w[k] = v; } },
            [a, cc](size_t s) { return "LCG x=" + std::to_string(a) + "*x+" + std::to_string(cc) + " seed " + std::to_string(s) + ", top byte"; });
    }
    F.secs = now() - t0; report(F);
}

// ---------------- formulas written by the machine ----------------
enum Op : uint8_t { I_, X_, C_, NEG, SQR, ISQ, POPC, DSUM, TRI, FIB, ADD, SUB, MUL, DIV, MOD, XOR, AND, OR, SHL, SHR, POW, GCD };
static const char* OPN[] = {"i", "x", "c", "-", "sq", "isqrt", "popcount", "digitsum", "tri", "fib", "+", "-", "*", "/", "mod", "xor", "and", "or", "<<", ">>", "^", "gcd"};
struct Node { uint8_t op; u64 c; int32_t a, b; };
static std::vector<Node> NODES;
static u64 FIBT[94];
static u64 ev(int n, u64 i, u64 x) {
    const Node& N = NODES[n];
    switch (N.op) {
    case I_: return i; case X_: return x; case C_: return N.c;
    case NEG: return 0 - ev(N.a, i, x); case SQR: { u64 v = ev(N.a, i, x); return v * v; }
    case ISQ: { u64 v = ev(N.a, i, x); u64 r = (u64)std::sqrt((double)v); while (r * r > v) r--; while ((r + 1) * (r + 1) <= v && r < 0xFFFFFFFFull) r++; return r; }
    case POPC: return (u64)std::popcount(ev(N.a, i, x)); case DSUM: { u64 v = ev(N.a, i, x), s = 0; while (v) { s += v % 10; v /= 10; } return s; }
    case TRI: { u64 v = ev(N.a, i, x); return v * (v + 1) / 2; } case FIB: return FIBT[ev(N.a, i, x) % 94];
    default: break;
    }
    u64 a = ev(N.a, i, x), b = ev(N.b, i, x);
    switch (N.op) {
    case ADD: return a + b; case SUB: return a - b; case MUL: return a * b; case DIV: return b ? a / b : 0; case MOD: return b ? a % b : 0;
    case XOR: return a ^ b; case AND: return a & b; case OR: return a | b; case SHL: return a << (b & 63); case SHR: return a >> (b & 63);
    case POW: { u64 r = 1, e = b & 63, p = a; while (e) { if (e & 1) r *= p; p *= p; e >>= 1; } return r; }
    case GCD: { while (b) { u64 t = a % b; a = b; b = t; } return a; }
    }
    return 0;
}
static std::string show(int n) {
    const Node& N = NODES[n];
    if (N.op == I_) return "i"; if (N.op == X_) return "x"; if (N.op == C_) return std::to_string(N.c);
    if (N.op < ADD) return std::string(OPN[N.op]) + "(" + show(N.a) + ")";
    return "(" + show(N.a) + " " + OPN[N.op] + " " + show(N.b) + ")";
}
// enumerate distinct expressions by size; recurrence mode adds leaf x and judges by the sequence x(k+1) = f(x(k), k) from x(0)=1
static std::vector<int> enumerate(bool recur, size_t cap, int maxsize) {
    NODES.clear(); std::vector<std::vector<int>> bys(maxsize + 1); std::unordered_set<u64> seen; std::vector<int> all;
    auto sig = [&](int n) { u64 h = 1469598103934665603ull, x = 1;
        for (u64 i = 0; i < 24; i++) { u64 v = recur ? (x = ev(n, i, x)) : ev(n, i, 0); h = (h ^ v) * 1099511628211ull; } return h; };
    auto add = [&](Node nd, int size) { NODES.push_back(nd); int id = (int)NODES.size() - 1; u64 h = sig(id);
        if (!seen.insert(h).second) { NODES.pop_back(); return; } bys[size].push_back(id); all.push_back(id); };
    add({I_, 0, -1, -1}, 1); if (recur) add({X_, 0, -1, -1}, 1);
    for (u64 c : {1, 2, 3, 5, 7, 10, 26, 64, 255}) add({C_, c, -1, -1}, 1);
    for (int s = 2; s <= maxsize && all.size() < cap; s++) {
        for (int a : std::vector<int>(bys[s - 1])) for (uint8_t op = NEG; op <= FIB && all.size() < cap; op++) add({op, 0, a, -1}, s);
        for (int s1 = 1; s1 <= s - 2; s1++) { int s2 = s - 1 - s1;
            for (int a : std::vector<int>(bys[s1])) for (int b : std::vector<int>(bys[s2])) for (uint8_t op = ADD; op <= GCD && all.size() < cap; op++) {
                bool commut = op == ADD || op == MUL || op == XOR || op == AND || op == OR || op == GCD; if (commut && s1 == s2 && a > b) continue;
                add({op, 0, a, b}, s); } }
        std::printf("  size %d: %zu distinct so far\n", s, all.size()); std::fflush(stdout);
    }
    return all;
}
static void fam_formulas(bool recur) {
    const char* nm = recur ? "recurrences" : "formulas";
    start(nm, recur ? "every rule x(k+1) = f(x(k), k) up to size 6 built from x, k, 1,2,3,5,7,10,26,64,255 and - sq isqrt popcount digitsum tri fib + - * / mod xor and or << >> ^ gcd; "
                      "start x(0) in {0,1,2,3}; read out as bit 0..7, divisible by 3, rising, the low byte, letter a+v mod 26, printable char"
                    : "every formula f(i) up to size 6 built from i, 1,2,3,5,7,10,26,64,255 and - sq isqrt popcount digitsum tri fib + - * / mod xor and or << >> ^ gcd; "
                      "read out as bit 0..7, divisible by 3, rising, the low byte, letter a+v mod 26, printable char");
    double t0 = now(); FIBT[0] = 0; FIBT[1] = 1; for (int k = 2; k < 94; k++) FIBT[k] = FIBT[k - 1] + FIBT[k - 2];
    std::vector<int> ex = enumerate(recur, 4000000, 6);
    const int NMAP = 13, X0 = recur ? 4 : 1;
    Fam F; F.name = nm; F.candidates = (double)ex.size() * X0 * NMAP * 2; F.name_bits = std::log2(F.candidates) + 3;
    const char* mapn[NMAP] = {"bit 0", "bit 1", "bit 2", "bit 3", "bit 4", "bit 5", "bit 6", "bit 7", "divisible by 3", "rising", "low byte", "letter a+v mod 26", "printable char 32+v mod 95"};
    std::vector<Local> locs;
    par_for(ex.size() * X0, locs, [&](size_t q, Local& L) {
        int e = ex[q / X0]; u64 x0 = q % X0; std::vector<u64> v(NB + 1); u64 x = x0;
        for (size_t i = 0; i <= NB; i++) v[i] = recur ? (x = ev(e, i, x)) : ev(e, i, 0);
        auto desc = [&](int mp) { return std::string(recur ? "x(k+1) = " : "f(i) = ") + show(e) + (recur ? ", x(0)=" + std::to_string(x0) : "") + " -> " + mapn[mp]; };
        for (int mp = 0; mp < 11; mp++) {
            Bits S; S.w.assign(KW + 2, 0); S.n = 0;
            if (mp < 10) for (size_t i = 0; i < NB; i++) S.push(mp < 8 ? (int)(v[i + (mp == 9)] >> mp & 1) : mp == 8 ? v[i] % 3 == 0 : v[i + 1] > v[i]);
            else for (size_t i = 0; i < NB / 8; i++) S.push_byte((int)(v[i] & 255));
            S.w.resize(KW + 2, 0);
            bool comp; long pre; long m = eval_bits(S, 0, L.bound, comp, pre);
            if (pre > L.prefix) offer_prefix(L, pre, [&] { return desc(mp); });
            if (m >= 0) { if (m < L.bound) L.bound = m; offer(L, bit_cost(F.name_bits, m), m, "bits", [&] { return desc(mp) + (comp ? " (inverted)" : ""); }); }
        }
        for (int mp = 11; mp < 13; mp++) {
            long c = 0; size_t n = TB.size();
            for (size_t i = 0; i < n; i++) { int ch = mp == 11 ? 'a' + (int)(v[i] % 26) : 32 + (int)(v[i] % 95); c += ch != TB[i]; }
            offer(L, char_cost(F.name_bits, c), c, "chars", [&] { return desc(mp); });
        }
    });
    merge(F, locs); F.secs = now() - t0; report(F);
}

// ---------------- integer sequences, as bits and written out as text ----------------
static void fam_intseq() {
    start("integer sequences", "~40 named integer sequences (primes, Fibonacci, Catalan, partitions, Collatz, Recaman, Stern, Golomb, van Eck, totient, ...) "
          "read as bits (bit 0..7, div3, rising) from every start, and written out as text with separators '', ' ', ',', ', ', newline, '|' from every character");
    double t0 = now(); const size_t M = 6000; std::vector<std::pair<std::string, std::vector<u64>>> Q;
    auto seq = [&](const std::string& nm, auto f) { std::vector<u64> v(M); for (size_t i = 0; i < M; i++) v[i] = f(i, v); Q.push_back({nm, v}); };
    std::vector<uint8_t> sv(200000, 1); sv[0] = sv[1] = 0; for (size_t i = 2; i * i < sv.size(); i++) if (sv[i]) for (size_t j = i * i; j < sv.size(); j += i) sv[j] = 0;
    std::vector<u64> primes; for (size_t i = 2; primes.size() < M; i++) if (sv[i]) primes.push_back(i);
    auto phi = [](u64 n) { u64 r = n; for (u64 p = 2; p * p <= n; p++) if (n % p == 0) { while (n % p == 0) n /= p; r -= r / p; } if (n > 1) r -= r / n; return r; };
    seq("natural numbers", [](size_t i, auto&) { return (u64)i; }); seq("odd numbers", [](size_t i, auto&) { return (u64)(2 * i + 1); });
    seq("primes", [&](size_t i, auto&) { return primes[i]; }); seq("squares", [](size_t i, auto&) { return (u64)(i * i); });
    seq("cubes", [](size_t i, auto&) { return (u64)(i * i * i); }); seq("triangular", [](size_t i, auto&) { return (u64)(i * (i + 1) / 2); });
    seq("pentagonal", [](size_t i, auto&) { return (u64)(i * (3 * i - 1) / 2); });
    seq("Fibonacci", [](size_t i, auto& v) { return i < 2 ? (u64)i : v[i - 1] + v[i - 2]; }); seq("Lucas", [](size_t i, auto& v) { return i == 0 ? 2ull : i == 1 ? 1ull : v[i - 1] + v[i - 2]; });
    seq("Pell", [](size_t i, auto& v) { return i < 2 ? (u64)i : 2 * v[i - 1] + v[i - 2]; }); seq("Jacobsthal", [](size_t i, auto& v) { return i < 2 ? (u64)i : v[i - 1] + 2 * v[i - 2]; });
    seq("Padovan", [](size_t i, auto& v) { return i < 3 ? 1ull : v[i - 2] + v[i - 3]; }); seq("Perrin", [](size_t i, auto& v) { return i == 0 ? 3ull : i == 1 ? 0ull : i == 2 ? 2ull : v[i - 2] + v[i - 3]; });
    seq("Tribonacci", [](size_t i, auto& v) { return i < 2 ? 0ull : i == 2 ? 1ull : v[i - 1] + v[i - 2] + v[i - 3]; });
    seq("powers of 2", [](size_t i, auto&) { return i < 64 ? 1ull << i : 0ull; }); seq("powers of 3", [](size_t i, auto& v) { return i ? v[i - 1] * 3 : 1ull; });
    seq("factorials", [](size_t i, auto& v) { return i ? v[i - 1] * i : 1ull; });
    seq("Catalan", [](size_t i, auto& v) { if (!i) return 1ull; unsigned __int128 c = v[i - 1]; return (u64)(c * (4 * i - 2) / (i + 1)); });
    seq("partitions p(n)", [](size_t i, auto& v) { if (!i) return 1ull; long long s = 0; for (long k = 1;; k++) { long g1 = k * (3 * k - 1) / 2, g2 = k * (3 * k + 1) / 2; if (g1 > (long)i) break;
        long sg = (k & 1) ? 1 : -1; s += sg * (long long)v[i - g1]; if (g2 <= (long)i) s += sg * (long long)v[i - g2]; } return (u64)s; });
    seq("Collatz steps", [](size_t i, auto&) { u64 n = i + 1, c = 0; while (n != 1) { n = n & 1 ? 3 * n + 1 : n / 2; c++; } return c; });
    seq("divisor count", [](size_t i, auto&) { u64 n = i + 1, c = 0; for (u64 d = 1; d * d <= n; d++) if (n % d == 0) c += d * d == n ? 1 : 2; return c; });
    seq("divisor sum", [](size_t i, auto&) { u64 n = i + 1, c = 0; for (u64 d = 1; d * d <= n; d++) if (n % d == 0) c += d + (d * d == n ? 0 : n / d); return c; });
    seq("Euler totient", [&](size_t i, auto&) { return phi(i + 1); });
    seq("digit sum", [](size_t i, auto&) { u64 s = 0, n = i; while (n) { s += n % 10; n /= 10; } return s; });
    seq("binary weight", [](size_t i, auto&) { return (u64)std::popcount((u64)i); });
    { std::unordered_set<u64> used; seq("Recaman", [&](size_t i, auto& v) { if (!i) { used.insert(0); return 0ull; } u64 a = v[i - 1]; u64 r = (a > i && !used.count(a - i)) ? a - i : a + i; used.insert(r); return r; }); }
    seq("Stern diatomic", [](size_t i, auto& v) { if (i < 2) return (u64)i; return i & 1 ? v[i / 2] + v[i / 2 + 1] : v[i / 2]; });
    seq("Golomb", [](size_t i, auto& v) { if (i < 2) return (u64)i; return 1 + v[i - v[v[i - 1]]]; });
    { std::vector<long> last(1 << 20, -1); seq("van Eck", [&](size_t i, auto& v) { if (!i) return 0ull; u64 p = v[i - 1]; u64 r = (p < last.size() && last[p] >= 0) ? (i - 1 - last[p]) : 0; if (p < last.size()) last[p] = (long)i - 1; return r; }); }
    seq("Hofstadter Q", [](size_t i, auto& v) { if (i < 3) return 1ull; u64 a = v[i - 1], b = v[i - 2]; return (a <= i && b <= i) ? v[i - a] + v[i - b] : 0ull; });
    seq("Thue-Morse", [](size_t i, auto&) { return (u64)(std::popcount((u64)i) & 1); });
    seq("Sylvester", [](size_t i, auto& v) { return i ? v[i - 1] * v[i - 1] - v[i - 1] + 1 : 2ull; });
    seq("Mersenne 2^n-1", [](size_t i, auto&) { return i < 64 ? (1ull << i) - 1 : ~0ull; });
    seq("happy numbers indicator", [](size_t i, auto&) { u64 n = i + 1; for (int k = 0; k < 50 && n != 1; k++) { u64 s = 0; while (n) { s += (n % 10) * (n % 10); n /= 10; } n = s; } return (u64)(n == 1); });
    seq("prime gaps", [&](size_t i, auto&) { return i + 1 < primes.size() ? primes[i + 1] - primes[i] : 0ull; });
    seq("Moebius+1", [](size_t i, auto&) { u64 n = i + 1; int k = 0; for (u64 p = 2; p * p <= n; p++) if (n % p == 0) { n /= p; if (n % p == 0) return 1ull; k++; } if (n > 1) k++; return (u64)(k & 1 ? 0 : 2); });
    seq("years 1900..", [](size_t i, auto&) { return (u64)(1900 + i); });
    Fam F; F.name = "integer sequences"; std::vector<Local> locs;
    const char* seps[6] = {"", " ", ",", ", ", "\n", "|"}; const size_t T = 3000;
    F.candidates = (double)Q.size() * (10 * (double)T + 6 * 20000.0) * 2; F.name_bits = std::log2(F.candidates) + 3;
    par_for(Q.size(), locs, [&](size_t q, Local& L) {
        auto& [nm, v] = Q[q];
        for (int mp = 0; mp < 10; mp++) { Bits S; for (size_t i = 0; i < T + NB + 1; i++) S.push(mp < 8 ? (int)(v[i] >> mp & 1) : mp == 8 ? v[i] % 3 == 0 : v[i + 1] > v[i]); S.pad();
            const char* mn[10] = {"bit 0", "bit 1", "bit 2", "bit 3", "bit 4", "bit 5", "bit 6", "bit 7", "divisible by 3", "rising"};
            scan_stream(S, 0, T, F.name_bits, L, [&](size_t t) { return nm + " -> " + mn[mp] + ", from term " + std::to_string(t); }); }
        for (int sp = 0; sp < 6; sp++) { std::string txt; for (size_t i = 0; i < M && txt.size() < 20000 + TB.size(); i++) { txt += std::to_string(v[i]); txt += seps[sp]; }
            for (size_t t = 0; t + TB.size() <= txt.size(); t++) { long c = 0; for (size_t k = 0; k < TB.size() && c < L.bound + 300; k++) c += txt[t + k] != (char)TB[k];
                offer(L, char_cost(F.name_bits, c), c, "chars", [&] { return nm + " written out with separator '" + std::string(sp == 4 ? "\\n" : seps[sp]) + "', from character " + std::to_string(t); });
                long pre = 0; while (pre < (long)TB.size() && txt[t + pre] == (char)TB[pre]) pre++; if (8 * pre > L.prefix) offer_prefix(L, 8 * pre, [&] { return nm + " written out from character " + std::to_string(t); }); } }
    });
    merge(F, locs); F.secs = now() - t0; report(F);
}

// ---------------- Fourier for bits (Walsh-Hadamard), XOR-polynomial (ANF), Fourier on characters (DCT) ----------------
static void fam_fourier() {
    start("Fourier", "Walsh-Hadamard (binary Fourier): keep the k largest of 4096 coefficients, rebuild the bits, correct the rest; "
          "ANF (the target as an XOR-polynomial of its 12 index bits); cosine transform of the 300 character values, k largest coefficients");
    double t0 = now(); Fam F; F.name = "Fourier"; F.candidates = 4096 + 300; F.name_bits = 3;
    const size_t P = 4096; std::vector<double> f(P); for (size_t x = 0; x < P; x++) f[x] = (x < NB && TGT.get(x)) ? -1.0 : 1.0;
    std::vector<double> W = f; for (size_t h = 1; h < P; h <<= 1) for (size_t i = 0; i < P; i += 2 * h) for (size_t j = i; j < i + h; j++) { double a = W[j], b = W[j + h]; W[j] = a + b; W[j + h] = a - b; }
    std::vector<size_t> ord(P); for (size_t i = 0; i < P; i++) ord[i] = i; std::sort(ord.begin(), ord.end(), [&](size_t a, size_t b) { return std::fabs(W[a]) > std::fabs(W[b]); });
    std::vector<double> rec(P, 0); Local L; L.bound = (long)NB;
    for (size_t k = 1; k <= P; k++) { size_t u = ord[k - 1]; for (size_t x = 0; x < P; x++) rec[x] += W[u] * ((std::popcount(u & x) & 1) ? -1.0 : 1.0);
        long m = 0; for (size_t x = 0; x < NB; x++) m += (rec[x] < 0) != (bool)TGT.get(x);
        double c = 3 + k * (12.0 + 13.0) + std::log2((double)NB + 1) + lg2C((double)NB, (double)m);
        if (k <= 8 || k % 64 == 0 || c < L.best.cost) offer(L, c, m, "bits", [&] { return "Walsh-Hadamard, " + std::to_string(k) + " largest coefficients"; });
        if (k == 1 || k == 4 || k == 16 || k == 64 || k == 256 || k == 1024) std::printf("  Walsh-Hadamard k=%4zu: %4ld wrong bits, total %.0f bits\n", k, m, c); }
    for (int variant = 0; variant < 2; variant++) {   // ANF via Moebius transform over GF(2)
        std::vector<uint8_t> a(P); for (size_t x = 0; x < P; x++) { size_t y = variant ? (size_t)(bitrev32((uint32_t)x) >> 20) : x; a[x] = (y < NB) ? (uint8_t)TGT.get(y) : 0; }
        for (size_t h = 1; h < P; h <<= 1) for (size_t i = 0; i < P; i++) if (i & h) a[i] ^= a[i ^ h];
        long mono = 0; for (auto v : a) mono += v; double c = 3 + std::log2(4097.0) + lg2C(4096, (double)mono);
        std::printf("  XOR-polynomial (ANF%s): %ld monomials of 4096 (random: ~2048) -> %.0f bits, exact\n", variant ? ", bit-reversed index" : "", mono, c);
        offer(L, c, 0, "bits", [&] { return "XOR-polynomial with " + std::to_string(mono) + " terms" + (variant ? " (bit-reversed index)" : ""); });
    }
    { size_t n = TB.size(); std::vector<double> X(n); for (size_t k = 0; k < n; k++) { double s = 0; for (size_t i = 0; i < n; i++) s += TB[i] * std::cos(M_PI / n * (i + 0.5) * k); X[k] = s * std::sqrt((k ? 2.0 : 1.0) / n); }
      std::vector<size_t> o(n); for (size_t i = 0; i < n; i++) o[i] = i; std::sort(o.begin(), o.end(), [&](size_t a, size_t b) { return std::fabs(X[a]) > std::fabs(X[b]); });
      std::vector<double> r(n, 0);
      for (size_t k = 1; k <= n; k++) { size_t u = o[k - 1]; double q = std::round(X[u]); for (size_t i = 0; i < n; i++) r[i] += q * std::sqrt((u ? 2.0 : 1.0) / n) * std::cos(M_PI / n * (i + 0.5) * u);
          long c = 0; for (size_t i = 0; i < n; i++) c += (long)std::lround(r[i]) != TB[i];
          double cost = 3 + k * (9.0 + 12.0) + std::log2((double)n + 1) + lg2C((double)n, (double)c) + 8.0 * c;
          offer(L, cost, c, "chars", [&] { return "cosine transform of the characters, " + std::to_string(k) + " largest coefficients"; });
          if (k == 1 || k == 10 || k == 50 || k == 150 || k == 300) std::printf("  cosine k=%3zu: %3ld wrong characters, total %.0f bits\n", k, c, cost); } }
    std::vector<Local> locs = {L}; merge(F, locs); F.secs = now() - t0; report(F);
}

// ---------------- cellular rules, Langton's ant, shapes, repeats ----------------
static Bits eca(int rule, size_t W, std::vector<uint8_t> row, size_t rows) {
    Bits out; std::vector<uint8_t> nx(W);
    for (size_t r = 0; r < rows; r++) { for (size_t i = 0; i < W; i++) out.push(row[i]);
        for (size_t i = 0; i < W; i++) nx[i] = (uint8_t)(rule >> (row[(i + W - 1) % W] << 2 | row[i] << 1 | row[(i + 1) % W]) & 1); row.swap(nx); }
    out.pad(); return out;
}
static void fam_geometry() {
    start("geometry", "all 256 cellular rules seeded with the target's first row (10 widths) or one cell (start row 0..1023); Langton's ant on 12 grids "
          "(4M steps); grids of every width: rows/columns/diagonals constant, pyramid shells; repeating patterns of 1..600 bits");
    double t0 = now(); Fam F; F.name = "geometry"; const size_t Ws[10] = {8, 16, 24, 32, 48, 80, 96, 120, 160, 240};
    const size_t width_sum = std::accumulate(std::begin(Ws), std::end(Ws), size_t{0});
    F.candidates = 256 * 10 + 256 * 1024 * width_sum + 24 * 4194305.0 + 600 + 4 * 1200; F.name_bits = std::log2(F.candidates * 2) + 3;
    std::vector<Local> locs;
    par_for(2560, locs, [&](size_t q, Local& L) {
        int rule = (int)(q % 256); size_t W = Ws[q / 256];
        std::vector<uint8_t> row(W); for (size_t i = 0; i < W; i++) row[i] = (uint8_t)TGT.get(i);
        Bits g = eca(rule, W, row, NB / W + 2); bool comp; long pre; long m = eval_bits(g, 0, (long)NB, comp, pre);
        double nb = F.name_bits + (double)W;   // the seed row is part of the description
        offer(L, bit_cost(nb, m), m, "bits", [&] { return "rule " + std::to_string(rule) + ", width " + std::to_string(W) + ", seeded with the target's first row" + (comp ? " (inverted)" : ""); });
        std::vector<uint8_t> one(W, 0); one[W / 2] = 1; Bits h = eca(rule, W, one, 1024 + NB / W + 2);
        scan_stream(h, 0, 1024 * W, F.name_bits, L, [&](size_t t) { return "rule " + std::to_string(rule) + ", width " + std::to_string(W) + ", from one cell, row " + std::to_string(t / W) + (t % W ? "+" + std::to_string(t % W) : ""); });
    });
    merge(F, locs);
    const size_t AW[12] = {10, 12, 15, 16, 20, 24, 30, 40, 48, 60, 80, 120};
    par_for(24, locs, [&](size_t q, Local& L) {
        size_t W = AW[q / 2], H = NB / W; int mirror = (int)(q % 2); std::vector<uint8_t> g(W * H, 0);
        long mis = 0; for (size_t i = 0; i < W * H; i++) mis += TGT.get(i);
        long best = std::min(mis, (long)(W * H) - mis); size_t bt = 0; long x = W / 2, y = H / 2; int dir = 0; const int dx[4] = {0, 1, 0, -1}, dy[4] = {-1, 0, 1, 0};
        for (size_t t = 1; t <= 4194304; t++) { size_t i = (size_t)y * W + (size_t)x; dir = (dir + ((g[i] == 0) != (bool)mirror ? 1 : 3)) & 3; g[i] ^= 1; mis += (g[i] != TGT.get(i)) ? 1 : -1;
            x = (x + dx[dir] + (long)W) % (long)W; y = (y + dy[dir] + (long)H) % (long)H; long m = std::min(mis, (long)(W * H) - mis); if (m < best) { best = m; bt = t; } }
        const size_t covered = W * H;
        offer(L, bit_cost_span(F.name_bits + (NB - covered), best, covered), best, "bits", [&] { return std::string("Langton's ant") + (mirror ? " (mirrored)" : "") + " on " + std::to_string(W) + "x" + std::to_string(H) + " after " + std::to_string(bt) + " steps, plus literal tail"; });
    });
    merge(F, locs);
    Local L; L.bound = (long)NB;
    for (size_t W = 2; W <= 1200; W++) { size_t H = NB / W; if (H < 2) break; long er = 0, ec = 0, ed = 0, es = 0; std::vector<long> col(W, 0), d1(W + H, 0), dn(W + H, 0), s1(W, 0), sn(W, 0);
        for (size_t r = 0; r < H; r++) { long ones = 0; for (size_t c = 0; c < W; c++) { int v = TGT.get(r * W + c); ones += v; col[c] += v; d1[r + c] += v; dn[r + c]++;
            size_t s = std::min(std::min(r, H - 1 - r), std::min(c, W - 1 - c)); s1[s] += v; sn[s]++; } er += std::min(ones, (long)W - ones); }
        for (size_t c = 0; c < W; c++) ec += std::min(col[c], (long)H - col[c]);
        for (size_t k = 0; k < W + H; k++) ed += std::min(d1[k], dn[k] - d1[k]); for (size_t k = 0; k < W; k++) es += std::min(s1[k], sn[k] - s1[k]);
        const size_t covered = W * H;
        const double name_with_tail = F.name_bits + (NB - covered);
        offer(L, bit_cost_span(name_with_tail + H, er, covered), er, "bits", [&] { return "grid " + std::to_string(W) + " wide, every row constant, plus literal tail"; });
        offer(L, bit_cost_span(name_with_tail + W, ec, covered), ec, "bits", [&] { return "grid " + std::to_string(W) + " wide, every column constant, plus literal tail"; });
        offer(L, bit_cost_span(name_with_tail + W + H, ed, covered), ed, "bits", [&] { return "grid " + std::to_string(W) + " wide, every diagonal constant, plus literal tail"; });
        offer(L, bit_cost_span(name_with_tail + (std::min(W, H) + 1) / 2, es, covered), es, "bits", [&] { return "grid " + std::to_string(W) + " wide, pyramid shells, plus literal tail"; }); }
    for (size_t p = 1; p <= 600; p++) { long m = 0; for (size_t i = p; i < NB; i++) m += TGT.get(i) != TGT.get(i % p);
        offer(L, bit_cost(F.name_bits + (double)p, m), m, "bits", [&] { return "the first " + std::to_string(p) + " bits repeated"; }); }
    locs = {L}; merge(F, locs); F.secs = now() - t0; report(F);
}

int main(int argc, char** argv) {
    if (argc < 3 || !read_all(argv[1], TB)) { std::fprintf(stderr, "usage: hunt TARGET DIGITDIR [families]\n"); return 1; }
    std::string fams = argc > 3 ? argv[3] : "streams,roots,prng,formulas,recur,intseq,fourier,geometry";
    for (uint8_t b : TB) TGT.push_byte(b); NB = TGT.n; KW = (NB + 63) / 64; LASTMASK = NB % 64 ? ~0ull << (64 - NB % 64) : ~0ull; TGT.pad();
    double h0 = 0; { std::vector<double> c(256, 0); for (uint8_t b : TB) c[b]++; for (double x : c) if (x) h0 -= x * std::log2(x / TB.size()); }
    std::printf("COINCIDENCE HUNT  target %s: %zu characters = %zu bits; %u threads\n", argv[1], TB.size(), NB, NT);
    std::printf("bars: raw %zu bits | its own letter statistics (order-0, table not counted) %.0f bits\n", NB, h0);
    double t0 = now();
    if (fams.find("streams") != std::string::npos) fam_streams(argv[2]);
    if (fams.find("roots") != std::string::npos) fam_roots();
    if (fams.find("prng") != std::string::npos) fam_prng();
    if (fams.find("formulas") != std::string::npos) fam_formulas(false);
    if (fams.find("recur") != std::string::npos) fam_formulas(true);
    if (fams.find("intseq") != std::string::npos) fam_intseq();
    if (fams.find("fourier") != std::string::npos) fam_fourier();
    if (fams.find("geometry") != std::string::npos) fam_geometry();
    std::sort(GLOBAL.begin(), GLOBAL.end(), [](const Hit& a, const Hit& b) { return a.cost < b.cost; });
    std::printf("\nRANKING (best candidate of each family; raw = %zu bits, letter statistics = %.0f bits), total %.0fs\n", NB, h0, now() - t0);
    for (size_t i = 0; i < GLOBAL.size(); i++) std::printf("  %zu. %7.0f bits  %s%s  [%ld wrong %s]\n", i + 1, GLOBAL[i].cost, GLOBAL[i].cost < NB ? "BEATS RAW  " : "",
                                                          GLOBAL[i].desc.c_str(), GLOBAL[i].wrong, GLOBAL[i].unit.c_str());
    return 0;
}
