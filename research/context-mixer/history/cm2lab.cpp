// CM lab v2: configurable raw-text context mixing (own code). Knobs come from environment variables so many variants
// can run in parallel. Size = exact adaptive-coding cost (sum of -log2 p).   usage: cm2lab FILE
//   CM_CTX   comma list of contexts: o1..o8 (last k bytes), w (word), w2 (word+previous word), s2 (byte 2 back), s23 (bytes 2-3 back),
//            s4 (byte 4 back), wl (word + byte before it), col (position in line + byte above), x8 (bytes 5-8 back)
//   CM_LIM   counter limit for high orders (default 255);  CM_LIMLO limit for o1/o2 (1023)
//   CM_DUAL  1 = also a fast counter per context (limit 4) as extra input
//   CM_LR    mixer learning rate (0.012);  CM_SEL 1 = first mixer selected by number of known contexts
//   CM_MATCH min match length (6; 0 = no match model)
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "../../statico/src/io.hpp"
#include "../../statico/src/sha256.hpp"
#include "../lstm.hpp"
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
static float RT[1024]; static float STT[4096];
static inline float clampp(float p) { return std::min(std::max(p, 1.0f / 4096), 1.0f - 1.0f / 4096); }
static inline float st(float p) { p = clampp(p); return std::log(p / (1 - p)); }
static inline float sq(float x) { return 1.0f / (1.0f + std::exp(-x)); }
static inline float stq(float p) { int q = (int)(p * 4096); q = std::min(std::max(q, 0), 4095); return STT[q]; }
static inline double cost(float p, int bit) { p = clampp(p); return -std::log2(bit ? p : 1 - p); }
struct HCtr { float p = 0.5f; uint16_t n = 0; uint16_t chk = 0; };
static inline void upd(HCtr& c, int bit, int limit) { c.p += ((float)bit - c.p) * RT[c.n]; if (c.n < limit) c.n++; }
struct Mixer { int n; std::vector<float> w; float lr; std::vector<float> in; int sel = 0; float pr = 0.5f;
    Mixer(int n_, int sets, float lr_) : n(n_), w((size_t)n_ * sets, 0.15f), lr(lr_), in(n_) {}
    float mix(int s) { sel = s; float d = 0; const float* W = &w[(size_t)s * n]; for (int i = 0; i < n; i++) d += W[i] * in[i]; pr = clampp(sq(d)); return pr; }
    void update(int bit) { float e = ((float)bit - pr) * lr; float* W = &w[(size_t)sel * n]; for (int i = 0; i < n; i++) W[i] += e * in[i]; } };
struct APM { std::vector<float> t; int idx = 0; float wlo = 0; APM(int ctx) : t((size_t)ctx * 33) { for (int c = 0; c < ctx; c++) for (int j = 0; j < 33; j++) t[(size_t)c * 33 + j] = sq((j - 16) / 2.0f); }
    float pp(float p, int c) { float s = std::min(std::max(st(p), -7.99f), 7.99f) * 2 + 16; int j = (int)s; wlo = s - j; idx = c * 33 + j; return t[idx] * (1 - wlo) + t[idx + 1] * wlo; }
    void update(int bit, float r = 0.02f) { t[idx] += ((float)bit - t[idx]) * r * (1 - wlo); t[idx + 1] += ((float)bit - t[idx + 1]) * r * wlo; } };
static inline uint64_t H(uint64_t a) { a *= 0x9E3779B97F4A7C15ull; return a ^ (a >> 29); }
static std::string env(const char* k, const char* d) { const char* v = std::getenv(k); return v ? v : d; }

int main(int argc, char** argv) {
    for (int i = 0; i < 1024; i++) RT[i] = 1.0f / (i + 1.5f);
    for (int i = 0; i < 4096; i++) STT[i] = st((i + 0.5f) / 4096);
    // modes: cm2lab FILE (cost only) | cm2lab c IN OUT (write archive) | cm2lab d IN OUT (decode archive)
    int mode = 0; std::vector<uint8_t> x, arc; std::string outp;
    if (argc >= 4 && std::string(argv[1]) == "c") { mode = 1; if (!read_all(argv[2], x)) return 1; outp = argv[3]; }
    else if (argc >= 4 && std::string(argv[1]) == "d") { mode = 2; if (!read_all(argv[2], arc) || arc.size() < 8) return 1; outp = argv[3];
        uint64_t nn = 0; for (int q = 0; q < 8; q++) nn |= (uint64_t)arc[q] << (8 * q); x.assign(nn, 0); }
    else if (argc < 2 || !read_all(argv[1], x)) { std::fprintf(stderr, "usage: cm2lab FILE | c IN OUT | d IN OUT\n"); return 1; }
    // binary arithmetic coder (carry-less, 32-bit), probability of a 1 in 16 bits
    uint32_t x1 = 0, x2 = 0xffffffffu, xv = 0; size_t ap = 8; std::vector<uint8_t> out;
    if (mode == 1) { uint64_t nn = x.size(); for (int q = 0; q < 8; q++) out.push_back((uint8_t)(nn >> (8 * q))); }
    if (mode == 2) for (int q = 0; q < 4; q++) xv = xv << 8 | (ap < arc.size() ? arc[ap++] : 0);
    std::vector<std::string> ctx; { std::string s = env("CM_CTX", "o1,o2,o3,o4,o6,w,w2"); size_t a = 0; while (a < s.size()) { size_t b = s.find(',', a); if (b == std::string::npos) b = s.size(); ctx.push_back(s.substr(a, b - a)); a = b + 1; } }
    int LIM = std::atoi(env("CM_LIM", "255").c_str()), LIMLO = std::atoi(env("CM_LIMLO", "1023").c_str()); bool DUAL = env("CM_DUAL", "0") == "1";
    float LR = std::atof(env("CM_LR", "0.012").c_str()); bool SEL = env("CM_SEL", "0") == "1"; int MINLEN = std::atoi(env("CM_MATCH", "6").c_str());
    float LRD = std::atof(env("CM_LRD", "0").c_str()); bool SSEM = env("CM_SSEM", "0") == "1";
    float APMR = std::atof(env("CM_APMR", "0.02").c_str()), FBW = std::atof(env("CM_FB", "0.75").c_str()), SSW = std::atof(env("CM_SSW", "0.5").c_str());
    int SEL2 = std::atoi(env("CM_SEL2", "0").c_str()); bool NOCONF = env("CM_NOCONF", "0") == "1";
    bool M45 = env("CM_M45", "0") == "1", BRK2 = env("CM_BRK2", "0") == "1";
    bool L2 = env("CM_L2", "0") == "1", M3ON = env("CM_M3", "0") == "1", INH = env("CM_INH", "0") == "1", APMW = env("CM_APMW", "0") == "1";
    const int NC = (int)ctx.size(); const size_t TB = std::atoi(env("CM_TB", x.size() > 20000000 ? "24" : "22").c_str()), MASK = (1u << TB) - 1;
    std::vector<std::vector<HCtr>> T(NC, std::vector<HCtr>(1u << TB)), TF(DUAL ? NC : 0, std::vector<HCtr>(1u << TB)); std::vector<HCtr> O0(256);
    const int LN = std::atoi(env("CM_LSTM", "0").c_str());
    LSTM* lstm = LN ? new LSTM(LN, std::atoi(env("CM_LSTMT", "16").c_str()), (float)std::atof(env("CM_LSTMLR", "0.01").c_str())) : nullptr;
    const int NI = (LN ? 2 : 0) + NC * (DUAL ? 3 : 2) + 4 + (env("CM_GEN", "").empty() ? 0 : 1) + (std::atoi(env("CM_MATCH2", "0").c_str()) ? 1 : 0) + (env("CM_BH", "0") == "1" ? NC : 0);
    Mixer M1(NI, 16 * 8 * 8, LR), M2(NI, 256 * 8, LR), M3(NI, 4096, LR), M4(NI, 1024 * 8, LR), M5(NI, 64 * 8, LR), F(4, 8 * 16, 0.004f), FA(5, 8 * 16, 0.003f);
    for (auto& w : F.w) w = 0.33f; for (auto& w : FA.w) w = 0.2f;
    F.lr = std::atof(env("CM_L2LR", "0.004").c_str()); std::string M3SEL = env("CM_M3SEL", "c2"); APM A1(256 * 256), A2(65536), A3(1024 * 64);
    const size_t MH = 1 << 22; std::vector<uint32_t> mtab(MH, 0); size_t mptr = 0, mlen = 0; std::vector<HCtr> MM(64 * 2 * 256);
    int MIN2 = std::atoi(env("CM_MATCH2", "0").c_str()); std::vector<uint32_t> mtab2(MIN2 ? MH : 1, 0); size_t mptr2 = 0, mlen2 = 0; std::vector<HCtr> MM2(64 * 2 * 256);
    std::vector<uint32_t> ind(1 << 16, 0), ind1(256, 0), indw(1 << 20, 0);
    std::string GEN = env("CM_GEN", ""); std::vector<uint8_t> gdig; if (GEN == "pi") read_all("work/digits/pi.dig", gdig);
    bool BH = env("CM_BH", "0") == "1"; std::vector<std::vector<uint16_t>> S(BH ? NC : 0, std::vector<uint16_t>(1u << TB, 0));
    bool BHP = env("CM_BHP", "0") == "1", BH2 = env("CM_BH2", "0") == "1";
    struct SMap { std::vector<float> p; std::vector<uint16_t> n; SMap() : p(1024 * 8, 0.5f), n(1024 * 8, 0) {} };
    std::vector<SMap> SM(BH ? NC : 0);   // indirect: last 2 bytes seen after each order-2 context
    std::vector<uint64_t> h(NC); std::vector<int> limit(NC);
    for (int j = 0; j < NC; j++) limit[j] = (ctx[j] == "o1" || ctx[j] == "o2") ? LIMLO : LIM;
    bool isl[256]; for (int q = 0; q < 256; q++) isl[q] = (q >= 'a' && q <= 'z') || (q >= 'A' && q <= 'Z') || q >= 128;
    { std::string L = env("CM_LETTERS", ""); size_t a = 0; while (a < L.size()) { size_t bb = L.find(',', a); if (bb == std::string::npos) bb = L.size(); isl[std::atoi(L.substr(a, bb - a).c_str()) & 255] = true; a = bb + 1; } }
    uint64_t wcase = 0; int wlen = 0; uint64_t word = 0, pword = 0, ppword = 0; int brk = 0, fmt = 0, ndig = 0, numprev = 0; size_t linestart = 0; APM A4(16 * 2 * 256); double bits = 0; size_t n = x.size(); double t0 = now();
    for (size_t i = 0; i < n; i++) {
        uint64_t hist = 0; for (int k = 1; k <= 8; k++) hist |= (uint64_t)(i >= (size_t)k ? x[i - k] : 0) << (8 * (k - 1));
        auto B = [&](int k) -> uint64_t { return hist >> (8 * (k - 1)) & 255; };
        size_t col = i - linestart; uint8_t above = (linestart >= col + 1 && linestart > 0) ? 0 : 0;
        for (int j = 0; j < NC; j++) { const std::string& c = ctx[j]; uint64_t v = 0;
            if (c[0] == 'o') { int k = c[1] - '0'; v = k >= 8 ? hist : hist & ((1ull << (8 * k)) - 1); }
            else if (c == "w") v = word; else if (c == "w2") v = word ^ pword * 0x100000001B3ull; else if (c == "w3") v = word ^ pword * 0x100000001B3ull ^ ppword * 0xC2B2AE3D27D4EB4Full;
            else if (c == "brk") v = (uint64_t)brk << 16 | (hist & 0xFFFF);
            else if (c == "wc") v = wcase;
            else if (c == "ws") v = word ^ ppword * 0x9E3779B97F4A7C15ull;
            else if (c[0] == 'h') { int kk = std::atoi(c.c_str() + 1); uint64_t hh = 0; for (int q = 1; q <= kk; q++) hh = (hh + (i >= (size_t)q ? x[i - q] : 0) + 1) * 0x100000001B3ull; v = hh; }
            else if (c == "wpos") v = (uint64_t)std::min(wlen, 15) << 8 | B(1);
            else if (c == "num") v = (uint64_t)ndig << 16 | numprev << 8 | (ndig ? B(1) : 0);
            else if (c == "fmt") v = (uint64_t)(brk * 16 + fmt) << 16 | (hist & 0xFFFF);
            else if (c == "ind") v = (uint64_t)ind[hist & 0xFFFF] << 16 | (hist & 0xFF);
            else if (c == "ind1") v = (uint64_t)ind1[hist & 0xFF] << 16 | (hist & 0xFF);
            else if (c == "indw") v = (uint64_t)indw[word & 0xFFFFF] << 32 ^ word;
            else if (c == "ind3") v = (uint64_t)ind[hist & 0xFFFF] << 24 | (hist & 0xFFFF); else if (c == "s2") v = B(2); else if (c == "s23") v = B(2) | B(3) << 8;
            else if (c == "s4") v = B(4); else if (c == "wl") v = word ^ B(1) << 56; else if (c == "x8") v = hist >> 32; else if (c == "col") v = std::min<size_t>(col, 255) | B(1) << 8 | (uint64_t)above << 16;
            h[j] = H((uint64_t)(j + 1) << 58 ^ v); }
        if (MINLEN && i >= (size_t)MINLEN) {
            uint64_t key = H(hist & ((1ull << (8 * MINLEN)) - 1)) & (MH - 1);
            if (mlen == 0 && mtab[key]) { mptr = mtab[key]; size_t a = mptr, b = i; while (a > 0 && b > 0 && x[a - 1] == x[b - 1] && mlen < 400) { a--; b--; mlen++; } if (mlen < (size_t)MINLEN) mlen = 0; }
            mtab[key] = (uint32_t)i;
        }
        if (MIN2 && i >= 32) {
            uint64_t key = H(hist ^ (uint64_t)x[i - 9] << 1 ^ (uint64_t)x[i - 12] << 9 ^ (uint64_t)x[i - 16] << 17) & (MH - 1);
            if (mlen2 == 0 && mtab2[key]) { mptr2 = mtab2[key]; size_t a = mptr2, b = i; while (a > 0 && b > 0 && x[a - 1] == x[b - 1] && mlen2 < 2000) { a--; b--; mlen2++; } if (mlen2 < (size_t)MIN2) mlen2 = 0; }
            mtab2[key] = (uint32_t)i;
        }
        int expected2 = mlen2 ? x[mptr2] : -1;
        int expected = mlen ? x[mptr] : -1; int c1 = (int)B(1), c2 = (int)B(2);
        int node = 1;
        for (int b = 7; b >= 0; b--) {
            int bit = 0; HCtr* c[24]; HCtr* cf[24]; size_t sidx[24]; int smi[24]; int k = 0, known = 0, hiord = -1;
            for (int j = 0; j < NC; j++) {
                size_t ix = (h[j] + (uint64_t)node * 0x2545F4914F6CDD1Dull) >> 7 & MASK; c[j] = &T[j][ix];
                uint16_t chk = (uint16_t)((h[j] + node) >> 48); if (c[j]->chk != chk) { c[j]->chk = chk; c[j]->p = (INH && j > 0 && ctx[j][0] == 'o' && ctx[j - 1][0] == 'o') ? c[j - 1]->p : 0.5f; c[j]->n = 0; }
                known += c[j]->n > 0; if (c[j]->n > 0 && ctx[j][0] == 'o') hiord = j;
                float s = stq(c[j]->p); M1.in[k] = M2.in[k] = M3.in[k] = s; k++;
                float conf = (c[j]->n && !NOCONF) ? s * std::min(1.0f, c[j]->n / 4.0f) : 0.0f; M1.in[k] = M2.in[k] = M3.in[k] = conf; k++;
                if (BH) { uint16_t& sv = S[j][ix]; if (c[j]->n == 0) sv = 0; sidx[j] = ix; smi[j] = (BH2 ? (sv & 1023) : (sv & 511)) + (BHP ? 1024 * (7 - b) : 0); float sp = SM[j].p[smi[j]]; M1.in[k] = M2.in[k] = M3.in[k] = stq(sp); k++; }
                if (DUAL) { cf[j] = &TF[j][ix]; if (cf[j]->chk != chk) { cf[j]->chk = chk; cf[j]->p = c[j]->p; cf[j]->n = 0; } M1.in[k] = M2.in[k] = M3.in[k] = stq(cf[j]->p); k++; }
            }
            M1.in[k] = M2.in[k] = M3.in[k] = stq(O0[node].p); k++;
            int lb = 0; float mv = 0;
            if (expected >= 0 && ((expected + 256) >> (b + 1)) == node) { int eb = expected >> b & 1; lb = (int)std::min<size_t>(15, mlen / 4 + 1); mv = stq(MM[(lb * 2 + eb) * 256 + node].p); }
            M1.in[k] = M2.in[k] = M3.in[k] = mv; k++; M1.in[k] = M2.in[k] = M3.in[k] = lb ? ((expected >> b & 1) ? 1.0f : -1.0f) * std::min(4.0f, lb / 2.0f) : 0.0f; k++;
            { float mv2 = 0; int lb2 = 0; if (MIN2 && expected2 >= 0 && ((expected2 + 256) >> (b + 1)) == node) { int eb = expected2 >> b & 1; lb2 = (int)std::min<size_t>(15, mlen2 / 16 + 1); mv2 = stq(MM2[(lb2 * 2 + eb) * 256 + node].p); }
              if (MIN2) { M1.in[k] = M2.in[k] = M3.in[k] = mv2; k++; } }
            if (lstm) { float pl = lstm->pbit(node, b); float sl = stq(pl); M1.in[k] = M2.in[k] = M3.in[k] = sl; k++; M1.in[k] = M2.in[k] = M3.in[k] = sl * 0.5f * (lb ? 1.0f : 0.0f); k++; }
            if (!GEN.empty()) { int gb = GEN == "pi" ? (gdig[(i * 8 + (7 - b)) % gdig.size()] & 1) : (0x64 >> b & 1);   // pi digit parity | fixed byte 'd'
                M1.in[k] = M2.in[k] = M3.in[k] = gb ? 1.0f : -1.0f; k++; }
            M1.in[k] = M2.in[k] = M3.in[k] = 0.25f;
            int kb = SEL2 ? std::min(7, hiord + 1) : SEL ? std::min(7, known * 8 / std::max(1, NC)) : (c1 == ' ' ? 1 : 0);
            float p1 = M1.mix((lb * 8 + kb) * 8 + (7 - b)), p2 = M2.mix(c1 * 8 + (7 - b));
            float p3 = M3ON ? M3.mix(M3SEL == "node" ? node * 8 + (7 - b) : M3SEL == "c2node" ? ((c2 & 0xF0) << 4 | node) % 2048 : c2 * 8 + (7 - b)) : p2;
            float p4 = p3, p5 = p3;
            if (M45) { for (int q = 0; q < NI; q++) { M4.in[q] = M1.in[q]; M5.in[q] = M1.in[q]; }
                p4 = M4.mix((int)(word & 1023) * 8 + (7 - b)); p5 = M5.mix((brk * 8 + std::min(7, fmt)) * 8 + (7 - b)); }
            float pm;
            if (L2) { F.in[0] = stq(p1); F.in[1] = stq(p2); F.in[2] = stq(p3); F.in[3] = 0.25f; pm = F.mix((7 - b) * 16 + std::min(15, lb)); }
            else if (M45) pm = sq((stq(p1) + stq(p2) + stq(p3) + stq(p4) + stq(p5)) / 5);
            else pm = M3ON ? sq((stq(p1) + stq(p2) + stq(p3)) / 3) : sq((stq(p1) + stq(p2)) / 2);
            float pa = A1.pp(pm, c1 * 256 + node), pb = A2.pp(pm, (int)((c1 << 8 | c2) & 0xFFFF)), pc = A3.pp(pm, (int)((H(hist & 0xFFFFFF) >> 20) & 1023) * 64 + (node & 63));
            if (LRD > 0) { static const float LRMIN = (float)std::atof(env("CM_LRMIN", "0.002").c_str()); float lr = std::max(LRMIN, LR / (1.0f + (float)i / LRD)) ; M1.lr = M2.lr = M3.lr = lr; }
            float pf;
            if (APMW) { FA.in[0] = stq(pm); FA.in[1] = stq(pa); FA.in[2] = stq(pb); FA.in[3] = stq(pc); FA.in[4] = 0.25f; pf = FA.mix((7 - b) * 16 + std::min(15, lb)); pf = pf * FBW + (1 - FBW) * (2 * pm + pa + pb + 2 * pc) / 6; }
            else pf = (2 * pm + pa + pb + 2 * pc) / 6;
            if (SSEM) { float pd = A4.pp(pf, lb ? ((lb * 2 + (expected >> b & 1)) * 256 + node) : node); pf = pf * (1 - SSW) + pd * SSW; }
            { uint32_t p16 = (uint32_t)std::min(65535.0f, std::max(1.0f, pf * 65536.0f)); uint32_t xmid = x1 + (uint32_t)(((uint64_t)(x2 - x1) * p16) >> 16);
              if (mode == 2) bit = xv <= xmid; else bit = x[i] >> b & 1;
              if (bit) x2 = xmid; else x1 = xmid + 1;
              while (((x1 ^ x2) & 0xff000000u) == 0) { if (mode == 1) out.push_back((uint8_t)(x2 >> 24)); x1 <<= 8; x2 = (x2 << 8) | 255;
                  if (mode == 2) xv = (xv << 8) | (ap < arc.size() ? arc[ap++] : 0); } }
            bits += cost(pf, bit);
            if (SSEM) A4.update(bit, APMR);
            M1.update(bit); M2.update(bit); if (M3ON) M3.update(bit); if (M45) { M4.update(bit); M5.update(bit); } if (L2) F.update(bit); if (APMW) FA.update(bit); A1.update(bit, APMR); A2.update(bit, APMR); A3.update(bit, APMR);
            for (int j = 0; j < NC; j++) { upd(*c[j], bit, limit[j]); if (DUAL) upd(*cf[j], bit, 4);
                if (BH) { uint16_t& sv = S[j][sidx[j]]; int q = smi[j]; SMap& m = SM[j]; m.p[q] += ((float)bit - m.p[q]) * RT[m.n[q]]; if (m.n[q] < 1023) m.n[q]++;
                    int n0 = sv >> 5 & 15, n1 = sv >> 1 & 15, prevlast = sv & 1;
                    if (bit) { n1 = std::min(15, n1 + 1); if (n0 > 2) n0 = (n0 + 2) / 2; } else { n0 = std::min(15, n0 + 1); if (n1 > 2) n1 = (n1 + 2) / 2; }
                    sv = (uint16_t)((BH2 ? prevlast << 9 : 0) | n0 << 5 | n1 << 1 | bit); } }
            upd(O0[node], bit, 1023);
            if (lb) { int eb = expected >> b & 1; upd(MM[(lb * 2 + eb) * 256 + node], bit, 1023); }
            if (MIN2 && expected2 >= 0 && ((expected2 + 256) >> (b + 1)) == node) { int lb2 = (int)std::min<size_t>(15, mlen2 / 16 + 1); upd(MM2[(lb2 * 2 + (expected2 >> b & 1)) * 256 + node], bit, 1023); }
            node = node * 2 + bit;
        }
        if (mode == 2) x[i] = (uint8_t)(node & 255);
        if (lstm) lstm->update(x[i]);
        if (mlen) { if (expected == x[i]) { mlen++; mptr++; } else mlen = 0; }
        if (mlen2) { if (expected2 == x[i]) { mlen2++; mptr2++; } else mlen2 = 0; }
        ind[hist & 0xFFFF] = (ind[hist & 0xFFFF] << 8 | x[i]) & 0xFFFF;
        ind1[hist & 0xFF] = (ind1[hist & 0xFF] << 8 | x[i]) & 0xFFFF; indw[word & 0xFFFFF] = (indw[word & 0xFFFFF] << 8 | x[i]) & 0xFFFF;
        int ch = x[i]; bool letter = isl[ch];
        if (letter) wlen++; else wlen = 0;
        if (letter) wcase = (wcase + (uint64_t)ch + 1) * 0x9E3779B1ull; else wcase = 0;
        if (letter) word = (word + (uint64_t)(ch | 32) + 1) * 0x2F0F3A9Bull; else if (word) { ppword = pword; pword = word; word = 0; }
        // markup state: 1 inside [[ ]], 2 inside {{ }}, 3 inside < >, 4 inside , 5 after = in a template line, 6 inside a table row
        if (ch == '[' && i && x[i - 1] == '[') brk = 1; else if (ch == ']' && brk == 1) brk = 0; else if (ch == '{' && i && x[i - 1] == '{') brk = 2; else if (ch == '}' && brk == 2) brk = 0;
        else if (ch == '<') brk = 3; else if (ch == '>' && brk == 3) brk = 0; else if (ch == '\n') brk = 0;
        if (BRK2) {   // line/format state: 1 heading (=), 2 list (*,#), 3 table (|,!), 4 bold/italic open ('') , 5 entity (&..;), 6 indent (:)
            if (i && x[i - 1] == '\n') fmt = ch == '=' ? 1 : (ch == '*' || ch == '#') ? 2 : (ch == '|' || ch == '!') ? 3 : ch == ':' ? 6 : 0;
            if (ch == '\'' && i && x[i - 1] == '\'') fmt = fmt == 4 ? 0 : 4; if (ch == '&') fmt = 5; else if (ch == ';' && fmt == 5) fmt = 0; if (ch == '\n') fmt = 0; }
        if (ch >= '0' && ch <= '9') { if (!ndig) numprev = i ? x[i - 1] : 0; ndig = std::min(ndig + 1, 15); } else ndig = 0;
        if (ch == '\n') linestart = i + 1;
    }
    if (mode == 1) { out.push_back((uint8_t)(x1 >> 24)); out.push_back(255); out.push_back(255); out.push_back(255); write_all(outp.c_str(), out);
        auto hsh = sha256(x.data(), x.size()); std::printf("WROTE %s: %zu bytes (%zu in); sha256 of input %02x%02x%02x%02x...\n", outp.c_str(), out.size(), x.size(), hsh[0], hsh[1], hsh[2], hsh[3]); }
    if (mode == 2) { write_all(outp.c_str(), x); auto hsh = sha256(x.data(), x.size()); std::printf("DECODED %s: %zu bytes; sha256 %02x%02x%02x%02x...\n", outp.c_str(), x.size(), hsh[0], hsh[1], hsh[2], hsh[3]); }
    std::printf("%12.0f bytes  %.4f bits/byte  [%.0fs]  LRD=%g SSEM=%d CM_CTX=%s LIM=%d LIMLO=%d DUAL=%d LR=%g SEL=%d MATCH=%d L2=%d M3=%d INH=%d APMW=%d\n", bits / 8, bits / n, now() - t0, LRD, (int)SSEM,
                env("CM_CTX", "o1,o2,o3,o4,o6,w,w2").c_str(), LIM, LIMLO, (int)DUAL, LR, (int)SEL, MINLEN, (int)L2, (int)M3ON, (int)INH, (int)APMW);
    return 0;
}
