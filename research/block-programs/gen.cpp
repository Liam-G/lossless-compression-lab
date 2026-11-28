// Arena stage 2 (lab): program/generator search per block.  usage: gen DATA DIGITDIR [blockbytes=4096] [nblocks=240] [--plant]
// Each block is read as bits (MSB first). For every generator family we look for the candidate that best reproduces
// the block as a LAYER: leftover = block XOR generator. Cost of a candidate = bits to name it (its parameters)
// + bits to send the leftover (number of wrong bits m, then which ones: log2 C(n,m)).
// Baseline = static order-0 cost of the block's bytes (an easy bar; real compressors do better).
// Also reported: the longest exact prefix any candidate reproduces (bits recreated vs bits to name it).
#include <algorithm>
#include <atomic>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <random>
#include <string>
#include <thread>
#include <vector>
#include "../statico/src/io.hpp"
using u64 = uint64_t;

struct Bits { std::vector<u64> w; size_t n = 0;
    void push(int b) { if (n % 64 == 0) w.push_back(0); if (b) w[n / 64] |= 1ull << (63 - n % 64); n++; }
    int get(size_t i) const { return (int)(w[i / 64] >> (63 - i % 64) & 1); }
    u64 ext(size_t p) const { size_t q = p / 64, b = p % 64; if (!b) return w[q]; return (w[q] << b) | (q + 1 < w.size() ? w[q + 1] >> (64 - b) : 0); }
};
static double lg2C(double n, double m) { return (std::lgamma(n + 1) - std::lgamma(m + 1) - std::lgamma(n - m + 1)) / std::log(2.0); }

struct Best { double cost = 1e300; std::string what; long prefix = 0; double prefix_name = 0; std::string prefix_what; };
struct Block { size_t idx; Bits d; double base; size_t n, K; std::vector<int> allow; std::string planted; };

// error schedule: after k words, abort if min(err, comp) > allow[k]  (sound only for candidates that beat the baseline
// with an even spread of errors; a candidate whose first words are much worse than its average can be missed)
static void make_allow(Block& B) {
    double n = (double)B.n; int mmax = 0;
    while (mmax < (int)n / 2 && lg2C(n, mmax + 1) + std::log2(n) + 40 < B.base) mmax++;
    double e = std::max(1e-4, mmax / n); B.allow.resize(B.K);
    for (size_t k = 0; k < B.K; k++) { double bits = 64.0 * (k + 1); B.allow[k] = (int)(bits * e + 4 * std::sqrt(bits * e * (1 - e)) + 4); }
}
// evaluate stream A from bit t against block; returns wrong bits (with complement chosen) or -1 if aborted
static long eval(const Block& B, const Bits& A, size_t t, bool& comp, long& prefix) {
    long err = 0; prefix = -1;
    for (size_t k = 0; k < B.K; k++) {
        u64 x = A.ext(t + 64 * k) ^ B.d.w[k];
        if (prefix < 0 && x) prefix = 64 * k + std::countl_zero(x);
        err += std::popcount(x);
        long bits = 64 * (long)(k + 1), c = bits - err;
        if (std::min(err, c) > B.allow[k]) { if (prefix < 0) prefix = bits; return -1; }
    }
    if (prefix < 0) prefix = (long)B.n;
    comp = err > (long)B.n / 2; return comp ? (long)B.n - err : err;
}
static void consider(Best& b, double name_bits, long m, double n, const std::string& what) {
    double c = name_bits + std::log2(n) + lg2C(n, (double)m);
    if (c < b.cost) { b.cost = c; b.what = what + " wrong bits " + std::to_string(m); }
}
static void consider_prefix(Best& b, long prefix, double name_bits, const std::string& what) {
    if (prefix > b.prefix) { b.prefix = prefix; b.prefix_name = name_bits; b.prefix_what = what; }
}

// ---------- generator streams ----------
struct Stream { std::string name; Bits bits; };
static std::vector<Stream> STREAMS;         // decimated (stream, step, all phases concatenated)
static double STREAM_NAME_BITS = 0;
static std::vector<std::pair<std::string, std::vector<uint8_t>>> load_digits(const std::string& dir) {
    std::vector<std::pair<std::string, std::vector<uint8_t>>> v;
    for (auto nm : {"pi", "e", "sqrt2", "sqrt3", "sqrt5", "phi", "sqrt2+sqrt3"}) { std::vector<uint8_t> d; read_all((dir + "/" + nm + ".dig").c_str(), d); v.push_back({nm, d}); }
    size_t nc = v.size();
    for (size_t i = 0; i < nc; i++) for (size_t j = i + 1; j < nc; j++) {
        std::vector<uint8_t> s(v[i].second.size()); for (size_t k = 0; k < s.size(); k++) s[k] = (uint8_t)((v[i].second[k] + v[j].second[k]) % 10);
        v.push_back({v[i].first + "(+)" + v[j].first, s});
    }
    return v;
}
static std::vector<std::pair<std::string, Bits>> base_streams(const std::string& dir, size_t N) {
    std::vector<std::pair<std::string, Bits>> out;
    const char* tn[8] = {"odd", "div3", ">=5", "bit1", "bit2", "bit3", "zero", "prime"};
    for (auto& [nm, d] : load_digits(dir)) for (int t = 0; t < 8; t++) {
        Bits b; for (size_t k = 0; k < N && k < d.size(); k++) { int x = d[k], r = 0;
            switch (t) { case 0: r = x & 1; break; case 1: r = x % 3 == 0; break; case 2: r = x >= 5; break; case 3: r = x >> 1 & 1; break;
                         case 4: r = x >> 2 & 1; break; case 5: r = x >> 3 & 1; break; case 6: r = x == 0; break; default: r = x == 2 || x == 3 || x == 5 || x == 7; }
            b.push(r); }
        out.push_back({"digits of " + nm + " -> " + tn[t], b});
    }
    auto add = [&](const std::string& nm, auto f) { Bits b; for (size_t k = 0; k < N; k++) b.push(f(k)); out.push_back({nm, b}); };
    add("Thue-Morse", [](size_t k) { return std::popcount(k) & 1; });
    { std::vector<int> f = {0}; std::vector<int> a = {0}, bb = {0, 1}; while (bb.size() < N) { auto c = bb; c.insert(c.end(), a.begin(), a.end()); a = bb; bb = c; }
      add("Fibonacci word", [&](size_t k) { return bb[k]; }); }
    add("paperfolding (dragon curve)", [](size_t k) { size_t m = k + 1; while (!(m & 1)) m >>= 1; return (int)((m >> 1) & 1); });
    add("Rudin-Shapiro", [](size_t k) { int c = 0; for (size_t m = k; m; m >>= 1) if ((m & 3) == 3) c++; return c & 1; });
    add("period-doubling", [](size_t k) { return (int)(std::countr_zero(k + 1) & 1); });
    { std::vector<int> ko = {1, 2, 2}; for (size_t i = 2; ko.size() < N; i++) { int v = ko.size() % 2 ? 2 : 1; v = (ko.back() == 1) ? 2 : 1; for (int r = 0; r < ko[i] && ko.size() < N; r++) ko.push_back(v); }
      add("Kolakoski", [&](size_t k) { return ko[k] - 1; }); }
    add("Baum-Sweet", [](size_t k) { if (!k) return 1; size_t m = k; while (m) { int z = 0; while (m && !(m & 1)) { z++; m >>= 1; } if (z & 1) return 0; while (m & 1) m >>= 1; } return 1; });
    add("Cantor set (no 1 in base 3)", [](size_t k) { for (size_t m = k; m; m /= 3) if (m % 3 == 1) return 0; return 1; });
    { std::vector<int> pas; std::vector<int> row = {1}; while (pas.size() < N) { pas.insert(pas.end(), row.begin(), row.end()); std::vector<int> nx(row.size() + 1, 1); for (size_t i = 1; i < row.size(); i++) nx[i] = row[i - 1] ^ row[i]; row = nx; }
      add("Pascal triangle mod 2 (Sierpinski) rows", [&](size_t k) { return pas[k]; }); }
    { std::vector<uint8_t> sv(N + 1, 1); sv[0] = sv[1] = 0; for (size_t i = 2; i * i <= N; i++) if (sv[i]) for (size_t j = i * i; j <= N; j += i) sv[j] = 0;
      add("primes indicator", [&](size_t k) { return (int)sv[k]; }); }
    add("squares indicator", [](size_t k) { size_t r = (size_t)std::sqrt((double)k); while (r * r > k) r--; while ((r + 1) * (r + 1) <= k) r++; return r * r == k ? 1 : 0; });
    { std::vector<int> ch; for (size_t v = 1; ch.size() < N; v++) { int L = 64 - std::countl_zero(v); for (int i = L - 1; i >= 0; i--) ch.push_back(v >> i & 1); }
      add("Champernowne binary (counter 1,2,3,...)", [&](size_t k) { return ch[k]; }); }
    for (int rule : {30, 45, 73, 110}) {   // centre column of a cellular rule from a single cell
        size_t W = 2 * N / 1 + 3; (void)W; std::vector<uint8_t> a(4 * 4096 + 1, 0), b2(a.size()); size_t c = a.size() / 2; a[c] = 1; std::vector<int> col;
        for (size_t t = 0; t < N; t++) { col.push_back(a[c]); if (t >= 8000) break; for (size_t i = 1; i + 1 < a.size(); i++) b2[i] = (uint8_t)(rule >> (a[i - 1] << 2 | a[i] << 1 | a[i + 1]) & 1); a.swap(b2); }
        add("rule " + std::to_string(rule) + " centre column", [&](size_t k) { return k < col.size() ? col[k] : 0; });
    }
    return out;
}

static void build_streams(const std::string& dir, size_t N) {
    auto base = base_streams(dir, N);
    const int steps[] = {1, 2, 3, 4, 5, 7, 8, 10};
    double total = 0;
    for (auto& [nm, b] : base) for (int s : steps) {
        Stream st; st.name = nm + (s > 1 ? " every " + std::to_string(s) + "th" : "");
        for (int ph = 0; ph < s; ph++) for (size_t k = ph; k < b.n; k += s) st.bits.push(b.get(k));
        total += (double)st.bits.n; STREAMS.push_back(std::move(st));
    }
    STREAM_NAME_BITS = std::log2(total) + 1;   // which (stream, step, start) + complement flag
    std::printf("generator streams: %zu base sequences x %zu steps = %zu streams, %.0f candidate start positions -> naming one costs %.1f bits\n",
                base.size(), std::size(steps), STREAMS.size(), total, STREAM_NAME_BITS);
}

// ---------- families ----------
static void fam_streams(const Block& B, Best& b) {
    for (auto& S : STREAMS) {
        if (S.bits.n < B.n + 64) continue;
        for (size_t t = 0; t + B.n + 64 <= S.bits.n; t++) {
            bool comp; long prefix; long m = eval(B, S.bits, t, comp, prefix);
            if (prefix > b.prefix) consider_prefix(b, prefix, STREAM_NAME_BITS, S.name + " from position " + std::to_string(t));
            if (m >= 0) consider(b, STREAM_NAME_BITS, m, (double)B.n, S.name + " from " + std::to_string(t) + (comp ? " (inverted)" : ""));
        }
    }
}
static Bits eca_rows(int rule, size_t W, std::vector<uint8_t> row, size_t rows) {
    Bits out; std::vector<uint8_t> nx(W);
    for (size_t r = 0; r < rows; r++) {
        for (size_t i = 0; i < W; i++) out.push(row[i]);
        for (size_t i = 0; i < W; i++) nx[i] = (uint8_t)(rule >> (row[(i + W - 1) % W] << 2 | row[i] << 1 | row[(i + 1) % W]) & 1);
        row.swap(nx);
    }
    return out;
}
static void fam_eca_seeded(const Block& B, Best& b) {
    for (size_t W : {8, 16, 32, 64, 128, 256}) for (int rule = 0; rule < 256; rule++) {
        std::vector<uint8_t> row(W); for (size_t i = 0; i < W; i++) row[i] = (uint8_t)B.d.get(i);
        Bits g = eca_rows(rule, W, row, B.n / W + 2); g.push(0);
        for (int k = 0; k < 64; k++) g.push(0);
        bool comp; long prefix; double nb = 8 + 3 + (double)W;
        long m = eval(B, g, 0, comp, prefix);
        consider_prefix(b, prefix, nb, "rule " + std::to_string(rule) + " width " + std::to_string(W) + " seeded with the block's first row");
        if (m >= 0) consider(b, nb, m, (double)B.n, "rule " + std::to_string(rule) + " width " + std::to_string(W) + " seeded" + (comp ? " (inverted)" : ""));
    }
}
static std::vector<std::pair<std::string, Bits>> ECA1;   // single-cell runs, precomputed
static void build_eca1(size_t n) {
    for (size_t W : {8, 16, 32, 64, 128, 256}) for (int rule = 0; rule < 256; rule++) {
        std::vector<uint8_t> row(W, 0); row[W / 2] = 1;
        Bits g = eca_rows(rule, W, row, 1024 + n / W + 2); for (int k = 0; k < 64; k++) g.push(0);
        ECA1.push_back({"rule " + std::to_string(rule) + " width " + std::to_string(W) + " from one cell", g});
    }
}
static void fam_eca_single(const Block& B, Best& b) {
    double nb = 8 + 3 + 10 + 1;
    for (auto& [nm, g] : ECA1) {
        size_t W = (size_t)std::stoul(nm.substr(nm.find("width ") + 6));
        for (size_t t = 0; t < 1024; t++) {
            if (t * W + B.n + 64 > g.n) break;
            bool comp; long prefix; long m = eval(B, g, t * W, comp, prefix);
            consider_prefix(b, prefix, nb, nm + " starting at row " + std::to_string(t));
            if (m >= 0) consider(b, nb, m, (double)B.n, nm + " row " + std::to_string(t) + (comp ? " (inverted)" : ""));
        }
    }
}
static void fam_ant(const Block& B, Best& b) {
    const size_t TMAX = 1 << 22;
    for (size_t W : {16, 32, 64, 128, 256}) for (int mirror = 0; mirror < 2; mirror++) {
        size_t H = B.n / W; std::vector<uint8_t> g(W * H, 0);
        long mis = 0; for (size_t i = 0; i < W * H; i++) mis += B.d.get(i);   // grid all 0 vs data
        long best = std::min(mis, (long)(W * H) - mis); size_t bestT = 0;
        long x = W / 2, y = H / 2; int dir = 0; const int dx[4] = {0, 1, 0, -1}, dy[4] = {-1, 0, 1, 0};
        for (size_t t = 1; t <= TMAX; t++) {
            size_t i = (size_t)y * W + (size_t)x; int c = g[i];
            dir = (dir + ((c == 0) != (bool)mirror ? 1 : 3)) & 3;     // white: turn right (mirror: left)
            g[i] ^= 1; mis += (g[i] != B.d.get(i)) ? 1 : -1;
            x = (x + dx[dir] + (long)W) % (long)W; y = (y + dy[dir] + (long)H) % (long)H;
            long m = std::min(mis, (long)(W * H) - mis); if (m < best) { best = m; bestT = t; }
        }
        consider(b, 22 + 3 + 1 + 1, best, (double)B.n, std::string("Langton's ant ") + (mirror ? "(mirrored) " : "") + "on " + std::to_string(W) + "x" + std::to_string(H) + " after " + std::to_string(bestT) + " steps");
    }
}
static void fam_shapes(const Block& B, Best& b) {
    double n = (double)B.n;
    auto row_const = [&](size_t W, std::string tag) {   // each row of a W-wide grid is one constant bit; same for columns
        size_t H = B.n / W; long er = 0, ec = 0; std::vector<long> col(W, 0);
        for (size_t r = 0; r < H; r++) { long ones = 0; for (size_t c = 0; c < W; c++) { int v = B.d.get(r * W + c); ones += v; col[c] += v; } er += std::min(ones, (long)W - ones); }
        for (size_t c = 0; c < W; c++) ec += std::min(col[c], (long)H - col[c]);
        consider(b, 10 + (double)H, er, n, tag + "grid " + std::to_string(W) + " wide, every row constant");
        consider(b, 10 + (double)W, ec, n, tag + "grid " + std::to_string(W) + " wide, every column constant");
        // pyramid shells: cell value depends only on its distance to the border; and diagonals
        size_t S = std::min(W, H) / 2 + 1; std::vector<long> sh1(S, 0), shn(S, 0), d1(W + H, 0), dn(W + H, 0);
        for (size_t r = 0; r < H; r++) for (size_t c = 0; c < W; c++) { size_t s = std::min(std::min(r, H - 1 - r), std::min(c, W - 1 - c)); s = std::min(s, S - 1);
            int v = B.d.get(r * W + c); sh1[s] += v; shn[s]++; d1[r + c] += v; dn[r + c]++; }
        long es = 0, ed = 0; for (size_t s = 0; s < S; s++) es += std::min(sh1[s], shn[s] - sh1[s]);
        for (size_t k = 0; k < W + H; k++) ed += std::min(d1[k], dn[k] - d1[k]);
        consider(b, 10 + (double)S, es, n, tag + "grid " + std::to_string(W) + " wide, pyramid shells (value by distance to border)");
        consider(b, 10 + (double)(W + H), ed, n, tag + "grid " + std::to_string(W) + " wide, every diagonal constant");
    };
    for (size_t W = 2; W <= 2048 && W < B.n; W *= 2) row_const(W, "");
    for (size_t W : {6, 10, 12, 24, 40, 48, 80, 100, 120, 160, 200}) if (W < B.n) row_const(W, "");
    for (size_t W : {8, 16, 32}) for (size_t H : {8, 16, 32}) {   // 3D box W x H x D: planes constant along depth
        size_t D = B.n / (W * H); if (D < 2) continue; long e = 0;
        for (size_t z = 0; z < D; z++) { long ones = 0; for (size_t i = 0; i < W * H; i++) ones += B.d.get(z * W * H + i); e += std::min(ones, (long)(W * H) - ones); }
        consider(b, 12 + (double)D, e, n, "3D box " + std::to_string(W) + "x" + std::to_string(H) + "x" + std::to_string(D) + ", each depth plane constant (pyramid layers)");
    }
}
static void fam_counters(const Block& B, Best& b) {
    size_t nbytes = B.n / 8; std::vector<uint8_t> by(nbytes); for (size_t i = 0; i < nbytes; i++) by[i] = (uint8_t)(B.d.w[i / 8] >> (56 - 8 * (i % 8)));
    for (int a = 0; a < 256; a++) for (int d = 0; d < 256; d++) {   // byte i = a + d*i
        long m = 0; bool ok = true;
        for (size_t i = 0; i < nbytes; i++) { m += std::popcount((unsigned)(uint8_t)(by[i] ^ (uint8_t)(a + d * i))); if (i == 63 && m > 160) { ok = false; break; } }
        if (ok) consider(b, 16, m, (double)B.n, "byte counter start " + std::to_string(a) + " step " + std::to_string(d));
    }
    for (size_t p = 1; p <= 512; p++) {   // repeat the first p bits
        long m = 0; for (size_t i = p; i < B.n; i++) m += B.d.get(i) != B.d.get(i % p);
        consider(b, 10 + (double)p, m, (double)B.n, "repeat of the first " + std::to_string(p) + " bits");
    }
}
static void fam_lfsr(const Block& B, Best& b) {   // Berlekamp-Massey on the first 4096 bits
    size_t N = std::min<size_t>(B.n, 4096); std::vector<uint8_t> s(N), C(N + 1, 0), Bp(N + 1, 0), T; for (size_t i = 0; i < N; i++) s[i] = (uint8_t)B.d.get(i);
    C[0] = Bp[0] = 1; size_t L = 0; long m = -1;
    for (size_t i = 0; i < N; i++) { int dlt = s[i]; for (size_t j = 1; j <= L; j++) dlt ^= C[j] & s[i - j];
        if (dlt) { T = C; for (size_t j = 0; j + i - m <= N; j++) C[j + i - m] ^= Bp[j]; if (2 * L <= i) { L = i + 1 - L; m = (long)i; Bp = T; } } }
    if (2 * L + 16 < N) consider(b, 2.0 * L + 16 + (double)(B.n - N), 0, (double)B.n, "linear XOR rule (LFSR) of length " + std::to_string(L));
    else if (b.what.empty()) {}
    consider_prefix(b, 0, 0, "");
    char buf[96]; std::snprintf(buf, sizeof buf, "   [LFSR on first %zu bits: shortest linear rule %zu (random: ~%zu)]", N, L, N / 2); (void)buf;
}

static double order0_bytes(const Bits& d, size_t nbytes) {
    std::vector<double> c(256, 0); for (size_t i = 0; i < nbytes; i++) c[(d.w[i / 8] >> (56 - 8 * (i % 8))) & 255]++;
    double h = 0; for (double x : c) if (x) h -= x * std::log2(x / nbytes); return h;
}

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage: gen DATA DIGITDIR [blockbytes] [nblocks] [--plant]\n"); return 1; }
    std::vector<uint8_t> data; if (!read_all(argv[1], data)) return 1;
    size_t BB = argc > 3 ? std::stoul(argv[3]) : 4096, NBK = argc > 4 ? std::stoul(argv[4]) : 240;
    bool plant = argc > 5 && std::string(argv[5]) == "--plant";
    size_t total_blocks = data.size() / BB; NBK = std::min(NBK, total_blocks);
    std::printf("GENERATOR SEARCH on %s: %zu bytes, %zu blocks of %zu bytes (%zu bits); scanning %zu evenly spaced blocks\n",
                argv[1], data.size(), total_blocks, BB, BB * 8, NBK);
    build_streams(argv[2], (1 << 20) - 64); build_eca1(BB * 8);
    std::printf("cellular rules from one cell: %zu precomputed runs (256 rules x 6 widths), 1024 start rows each\n", ECA1.size());
    std::vector<Block> blocks(NBK);
    for (size_t k = 0; k < NBK; k++) {
        Block& B = blocks[k]; B.idx = k * total_blocks / NBK; B.n = BB * 8; B.K = B.n / 64;
        B.d.n = B.n; B.d.w.resize(B.K);
        for (size_t j = 0; j < B.K; j++) { u64 v = 0; for (int q = 0; q < 8; q++) v = v << 8 | data[B.idx * BB + j * 8 + q]; B.d.w[j] = v; }
    }
    if (plant) {   // CONTROLS: known generator output with a little noise; the search must find these
        std::mt19937_64 rng(7); auto noise = [&](Block& B, double p) { for (size_t i = 0; i < B.n; i++) if ((rng() % 100000) < p * 100000) B.d.w[i / 64] ^= 1ull << (63 - i % 64); };
        auto from = [&](Block& B, const Bits& g, size_t t) { for (size_t j = 0; j < B.K; j++) B.d.w[j] = g.ext(t + 64 * j); };
        const Stream* s = nullptr; for (auto& S : STREAMS) if (S.name == "digits of sqrt2+sqrt3 -> >=5 every 7th") s = &S;
        from(blocks[0], s->bits, 123457); noise(blocks[0], 0.02); blocks[0].planted = "PLANTED: digits of sqrt2+sqrt3 -> >=5 every 7th from 123457, 2% noise";
        std::vector<uint8_t> row(64); for (auto& x : row) x = rng() & 1; Bits g = eca_rows(30, 64, row, blocks[1].n / 64 + 2); for (int k = 0; k < 64; k++) g.push(0);
        from(blocks[1], g, 0); blocks[1].planted = "PLANTED: rule 30 width 64 from a random first row";
        { Block& B = blocks[2]; size_t W = 128, H = B.n / W; std::vector<uint8_t> gr(W * H, 0); long x = W / 2, y = H / 2; int dir = 0; const int dx[4] = {0, 1, 0, -1}, dy[4] = {-1, 0, 1, 0};
          for (size_t t = 1; t <= 11000; t++) { size_t i = y * W + x; dir = (dir + (gr[i] == 0 ? 1 : 3)) & 3; gr[i] ^= 1; x = (x + dx[dir] + W) % W; y = (y + dy[dir] + H) % H; }
          for (size_t j = 0; j < B.K; j++) { u64 v = 0; for (int q = 0; q < 64; q++) v = v << 1 | gr[j * 64 + q]; B.d.w[j] = v; }
          B.planted = "PLANTED: Langton's ant on 128x256 after 11000 steps"; }
        { Block& B = blocks[3]; size_t W = 16, H = 16, D = B.n / 256; for (size_t z = 0; z < D; z++) for (size_t i = 0; i < W * H; i++) { size_t p = z * 256 + i; int v = z < D / 3 ? 1 : 0; B.d.w[p / 64] = (B.d.w[p / 64] & ~(1ull << (63 - p % 64))) | ((u64)v << (63 - p % 64)); }
          noise(B, 0.01); B.planted = "PLANTED: a pyramid: 3D box 16x16, top third of the planes all ones, rest zeros, 1% noise"; }
        for (auto& S : STREAMS) if (S.name == "Thue-Morse every 3th") { from(blocks[4], S.bits, 9999); blocks[4].planted = "PLANTED: Thue-Morse every 3rd from 9999"; }
    }
    for (auto& B : blocks) { B.base = order0_bytes(B.d, B.n / 8); make_allow(B); }

    std::mutex mu; std::atomic<size_t> next{0}; size_t done = 0;
    struct Res { std::vector<std::pair<std::string, Best>> fam; };
    std::vector<Res> res(NBK);
    auto worker = [&]() {
        for (size_t k; (k = next++) < NBK;) {
            Block& B = blocks[k]; Res r;
            std::pair<const char*, void (*)(const Block&, Best&)> F[] = {{"digits+sequences", fam_streams}, {"cellular (seeded)", fam_eca_seeded},
                {"cellular (one cell)", fam_eca_single}, {"Langton's ant", fam_ant}, {"shapes", fam_shapes}, {"counters+repeats", fam_counters}, {"linear XOR rule", fam_lfsr}};
            for (auto& [nm, f] : F) { Best b; f(B, b); r.fam.push_back({nm, b}); }
            res[k] = r;
            std::lock_guard<std::mutex> g(mu); done++;
            const Best* win = nullptr; std::string wname;
            for (auto& [nm, b] : r.fam) if (!win || b.cost < win->cost) { win = &b; wname = nm; }
            long pre = 0; double pre_name = 0; std::string pw; for (auto& [nm, b] : r.fam) if (b.prefix > pre) { pre = b.prefix; pre_name = b.prefix_name; pw = b.prefix_what; }
            std::printf("[%3zu/%zu] block %5zu @ byte %10zu%s\n", done, NBK, B.idx, B.idx * BB, B.planted.empty() ? "" : ("   <<< " + B.planted).c_str());
            std::printf("     block alone (order-0 bytes): %8.0f bits | best generator layer: %8.0f bits = %s: %s  => %s %.0f bits\n",
                        B.base, win->cost, wname.c_str(), win->what.c_str(), win->cost < B.base ? "SAVES" : "loses", std::fabs(B.base - win->cost));
            std::printf("     longest exact run any generator recreates: %ld bits (naming it costs %.1f bits): %s\n", pre, pre_name, pw.c_str());
            std::fflush(stdout);
        }
    };
    std::vector<std::thread> th; unsigned nt = std::max(1u, std::thread::hardware_concurrency() - 2);
    std::printf("searching with %u threads...\n", nt); std::fflush(stdout);
    for (unsigned i = 0; i < nt; i++) th.emplace_back(worker);
    for (auto& t : th) t.join();

    std::printf("\nSUMMARY per family (over %zu blocks%s)\n", NBK, plant ? ", first 5 are planted controls" : "");
    std::printf("%-22s %14s %16s %22s\n", "family", "blocks it wins", "bits saved there", "longest exact run");
    const char* names[] = {"digits+sequences", "cellular (seeded)", "cellular (one cell)", "Langton's ant", "shapes", "counters+repeats", "linear XOR rule"};
    for (int f = 0; f < 7; f++) {
        long wins = 0; double saved = 0, pre = 0;
        for (size_t k = 0; k < NBK; k++) { auto& b = res[k].fam[f].second; if (b.cost < blocks[k].base) { wins++; saved += blocks[k].base - b.cost; } pre = std::max(pre, (double)b.prefix); }
        std::printf("%-22s %14ld %16.0f %22.0f\n", names[f], wins, saved, pre);
    }
    long real = 0; for (size_t k = plant ? 5 : 0; k < NBK; k++) for (auto& [nm, b] : res[k].fam) if (b.cost < blocks[k].base) { real++; break; }
    std::printf("real (not planted) blocks where some generator beats the block's own order-0 cost: %ld of %zu\n", real, NBK - (plant ? 5 : 0));
    return 0;
}
