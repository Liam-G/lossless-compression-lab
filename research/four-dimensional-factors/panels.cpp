// Factor each 16-by-8 binary panel as two basis rows, their coordinates,
// and a byte-exact XOR residue. Equivalent bases reconstruct the same panel.
#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace {
using Basis = std::array<uint8_t, 2>;

struct Panel {
  uint8_t a, b;
  uint16_t ca = 0, cb = 0;
  std::array<uint8_t, 16> error{};
};

Panel approximate(const uint8_t *rows) {
  // Use the two most frequent distinct nonzero source rows. Stable ties
  // select the earliest row, and zero remains an implicit symbol.
  Basis basis{};
  for (unsigned k = 0; k < 2; ++k) {
    unsigned high = 0;
    for (unsigned i = 0; i < 16; ++i) {
      uint8_t value = rows[i];
      if (!value || value == basis[0])
        continue;
      unsigned count = std::count(rows + i, rows + 16, value);
      if (count > high) {
        high = count;
        basis[k] = value;
      }
    }
  }
  Panel p{basis[0], basis[1]};
  std::array<unsigned, 4> lookup = {0, p.a, p.b,
                                    static_cast<unsigned>(p.a ^ p.b)};
  for (unsigned i = 0; i < 16; ++i) {
    unsigned best = 0, distance = 9;
    for (unsigned k = 0; k < 4; ++k) {
      unsigned h = std::popcount(static_cast<unsigned>(rows[i]) ^ lookup[k]);
      if (h < distance) {
        distance = h;
        best = k;
      }
    }
    p.ca |= (best & 1) << i;
    p.cb |= (best >> 1) << i;
    p.error[i] = rows[i] ^ lookup[best];
  }
  return p;
}

void choose_equivalent(Panel &p, const Panel &prev) {
  std::array<uint8_t, 3> b = {p.a, p.b, static_cast<uint8_t>(p.a ^ p.b)};
  std::array<uint16_t, 3> c = {p.ca, p.cb, static_cast<uint16_t>(p.ca ^ p.cb)};
  constexpr unsigned forms[][4] = {{0, 1, 0, 1}, {1, 0, 1, 0}, {0, 2, 2, 1},
                                   {2, 0, 1, 2}, {1, 2, 2, 0}, {2, 1, 0, 2}};
  unsigned best = ~0u;
  for (const auto &f : forms) {
    unsigned score = 2 * std::popcount(unsigned(b[f[0]] ^ prev.a)) +
                     2 * std::popcount(unsigned(b[f[1]] ^ prev.b)) +
                     std::popcount(unsigned(c[f[2]] ^ prev.ca)) +
                     std::popcount(unsigned(c[f[3]] ^ prev.cb));
    if (score < best) {
      best = score;
      p.a = b[f[0]];
      p.b = b[f[1]];
      p.ca = c[f[2]];
      p.cb = c[f[3]];
    }
  }
}
} // namespace

extern "C" void factor_panels(const uint8_t *source, uint8_t *dst,
                              size_t panels, bool equiv) {
  Panel prev{};
  for (size_t i = 0; i < panels; ++i) {
    Panel p = approximate(source + 16 * i);
    if (equiv)
      choose_equivalent(p, prev);
    dst[i] = p.a;
    dst[panels + i] = p.b;
    dst[2 * panels + i] = uint8_t(p.ca);
    dst[3 * panels + i] = uint8_t(p.ca >> 8);
    dst[4 * panels + i] = uint8_t(p.cb);
    dst[5 * panels + i] = uint8_t(p.cb >> 8);
    std::memcpy(dst + 6 * panels + 16 * i, p.error.data(), 16);
    prev = p;
  }
}

extern "C" void restore_panels(const uint8_t *src, uint8_t *dst,
                               size_t panels) {
  for (size_t i = 0; i < panels; ++i) {
    uint16_t ca = src[2 * panels + i] | uint16_t(src[3 * panels + i]) << 8;
    uint16_t cb = src[4 * panels + i] | uint16_t(src[5 * panels + i]) << 8;
    for (unsigned r = 0; r < 16; ++r) {
      dst[16 * i + r] = src[6 * panels + 16 * i + r] ^
                        (ca >> r & 1 ? src[i] : 0) ^
                        (cb >> r & 1 ? src[panels + i] : 0);
    }
  }
}
