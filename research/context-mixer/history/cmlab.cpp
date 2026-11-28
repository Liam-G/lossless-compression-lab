// CM lab: context mixing directly on the raw text (the record holders' family), our own code.
// Every model predicts the next bit; a mixer learns how much to trust each; refinement stages (APM) fix the result.
// Size = exact adaptive-coding cost (sum of -log2 p). usage: cmlab FILE [models]   models: any of o1 o2 o3 o4 o6 word match (default all)
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "../../statico/src/io.hpp"
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
static float RT[1024]; static float STT[4096];
static inline float clampp(float p) { return std::min(std::max(p, 1.0f / 4096), 1.0f - 1.0f / 4096); }
static inline float st(float p) { p = clampp(p); return std::log(p / (1 - p)); }
static inline float sq(float x) { return 1.0f / (1.0f + std::exp(-x)); }
static inline float stq(float p) { int q = (int)(p * 4096); q = std::min(std::max(q, 0), 4095); return STT[q]; }
static inline double cost(float p, int bit) { p = clampp(p); return -std::log2(bit ? p : 1 - p); }
struct HCtr { float p = 0.5f; uint16_t n = 0; uint16_t chk = 0; };
template <class C> static inline void upd(C& c, int bit, int limit) { c.p += ((float)bit - c.p) * RT[c.n]; if (c.n < limit) c.n++; }
struct Mixer { int n; std::vector<float> w; float lr; std::vector<float> in; int sel = 0; float pr = 0.5f;
    Mixer(int n_, int sets, float lr_) : n(n_), w((size_t)n_ * sets, 0.2f), lr(lr_), in(n_) {}
    float mix(int s) { sel = s; float d = 0; for (int i = 0; i < n; i++) d += w[(size_t)s * n + i] * in[i]; pr = clampp(sq(d)); return pr; }
    void update(int bit) { float e = ((float)bit - pr) * lr; for (int i = 0; i < n; i++) w[(size_t)sel * n + i] += e * in[i]; } };
struct APM { std::vector<float> t; int idx = 0; float wlo = 0; APM(int ctx) : t((size_t)ctx * 33) { for (int c = 0; c < ctx; c++) for (int j = 0; j < 33; j++) t[(size_t)c * 33 + j] = sq((j - 16) / 2.0f); }
    float pp(float p, int c) { float s = std::min(std::max(st(p), -7.99f), 7.99f) * 2 + 16; int j = (int)s; wlo = s - j; idx = c * 33 + j; return t[idx] * (1 - wlo) + t[idx + 1] * wlo; }
    void update(int bit, float r = 0.02f) { t[idx] += ((float)bit - t[idx]) * r * (1 - wlo); t[idx + 1] += ((float)bit - t[idx + 1]) * r * wlo; } };
static inline uint64_t H(uint64_t a) { a *= 0x9E3779B97F4A7C15ull; return a ^ (a >> 29); }

static double run(const std::vector<uint8_t>& x, const std::string& models, bool verbose) {
    auto has = [&](const char* m) { return models == "all" || models.find(m) != std::string::npos; };
    const int ORD[5] = {1, 2, 3, 4, 6}; bool use_o[5]; for (int k = 0; k < 5; k++) use_o[k] = has(("o" + std::to_string(ORD[k])).c_str());
    bool use_word = has("word"), use_match = has("match");
    const int NC = 5 + 2;   // 5 orders + word + word-pair
    const size_t TB = x.size() > 20000000 ? 24 : 22, MASK = (1u << TB) - 1;
    std::vector<std::vector<HCtr>> T(NC, std::vector<HCtr>(1u << TB)); std::vector<HCtr> O0(256);
    const int NI = 2 * NC + 2 + 2 + 1;
    Mixer M1(NI, 64 * 8, 0.012f), M2(NI, 256 * 8, 0.012f); APM A1(256 * 256), A2(65536), A3(1024 * 64);
    // match model
    const size_t MH = 1 << 22; std::vector<uint32_t> mtab(MH, 0); size_t mptr = 0, mlen = 0; const int MINLEN = 6;
    std::vector<HCtr> MM(64 * 2 * 256);
    std::vector<uint64_t> h(NC); uint64_t word = 0, pword = 0; double bits = 0; size_t n = x.size();
    for (size_t i = 0; i < n; i++) {
        // byte-boundary context hashes
        uint64_t hist = 0; for (int k = 1; k <= 6; k++) hist |= (uint64_t)(i >= (size_t)k ? x[i - k] : 0) << (8 * (k - 1));
        for (int k = 0; k < 5; k++) h[k] = H((uint64_t)(k + 1) << 56 ^ (hist & ((1ull << (8 * ORD[k])) - 1)));
        h[5] = H(0x77ull << 56 ^ word); h[6] = H(0x78ull << 56 ^ word ^ pword * 0x100000001B3ull);
        // match model: find the last occurrence of the previous MINLEN bytes
        if (i >= (size_t)MINLEN) {
            uint64_t key = H(hist & 0xFFFFFFFFFFFFull) & (MH - 1);
            if (mlen == 0 && mtab[key]) { mptr = mtab[key]; mlen = 0; size_t a = mptr, b = i; while (a > 0 && b > 0 && x[a - 1] == x[b - 1] && mlen < 400) { a--; b--; mlen++; } if (mlen < (size_t)MINLEN) mlen = 0; }
            mtab[key] = (uint32_t)i;
        }
        int expected = mlen ? x[mptr] : -1;
        int c1 = i ? x[i - 1] : 0, c2 = i > 1 ? x[i - 2] : 0;
        int node = 1;
        for (int b = 7; b >= 0; b--) {
            int bit = x[i] >> b & 1; HCtr* c[NC]; int k = 0;
            for (int j = 0; j < NC; j++) {
                bool use = j < 5 ? use_o[j] : use_word;
                size_t ix = (h[j] + (uint64_t)node * 0x2545F4914F6CDD1Dull) >> 7 & MASK; c[j] = &T[j][ix];
                uint16_t chk = (uint16_t)((h[j] + node) >> 48); if (c[j]->chk != chk) { c[j]->chk = chk; c[j]->p = 0.5f; c[j]->n = 0; }
                float s = use ? stq(c[j]->p) : 0.0f; M1.in[k] = M2.in[k] = s; k++;
                float conf = use && c[j]->n ? s * std::min(1.0f, c[j]->n / 4.0f) : 0.0f; M1.in[k] = M2.in[k] = conf; k++;
            }
            float s0 = stq(O0[node].p); M1.in[k] = M2.in[k] = s0; k++;
            // match input: strong vote for the expected bit while the match holds
            int lb = 0; float mv = 0;
            if (use_match && expected >= 0 && ((expected + 256) >> (b + 1)) == node) { int eb = expected >> b & 1; lb = std::min<size_t>(15, mlen / 4 + 1);
                HCtr& mc = MM[(lb * 2 + eb) * 256 + node]; mv = stq(mc.p); }
            M1.in[k] = M2.in[k] = mv; k++; M1.in[k] = M2.in[k] = lb ? ((expected >> b & 1) ? 1.0f : -1.0f) * std::min(4.0f, lb / 2.0f) : 0.0f; k++;
            M1.in[k] = M2.in[k] = 0.25f;
            int sel1 = (lb * 4 + std::min(3, (int)(use_word && word ? 1 : 0) + (c1 == ' ' ? 2 : 0))) * 8 + (7 - b);
            float p1 = M1.mix(sel1 % (64 * 8)), p2 = M2.mix(c1 * 8 + (7 - b));
            float pm = sq((stq(p1) + stq(p2)) / 2);
            float pa = A1.pp(pm, c1 * 256 + node), pb = A2.pp(pm, (int)((c1 << 8 | c2) & 0xFFFF)), pc = A3.pp(pm, (int)((h[1] >> 20) & 1023) * 64 + std::min(63, node & 63));
            float pf = (2 * pm + pa + pb + 2 * pc) / 6;
            bits += cost(pf, bit);
            M1.update(bit); M2.update(bit); A1.update(bit); A2.update(bit); A3.update(bit);
            for (int j = 0; j < NC; j++) upd(*c[j], bit, 1023);
            upd(O0[node], bit, 1023);
            if (lb) { int eb = expected >> b & 1; upd(MM[(lb * 2 + eb) * 256 + node], bit, 1023); }
            node = node * 2 + bit;
        }
        // after the byte
        if (mlen) { if (expected == x[i]) { mlen++; mptr++; } else mlen = 0; }
        int ch = x[i]; bool letter = (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch >= 128;
        if (letter) word = (word + (uint64_t)(ch | 32) + 1) * 0x2F0F3A9Bull; else if (word) { pword = word; word = 0; }
        if (verbose && (i + 1) % (1 << 20) == 0) { std::fprintf(stderr, "  %zu MB: %.3f bits/byte so far\n", (i + 1) >> 20, bits / (i + 1)); }
    }
    return bits;
}

int main(int argc, char** argv) {
    for (int i = 0; i < 1024; i++) RT[i] = 1.0f / (i + 1.5f);
    for (int i = 0; i < 4096; i++) STT[i] = st((i + 0.5f) / 4096);
    std::vector<uint8_t> x; if (argc < 2 || !read_all(argv[1], x)) { std::fprintf(stderr, "usage: cmlab FILE [model sets separated by ;]\n"); return 1; }
    std::string sets = argc > 2 ? argv[2] : "all";
    std::printf("CM LAB on %s (%zu bytes); size = exact adaptive-coding cost\n", argv[1], x.size()); std::fflush(stdout);
    size_t a = 0;
    while (a <= sets.size()) { size_t b = sets.find(';', a); if (b == std::string::npos) b = sets.size(); std::string m = sets.substr(a, b - a); a = b + 1;
        double t = now(); double bits = run(x, m, false);
        std::printf("  models [%s]: %12.0f bytes  %.4f bits/byte  [%.0fs]\n", m.c_str(), bits / 8, bits / x.size(), now() - t); std::fflush(stdout); }
    return 0;
}
