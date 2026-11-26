// M0 baseline: adaptive order-0 byte coder.
#pragma once
#include "rc.hpp"

inline std::vector<uint8_t> order0_encode(const uint8_t* p, size_t n) {
    RangeEncoder rc; AdaptiveModel m(256);
    for (size_t i = 0; i < n; i++) m.encode(rc, p[i]);
    return rc.finish();
}

inline bool order0_decode(const uint8_t* p, const uint8_t* end, uint8_t* out, size_t n) {
    RangeDecoder rc(p, end); AdaptiveModel m(256);
    for (size_t i = 0; i < n; i++) out[i] = (uint8_t)m.decode(rc);
    return !rc.overrun();
}
