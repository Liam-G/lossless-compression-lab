// The original lab/hutter/automa-8x8-passo-byte/scacchiera.cpp update.
// Row bytes increase downwards. Each phase reads only the opposite parity.
#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
using Word = uint64_t;
static_assert(std::endian::native == std::endian::little);
constexpr Word even = 0x55aa55aa55aa55aaULL;

static inline Word phase(Word s, Word mask) {
  const Word left =
      ((s >> 1) & 0x7f7f7f7f7f7f7f7fULL) | ((s & 0x0101010101010101ULL) << 7);
  const Word right =
      ((s << 1) & 0xfefefefefefefefeULL) | ((s >> 7) & 0x0101010101010101ULL);
  const Word vertical = std::rotl(s, 8) | std::rotr(s, 8);
  return s ^ (mask & ((left & right) ^ vertical));
}

static inline Word predecessor(Word x) { return phase(phase(x, ~even), even); }
static inline Word forward(Word x) { return phase(phase(x, even), ~even); }
static inline unsigned minority(Word x) {
  unsigned n = std::popcount(x);
  return std::min(n, 64 - n);
}

extern "C" void find_minimum(const Word *input, Word *seeds, uint16_t *times,
                             size_t size, unsigned limit) {
  for (size_t i = 0; i < size; ++i) {
    Word current = input[i], best = current;
    unsigned weight = minority(current), time = 0;
    for (unsigned t = 1; t <= limit; ++t) {
      current = predecessor(current);
      unsigned score = minority(current);
      if (score < weight) {
        weight = score;
        time = t;
        best = current;
      }
    }
    seeds[i] = best;
    times[i] = time;
  }
}

extern "C" void score_shared(const Word *samples, size_t n, uint32_t *scores,
                             unsigned limit) {
  for (size_t i = 0; i < n; ++i) {
    Word word = samples[i];
    for (unsigned j = 0; j <= limit; ++j) {
      scores[j] += minority(word);
      word = predecessor(word);
    }
  }
}

extern "C" void apply_orbit(Word *words, const uint16_t *times, size_t n,
                            unsigned common, bool inverse) {
  for (size_t i = 0; i < n; ++i) {
    Word word = words[i];
    unsigned steps = times ? times[i] : common;
    if (inverse)
      for (unsigned t = 0; t < steps; ++t)
        word = predecessor(word);
    else
      for (unsigned t = 0; t < steps; ++t)
        word = forward(word);
    words[i] = word;
  }
}
