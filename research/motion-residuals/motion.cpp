#include <algorithm>
#include <climits>
#include <cstdint>
#include <cstdlib>

// Search whole-pixel translations on a sparse grid in each tile and refine the
// winner.
extern "C" void motion_vectors(const uint8_t *current, const uint8_t *previous,
                               int8_t *vectors, int width, int height,
                               int tile) {
  unsigned at = 0;
  for (int y = 0; y < height; y += tile)
    for (int x = 0; x < width; x += tile) {
      int h = std::min(height - y, tile), w = std::min(width - x, tile);
      int best = INT_MAX, bx = 0, by = 0;
      auto score = [&](int dx, int dy) {
        if (x + dx < 0 || y + dy < 0 || x + dx + w > width ||
            y + dy + h > height)
          return;
        int cost = 0;
        for (int j = 0; j < h; j += 3)
          for (int i = 0; i < w; i += 3) {
            auto p = (y + j) * width + x + i;
            cost +=
                std::abs(int(current[p]) - int(previous[p + dy * width + dx]));
          }
        // Prefer a short vector when several positions give the very same
        // predictions.
        cost = cost * 64 + std::abs(dx) + std::abs(dy);
        if (cost < best) {
          best = cost;
          bx = dx;
          by = dy;
        }
      };
      score(0, 0);
      for (int dy = -8; dy <= 8; dy += 4)
        for (int dx = -8; dx <= 8; dx += 4)
          score(dx, dy);
      for (int step : {2, 1}) {
        int cx = bx, cy = by;
        for (int dy = -step; dy <= step; dy += step)
          for (int dx = -step; dx <= step; dx += step)
            score(cx + dx, cy + dy);
      }
      vectors[at++] = int8_t(bx);
      vectors[at++] = int8_t(by);
    }
}

extern "C" int warp(const uint8_t *previous, const int8_t *vectors,
                    uint8_t *out, int width, int height, int tile) {
  unsigned at = 0;
  for (int y = 0; y < height; y += tile)
    for (int x = 0; x < width; x += tile) {
      int h = std::min(height - y, tile), w = std::min(width - x, tile);
      int dx = vectors[at++], dy = vectors[at++];
      if (x + dx < 0 || y + dy < 0 || x + dx + w > width || y + dy + h > height)
        return -1;
      for (int j = 0; j < h; ++j)
        std::copy_n(previous + (y + j + dy) * width + x + dx, w,
                    out + (y + j) * width + x);
    }
  return 0;
}

extern "C" void spatial(const uint8_t *src, uint8_t *dst, int w, int h,
                        int kind, bool inverse) {
  const uint8_t *history = inverse ? dst : src;
  for (int y = 0; y < h; ++y)
    for (int x = 0; x < w; ++x) {
      int i = y * w + x, left = x ? history[i - 1] : 0,
          top = y ? history[i - w] : 0,
          corner = x && y ? history[i - w - 1] : 0;
      int prediction =
          kind == 1 ? left
                    : std::clamp(left + top - corner, std::min(left, top),
                                 std::max(left, top));
      dst[i] = uint8_t(inverse ? int(src[i]) + prediction
                               : int(src[i]) - prediction);
    }
}
