// Fixed grammar for F_k(a,d) = floor((a^4+d^4)/2^k).
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <gmpxx.h>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using U = uint64_t;
using Wide = __uint128_t;
constexpr unsigned book_bits = 16;
constexpr unsigned literals = 16;
constexpr unsigned small_width = 48;

struct Shape {
  U k, left, right;
};

Shape shape(U w) {
  U k = std::max<U>(4, (9 * w / 7) / 4 * 4);
  for (;; k += 4) {
    U p = (w + k + 3) / 4, s = (3 * p + 5) / 4;
    if (k >= 3 * s + 2)
      return {k, p, s + 1};
  }
}

const auto small_shapes = [] {
  std::array<Shape, small_width + 1> arr{};
  for (unsigned w = book_bits + 1; w <= small_width; ++w)
    arr[w] = shape(w);
  return arr;
}();

Wide fourth(U x) {
  Wide sq = Wide(x) * x;
  return sq * sq;
}

U root4(Wide x) {
  U a = static_cast<U>(std::sqrt(std::sqrt(static_cast<double>(x))));
  while (fourth(a) > x)
    --a;
  while (fourth(a + 1) <= x)
    ++a;
  return a;
}

std::pair<U, U> children(U x, U k) {
  Wide t = Wide(x) << k;
  U a = root4(t);
  Wide r = t - fourth(a);
  U d = root4(r);
  if (fourth(d) < r)
    ++d;
  return {a, d};
}

// A fixed, shared dictionary of actual fourth-power expressions. Its ordering
// within each bit length is by production, so an index need not equal its
// value.
struct Entry {
  unsigned k = 0, a = 0, d = 0, nodes = 0, depth = 0, value = 0;
};
struct Book {
  std::array<Entry, 65536> by_index{};
  std::array<unsigned, 65536> index{};
  Book() {
    std::vector<Entry> e(65536);
    for (unsigned x = 0; x < e.size(); ++x) {
      if (x < literals) {
        e[x].value = x;
        continue;
      }
      unsigned best = ~0u;
      auto consider = [&](unsigned k, U a, U d) {
        if (a >= x || d >= x)
          return;
        unsigned y = static_cast<unsigned>((fourth(a) + fourth(d)) >> k);
        if (y != x)
          return;
        unsigned nodes = 1 + e[a].nodes + e[d].nodes;
        if (nodes < best) {
          best = nodes;
          // Evaluate previously defined children, all the way to literals.
          e[x] = {k,
                  unsigned(a),
                  unsigned(d),
                  nodes,
                  1 + std::max(e[a].depth, e[d].depth),
                  unsigned((fourth(e[a].value) + fourth(e[d].value)) >> k)};
        }
      };
      for (unsigned k = 4; k <= 40; k += 4) {
        auto [a, d] = children(x, k);
        consider(k, a, d);
        if (x < 256) {
          Wide target = Wide(x) << k;
          for (U other = 0; other < std::min<U>(x, a); ++other) {
            Wide remainder = target - fourth(other);
            U next = root4(remainder);
            consider(k, other, next + (fourth(next) < remainder));
          }
        }
      }
      if (best == ~0u || e[x].value != x)
        throw std::logic_error("Missing dictionary expression");
    }
    std::vector<unsigned> ids(e.size());
    std::iota(ids.begin(), ids.end(), 0);
    for (unsigned begin = literals; begin < ids.size(); begin *= 2) {
      std::sort(ids.begin() + begin, ids.begin() + 2 * begin,
                [&](unsigned a, unsigned b) {
                  return std::tie(e[a].k, e[a].a, e[a].d) <
                         std::tie(e[b].k, e[b].a, e[b].d);
                });
    }
    for (unsigned i = 0; i < ids.size(); ++i) {
      index[ids[i]] = i;
      by_index[i] = e[ids[i]];
    }
  }
};

struct Stream {
  std::fstream file;
  U pending = 0;
  unsigned nbits = 0;
  explicit Stream(const char *path, bool writing)
      : file(path,
             std::ios::binary | (writing ? std::ios::out : std::ios::in)) {
    if (!file)
      throw std::runtime_error("Cannot open formula stream");
  }
  void put(unsigned x, unsigned w) {
    if (x >= (1u << w))
      throw std::logic_error("Index out of range");
    pending = (pending << w) + x;
    nbits += w;
    while (nbits >= 8) {
      nbits -= 8;
      file.put(char(pending >> nbits));
    }
    pending &= (U(1) << nbits) - 1;
  }
  unsigned get(unsigned w) {
    while (nbits < w) {
      int b = file.get();
      if (b == EOF)
        throw std::runtime_error("Truncated formula");
      pending = (pending << 8) + unsigned(b);
      nbits += 8;
    }
    nbits -= w;
    unsigned result = unsigned(pending >> nbits);
    pending &= (U(1) << nbits) - 1;
    return result;
  }
  void finish(bool writing) {
    if (writing) {
      if (nbits)
        file.put(char(pending << (8 - nbits)));
      file.flush();
      if (!file)
        throw std::runtime_error("Write failed");
    } else if (pending || file.peek() != EOF)
      throw std::runtime_error("Invalid trailing data");
  }
};

struct Formula {
  const Book &book;
  Stream &stream;
  U refs = 0, shared_ops = 0, outer_ops = 0, max_depth = 0;
  void account(unsigned id, U depth) {
    ++refs;
    const auto &e = book.by_index[id];
    shared_ops += e.nodes;
    max_depth = std::max(max_depth, depth + e.depth);
  }
  void encode_small(U x, U w, U depth) {
    if (w <= book_bits) {
      auto id = book.index.at(x);
      stream.put(id, w);
      account(id, depth);
      return;
    }
    ++outer_ops;
    auto s = small_shapes[w];
    auto [a, d] = children(x, s.k);
    encode_small(a, s.left, depth + 1);
    encode_small(d, s.right, depth + 1);
  }
  U decode_small(U w, U depth) {
    if (w <= book_bits) {
      auto id = stream.get(w);
      account(id, depth);
      return book.by_index[id].value;
    }
    ++outer_ops;
    auto s = small_shapes[w];
    U a = decode_small(s.left, depth + 1), d = decode_small(s.right, depth + 1);
    return U((fourth(a) + fourth(d)) >> s.k);
  }
  void encode(const mpz_class &x, U w, U depth) {
    if (w <= small_width) {
      encode_small(x.get_ui(), w, depth);
      return;
    }
    ++outer_ops;
    auto s = shape(w);
    mpz_class a, d;
    {
      mpz_class t = x << s.k, r;
      mpz_rootrem(a.get_mpz_t(), r.get_mpz_t(), t.get_mpz_t(), 4);
      if (!mpz_root(d.get_mpz_t(), r.get_mpz_t(), 4))
        ++d;
    }
    encode(a, s.left, depth + 1);
    encode(d, s.right, depth + 1);
  }
  mpz_class decode(U w, U depth) {
    if (w <= small_width)
      return mpz_class(decode_small(w, depth));
    ++outer_ops;
    auto s = shape(w);
    auto a = decode(s.left, depth + 1), d = decode(s.right, depth + 1);
    mpz_pow_ui(a.get_mpz_t(), a.get_mpz_t(), 4);
    mpz_pow_ui(d.get_mpz_t(), d.get_mpz_t(), 4);
    a += d;
    a >>= s.k;
    return a;
  }
};

mpz_class read_integer(const char *path) {
  std::ifstream f(path, std::ios::binary | std::ios::ate);
  if (!f)
    throw std::runtime_error("Cannot open input");
  auto size = f.tellg();
  std::vector<unsigned char> bytes(static_cast<size_t>(size));
  f.seekg(0);
  if (!f.read(reinterpret_cast<char *>(bytes.data()), size))
    throw std::runtime_error("Read error");
  mpz_class x;
  mpz_import(x.get_mpz_t(), bytes.size(), 1, 1, 1, 0, bytes.data());
  return x;
}
void write_integer(const char *path, const mpz_class &x) {
  std::vector<unsigned char> bytes((mpz_sizeinbase(x.get_mpz_t(), 2) + 7) / 8);
  size_t written = 0;
  mpz_export(bytes.data(), &written, 1, 1, 1, 0, x.get_mpz_t());
  std::ofstream out(path, std::ios::binary);
  if (!out.write(reinterpret_cast<const char *>(bytes.data()), written))
    throw std::runtime_error("Write error");
}
void print_expression(const Book &book, unsigned id) {
  const auto &e = book.by_index[id];
  if (!e.nodes) {
    std::cout << e.value;
    return;
  }
  std::cout << "[" << e.k << ",";
  print_expression(book, book.index[e.a]);
  std::cout << ",";
  print_expression(book, book.index[e.d]);
  std::cout << "]";
}

int main(int argc, char **argv) try {
  if (argc == 3 && std::string(argv[1]) == "expr") {
    static const Book book;
    unsigned long id = std::stoul(argv[2]);
    if (id >= book.by_index.size())
      throw std::runtime_error("Index out of range");
    print_expression(book, static_cast<unsigned>(id));
    std::cout << "\n";
    return 0;
  }
  if (argc != 5)
    throw std::runtime_error("encode|decode width input output");
  std::string mode = argv[1];
  bool writing = mode == "encode";
  if (!writing && mode != "decode")
    throw std::runtime_error("Unknown mode");
  if (std::filesystem::exists(argv[4]))
    throw std::runtime_error("Output already exists");
  U width = std::stoull(argv[2]);
  if (!width || width > 1000000000)
    throw std::runtime_error("Width out of range");
  static const Book book;
  Stream stream(writing ? argv[4] : argv[3], writing);
  Formula f{book, stream};
  if (writing) {
    auto x = read_integer(argv[3]);
    if (mpz_sizeinbase(x.get_mpz_t(), 2) > width)
      throw std::runtime_error("Input too wide");
    f.encode(x, width, 0);
    stream.finish(true);
  } else {
    auto x = f.decode(width, 0);
    stream.finish(false);
    write_integer(argv[4], x);
  }
  std::cout << "{\"references\":" << f.refs
            << ",\"dictionary_op_occurrences\":" << f.shared_ops
            << ",\"explicit_ops\":" << f.outer_ops
            << ",\"max_depth\":" << f.max_depth << "}\n";
  return 0;
} catch (const std::exception &e) {
  std::cerr << e.what() << "\n";
  return 1;
}
