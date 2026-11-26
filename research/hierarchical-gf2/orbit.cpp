// Predecessor search. The Python decoder implements the forward rule.
#include <algorithm>
#include <cstdint>

struct State {
    uint16_t rows[16];
    uint16_t weight, rank;
};

static int rank_of(const uint16_t* rows, int h) {
    uint16_t basis[16]{};
    int rank = 0;
    for (int y = 0; y < h; ++y) {
        unsigned x = rows[y];
        while (x) {
            int pivot = 31 - __builtin_clz(x);
            if (!basis[pivot]) {
                basis[pivot] = x;
                ++rank;
                break;
            }
            x ^= basis[pivot];
        }
    }
    return rank;
}

// Even axes wrap. Odd axes have zero boundaries.
// Both choices keep every updated neighbor on the opposite parity.
extern "C" int orbit(const uint16_t* input, int h, int w, int limit, bool ranks,
                     State* out) {
    uint16_t rows[16]{};
    std::copy_n(input, h, rows);
    const unsigned mask = (1u << w) - 1;
    for (int t = 0;; ++t) {
        auto& state = out[t];
        std::copy_n(rows, h, state.rows);
        state.weight = 0;
        for (int y = 0; y < h; ++y) state.weight += __builtin_popcount(rows[y]);
        state.rank = ranks ? rank_of(rows, h) : 0;
        if (t == limit) return t + 1;
        for (int phase : {1, 0}) {
            for (int y = 0; y < h; ++y) {
                unsigned x = rows[y], left = x << 1, right = x >> 1;
                if (w % 2 == 0) {
                    left |= x >> (w - 1);
                    right |= (x & 1) << (w - 1);
                }
                unsigned up = y ? rows[y-1] : (h % 2 ? 0 : rows[h-1]);
                unsigned down = y+1 < h ? rows[y+1] : (h % 2 ? 0 : rows[0]);
                unsigned color = (phase ^ (y & 1)) ? 0xaaaa : 0x5555;
                rows[y] ^= ((left & right) ^ (up | down)) & color & mask;
            }
        }
        if (std::equal(rows, rows+h, input)) return t + 1;
    }
}
