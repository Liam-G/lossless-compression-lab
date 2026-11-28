// BWT lab: reversible transform, then a ladder of second stages, each priced exactly as an adaptive binary arithmetic
// coder would pay (sum of -log2 p over every coded bit). Same models with and without BWT (ablation).
// usage: bwtlab FILE [stages]
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>
#include "../statico/src/io.hpp"
#include "../statico/third_party/libsais/libsais.h"
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

// ---------- bit-level model pieces ----------
static float RT[1024]; static void init_rt() { for (int i = 0; i < 1024; i++) RT[i] = 1.0f / (i + 1.5f); }
struct Ctr { float p = 0.5f; uint16_t n = 0; };
template <class C> static inline void upd(C& c, int bit, int limit) { c.p += ((float)bit - c.p) * RT[c.n]; if (c.n < limit) c.n++; }
static inline float clampp(float p) { return std::min(std::max(p, 1.0f / 4096), 1.0f - 1.0f / 4096); }
static inline float st(float p) { p = clampp(p); return std::log(p / (1 - p)); }
static inline float sq(float x) { return 1.0f / (1.0f + std::exp(-x)); }
static inline double cost(float p, int bit) { p = clampp(p); return -std::log2(bit ? p : 1 - p); }
struct Mixer { int n, sets; std::vector<float> w; float lr; std::vector<float> in; int sel = 0; float pr = 0.5f;
    Mixer(int n_, int sets_, float lr_) : n(n_), sets(sets_), w((size_t)n_ * sets_, 0.3f), lr(lr_), in(n_) {}
    float mix(int s) { sel = s; float d = 0; for (int i = 0; i < n; i++) d += w[(size_t)s * n + i] * in[i]; pr = clampp(sq(d)); return pr; }
    void update(int bit) { float e = ((float)bit - pr) * lr; for (int i = 0; i < n; i++) w[(size_t)sel * n + i] += e * in[i]; } };
struct APM { std::vector<float> t; int idx = 0; float wlo = 0; APM(int ctx) : t((size_t)ctx * 33) { for (int c = 0; c < ctx; c++) for (int j = 0; j < 33; j++) t[(size_t)c * 33 + j] = sq((j - 16) / 2.0f); }
    float pp(float p, int c) { float s = std::min(std::max(st(p), -7.99f), 7.99f) * 2 + 16; int j = (int)s; wlo = s - j; idx = c * 33 + j; return t[idx] * (1 - wlo) + t[idx + 1] * wlo; }
    void update(int bit, float r = 0.02f) { t[idx] += ((float)bit - t[idx]) * r * (1 - wlo); t[idx + 1] += ((float)bit - t[idx + 1]) * r * wlo; } };

// ---------- simple context models: byte coded as 8 binary decisions, counters indexed [ctx][node] ----------
static double order_k(const std::vector<uint8_t>& y, int k, int limit) {
    size_t nctx = k == 0 ? 1 : k == 1 ? 256 : 65536; std::vector<Ctr> T(nctx * 256); double bits = 0;
    for (size_t i = 0; i < y.size(); i++) {
        size_t c = k == 0 ? 0 : k == 1 ? (i ? y[i - 1] : 0) : ((i ? y[i - 1] : 0) << 8 | (i > 1 ? y[i - 2] : 0));
        int node = 1; for (int b = 7; b >= 0; b--) { int bit = y[i] >> b & 1; Ctr& t = T[c * 256 + node]; bits += cost(t.p, bit); upd(t, bit, limit); node = node * 2 + bit; }
    }
    return bits;
}
// mixing model: order-0, order-1, order-2 (two speeds each) + run model, mixer selected by run length and bit position, APM on order-1
static double cm(const std::vector<uint8_t>& y, bool verbose_name = false) {
    (void)verbose_name; std::vector<Ctr> O0(256), O1(65536), O1f(65536), O2((size_t)65536 * 256), O2f((size_t)65536 * 256), RUN((size_t)16 * 256 * 256);
    Mixer M(8, 16 * 8, 0.02f); APM A1(256 * 256), A2(65536); double bits = 0; size_t run = 0;
    for (size_t i = 0; i < y.size(); i++) {
        int c1 = i ? y[i - 1] : 0, c2 = i > 1 ? y[i - 2] : 0; if (i && i > 1 && y[i - 1] == y[i - 2]) run++; else run = 0;
        int rb = run == 0 ? 0 : std::min(15, 1 + (int)std::log2((double)run));
        size_t o2 = ((size_t)c1 << 8 | c2) * 256;
        int node = 1;
        for (int b = 7; b >= 0; b--) {
            int bit = y[i] >> b & 1;
            Ctr& a = O0[node]; Ctr& p1 = O1[c1 * 256 + node]; Ctr& p1f = O1f[c1 * 256 + node]; Ctr& p2 = O2[o2 + node]; Ctr& p2f = O2f[o2 + node]; Ctr& r = RUN[((size_t)rb * 256 + c1) * 256 + node];
            // expected bit if the byte repeats c1
            int expect = (c1 + 256) >> b & 1; int same_prefix = ((c1 + 256) >> (b + 1)) == node;
            M.in[0] = st(a.p); M.in[1] = st(p1.p); M.in[2] = st(p1f.p); M.in[3] = st(p2.p); M.in[4] = st(p2f.p); M.in[5] = st(r.p);
            M.in[6] = same_prefix ? (expect ? 1.0f : -1.0f) * std::min(8.0f, 0.5f + rb) : 0.0f; M.in[7] = 0.3f;
            float pm = M.mix(rb * 8 + (7 - b));
            float pa = A1.pp(pm, c1 * 256 + node), pb = A2.pp(pm, (int)(((size_t)c1 << 8 | c2) & 0xFFFF));
            float pf = (pm + pa + 2 * pb) / 4;
            bits += cost(pf, bit);
            M.update(bit); A1.update(bit); A2.update(bit);
            upd(a, bit, 1023); upd(p1, bit, 1023); upd(p1f, bit, 6); upd(p2, bit, 1023); upd(p2f, bit, 6); upd(r, bit, 255);
            node = node * 2 + bit;
        }
    }
    return bits;
}

// ---------- cm2: hashed context mixing; contexts may include the RIGHT context (first column F of the BWT matrix) ----------
static float STT[4096]; static void init_st() { for (int i = 0; i < 4096; i++) STT[i] = st((i + 0.5f) / 4096); }
static inline float stq(float p) { int q = (int)(p * 4096); q = std::min(std::max(q, 0), 4095); return STT[q]; }
struct HCtr { float p = 0.5f; uint16_t n = 0; uint16_t chk = 0; };
static double cm2(const std::vector<uint8_t>& y, const std::vector<uint8_t>* F1, const std::vector<uint8_t>* F2, const std::vector<uint8_t>* F3, int variant) {
    const int NC = 9; const size_t TB = 22; const size_t MASK = (1u << TB) - 1;
    std::vector<std::vector<HCtr>> T(NC, std::vector<HCtr>(1u << TB));
    int NI = 2 * NC + 2; Mixer M1(NI, 16 * 8, 0.015f), M2(NI, 256 * 8, 0.015f); APM A1(256 * 256), A2(65536), A3(65536);
    double bits = 0; size_t run = 0; std::vector<uint64_t> h(NC);
    for (size_t i = 0; i < y.size(); i++) {
        int c1 = i ? y[i - 1] : 0, c2 = i > 1 ? y[i - 2] : 0, c3 = i > 2 ? y[i - 3] : 0; if (i > 1 && y[i - 1] == y[i - 2]) run++; else run = 0;
        int rb = run == 0 ? 0 : std::min(15, 1 + (int)std::log2((double)run));
        int f1 = F1 ? (*F1)[i] : 0, f2 = F2 ? (*F2)[i] : 0, f3 = F3 ? (*F3)[i] : 0;
        auto H = [](uint64_t a) { a *= 0x9E3779B97F4A7C15ull; return a ^ (a >> 29); };
        h[0] = H(1); h[1] = H(2ull << 32 | c1); h[2] = H(3ull << 32 | c1 << 8 | c2); h[3] = H(4ull << 32 | c1 << 16 | c2 << 8 | c3);
        h[4] = H(5ull << 32 | f1); h[5] = H(6ull << 32 | f1 << 8 | c1); h[6] = H(7ull << 32 | f1 << 8 | f2); h[7] = H(8ull << 40 | (uint64_t)f1 << 16 | f2 << 8 | c1);
        h[8] = H(9ull << 40 | (uint64_t)f1 << 16 | f2 << 8 | f3);
        int node = 1;
        for (int b = 7; b >= 0; b--) {
            int bit = y[i] >> b & 1; HCtr* c[NC];
            for (int j = 0; j < NC; j++) { size_t ix = (h[j] + (uint64_t)node * 0x2545F4914F6CDD1Dull) >> 7 & MASK; c[j] = &T[j][ix];
                uint16_t chk = (uint16_t)((h[j] ^ node) >> 48); if (c[j]->chk != chk) { c[j]->chk = chk; c[j]->p = 0.5f; c[j]->n = 0; } }
            int k = 0;
            for (int j = 0; j < NC; j++) { bool use = (F1 || j < 4) && (F2 || (j != 6 && j != 7 && j != 8)) && (F3 || j != 8);
                float s = use ? stq(c[j]->p) : 0.0f; M1.in[k] = s; M2.in[k] = s; k++;
                float conf = use ? s * std::min(1.0f, c[j]->n / 8.0f) : 0.0f; M1.in[k] = conf; M2.in[k] = conf; k++; }
            int expect = (c1 + 256) >> b & 1; int same = ((c1 + 256) >> (b + 1)) == node;
            float e = same ? (expect ? 1.0f : -1.0f) * std::min(8.0f, 0.5f + rb) : 0.0f; M1.in[k] = e; M2.in[k] = e; k++; M1.in[k] = 0.3f; M2.in[k] = 0.3f;
            float p1 = M1.mix(rb * 8 + (7 - b)), p2 = M2.mix((F1 ? f1 : c1) * 8 + (7 - b));
            float pm = sq((stq(p1) + stq(p2)) / 2);
            float pa = A1.pp(pm, c1 * 256 + node), pb = A2.pp(pm, (int)((c1 << 8 | c2) & 0xFFFF)), pc = A3.pp(pm, F1 ? (f1 << 8 | (variant ? f2 : c1)) : node);
            float pf = (pm + pa + pb + pc) / 4;
            bits += cost(pf, bit);
            M1.update(bit); M2.update(bit); A1.update(bit); A2.update(bit); A3.update(bit);
            for (int j = 0; j < NC; j++) upd(*c[j], bit, j < 4 ? 255 : 1023);
            node = node * 2 + bit;
        }
    }
    return bits;
}
static double gamma_bits(uint64_t v) { return 2 * std::floor(std::log2((double)v + 1)) + 1; }
// move-to-front ranks + zero-run structure (the "run generator + corrections" view)
static std::vector<uint8_t> mtf(const std::vector<uint8_t>& y) { uint8_t t[256]; for (int i = 0; i < 256; i++) t[i] = (uint8_t)i; std::vector<uint8_t> o(y.size());
    for (size_t i = 0; i < y.size(); i++) { int r = 0; while (t[r] != y[i]) r++; o[i] = (uint8_t)r; std::memmove(t + 1, t, r); t[0] = y[i]; } return o; }
static double mtf_runs(const std::vector<uint8_t>& m) {   // rank==0 flag with context (zero-run length bucket, previous rank bucket); else rank tree with context
    std::vector<Ctr> Z(16 * 8), R(8 * 256); double bits = 0; size_t zr = 0; int prevb = 0;
    auto bucket = [](int r) { return r == 0 ? 0 : r == 1 ? 1 : r == 2 ? 2 : r < 5 ? 3 : r < 9 ? 4 : r < 17 ? 5 : r < 65 ? 6 : 7; };
    for (size_t i = 0; i < m.size(); i++) {
        int zb = zr == 0 ? 0 : std::min(15, 1 + (int)std::log2((double)zr));
        Ctr& z = Z[zb * 8 + prevb]; int isz = m[i] == 0; bits += cost(z.p, isz); upd(z, isz, 255);
        if (!isz) { int v = m[i] - 1, node = 1; for (int b = 7; b >= 0; b--) { int bit = v >> b & 1; Ctr& t = R[prevb * 256 + node]; bits += cost(t.p, bit); upd(t, bit, 255); node = node * 2 + bit; } zr = 0; }
        else zr++;
        prevb = bucket(m[i]);
    }
    return bits;
}

int main(int argc, char** argv) {
    init_rt();
    std::vector<uint8_t> x; if (argc < 2 || !read_all(argv[1], x)) { std::fprintf(stderr, "usage: bwtlab FILE\n"); return 1; }
    size_t n = x.size(); double t0 = now();
    std::printf("BWT LAB on %s (%zu bytes). Sizes are exact adaptive-coding costs (what an arithmetic coder writes, +-0.01%%).\n", argv[1], n);
    std::vector<uint8_t> y(n); std::vector<int32_t> A(n + 1);
    int32_t pidx = libsais_bwt(x.data(), y.data(), A.data(), (int32_t)n, 0, nullptr);
    { std::vector<uint8_t> back(n); libsais_unbwt(y.data(), back.data(), A.data(), (int32_t)n, nullptr, pidx);
      std::printf("BWT: primary index %d, inverse BWT gives the input back: %s  [%.1fs]\n", pidx, back == x ? "YES (byte-exact)" : "NO", now() - t0); }
    // show what BWT does to text
    { std::string s; for (size_t i = n / 2; i < n / 2 + 120; i++) s += (y[i] >= 32 && y[i] < 127) ? (char)y[i] : '.';
      size_t runs = 1; for (size_t i = 1; i < n; i++) runs += y[i] != y[i - 1];
      size_t runs0 = 1; for (size_t i = 1; i < n; i++) runs0 += x[i] != x[i - 1];
      std::printf("what BWT output looks like (middle of the file): %s\n", s.c_str());
      std::printf("runs of identical bytes: original %zu (avg length %.2f), after BWT %zu (avg length %.2f)\n", runs0, (double)n / runs0, runs, (double)n / runs); }
    std::vector<uint8_t> m = mtf(y);
    { size_t z = 0; for (auto v : m) z += v == 0; std::printf("after BWT + move-to-front: %.1f%% of all bytes are 0\n", 100.0 * z / n); }
    std::fflush(stdout);
    std::string want = argc > 2 ? argv[2] : "all";
    double t = now();
    auto row = [&](const char* name, double bits, double tt_unused) { (void)tt_unused; double tt = now() - t; std::printf("  %-62s %12.0f bytes  %.3f bits/byte  [%.1fs]\n", name, bits / 8 + 8, bits / n, tt); std::fflush(stdout); };
    if (want == "all") {
    std::printf("\nSECOND STAGE (same models, without and with BWT):\n");
    t = now(); row("raw text   -> letter counts (order-0)", order_k(x, 0, 1023), now() - t);
    t = now(); row("BWT output -> letter counts (order-0)", order_k(y, 0, 1023), now() - t);
    t = now(); row("raw text   -> next byte given previous byte (order-1)", order_k(x, 1, 1023), now() - t);
    t = now(); row("BWT output -> next byte given previous byte (order-1)", order_k(y, 1, 255), now() - t);
    t = now(); row("raw text   -> next byte given previous 2 bytes (order-2)", order_k(x, 2, 1023), now() - t);
    t = now(); row("BWT output -> next byte given previous 2 bytes (order-2)", order_k(y, 2, 255), now() - t);
    t = now(); row("BWT -> move-to-front -> rank counts", order_k(m, 0, 1023), now() - t);
    t = now(); row("BWT -> move-to-front -> runs of 0 + ranks (run generator + fixes)", mtf_runs(m), now() - t);
    t = now(); row("raw text   -> mix of order-0/1/2 + run model + 2 APMs", cm(x), now() - t);
    t = now(); row("BWT output -> mix of order-0/1/2 + run model + 2 APMs", cm(y), now() - t);
    }
    init_st();
    if (want == "all" || want.find("cm2") != std::string::npos) {
        std::vector<int32_t> SA(n); libsais(x.data(), SA.data(), (int32_t)n, 0, nullptr);
        // y2 = BWT from the suffix array (rotation-free variant: the char before each sorted suffix; first suffix gets 0)
        std::vector<uint8_t> y2(n), f1(n), f2(n), f3(n);
        for (size_t i = 0; i < n; i++) { size_t p = (size_t)SA[i]; y2[i] = p ? x[p - 1] : 0; f1[i] = x[p]; f2[i] = p + 1 < n ? x[p + 1] : 0; f3[i] = p + 2 < n ? x[p + 2] : 0; }
        // header costs: counts of single letters / letter pairs / triples (what the decoder needs to know F1 / F2 / F3 at every position)
        std::vector<uint64_t> c1c(256, 0); std::vector<uint64_t> c2c(65536, 0); for (size_t i = 0; i < n; i++) { c1c[x[i]]++; if (i + 1 < n) c2c[x[i] << 8 | x[i + 1]]++; }
        double h1 = 0, h2 = 0; for (auto v : c1c) h1 += gamma_bits(v) ; long last = -1; size_t nz = 0;
        for (size_t k = 0; k < 65536; k++) if (c2c[k]) { h2 += gamma_bits(k - last) + gamma_bits(c2c[k]); last = (long)k; nz++; }
        std::unordered_map<uint32_t, uint64_t> c3c; for (size_t i = 0; i + 2 < n; i++) c3c[x[i] << 16 | x[i + 1] << 8 | x[i + 2]]++;
        std::vector<std::pair<uint32_t, uint64_t>> c3v(c3c.begin(), c3c.end()); std::sort(c3v.begin(), c3v.end()); double h3 = 0; long l3 = -1;
        for (auto& [k, v] : c3v) { h3 += gamma_bits(k - l3) + gamma_bits(v); l3 = (long)k; }
        std::printf("\nRIGHT-CONTEXT HINTS (the decoder can know the letters that FOLLOW each BWT symbol if the archive stores counts):\n");
        std::printf("  header: letter counts %.0f bytes | letter-pair counts (%zu pairs) %.0f bytes | triple counts (%zu triples) %.0f bytes\n", h1 / 8, nz, h2 / 8, c3v.size(), h3 / 8);
        std::fflush(stdout);
        t = now(); row("BWT -> bigger mix (hashed order 0-3, two mixers, 3 APMs), no hints", cm2(y2, nullptr, nullptr, nullptr, 0), 0);
        t = now(); { double b = cm2(y2, &f1, nullptr, nullptr, 0) + h1; row("  + hint: the next letter (letter counts in the header, included)", b, 0); }
        t = now(); { double b = cm2(y2, &f1, &f2, nullptr, 1) + h2; row("  + hint: the next 2 letters (pair counts in the header, included)", b, 0); }
        t = now(); { double b = cm2(y2, &f1, &f2, &f3, 1) + h3; row("  + hint: the next 3 letters (triple counts in the header, included)", b, 0); }
    }
    std::printf("(BWT side costs 4 bytes for the primary index, included as +8 bytes header)\n");
    return 0;
}
