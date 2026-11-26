// Archive header: "STC1", mode byte, varint original size, SHA-256 of original (omitted in STORED mode).
#pragma once
#include <array>
#include <cstdint>
#include <cstring>
#include <vector>

enum Mode : uint8_t { STORED = 0, ORDER0 = 1, GRAMMAR = 2 };

inline void put_varint(std::vector<uint8_t>& o, uint64_t v) {
    while (v >= 0x80) { o.push_back((uint8_t)(v | 0x80)); v >>= 7; }
    o.push_back((uint8_t)v);
}
inline bool get_varint(const uint8_t*& p, const uint8_t* end, uint64_t& v) {
    v = 0;
    for (int sh = 0; sh < 64; sh += 7) {
        if (p >= end) return false;
        uint8_t b = *p++; v |= (uint64_t)(b & 0x7F) << sh;
        if (!(b & 0x80)) return true;
    }
    return false;
}

struct Header { Mode mode; uint64_t size; std::array<uint8_t, 32> hash; };

inline std::vector<uint8_t> write_header(const Header& h) {
    std::vector<uint8_t> o = {'S', 'T', 'C', '1', (uint8_t)h.mode};
    put_varint(o, h.size);
    if (h.mode != STORED) o.insert(o.end(), h.hash.begin(), h.hash.end());
    return o;
}
inline bool read_header(const uint8_t*& p, const uint8_t* end, Header& h) {
    if (end - p < 5 || std::memcmp(p, "STC1", 4) != 0) return false;
    uint8_t m = p[4]; p += 5;
    if (m > GRAMMAR) return false;
    h.mode = (Mode)m;
    if (!get_varint(p, end, h.size)) return false;
    if (h.mode != STORED) {
        if (end - p < 32) return false;
        std::memcpy(h.hash.data(), p, 32); p += 32;
    }
    return true;
}
