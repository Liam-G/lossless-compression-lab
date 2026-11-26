// Raster bit contexts from the shape search with the Statico range coder.
#include "../statico/src/rc.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using Bytes = std::vector<uint8_t>;
using Counts = std::array<std::array<uint16_t, 2>, 1024>;

static unsigned bit(const Bytes &data, size_t i) {
  return (data[i / 8] >> (7 - i % 8)) & 1;
}

static unsigned context(const Bytes &data, size_t i, unsigned w,
                        unsigned model) {
  unsigned prev = i ? bit(data, i - 1) : 0;
  unsigned prev2 = i > 1 ? bit(data, i - 2) : 0;
  if (model == 0)
    return 2 * prev + prev2;
  unsigned col = i % w;
  auto above = [&](int shift, unsigned rows = 1) -> unsigned {
    int x = static_cast<int>(col) + shift;
    if (x < 0 || x >= static_cast<int>(w) || i < rows * w)
      return 0;
    return bit(data, i - rows * w + shift);
  };
  if (model == 1)
    return 8 * above(1) + 4 * prev + 2 * above(2) + above(0, 2);
  unsigned ctx = 2 * prev + prev2;
  for (int x = -2; x <= 2; ++x)
    ctx = 2 * ctx + above(x);
  return 2 * ctx + above(0, 2);
}

static void update(std::array<uint16_t, 2> &pair, unsigned b) {
  pair[b] += 2;
  if (pair[0] + pair[1] >= 32768) {
    for (auto &v : pair)
      v = (v + 1) / 2;
  }
}

static Bytes encode(const Bytes &raw, unsigned width, unsigned model) {
  RangeEncoder coder;
  Counts counts;
  counts.fill({1, 1});
  for (size_t i = 0; i < raw.size() * 8; ++i) {
    auto &f = counts[context(raw, i, width, model)];
    unsigned b = bit(raw, i);
    coder.encode(b ? f[0] : 0, f[b], f[0] + f[1]);
    update(f, b);
  }
  return coder.finish();
}

static Bytes decode(const Bytes &packed, size_t size, unsigned width,
                    unsigned model) {
  RangeDecoder coder(packed.data(), packed.data() + packed.size());
  Counts counts;
  counts.fill({1, 1});
  Bytes out(size);
  for (size_t i = 0; i < size * 8; ++i) {
    auto &f = counts[context(out, i, width, model)];
    unsigned b = coder.get_freq(f[0] + f[1]) >= f[0];
    coder.decode(b ? f[0] : 0, f[b]);
    out[i / 8] |= b << (7 - i % 8);
    update(f, b);
  }
  if (coder.overrun() || coder.p != coder.end)
    throw std::runtime_error("Invalid range stream");
  return out;
}

// Rank candidate raster widths by empirical conditional entropy on dispersed
// bits.
static std::vector<unsigned> widths(const Bytes &raw) {
  std::vector<unsigned> out = {1728, 1729};
  size_t end = raw.size() * 8;
  unsigned maxw = std::min<size_t>(2048, end / 8);
  if (!maxw)
    return out;
  std::vector<std::pair<double, unsigned>> scores;
  const size_t stride = std::max<size_t>(1, (end - maxw - 2) / 4096);
  for (unsigned w = 2; w <= maxw; ++w) {
    unsigned hist[8][2] = {};
    for (size_t i = maxw + 2; i < end; i += stride) {
      size_t p = i - w;
      unsigned ctx = 4 * bit(raw, p - 1) + 2 * bit(raw, p) + bit(raw, p + 1);
      hist[ctx][bit(raw, i)]++;
    }
    double score = 0;
    for (auto &c : hist)
      for (unsigned n : c)
        if (n)
          score += n * std::log2(double(c[0] + c[1]) / n);
    scores.emplace_back(score, w);
  }
  std::sort(scores.begin(), scores.end());
  for (auto [score, w] : scores) {
    if (std::find(out.begin(), out.end(), w) == out.end())
      out.push_back(w);
    if (out.size() == 5)
      break;
  }
  return out;
}

static void put(Bytes &out, uint64_t value, int n) {
  for (int i = n - 1; i >= 0; --i)
    out.push_back(value >> (8 * i));
}

static Bytes pack(const Bytes &raw, bool spatial) {
  Bytes best = raw;
  unsigned best_model = 255, best_width = 1;
  auto consider = [&](unsigned w, unsigned model) {
    Bytes payload = encode(raw, w, model);
    if (payload.size() < best.size()) {
      best = std::move(payload);
      best_width = w;
      best_model = model;
    }
  };
  consider(1, 0);
  if (spatial)
    for (auto w : widths(raw))
      for (unsigned m : {1, 2})
        consider(w, m);
  Bytes out = {'S', 'C', 'X', '1'};
  put(out, raw.size(), 8);
  put(out, best_width, 2);
  put(out, best_model, 1);
  out.insert(out.end(), best.begin(), best.end());
  return out;
}

static Bytes unpack(const Bytes &arc) {
  if (arc.size() < 15 || std::string(arc.begin(), arc.begin() + 4) != "SCX1")
    throw std::runtime_error("Invalid shape archive");
  uint64_t size = 0;
  for (int i = 4; i < 12; ++i)
    size = size * 256 + arc[i];
  unsigned w = 256 * arc[12] + arc[13], model = arc[14];
  if (!w || size > std::numeric_limits<size_t>::max() / 8)
    throw std::runtime_error("Invalid size");
  Bytes body(arc.begin() + 15, arc.end());
  if (model == 255 && body.size() == size)
    return body;
  if (model > 2 || body.size() < 5)
    throw std::runtime_error("Invalid shape model");
  return decode(body, size, w, model);
}

int main(int argc, char **argv) try {
  if (argc != 4)
    throw std::runtime_error("encode|history|decode INPUT NEW_OUTPUT");
  std::ifstream in(argv[2], std::ios::binary);
  if (!in || std::filesystem::exists(argv[3]))
    throw std::runtime_error("Check input and new output paths");
  Bytes data((std::istreambuf_iterator<char>(in)), {});
  std::string op = argv[1];
  if (op == "decode")
    data = unpack(data);
  else if (op == "encode" || op == "history")
    data = pack(data, op == "encode");
  else
    throw std::runtime_error("Unknown command");
  std::ofstream out(argv[3], std::ios::binary);
  out.write(reinterpret_cast<const char *>(data.data()), data.size());
  if (!out)
    throw std::runtime_error("Write failed");
  return 0;
} catch (const std::exception &e) {
  std::cerr << e.what() << "\n";
  return 1;
}
