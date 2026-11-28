// Arena reshapes (lab): reversible byte transforms.  usage: view enc|dec NAME[:PARAM] IN OUT
// NAME: bwt mtf delta xorprev reverse bitplanes base2 base3 base4 transpose:W
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "../statico/src/io.hpp"
#include "../statico/third_party/libsais/libsais.h"
using B = std::vector<uint8_t>;

static void put64(B& o, uint64_t v) { for (int i = 0; i < 8; i++) o.push_back((uint8_t)(v >> (8 * i))); }
static uint64_t get64(const B& b) { uint64_t v = 0; for (int i = 0; i < 8; i++) v |= (uint64_t)b[i] << (8 * i); return v; }

static B bwt_enc(const B& in) {
    int32_t n = (int32_t)in.size(); B o; std::vector<int32_t> A(n + 1); B U(n);
    int32_t pi = n ? libsais_bwt(in.data(), U.data(), A.data(), n, 0, nullptr) : 0;
    put64(o, (uint64_t)pi); o.insert(o.end(), U.begin(), U.end()); return o;
}
static B bwt_dec(const B& in) {
    int32_t pi = (int32_t)get64(in); int32_t n = (int32_t)in.size() - 8; B U(n); std::vector<int32_t> A(n + 1);
    if (n) libsais_unbwt(in.data() + 8, U.data(), A.data(), n, nullptr, pi); return U;
}
static B mtf(const B& in, bool enc) {
    uint8_t t[256]; for (int i = 0; i < 256; i++) t[i] = (uint8_t)i; B o(in.size());
    for (size_t i = 0; i < in.size(); i++) {
        int r; uint8_t c;
        if (enc) { c = in[i]; r = 0; while (t[r] != c) r++; o[i] = (uint8_t)r; }
        else { r = in[i]; c = t[r]; o[i] = c; }
        std::memmove(t + 1, t, r); t[0] = c;
    }
    return o;
}
static B delta(const B& in, bool enc, bool use_xor) {
    B o(in.size()); uint8_t prev = 0;
    for (size_t i = 0; i < in.size(); i++) {
        if (enc) { o[i] = use_xor ? in[i] ^ prev : (uint8_t)(in[i] - prev); prev = in[i]; }
        else { o[i] = use_xor ? in[i] ^ prev : (uint8_t)(in[i] + prev); prev = o[i]; }
    }
    return o;
}
static B bitplanes(const B& in, bool enc) {
    if (enc) {
        size_t n = in.size(), m = (n + 7) / 8; B o; put64(o, n); o.resize(8 + 8 * m, 0);
        for (int k = 0; k < 8; k++) for (size_t i = 0; i < n; i++) if (in[i] >> k & 1) o[8 + k * m + i / 8] |= (uint8_t)(1 << (i % 8));
        return o;
    }
    size_t n = get64(in), m = (n + 7) / 8; B o(n, 0);
    for (int k = 0; k < 8; k++) for (size_t i = 0; i < n; i++) if (in[8 + k * m + i / 8] >> (i % 8) & 1) o[i] |= (uint8_t)(1 << k);
    return o;
}
static B base(const B& in, bool enc, int b) {
    int d = b == 2 ? 8 : b == 3 ? 6 : 4; B o;
    if (enc) { o.reserve(in.size() * d); for (uint8_t x : in) { int v = x; uint8_t dig[8]; for (int j = d - 1; j >= 0; j--) { dig[j] = (uint8_t)(v % b); v /= b; } o.insert(o.end(), dig, dig + d); } }
    else { for (size_t i = 0; i + d <= in.size(); i += d) { int v = 0; for (int j = 0; j < d; j++) v = v * b + in[i + j]; o.push_back((uint8_t)v); } }
    return o;
}
static B transpose(const B& in, bool enc, size_t W) {
    if (enc) {
        size_t n = in.size(), R = n / W; B o; put64(o, n);
        for (size_t c = 0; c < W; c++) for (size_t r = 0; r < R; r++) o.push_back(in[r * W + c]);
        o.insert(o.end(), in.begin() + R * W, in.end()); return o;
    }
    size_t n = get64(in), R = n / W; B o(n);
    size_t p = 8; for (size_t c = 0; c < W; c++) for (size_t r = 0; r < R; r++) o[r * W + c] = in[p++];
    std::memcpy(o.data() + R * W, in.data() + p, n - R * W); return o;
}

int main(int argc, char** argv) {
    if (argc != 5) { std::fprintf(stderr, "usage: view enc|dec NAME[:PARAM] IN OUT\n"); return 1; }
    bool enc = std::string(argv[1]) == "enc"; std::string name = argv[2], prm;
    if (auto c = name.find(':'); c != std::string::npos) { prm = name.substr(c + 1); name = name.substr(0, c); }
    B in, o; if (!read_all(argv[3], in)) return 1;
    if (name == "bwt") o = enc ? bwt_enc(in) : bwt_dec(in);
    else if (name == "mtf") o = mtf(in, enc);
    else if (name == "delta") o = delta(in, enc, false);
    else if (name == "xorprev") o = delta(in, enc, true);
    else if (name == "reverse") o.assign(in.rbegin(), in.rend());
    else if (name == "bitplanes") o = bitplanes(in, enc);
    else if (name == "base2") o = base(in, enc, 2);
    else if (name == "base3") o = base(in, enc, 3);
    else if (name == "base4") o = base(in, enc, 4);
    else if (name == "transpose") o = transpose(in, enc, std::stoul(prm));
    else { std::fprintf(stderr, "unknown view %s\n", name.c_str()); return 1; }
    return write_all(argv[4], o) ? 0 : 1;
}
