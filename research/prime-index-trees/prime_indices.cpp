#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "../statico/src/rc.hpp"

namespace {

constexpr unsigned limit = 1 << 24;
constexpr unsigned block_size = 6;
constexpr std::array<std::array<unsigned, 4>, 5> shapes{{
    {3, 3, 0, 0},
    {2, 2, 2, 0},
    {1, 2, 2, 1},
    {1, 2, 3, 0},
    {3, 2, 1, 0},
}};
enum Mode { fixed, tree, sums, explore };

class Primes {
public:
  Primes() : rank(limit) {
    std::vector<bool> sieve(limit, true);
    sieve[0] = sieve[1] = false;
    for (unsigned p = 2; p * p < limit; ++p)
      if (sieve[p])
        for (unsigned n = p * p; n < limit; n += p)
          sieve[n] = false;
    plain.reserve(limit);
    for (unsigned n = 0; n < limit; ++n) {
      rank[n] = unsigned(primes.size());
      if (sieve[n])
        primes.push_back(n);
      else
        plain.push_back(n);
    }
  }

  unsigned below(unsigned n) const {
    return n == limit ? primes.size() : rank.at(n);
  }
  bool is_prime(unsigned n) const { return below(n + 1) != below(n); }
  unsigned index(unsigned n, bool prime) const {
    return prime ? below(n) : n - below(n);
  }
  unsigned value(unsigned i, bool prime) const {
    return (prime ? primes : plain).at(i);
  }

private:
  std::vector<unsigned> rank, primes, plain;
};

unsigned from_bytes(const uint8_t *data, unsigned width) {
  unsigned result = 0;
  for (unsigned i = 0; i < width; ++i)
    result = (result << 8) | data[i];
  return result;
}

void to_bytes(unsigned value, uint8_t *data, unsigned width) {
  for (unsigned i = width; i; --i) {
    data[i - 1] = value;
    value >>= 8;
  }
  if (value)
    throw std::runtime_error("value exceeds leaf width");
}

struct Leaf {
  unsigned rank;
  bool prime;
};

struct Model {
  explicit Model(const Primes &primes)
      : primes(primes),
        kinds{AdaptiveModel(2), AdaptiveModel(2), AdaptiveModel(2)} {
    for (unsigned w = 1; w <= 3; ++w) {
      const auto n = 1u << (8 * w);
      counts[w - 1] = {n - primes.below(n), primes.below(n)};
      prices[w - 1] = {std::log2(counts[w - 1][0]),
                       std::log2(counts[w - 1][1])};
    }
  }

  double price(unsigned w, Leaf l) const {
    return prices[w - 1][l.prime] + kinds[w - 1].cost_bits(l.prime);
  }
  Leaf leaf(unsigned n) const {
    const bool prime = primes.is_prime(n);
    return {primes.index(n, prime), prime};
  }
  void encode(unsigned w, Leaf l, RangeEncoder &metadata,
              RangeEncoder &payload) {
    kinds[w - 1].encode(metadata, l.prime);
    encode_uniform(payload, l.rank, counts[w - 1][l.prime]);
    ++leaves;
    prime_leaves += l.prime;
  }
  unsigned decode(unsigned w, RangeDecoder &metadata, RangeDecoder &payload) {
    const bool prime = kinds[w - 1].decode(metadata);
    return primes.value(decode_uniform(payload, counts[w - 1][prime]), prime);
  }

  const Primes &primes;
  std::array<AdaptiveModel, 3> kinds;
  std::array<std::array<unsigned, 2>, 3> counts;
  std::array<std::array<double, 2>, 3> prices;
  AdaptiveModel splits{int(shapes.size()), 8};
  std::array<uint64_t, shapes.size()> uses{};
  uint64_t leaves = 0, prime_leaves = 0;
};

std::array<unsigned, 4> tail_shape(unsigned width) {
  return width <= 3 ? std::array<unsigned, 4>{width, 0, 0, 0}
                    : std::array<unsigned, 4>{3, width - 3, 0, 0};
}

void encode_block(const uint8_t *bytes, unsigned size, Mode mode, Model &model,
                  RangeEncoder &metadata, RangeEncoder &payload) {
  std::array<std::array<Leaf, 4>, block_size> fields{};
  for (unsigned start = 0; start < size; ++start)
    for (unsigned w = 1; w <= 3 && start + w <= size; ++w)
      fields[start][w] = model.leaf(from_bytes(bytes + start, w));

  auto shape = size == block_size ? shapes[0] : tail_shape(size);
  if ((mode == tree || mode == explore) && size == block_size) {
    unsigned best = 0;
    double best_bits = 1e100;
    for (unsigned i = 0; i < shapes.size(); ++i) {
      double bits = mode == tree ? model.splits.cost_bits(i) : 0;
      unsigned start = 0;
      for (auto w : shapes[i]) {
        if (!w)
          break;
        bits += model.price(w, fields[start][w]);
        start += w;
      }
      if (bits < best_bits) {
        best = i;
        best_bits = bits;
      }
    }
    model.splits.encode(metadata, best);
    ++model.uses[best];
    shape = shapes[best];
  }
  unsigned start = 0;
  for (auto w : shape) {
    if (!w)
      break;
    model.encode(w, fields[start][w], metadata, payload);
    start += w;
  }
}

void decode_block(uint8_t *bytes, unsigned size, Mode mode, Model &model,
                  RangeDecoder &metadata, RangeDecoder &payload) {
  const auto shape =
      size != block_size
          ? tail_shape(size)
          : shapes[mode == fixed ? 0 : model.splits.decode(metadata)];
  unsigned start = 0;
  for (auto w : shape) {
    if (!w)
      break;
    to_bytes(model.decode(w, metadata, payload), bytes + start, w);
    start += w;
  }
}

struct Pairs {
  explicit Pairs(const Primes &primes)
      : primes(primes), left(1u << 16), right(1u << 16), first(256, 6) {
    for (unsigned x = 0; x < left.size(); ++x) {
      const unsigned even = 2 * x + 4;
      unsigned i = 0;
      for (; i < 256; ++i) {
        const unsigned p = primes.value(i, true);
        if (p > even / 2)
          break;
        if (primes.is_prime(even - p)) {
          left[x] = i;
          right[x] = primes.index(even - p, true);
          max_left = std::max(max_left, p);
          break;
        }
      }
      if (primes.value(left[x], true) + primes.value(right[x], true) != even)
        throw std::runtime_error("incomplete sum table");
    }
  }

  unsigned bound(unsigned w) const {
    return primes.below(2 * (1u << (8 * w)) + 3);
  }
  void encode(unsigned x, unsigned w, RangeEncoder &stream) {
    first.encode(stream, left[x]);
    encode_uniform(stream, right[x], bound(w));
  }
  unsigned decode(unsigned w, RangeDecoder &stream) {
    const auto p = primes.value(first.decode(stream), true);
    const auto q = primes.value(decode_uniform(stream, bound(w)), true);
    if ((p + q) & 1)
      throw std::runtime_error("invalid sum parity");
    return (p + q - 4) / 2;
  }

  const Primes &primes;
  std::vector<unsigned> left, right;
  AdaptiveModel first;
  unsigned max_left = 0;
};

void put_number(std::ostream &out, uint64_t n) {
  for (unsigned i = 0; i < 8; ++i)
    out.put(char(n >> (8 * i)));
}

uint64_t get_number(std::istream &in) {
  uint64_t n = 0;
  for (unsigned i = 0; i < 8; ++i) {
    const int byte = in.get();
    if (byte < 0)
      throw std::runtime_error("truncated header");
    n |= uint64_t(byte) << (8 * i);
  }
  return n;
}

void pack(const char *input, const char *output, Mode mode) {
  const auto size = std::filesystem::file_size(input);
  const Primes primes;
  Model model(primes);
  RangeEncoder metadata, payload;
  std::ifstream source(input, std::ios::binary);
  std::ofstream target(output, std::ios::binary);
  if (!source || !target)
    throw std::runtime_error("cannot open input or output");
  const unsigned width = mode == sums ? 2 : block_size;
  uint8_t bytes[block_size];
  Pairs pairs(primes);
  for (uint64_t left = size; left;) {
    const auto take = unsigned(std::min<uint64_t>(left, width));
    if (!source.read(reinterpret_cast<char *>(bytes), take))
      throw std::runtime_error("short input");
    if (mode == sums)
      pairs.encode(from_bytes(bytes, take), take, payload);
    else
      encode_block(bytes, take, mode, model, metadata, payload);
    left -= take;
  }
  const auto tags = metadata.finish(), indices = payload.finish();
  target.write("QPI1", 4);
  target.put(char(mode));
  put_number(target, size);
  put_number(target, tags.size());
  target.write(reinterpret_cast<const char *>(tags.data()), tags.size());
  target.write(reinterpret_cast<const char *>(indices.data()), indices.size());
  if (!target)
    throw std::runtime_error("write failed");
  std::cout << "input_bytes " << size << "\nmetadata_bytes " << tags.size()
            << "\npayload_bytes " << indices.size() << "\narchive_bytes "
            << target.tellp() << '\n';
  if (mode == sums)
    std::cout << "max_small_prime " << pairs.max_left << '\n';
  else
    std::cout << "prime_leaves " << model.prime_leaves << "\nall_leaves "
              << model.leaves << '\n';
  if (mode == tree || mode == explore) {
    std::cout << "shape_counts";
    for (auto used : model.uses)
      std::cout << ' ' << used;
    std::cout << '\n';
  }
}

void unpack(const char *input, const char *output) {
  const auto size = std::filesystem::file_size(input);
  std::ifstream source(input, std::ios::binary);
  char magic[4];
  if (!source.read(magic, 4) || std::string_view(magic, 4) != "QPI1")
    throw std::runtime_error("invalid archive");
  const int id = source.get();
  if (id < fixed || id > explore)
    throw std::runtime_error("invalid mode");
  const auto mode = Mode(id);
  const auto restored = get_number(source), tag_size = get_number(source);
  if (size < 31 || tag_size < 5 || tag_size > size - 26)
    throw std::runtime_error("invalid stream lengths");
  std::vector<uint8_t> data(size - 21);
  if (!source.read(reinterpret_cast<char *>(data.data()), data.size()))
    throw std::runtime_error("truncated archive");
  RangeDecoder metadata(data.data(), data.data() + tag_size);
  RangeDecoder payload(data.data() + tag_size, data.data() + data.size());
  const Primes primes;
  Model model(primes);
  Pairs pairs(primes);
  std::ofstream target(output, std::ios::binary);
  if (!target)
    throw std::runtime_error("cannot open output");
  const unsigned width = mode == sums ? 2 : block_size;
  uint8_t bytes[block_size];
  for (uint64_t left = restored; left;) {
    const auto take = unsigned(std::min<uint64_t>(left, width));
    if (mode == sums)
      to_bytes(pairs.decode(take, payload), bytes, take);
    else
      decode_block(bytes, take, mode, model, metadata, payload);
    if (!target.write(reinterpret_cast<const char *>(bytes), take))
      throw std::runtime_error("write failed");
    left -= take;
  }
  if (metadata.overrun() || payload.overrun() || metadata.p != metadata.end ||
      payload.p != payload.end)
    throw std::runtime_error("wrong stream lengths after decoding");
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "prime-indices fixed|tree|explore|sums|decode input output\n";
    return 2;
  }
  try {
    const std::string_view command(argv[1]);
    if (std::filesystem::exists(argv[3]))
      throw std::runtime_error("output already exists");
    if (command == "decode")
      unpack(argv[2], argv[3]);
    else if (command == "fixed")
      pack(argv[2], argv[3], fixed);
    else if (command == "tree")
      pack(argv[2], argv[3], tree);
    else if (command == "explore")
      pack(argv[2], argv[3], explore);
    else if (command == "sums")
      pack(argv[2], argv[3], sums);
    else
      return 2;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
