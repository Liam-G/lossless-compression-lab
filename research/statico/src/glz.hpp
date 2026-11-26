// GLZ stream: the grammar is sent as a traversal of `main` where every symbol is defined inline at its
// first occurrence (pre-order). Events:
//   REF  : event = class c (0..31), then the symbol's index within class c (uniform).
//   NEW  : event = 32, then class (32-way), kind (byte|rule), then 8 bits (byte) or body length (rule)
//          followed by the body's symbols as further events.
// Class = floor(log2(uses)), capped at 31; uses counts every appearance including the definition.
// The decoder stores each defined symbol as (offset,len) into the output and copies on REF.
#pragma once
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <vector>
#include "grammar.hpp"
#include "rc.hpp"

namespace glz {
constexpr int NCLASS = 32, EV_NEW = 32;
inline int bitlen(uint64_t v) { int b = 0; while (v) { b++; v >>= 1; } return b; }
struct Models {
    AdaptiveModel event{NCLASS + 1}, cls{NCLASS}, kind{2}, lenb{40};
};
inline void put_bits(RangeEncoder& rc, uint64_t v, int n) { while (n > 0) { int k = std::min(n, 16); rc.bits((uint32_t)(v & ((1u << k) - 1)), k); v >>= k; n -= k; } }
inline uint64_t get_bits(RangeDecoder& rc, int n) { uint64_t v = 0; int sh = 0; while (n > 0) { int k = std::min(n, 16); v |= (uint64_t)rc.bits(k) << sh; sh += k; n -= k; } return v; }
}  // namespace glz

inline std::vector<uint8_t> glz_encode(const Grammar& g, size_t n_out) {
    using namespace glz;
    const size_t R = g.rules.size(), NS = 256 + R;
    std::vector<uint64_t> uses(NS, 0);
    for (uint32_t x : g.main) uses[x]++;
    for (auto& b : g.rules) for (uint32_t x : b) uses[x]++;
    auto cls_of = [&](uint32_t x) { return std::min(NCLASS - 1, bitlen(uses[x]) - 1); };

    RangeEncoder rc; Models m;
    put_bits(rc, g.main.size(), 48);
    (void)n_out;
    std::vector<uint8_t> defined(NS, 0);          // 0 never seen, 1 definition in progress, 2 defined
    std::vector<uint64_t> idx(NS, 0), class_size(NCLASS, 0);
    struct Frame { const std::vector<uint32_t>* seq; size_t i; int64_t rule; };
    std::vector<Frame> st = {{&g.main, 0, -1}};
    while (!st.empty()) {
        Frame& f = st.back();
        if (f.i == f.seq->size()) {
            if (f.rule >= 0) { uint32_t x = 256 + (uint32_t)f.rule; int c = cls_of(x); idx[x] = class_size[c]++; defined[x] = 2; }
            st.pop_back(); continue;
        }
        uint32_t x = (*f.seq)[f.i++];
        int c = cls_of(x);
        if (defined[x] == 2) {
            m.event.encode(rc, c);
            encode_uniform(rc, idx[x], class_size[c]);
        } else {
            if (defined[x] == 1) throw std::runtime_error("glz: cyclic grammar");
            m.event.encode(rc, EV_NEW);
            m.cls.encode(rc, c);
            m.kind.encode(rc, x >= 256);
            if (x < 256) { rc.bits(x, 8); idx[x] = class_size[c]++; defined[x] = 2; }
            else {
                const auto& body = g.rules[x - 256];
                uint64_t L1 = body.size() - 1;       // body length >= 2
                int b = bitlen(L1);
                m.lenb.encode(rc, b);
                put_bits(rc, L1, b - 1);              // top bit implied
                defined[x] = 1;
                st.push_back({&body, 0, (int64_t)(x - 256)});
            }
        }
    }
    return rc.finish();
}

inline bool glz_decode(const uint8_t* p, const uint8_t* end, uint8_t* out, size_t n_out) {
    using namespace glz;
    RangeDecoder rc(p, end); Models m;
    uint64_t main_len = get_bits(rc, 48);
    if (main_len > n_out) return false;
    std::vector<uint64_t> off, len;                    // by decoder id (definition order)
    std::vector<std::vector<uint32_t>> cl(NCLASS);    // class lists of decoder ids
    struct Frame { uint64_t remaining; int64_t start; int cls; };   // start < 0 for main
    std::vector<Frame> st = {{main_len, -1, 0}};
    size_t pos = 0;
    while (!st.empty()) {
        if (rc.overrun()) return false;
        Frame& f = st.back();
        if (f.remaining == 0) {
            if (f.start >= 0) {
                off.push_back((uint64_t)f.start); len.push_back(pos - (uint64_t)f.start);
                cl[f.cls].push_back((uint32_t)(off.size() - 1));
            }
            st.pop_back(); continue;
        }
        f.remaining--;
        int ev = m.event.decode(rc);
        if (ev != EV_NEW) {
            auto& list = cl[ev];
            if (list.empty()) return false;
            uint64_t k = decode_uniform(rc, list.size());
            if (k >= list.size()) return false;
            uint32_t id = list[k];
            if (len[id] > n_out - pos) return false;
            std::memcpy(out + pos, out + off[id], len[id]);
            pos += len[id];
        } else {
            int c = m.cls.decode(rc);
            int is_rule = m.kind.decode(rc);
            if (!is_rule) {
                if (pos >= n_out) return false;
                out[pos] = (uint8_t)rc.bits(8);
                off.push_back(pos); len.push_back(1); cl[c].push_back((uint32_t)(off.size() - 1));
                pos++;
            } else {
                int b = m.lenb.decode(rc);
                if (b < 1 || b > 39) return false;
                uint64_t L1 = (1ull << (b - 1)) | get_bits(rc, b - 1);
                if (L1 + 1 > n_out - pos || st.size() > n_out) return false;   // each body symbol emits >= 1 byte
                st.push_back({L1 + 1, (int64_t)pos, c});
            }
        }
    }
    return pos == n_out && !rc.overrun();
}
