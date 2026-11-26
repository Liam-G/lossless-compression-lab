// cm3 (lab): our context-mixing compressor, clean version with only the features that won in cm2lab, and
// cache-line hash buckets: each context does 2 lookups per byte (one per half-byte), each bucket = one 64-byte line
// holding the 15 bit-slots of that half-byte. Real arithmetic coder; c/d modes with SHA-256 check.
// usage: cm3 FILE (cost only) | cm3 c IN OUT | cm3 d IN OUT          knobs: CM3_BITS (log2 buckets per context), CM3_LSTM (cells)
// CM3_PATTERN enables periods (1), ramps (2), xorshift32 (4), and numeric formulas (8).
// CM3_SKELETON folds decimal values (1), ASCII case (2), and allows different digit run lengths (4 with 1).
// CM3_LSTM_UPDATE_EVERY sets the training stride in windows. CM3_LSTM_SKIP_MATCH skips windows with that many match hits.
// CM3_PRIME_PATH supplies a shared byte prefix for model training. Archive lengths describe the payload alone.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "../statico/src/io.hpp"
#include "../statico/src/sha256.hpp"
#include "lstm.hpp"
#include "pattern_predictor.hpp"
#include "skeleton_predictor.hpp"
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
static std::string env(const char* k, const char* d) { const char* v = std::getenv(k); return v ? v : d; }
static float RT[1024], STT[4096];
static inline float clampp(float p) { return std::min(std::max(p, 1.0f / 4096), 1.0f - 1.0f / 4096); }
static inline float st(float p) { p = clampp(p); return std::log(p / (1 - p)); }
static inline float sq(float x) { return 1.0f / (1.0f + std::exp(-x)); }
static inline float stq(float p) { int q = (int)(p * 4096); q = std::min(std::max(q, 0), 4095); return STT[q]; }
static inline double cost(float p, int bit) { p = clampp(p); return -std::log2(bit ? p : 1 - p); }
static inline uint64_t H(uint64_t a) { a *= 0x9E3779B97F4A7C15ull; return a ^ (a >> 29); }

struct Slot { uint16_t p; uint8_t n; uint8_t s; };            // probability (1/65536), count, bit-history state
struct alignas(64) Bucket { uint16_t chk; uint8_t used; uint8_t pad; Slot sl[15]; };
static_assert(sizeof(Bucket) == 64, "bucket must be one cache line");
struct Table {
    std::vector<Bucket> b; size_t mask;
    explicit Table(int bits) : b((size_t)1 << bits), mask(((size_t)1 << bits) - 1) {}
    Bucket* find(uint64_t h) {   // two candidate buckets; on miss replace the less used one
        uint16_t chk = (uint16_t)(h >> 48); size_t i = (h >> 8) & mask; Bucket* a = &b[i]; Bucket* c = &b[i ^ 1];
        if (a->chk == chk && a->used) return a; if (c->chk == chk && c->used) return c;
        Bucket* r = a->sl[0].n <= c->sl[0].n ? a : c; if (!a->used) r = a; else if (!c->used) r = c; std::memset(r, 0, sizeof(Bucket)); r->chk = chk; r->used = 1;
        for (auto& s : r->sl) s.p = 32768; return r;
    }
};
// compact slots: 2-byte slots in 32-byte buckets (state + 8-bit probability), or 1-byte slots in 16-byte buckets (state only)
static float Q2P[256]; static uint8_t P2Q(float p) { int q = (int)std::lround((st(p) + 8.0f) * 16.0f); return (uint8_t)std::min(255, std::max(0, q)); }
struct alignas(32) B2 { uint16_t chk; struct { uint8_t s, q; } sl[15]; };
struct alignas(16) B1 { uint8_t chk; uint8_t sl[15]; };
static inline int prio(uint8_t s) { return (s >> 4 & 7) + (s >> 1 & 7); }
template <class BK> struct CTable { std::vector<BK> b; size_t mask; explicit CTable(int bits) : b((size_t)1 << bits), mask(((size_t)1 << bits) - 1) {}
    BK* find(uint64_t h) { size_t i = (h >> 8) & mask; BK* a = &b[i]; BK* c = &b[i ^ 1]; auto ck = (decltype(a->chk))(h >> 48); if (!ck) ck = 1;
        if (a->chk == ck) return a; if (c->chk == ck) return c;
        auto pr = [](BK* x) { if constexpr (sizeof(BK) == 32) return prio(x->sl[0].s); else return prio(x->sl[0]); };
        BK* r = pr(a) <= pr(c) ? a : c; std::memset(r, 0, sizeof(BK)); r->chk = ck;
        if constexpr (sizeof(BK) == 32) for (auto& z : r->sl) z.q = 128;
        return r; } };
struct Mixer { int n; std::vector<float> w; float lr; std::vector<float> in; int sel = 0; float pr = 0.5f;
    Mixer(int n_, int sets, float lr_) : n(n_), w((size_t)n_ * sets, 0.15f), lr(lr_), in(n_) {}
    float mix(int s) { sel = s; float d = 0; const float* W = &w[(size_t)s * n]; for (int i = 0; i < n; i++) d += W[i] * in[i]; pr = clampp(sq(d)); return pr; }
    void update(int bit) { float e = ((float)bit - pr) * lr; float* W = &w[(size_t)sel * n]; for (int i = 0; i < n; i++) W[i] += e * in[i]; } };
struct APM { std::vector<float> t; int idx = 0; float wlo = 0; APM(int ctx) : t((size_t)ctx * 33) { for (int c = 0; c < ctx; c++) for (int j = 0; j < 33; j++) t[(size_t)c * 33 + j] = sq((j - 16) / 2.0f); }
    float pp(float p, int c) { float s = std::min(std::max(st(p), -7.99f), 7.99f) * 2 + 16; int j = (int)s; wlo = s - j; idx = c * 33 + j; return t[idx] * (1 - wlo) + t[idx + 1] * wlo; }
    void update(int bit, float r) { t[idx] += ((float)bit - t[idx]) * r * (1 - wlo); t[idx + 1] += ((float)bit - t[idx + 1]) * r * wlo; } };

int main(int argc, char** argv) {
    for (int i = 0; i < 1024; i++) RT[i] = 1.0f / (i + 1.5f);
    for (int i = 0; i < 4096; i++) STT[i] = st((i + 0.5f) / 4096);
    int mode = 0; std::vector<uint8_t> x, arc; std::string outp;
    if (argc >= 4 && std::string(argv[1]) == "c") { mode = 1; if (!read_all(argv[2], x)) return 1; outp = argv[3]; }
    else if (argc >= 4 && std::string(argv[1]) == "d") { mode = 2; if (!read_all(argv[2], arc) || arc.size() < 8) return 1; outp = argv[3];
        uint64_t nn = 0; for (int q = 0; q < 8; q++) nn |= (uint64_t)arc[q] << (8 * q); x.assign(nn, 0); }
    else if (argc < 2 || !read_all(argv[1], x)) { std::fprintf(stderr, "usage: cm3 FILE | c IN OUT | d IN OUT\n"); return 1; }
    const size_t payload_size = x.size();
    const std::string prime_path = env("CM3_PRIME_PATH", "");
    std::vector<uint8_t> prime;
    if (!prime_path.empty() && !read_all(prime_path.c_str(), prime)) {
        std::fprintf(stderr, "cannot read primer %s\n", prime_path.c_str());
        return 1;
    }
    const size_t prime_size = prime.size();
    if (prime_size) x.insert(x.begin(), prime.begin(), prime.end());
    const size_t n = x.size();
    std::vector<std::string> ctx = {"o1", "o2", "o3", "o4", "o5", "o6", "o7", "o8", "h12", "w", "w2", "w3", "ws", "wc", "brk", "fmt", "num", "ind", "ind1", "indw"};
    { std::string extra = env("CM3_ADD", ""); size_t a = 0; while (a < extra.size()) { size_t b = extra.find(',', a); if (b == std::string::npos) b = extra.size(); ctx.push_back(extra.substr(a, b - a)); a = b + 1; } }
    const int NC = (int)ctx.size(); int BITS = std::atoi(env("CM3_BITS", n > 20000000 ? "22" : "20").c_str());
    const int SLOT = std::atoi(env("CM3_SLOT", "4").c_str());
    for (int q = 0; q < 256; q++) Q2P[q] = sq(q / 16.0f - 8.0f);
    std::vector<Table> T; std::vector<CTable<B2>> T2; std::vector<CTable<B1>> T1;
    // per-context table sizes: CM3_SIZES="name:bits,..." overrides BITS for the named contexts
    std::vector<int> cb(NC, BITS); { std::string S = env("CM3_SIZES", ""); size_t a = 0; while (a < S.size()) { size_t e = S.find(',', a); if (e == std::string::npos) e = S.size();
        std::string it = S.substr(a, e - a); size_t c = it.find(':'); for (int j = 0; j < NC; j++) if (ctx[j] == it.substr(0, c)) cb[j] = std::atoi(it.c_str() + c + 1); a = e + 1; } }
    double tabgb = 0; for (int j = 0; j < NC; j++) tabgb += (SLOT == 4 ? 64.0 : SLOT == 2 ? 32.0 : 16.0) * (1ull << cb[j]) / 1e9;
    for (int j = 0; j < NC; j++) { if (SLOT == 4) T.emplace_back(cb[j]); else if (SLOT == 2) T2.emplace_back(cb[j]); else T1.emplace_back(cb[j]); }
    std::vector<B2*> bk2(NC); std::vector<B1*> bk1(NC);
    const int LN = std::atoi(env("CM3_LSTM", "0").c_str()); LSTM* lstm = LN ? new LSTM(LN, 16, (float)std::atof(env("CM3_LSTMLR", "0.002").c_str()), env("CM3_LSTM2", "0") == "1") : nullptr;
    if (lstm) {
        lstm->decay = (float)std::atof(env("CM3_LSTMD", "0").c_str());
        lstm->training_stride = std::max(1, std::atoi(env("CM3_LSTM_UPDATE_EVERY", "1").c_str()));
        lstm->skip_matches = std::clamp(std::atoi(env("CM3_LSTM_SKIP_MATCH", "0").c_str()), 0, lstm->T);
    }
    const int M2MODE = std::atoi(env("CM3_M2", "0").c_str());   // 0 off, 1 = second-best candidate, 2 = best with min length 16
    const unsigned pattern_models = std::atoi(env("CM3_PATTERN", "0").c_str()) & 15;
    PatternPredictor patterns(pattern_models);
    const unsigned skeleton_models = std::atoi(env("CM3_SKELETON", "0").c_str()) & 7;
    SkeletonPredictor skeleton(skeleton_models);
    const int NI = 2 * NC + 1 + 2 + (LN ? 2 : 0) + 1 + (M2MODE ? 2 : 0);
    size_t mptr2 = 0, mlen2 = 0; std::vector<float> MM2(64 * 2 * 256, 0.5f); std::vector<uint16_t> MM2n(64 * 2 * 256, 0);
    const float LR0 = 0.02f, LRD = 150000, LRMIN = 0.0015f, APMR = 0.02f, FBW = 0.5f, SSW = 0.3f; const int LIM = 511, MINLEN = 6;
    Mixer M1(NI, 16 * 8 * 8, LR0), M2(NI, 256 * 8, LR0), M3(NI, 4096, LR0), FA(5, 8 * 16, 0.003f); for (auto& w : FA.w) w = 0.2f;
    const int L2 = std::atoi(env("CM3_L2", "0").c_str()); const float L2LR = (float)std::atof(env("CM3_L2LR", "0.001").c_str());   // 0 = average of 3; 3 = learned over 3; 6 = learned over 6
    Mixer M4(NI, 1024 * 8, LR0), M5(NI, 64 * 8, LR0), M6(NI, 65536 / 8 * 8, LR0), FL(L2 + 1, 8 * 16, L2LR); for (auto& w : FL.w) w = L2 ? 1.0f / L2 : 0;
    APM A1(256 * 256), A2(65536), A3(1024 * 64), A4(16 * 2 * 256);
    const bool H4 = env("CM3_H4", "0") == "1";
    struct SMap { std::vector<float> p; std::vector<uint16_t> c; SMap() : p(256, 0.5f), c(256, 0) {} }; std::vector<SMap> SM(NC);
    std::vector<float> O0(256, 0.5f); std::vector<uint16_t> O0n(256, 0);
    const int MCAND = std::atoi(env("CM3_MCAND", "1").c_str()), MBACK = std::atoi(env("CM3_MBACK", "400").c_str());
    std::vector<uint32_t> mprev(MCAND > 1 ? n : 0, 0);
    const size_t MH = 1 << 22; std::vector<uint32_t> mtab(MH, 0); size_t mptr = 0, mlen = 0; std::vector<float> MM(64 * 2 * 256, 0.5f); std::vector<uint16_t> MMn(64 * 2 * 256, 0);
    std::vector<uint32_t> ind(1 << 16, 0), ind1(256, 0), indw(1 << 20, 0);
    uint64_t word = 0, pword = 0, ppword = 0, wcase = 0, pstem = 0; std::string curw; int brk = 0, fmt = 0, ndig = 0, numprev = 0;
    std::vector<uint64_t> hc(NC); std::vector<Bucket*> bk(NC);
    uint32_t x1 = 0, x2 = 0xffffffffu, xv = 0; size_t ap = 8; std::vector<uint8_t> out;
    if (mode == 1) for (int q = 0; q < 8; q++) out.push_back((uint8_t)((uint64_t)payload_size >> (8 * q)));
    if (mode == 2) for (int q = 0; q < 4; q++) xv = xv << 8 | (ap < arc.size() ? arc[ap++] : 0);
    double bits = 0, t0 = now();
    for (size_t i = 0; i < n; i++) {
        const bool warming = i < prime_size;
        uint64_t hist = 0; for (int k = 1; k <= 8; k++) hist |= (uint64_t)(i >= (size_t)k ? x[i - k] : 0) << (8 * (k - 1));
        auto B = [&](int k) -> uint64_t { return hist >> (8 * (k - 1)) & 255; };
        for (int j = 0; j < NC; j++) { const std::string& c = ctx[j]; uint64_t v = 0;
            if (c[0] == 'o') { int k = c[1] - '0'; v = k >= 8 ? hist : hist & ((1ull << (8 * k)) - 1); }
            else if (c == "h12") { uint64_t hh = 0; for (int q = 1; q <= 12; q++) hh = (hh + (i >= (size_t)q ? x[i - q] : 0) + 1) * 0x100000001B3ull; v = hh; }
            else if (c == "w") v = word; else if (c == "w2") v = word ^ pword * 0x100000001B3ull; else if (c == "w3") v = word ^ pword * 0x100000001B3ull ^ ppword * 0xC2B2AE3D27D4EB4Full;
            else if (c == "ws") v = word ^ ppword * 0x9E3779B97F4A7C15ull; else if (c == "wc") v = wcase;
            else if (c == "brk") v = (uint64_t)brk << 16 | (hist & 0xFFFF); else if (c == "fmt") v = (uint64_t)(brk * 16 + fmt) << 16 | (hist & 0xFFFF);
            else if (c == "num") v = (uint64_t)ndig << 16 | numprev << 8 | (ndig ? B(1) : 0);
            else if (c == "ind") v = (uint64_t)ind[hist & 0xFFFF] << 16 | (hist & 0xFF); else if (c == "ind1") v = (uint64_t)ind1[hist & 0xFF] << 16 | (hist & 0xFF);
            else if (c == "indw") v = (uint64_t)indw[word & 0xFFFFF] << 32 ^ word;
            else if (c == "st2") v = pstem * 0x9E3779B97F4A7C15ull ^ word;
            else if (c == "st1") v = pstem;
            else if (c == "w1o2") v = pword * 0x9E3779B97F4A7C15ull ^ (hist & 0xFFFF);
            else if (c == "o3w") v = word * 0xC2B2AE3D27D4EB4Full ^ (hist & 0xFFFFFF);
            else if (c == "s24") v = (hist >> 8 & 0xFF) | (hist >> 16 & 0xFF00);
            else if (c == "o10") { uint64_t hh = 0; for (int q = 1; q <= 10; q++) hh = (hh + (i >= (size_t)q ? x[i - q] : 0) + 1) * 0x100000001B3ull; v = hh; }
            else if (c == "h20") { uint64_t hh = 0; for (int q = 1; q <= 20; q++) hh = (hh + (i >= (size_t)q ? x[i - q] : 0) + 1) * 0x100000001B3ull; v = hh; }
            hc[j] = H((uint64_t)(j + 1) << 58 ^ v); }
        if (i >= (size_t)MINLEN) { uint64_t key = H(hist & ((1ull << (8 * MINLEN)) - 1)) & (MH - 1);
            if ((mlen == 0 || (M2MODE && mlen2 == 0)) && mtab[key]) {   // follow the candidate whose preceding text agrees longest with ours
                size_t bestL = 0, bestp = 0, secL = 0, secp = 0; uint32_t p = mtab[key];
                for (int c = 0; c < MCAND && p; c++) { size_t a = p, b = i, L = 0; while (a > 0 && b > 0 && x[a - 1] == x[b - 1] && L < (size_t)MBACK) { a--; b--; L++; }
                    if (L > bestL) { secL = bestL; secp = bestp; bestL = L; bestp = p; } else if (L > secL && x[p] != x[bestp]) { secL = L; secp = p; }
                    if (MCAND == 1) break; p = mprev[p]; }
                if (mlen == 0 && bestL >= (size_t)MINLEN) { mptr = bestp; mlen = bestL; }
                if (M2MODE == 1 && mlen2 == 0 && secL >= (size_t)MINLEN) { mptr2 = secp; mlen2 = secL; }
                if (M2MODE == 2 && mlen2 == 0 && bestL >= 16) { mptr2 = bestp; mlen2 = bestL; } }
            if (MCAND > 1) mprev[i] = mtab[key];
            mtab[key] = (uint32_t)i; }
        int expected = mlen ? x[mptr] : -1; int expected2 = mlen2 ? x[mptr2] : -1; int c1 = (int)B(1), c2 = (int)B(2);
        if (pattern_models) patterns.start_byte(x.data(), i);
        if (skeleton_models) skeleton.start_byte(x.data(), i, expected);
        int node = 1;
        for (int b = 7; b >= 0; b--) {
            if (b == 7 || b == 3) for (int j = 0; j < NC; j++) { uint64_t hh = H(hc[j] + (b == 3 ? (uint64_t)(node & 15) * 0x9E3779B1ull + 1 : 0));
                if (SLOT == 4) bk[j] = T[j].find(hh); else if (SLOT == 2) bk2[j] = T2[j].find(hh); else bk1[j] = T1[j].find(hh); }
            int sidx = (b >= 4 ? node : (node & 15) | 0x10) ; int si = (b >= 4) ? (node - 1) : ((1 << (3 - b)) | (node & ((1 << (3 - b)) - 1))) - 1;
            (void)sidx; int k = 0, known = 0; Slot* s[24]; uint8_t* ss[24]; uint8_t* qq[24];
            for (int j = 0; j < NC; j++) {
                if (SLOT == 4) { s[j] = &bk[j]->sl[si]; ss[j] = &s[j]->s; known += s[j]->n > 0; M1.in[k] = M2.in[k] = M3.in[k] = stq(s[j]->p / 65536.0f); k++; }
                else if (SLOT == 2) { ss[j] = &bk2[j]->sl[si].s; qq[j] = &bk2[j]->sl[si].q; known += *ss[j] != 0; M1.in[k] = M2.in[k] = M3.in[k] = *qq[j] / 16.0f - 8.0f; k++; }
                else { ss[j] = &bk1[j]->sl[si]; known += *ss[j] != 0; M1.in[k] = M2.in[k] = M3.in[k] = 0; k++; }
                M1.in[k] = M2.in[k] = M3.in[k] = stq(SM[j].p[*ss[j]]); k++; }
            M1.in[k] = M2.in[k] = M3.in[k] = stq(O0[node]); k++;
            int lb = 0; float mv = 0;
            if (expected >= 0 && ((expected + 256) >> (b + 1)) == node) { int eb = expected >> b & 1; lb = (int)std::min<size_t>(15, mlen / 4 + 1); mv = stq(MM[(lb * 2 + eb) * 256 + node]); }
            M1.in[k] = M2.in[k] = M3.in[k] = mv; k++; M1.in[k] = M2.in[k] = M3.in[k] = lb ? ((expected >> b & 1) ? 1.0f : -1.0f) * std::min(4.0f, lb / 2.0f) : 0.0f; k++;
            int lb2 = 0; if (M2MODE) { float mv2 = 0; if (expected2 >= 0 && ((expected2 + 256) >> (b + 1)) == node) { lb2 = (int)std::min<size_t>(15, mlen2 / 4 + 1); mv2 = stq(MM2[(lb2 * 2 + (expected2 >> b & 1)) * 256 + node]); }
                M1.in[k] = M2.in[k] = M3.in[k] = mv2; k++; M1.in[k] = M2.in[k] = M3.in[k] = (lb2 && lb) ? ((expected2 >> b & 1) == (expected >> b & 1) ? 1.0f : -1.0f) : 0.0f; k++; }
            if (lstm) { float sl = stq(lstm->pbit(node, b)); M1.in[k] = M2.in[k] = M3.in[k] = sl; k++; M1.in[k] = M2.in[k] = M3.in[k] = lb ? sl * 0.5f : 0.0f; k++; }
            M1.in[k] = M2.in[k] = M3.in[k] = 0.25f;
            float lr = std::max(LRMIN, LR0 / (1.0f + (float)i / LRD)); M1.lr = M2.lr = M3.lr = lr;
            int kb = std::min(7, known * 8 / NC);
            float p1 = M1.mix((lb * 8 + kb) * 8 + (7 - b)), p2 = M2.mix(c1 * 8 + (7 - b)), p3 = M3.mix(((c2 & 0xF0) << 4 | node) % 4096);
            float pm;
            if (!L2) pm = sq((stq(p1) + stq(p2) + stq(p3)) / 3);
            else { FL.in[0] = stq(p1); FL.in[1] = stq(p2); FL.in[2] = stq(p3);
                if (L2 == 6) { for (int q = 0; q < NI; q++) M4.in[q] = M5.in[q] = M6.in[q] = M1.in[q];
                    FL.in[3] = stq(M4.mix((int)(word & 1023) * 8 + (7 - b))); FL.in[4] = stq(M5.mix((brk * 8 + std::min(7, fmt)) * 8 + (7 - b))); FL.in[5] = stq(M6.mix((int)((c1 << 8 | c2) * 0x9E37u >> 19 & 1023) * 8 + (7 - b))); }
                FL.in[L2] = 0.25f; pm = FL.mix((7 - b) * 16 + std::min(15, lb)); }
            float pa = A1.pp(pm, c1 * 256 + node), pb = A2.pp(pm, (c1 << 8 | c2) & 0xFFFF), pc = A3.pp(pm, (int)((H(hist & 0xFFFFFF) >> 20) & 1023) * 64 + (node & 63));
            FA.in[0] = stq(pm); FA.in[1] = stq(pa); FA.in[2] = stq(pb); FA.in[3] = stq(pc); FA.in[4] = 0.25f;
            float pf = FA.mix((7 - b) * 16 + std::min(15, lb)); pf = pf * FBW + (1 - FBW) * (2 * pm + pa + pb + 2 * pc) / 6;
            { float pd = A4.pp(pf, lb ? ((lb * 2 + (expected >> b & 1)) * 256 + node) : node); pf = pf * (1 - SSW) + pd * SSW; }
            if (pattern_models) pf = patterns.mix(pf, b);
            if (skeleton_models) pf = skeleton.mix(pf, b, node);
            int bit;
            if (warming) bit = x[i] >> b & 1;
            else {
                uint32_t p16 = (uint32_t)std::min(65535.0f, std::max(1.0f, pf * 65536.0f));
                uint32_t xmid = x1 + (uint32_t)(((uint64_t)(x2 - x1) * p16) >> 16);
                bit = mode == 2 ? (xv <= xmid) : (x[i] >> b & 1);
                if (bit) x2 = xmid;
                else x1 = xmid + 1;
                while (((x1 ^ x2) & 0xff000000u) == 0) {
                    if (mode == 1) out.push_back((uint8_t)(x2 >> 24));
                    x1 <<= 8;
                    x2 = (x2 << 8) | 255;
                    if (mode == 2) xv = (xv << 8) | (ap < arc.size() ? arc[ap++] : 0);
                }
                bits += cost(pf, bit);
            }
            if (pattern_models) patterns.observe_bit(bit, b);
            if (skeleton_models) skeleton.observe_bit(bit, b);
            if (L2) FL.update(bit); if (L2 == 6) { M4.update(bit); M5.update(bit); M6.update(bit); }
            A4.update(bit, APMR); M1.update(bit); M2.update(bit); M3.update(bit); FA.update(bit); A1.update(bit, APMR); A2.update(bit, APMR); A3.update(bit, APMR);
            for (int j = 0; j < NC; j++) { uint8_t& zs = *ss[j];
                if (SLOT == 4) { Slot& z = *s[j]; int lim = j < 2 ? 1023 : LIM; float r = RT[std::min<int>(z.n, 1023)];
                    z.p = (uint16_t)std::min(65535.0f, std::max(1.0f, z.p + ((bit ? 65535.0f : 0.0f) - z.p) * r)); if (z.n < std::min(lim, 255)) z.n++; }
                else if (SLOT == 2) { int cnt = (zs >> 4 & 7) + (zs >> 1 & 7); float p = Q2P[*qq[j]]; p += ((float)bit - p) * RT[std::min(cnt, 30)] ; *qq[j] = P2Q(p); }
                SMap& m = SM[j]; m.p[zs] += ((float)bit - m.p[zs]) * RT[m.c[zs]]; if (m.c[zs] < 1023) m.c[zs]++;
                if (H4 && SLOT == 4) { int a0 = zs >> 4, a1 = zs & 15; if (bit) { a1 = std::min(15, a1 + 1); if (a0 > 2) a0 = (a0 + 2) / 2; } else { a0 = std::min(15, a0 + 1); if (a1 > 2) a1 = (a1 + 2) / 2; }
                    zs = (uint8_t)(a0 << 4 | a1); continue; }
                int n0 = zs >> 4 & 7, n1 = zs >> 1 & 7; if (bit) { n1 = std::min(7, n1 + 1); if (n0 > 2) n0 = (n0 + 2) / 2; } else { n0 = std::min(7, n0 + 1); if (n1 > 2) n1 = (n1 + 2) / 2; }
                zs = (uint8_t)(n0 << 4 | n1 << 1 | bit | 0x80); }
            O0[node] += ((float)bit - O0[node]) * RT[O0n[node]]; if (O0n[node] < 1023) O0n[node]++;
            if (lb) { int q = (lb * 2 + (expected >> b & 1)) * 256 + node; MM[q] += ((float)bit - MM[q]) * RT[MMn[q]]; if (MMn[q] < 1023) MMn[q]++; }
            if (lb2) { int q = (lb2 * 2 + (expected2 >> b & 1)) * 256 + node; MM2[q] += ((float)bit - MM2[q]) * RT[MM2n[q]]; if (MM2n[q] < 1023) MM2n[q]++; }
            node = node * 2 + bit;
        }
        if (mode == 2) x[i] = (uint8_t)(node & 255);
        if (pattern_models) patterns.observe_byte(x.data(), i);
        if (skeleton_models) skeleton.observe_byte(x.data(), i);
        if (lstm) lstm->update(x[i], lstm->skip_matches && mlen >= 16 && expected == x[i]);
        if (mlen) { if (expected == x[i]) { mlen++; mptr++; } else mlen = 0; }
        if (mlen2) { if (expected2 == x[i]) { mlen2++; mptr2++; } else mlen2 = 0; }
        ind[hist & 0xFFFF] = (ind[hist & 0xFFFF] << 8 | x[i]) & 0xFFFF; ind1[hist & 0xFF] = (ind1[hist & 0xFF] << 8 | x[i]) & 0xFFFF;
        int ch = x[i]; bool letter = (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch >= 128;
        indw[word & 0xFFFFF] = (indw[word & 0xFFFFF] << 8 | x[i]) & 0xFFFF;
        if (letter) wcase = (wcase + (uint64_t)ch + 1) * 0x9E3779B1ull; else wcase = 0;
        if (letter) { word = (word + (uint64_t)(ch | 32) + 1) * 0x2F0F3A9Bull; if (curw.size() < 40) curw += (char)(ch | 32); }
        else if (word) { ppword = pword; pword = word; word = 0;
            std::string w = curw; for (const char* suf : {"ing", "ed", "es", "s", "ly", "er"}) { size_t L = std::strlen(suf); if (w.size() >= L + 3 && w.compare(w.size() - L, L, suf) == 0) { w.resize(w.size() - L); break; } }
            uint64_t hs = 0; for (char q : w) hs = (hs + (uint8_t)q + 1) * 0x100000001B3ull; pstem = hs; curw.clear(); }
        if (ch == '[' && i && x[i - 1] == '[') brk = 1; else if (ch == ']' && brk == 1) brk = 0; else if (ch == '{' && i && x[i - 1] == '{') brk = 2; else if (ch == '}' && brk == 2) brk = 0;
        else if (ch == '<') brk = 3; else if (ch == '>' && brk == 3) brk = 0; else if (ch == '\n') brk = 0;
        if (i && x[i - 1] == '\n') fmt = ch == '=' ? 1 : (ch == '*' || ch == '#') ? 2 : (ch == '|' || ch == '!') ? 3 : ch == ':' ? 6 : 0;
        if (ch == '\'' && i && x[i - 1] == '\'') fmt = fmt == 4 ? 0 : 4; if (ch == '&') fmt = 5; else if (ch == ';' && fmt == 5) fmt = 0; if (ch == '\n') fmt = 0;
        if (ch >= '0' && ch <= '9') { if (!ndig) numprev = i ? x[i - 1] : 0; ndig = std::min(ndig + 1, 15); } else ndig = 0;
    }
    if (mode == 1) { out.push_back((uint8_t)(x1 >> 24)); out.push_back(255); out.push_back(255); out.push_back(255); write_all(outp.c_str(), out); }
    if (prime_size) x.erase(x.begin(), x.begin() + prime_size);
    if (mode == 2) write_all(outp.c_str(), x);
    auto hsh = sha256(x.data(), x.size());
    std::printf("%12.0f bytes  %.4f bits/byte  [%.0fs]  cm3 BITS=%d (%.1f GB tables) LSTM=%d%s sha256 %02x%02x%02x%02x\n", mode == 1 ? (double)out.size() : bits / 8, bits / payload_size, now() - t0, BITS,
                tabgb, LN, mode == 1 ? " (real archive)" : mode == 2 ? " (decoded)" : "", hsh[0], hsh[1], hsh[2], hsh[3]);
    if (lstm && env("CM3_LSTM_STATS", "0") == "1") {
        std::fprintf(stderr, "LSTM updates: %ld/%zu windows\n", lstm->adam_t, n / lstm->T);
    }
    return 0;
}
