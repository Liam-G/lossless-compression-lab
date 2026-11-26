// Range coder (LZMA-style carry handling) + small adaptive frequency model + exact uniform coding.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

struct RangeEncoder {
    uint64_t low = 0;
    uint32_t range = 0xFFFFFFFFu;
    uint8_t cache = 0;
    uint64_t cache_size = 1;
    std::vector<uint8_t> out;

    void shift_low() {
        if ((uint32_t)low < 0xFF000000u || (low >> 32) != 0) {
            uint8_t carry = (uint8_t)(low >> 32), temp = cache;
            do { out.push_back((uint8_t)(temp + carry)); temp = 0xFF; } while (--cache_size);
            cache = (uint8_t)(low >> 24);
        }
        cache_size++;
        low = (low & 0x00FFFFFFu) << 8;
    }
    // total must be <= 1<<16
    void encode(uint32_t start, uint32_t size, uint32_t total) {
        range /= total;
        low += (uint64_t)start * range;
        range *= size;
        while (range < (1u << 24)) { range <<= 8; shift_low(); }
    }
    void bits(uint32_t v, int n) { if (n) encode(v, 1, 1u << n); }   // n <= 16
    std::vector<uint8_t> finish() { for (int i = 0; i < 5; i++) shift_low(); return std::move(out); }
};

struct RangeDecoder {
    const uint8_t *p, *end;
    uint32_t range = 0xFFFFFFFFu, code = 0;
    uint64_t over = 0;
    RangeDecoder(const uint8_t* p_, const uint8_t* e_) : p(p_), end(e_) { for (int i = 0; i < 5; i++) code = (code << 8) | next(); }
    uint8_t next() { if (p < end) return *p++; over++; return 0; }
    uint32_t get_freq(uint32_t total) {
        range /= total;
        uint32_t v = code / range;
        return v < total ? v : total - 1;   // only clamps on corrupt input
    }
    void decode(uint32_t start, uint32_t size) {
        code -= start * range;
        range *= size;
        while (range < (1u << 24)) { code = (code << 8) | next(); range <<= 8; }
    }
    uint32_t bits(int n) { if (!n) return 0; uint32_t f = get_freq(1u << n); decode(f, 1); return f; }
    bool overrun() const { return over != 0; }
};

// Adaptive frequency model for small alphabets (linear cumulative search). Total stays <= limit <= 1<<16.
struct AdaptiveModel {
    std::vector<uint32_t> f;
    uint32_t total, inc, limit;
    explicit AdaptiveModel(int nsym, int inc_ = 24, uint32_t limit_ = 1u << 16)
        : f(nsym, 1), total(nsym), inc(inc_), limit(limit_) {}
    void update(int s) {
        f[s] += inc; total += inc;
        if (total > limit) { total = 0; for (auto& x : f) { x = (x + 1) / 2; total += x; } }
    }
    void encode(RangeEncoder& rc, int s) {
        uint32_t c = 0; for (int i = 0; i < s; i++) c += f[i];
        rc.encode(c, f[s], total); update(s);
    }
    int decode(RangeDecoder& rc) {
        uint32_t v = rc.get_freq(total), c = 0; int s = 0, n = (int)f.size();
        while (s < n - 1 && c + f[s] <= v) c += f[s++];
        rc.decode(c, f[s]); update(s); return s;
    }
    double cost_bits(int s) const { return std::log2((double)total / f[s]); }
};

// Exact uniform coding of v in [0,n), n up to 2^48, as 16-bit digits from high to low.
inline int uniform_digits(uint64_t m) { int d = 0; while (m) { d++; m >>= 16; } return d; }
inline void encode_uniform(RangeEncoder& rc, uint64_t v, uint64_t n) {
    if (n <= 1) return;
    uint64_t m = n - 1; bool tight = true;
    for (int i = uniform_digits(m) - 1; i >= 0; i--) {
        uint32_t md = (uint32_t)(m >> (16 * i)) & 0xFFFF, d = (uint32_t)(v >> (16 * i)) & 0xFFFF;
        uint32_t tot = tight ? md + 1 : 65536;
        rc.encode(d, 1, tot);
        tight = tight && d == md;
    }
}
inline uint64_t decode_uniform(RangeDecoder& rc, uint64_t n) {
    if (n <= 1) return 0;
    uint64_t m = n - 1, v = 0; bool tight = true;
    for (int i = uniform_digits(m) - 1; i >= 0; i--) {
        uint32_t md = (uint32_t)(m >> (16 * i)) & 0xFFFF;
        uint32_t tot = tight ? md + 1 : 65536;
        uint32_t d = rc.get_freq(tot); rc.decode(d, 1);
        v |= (uint64_t)d << (16 * i);
        tight = tight && d == md;
    }
    return v;
}
