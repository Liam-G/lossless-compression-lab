// In each half-step, only one parity changes. Both donors have the other
// parity, so the very same half-step undoes itself.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

using Byte = uint8_t;

template <bool nonlinear>
void horizontal(Byte *data, size_t rows, size_t width, size_t stride,
                unsigned parity, Byte *work) {
  Byte mask = parity ? 0x55 : 0xaa;
  for (size_t row = 0; row < rows; ++row) {
    Byte *p = data + row * stride;
    for (size_t i = 0; i < stride; ++i) {
      unsigned left = (p[i] >> 1) | (i ? p[i - 1] << 7 : 0);
      unsigned right = (p[i] << 1) | (i + 1 < stride ? p[i + 1] >> 7 : 0);
      work[i] = p[i] ^ (mask & (nonlinear ? left & right : left));
    }
    if (width % 8)
      work[stride - 1] &= 0xff << (8 - width % 8);
    std::memcpy(p, work, stride);
  }
}

template <bool nonlinear>
void planes(Byte *data, size_t groups, size_t count, size_t stride,
            unsigned parity) {
  // At coordinate zero the left donor is zero. For AND, the last
  // coordinate also has a zero donor at the open boundary.
  size_t stop = count - (nonlinear ? 1 : 0);
  for (size_t g = 0; g < groups; ++g) {
    Byte *base = data + g * count * stride;
    for (size_t n = parity ? 1 : 2; n < stop; n += 2) {
      Byte *dest = base + n * stride;
      const Byte *left = dest - stride;
      for (size_t i = 0; i < stride; ++i) {
        if constexpr (nonlinear)
          dest[i] ^= left[i] & dest[stride + i];
        else
          dest[i] ^= left[i];
      }
    }
  }
}

extern "C" int evolve(Byte *data, size_t depth, size_t height, size_t width,
                      unsigned rule, unsigned inverse) {
  if (!depth || !height || !width || rule > 2 || inverse > 1)
    return 1;
  try {
    size_t stride = (width + 7) / 8;
    std::vector<Byte> work(stride);
    for (int i = 0; i < 6; ++i) {
      int half = inverse ? 5 - i : i;
      int axis = half / 2, parity = half % 2;
      if (rule == 2 && axis != 1)
        continue;
      bool nonlinear = rule == 1;
      if (axis == 0) {
        if (nonlinear)
          horizontal<true>(data, depth * height, width, stride, parity,
                           work.data());
        else
          horizontal<false>(data, depth * height, width, stride, parity,
                            work.data());
      } else {
        size_t groups = axis == 1 ? depth : 1;
        size_t count = axis == 1 ? height : depth;
        size_t slab = axis == 1 ? stride : height * stride;
        if (nonlinear)
          planes<true>(data, groups, count, slab, parity);
        else
          planes<false>(data, groups, count, slab, parity);
      }
    }
    return 0;
  } catch (...) {
    return 1;
  }
}
