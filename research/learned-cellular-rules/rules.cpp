// Learn a binary transition table for each bit plane from sampled training
// cells.
#include <array>
#include <cstddef>
#include <cstdint>

static unsigned address(const std::array<unsigned, 5> &neighbors,
                        unsigned bit) {
  unsigned key = 0;
  for (unsigned i = 0; i < neighbors.size(); ++i)
    key |= ((neighbors[i] >> bit) & 1U) << i;
  return key;
}

static std::array<unsigned, 5> neighbors(const uint8_t *prev, int x, int y,
                                         int w, int h) {
  const auto p = static_cast<std::size_t>(y) * w + x;
  return {prev[p], x ? prev[p - 1] : 0U, x + 1 < w ? prev[p + 1] : 0U,
          y ? prev[p - w] : 0U, y + 1 < h ? prev[p + w] : 0U};
}

extern "C" void fit(const uint8_t *input, uint32_t *rules, int w, int h,
                    int frames, bool second) {
  uint32_t ones[8][32]{}, total[8][32]{};
  const auto area = static_cast<std::size_t>(w) * h;
  for (int t = 1; t < frames; ++t) {
    const auto *prev = input + (t - 1) * area;
    for (int y = t % 3; y < h; y += 3)
      for (int x = (t + y) % 5; x < w; x += 5) {
        auto p = static_cast<std::size_t>(y) * w + x;
        auto local = neighbors(prev, x, y, w, h);
        auto target = input[t * area + p] ^
                      (second && t > 1 ? input[(t - 2) * area + p] : 0);
        for (unsigned bit = 0; bit < 8; ++bit) {
          auto k = address(local, bit);
          ones[bit][k] += (target >> bit) & 1U;
          ++total[bit][k];
        }
      }
  }
  for (unsigned bit = 0; bit < 8; ++bit) {
    rules[bit] = 0;
    for (unsigned k = 0; k < 32; ++k) {
      auto twice = 2 * ones[bit][k];
      if (twice > total[bit][k] || (twice == total[bit][k] && (k & 1)))
        rules[bit] |= uint32_t{1} << k;
    }
  }
}

extern "C" void translate(const uint8_t *input, uint8_t *output,
                          const uint32_t *rules, int w, int h, int frames,
                          bool second, bool reverse) {
  const auto area = static_cast<std::size_t>(w) * h;
  if (!frames)
    return;
  for (std::size_t p = 0; p < area; ++p)
    output[p] = input[p];
  const uint8_t *history = reverse ? output : input;
  for (int t = 1; t < frames; ++t) {
    auto *prev = history + (t - 1) * area;
    for (int y = 0; y < h; ++y)
      for (int x = 0; x < w; ++x) {
        auto p = static_cast<std::size_t>(y) * w + x;
        auto near = neighbors(prev, x, y, w, h);
        unsigned predicted = 0;
        for (unsigned bit = 0; bit < 8; ++bit)
          predicted |= ((rules[bit] >> address(near, bit)) & 1U) << bit;
        if (second && t > 1)
          predicted ^= history[(t - 2) * area + p];
        output[t * area + p] = input[t * area + p] ^ predicted;
      }
  }
}
