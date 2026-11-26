#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include <gmpxx.h>

#include "../statico/src/rc.hpp"

using Width = std::uint64_t;
constexpr std::string_view magic = "QRT1";
constexpr std::string_view compact_magic = "QRT2";
constexpr std::string_view residue_magic = "QRT3";
constexpr std::string_view mixed_magic = "QRT4";
constexpr std::string_view seeded_magic = "QRT5";
constexpr unsigned max_tree_arity = 128;
constexpr unsigned max_schedule_length = 32;
constexpr unsigned long prime_limit = 10'000;
enum Mode : unsigned { literal, zero, factored, split_node };

static Width bit_length(const mpz_class& value) {
    return value == 0 ? 0 : mpz_sizeinbase(value.get_mpz_t(), 2);
}

static Width bit_length(Width value) {
    Width width = 0;
    for (; value; value >>= 1) ++width;
    return width;
}

static Width gamma_width(Width n) {
    return 2 * bit_length(n) - 1;
}

static Width bytes_for(Width bits) {
    return bits / 8 + (bits % 8 != 0);
}

static void write_bytes(std::ostream& out, const char* data, std::size_t size) {
    if (!out.write(data, size)) throw std::runtime_error("Write failed");
}

static void read_bytes(std::istream& in, char* data, std::size_t size) {
    if (!in.read(data, size)) throw std::runtime_error("Unexpected end of input");
}

static mpz_class import(const unsigned char* bytes, Width size) {
    mpz_class value;
    if (size) mpz_import(value.get_mpz_t(), size, 1, 1, 1, 0, bytes);
    return value;
}

static std::vector<unsigned char> export_fixed(const mpz_class& value, Width width) {
    const auto bits = bit_length(value);
    if (bits > width) throw std::runtime_error("Value exceeds its bit width");
    std::vector<unsigned char> bytes(bytes_for(width));
    if (bits) mpz_export(bytes.data() + bytes.size() - bytes_for(bits), nullptr, 1, 1, 1, 0, value.get_mpz_t());
    return bytes;
}

class BitWriter {
public:
    BitWriter() = default;
    explicit BitWriter(std::ostream& out) : stream(&out) {}

    void put(unsigned value, unsigned count) {
        written += count;
        if (counting()) return;
        buffer = (buffer << count) | value;
        pending += count;
        if (pending >= 8) {
            pending -= 8;
            if (!stream->put(static_cast<char>(buffer >> pending))) throw std::runtime_error("Write failed");
            buffer &= (1U << pending) - 1;
        }
    }

    void gamma(Width n) {
        const auto width = bit_length(n);
        if (!width) throw std::runtime_error("Zero cannot be gamma-coded");
        for (Width i = 1; i < width; ++i) put(0, 1);
        for (Width i = width; i; --i) put((n >> (i - 1)) & 1, 1);
    }

    void number(const mpz_class& value, Width width) {
        if (counting()) {
            written += width;
            return;
        }
        const auto bytes = export_fixed(value, width);
        std::size_t offset = 0;
        if (width % 8) put(bytes[offset++], width % 8);
        if (!pending && offset < bytes.size()) {
            write_bytes(*stream, reinterpret_cast<const char*>(bytes.data() + offset), bytes.size() - offset);
            written += 8 * (bytes.size() - offset);
        } else {
            for (; offset < bytes.size(); ++offset) put(bytes[offset], 8);
        }
    }

    void finish() {
        if (pending && !stream->put(static_cast<char>(buffer << (8 - pending)))) {
            throw std::runtime_error("Write failed");
        }
    }

    Width written = 0;
    bool counting() const { return !stream; }

private:
    std::ostream* stream = nullptr;
    unsigned buffer = 0;
    unsigned pending = 0;
};

class BitReader {
public:
    explicit BitReader(std::istream& input) : stream(input) {}

    unsigned get(unsigned count) {
        if (count > pending) {
            const int byte = stream.get();
            if (byte == std::char_traits<char>::eof()) throw std::runtime_error("Truncated bitstream");
            buffer = (buffer << 8) | static_cast<unsigned>(byte);
            pending += 8;
        }
        pending -= count;
        const auto result = buffer >> pending;
        buffer &= (1U << pending) - 1;
        return result;
    }

    Width gamma() {
        unsigned zeros = 0;
        while (!get(1)) {
            if (++zeros == 64) throw std::runtime_error("Gamma code is too large");
        }
        Width value = 1;
        for (unsigned i = 0; i < zeros; ++i) value = (value << 1) | get(1);
        return value;
    }

    mpz_class number(Width width) {
        std::vector<unsigned char> bytes(bytes_for(width));
        std::size_t offset = 0;
        if (width % 8) bytes[offset++] = get(width % 8);
        if (!pending && offset < bytes.size()) {
            read_bytes(stream, reinterpret_cast<char*>(bytes.data() + offset), bytes.size() - offset);
        } else {
            for (; offset < bytes.size(); ++offset) bytes[offset] = get(8);
        }
        return import(bytes.data(), bytes.size());
    }

    void finish() {
        if (buffer || stream.peek() != std::char_traits<char>::eof() || stream.bad()) {
            throw std::runtime_error("Unexpected data after the tree");
        }
    }

    void align() {
        if (buffer) throw std::runtime_error("Invalid padding");
        pending = 0;
    }

private:
    std::istream& stream;
    unsigned buffer = 0;
    unsigned pending = 0;
};

struct Factor {
    Width twos = 0;
    mpz_class odd = 1;
    std::vector<std::pair<std::uint32_t, Width>> powers;
    bool trivial() const { return !twos && odd == 1; }

    Width removed_bits() const { return twos + (bit_length(odd) - 1); }

    Width code_bits() const {
        const auto odd_width = bit_length(odd);
        return gamma_width(twos + 1) + gamma_width(odd_width) + (odd_width > 1 ? odd_width - 2 : 0);
    }

    void write(BitWriter& writer) const {
        const auto odd_width = bit_length(odd);
        writer.gamma(twos + 1);
        writer.gamma(odd_width);
        if (odd_width > 1) {
            mpz_class interior = odd >> 1;
            mpz_fdiv_r_2exp(interior.get_mpz_t(), interior.get_mpz_t(), odd_width - 2);
            writer.number(interior, odd_width - 2);
        }
    }
};

struct Node {
    Factor factor;
    std::string primes;
    std::unique_ptr<Node> left, right;
    Width width = 0;
    Width leaf_width = 0;
    Width best_bits = 0;
    Width full_bits = 0;
    Mode best_mode = literal;
    Mode full_mode = literal;
};

static mpz_class lower_bits(const mpz_class& value, Width width) {
    mpz_class result;
    mpz_fdiv_r_2exp(result.get_mpz_t(), value.get_mpz_t(), width);
    return result;
}

static mpz_class bit_slice(const mpz_class& value, Width offset, Width width) {
    const auto first = offset / GMP_NUMB_BITS;
    const auto inner = offset % GMP_NUMB_BITS;
    const auto size = mpz_size(value.get_mpz_t());
    if (first >= size) return 0;
    const auto needed = (inner + width - 1) / GMP_NUMB_BITS + 1;
    mpz_class result;
    mpz_import(result.get_mpz_t(), std::min<Width>(size - first, needed), -1,
               sizeof(mp_limb_t), 0, GMP_NAIL_BITS, mpz_limbs_read(value.get_mpz_t()) + first);
    result >>= inner;
    mpz_fdiv_r_2exp(result.get_mpz_t(), result.get_mpz_t(), width);
    return result;
}

static void divide_by(mpz_class& value, const Factor& factor) {
    value >>= factor.twos;
    if (factor.odd != 1) mpz_divexact(value.get_mpz_t(), value.get_mpz_t(), factor.odd.get_mpz_t());
}

class SmallPrimes {
public:
    explicit SmallPrimes(unsigned long limit = prime_limit) {
        mpz_primorial_ui(odd_primorial.get_mpz_t(), limit);
        odd_primorial >>= 1;
        mpz_class p = 2;
        candidates.push_back(2);
        for (;;) {
            mpz_nextprime(p.get_mpz_t(), p.get_mpz_t());
            if (p > limit) break;
            candidates.push_back(p.get_ui());
        }
    }

    Factor extract(mpz_class& value) const {
        Factor factor;
        factor.twos = mpz_scan1(value.get_mpz_t(), 0);
        if (factor.twos) factor.powers.emplace_back(2, factor.twos);
        value >>= factor.twos;

        mpz_class shared;
        mpz_gcd(shared.get_mpz_t(), value.get_mpz_t(), odd_primorial.get_mpz_t());
        for (auto p : candidates) {
            if (shared == 1) break;
            if (p == 2 || !mpz_divisible_ui_p(shared.get_mpz_t(), p)) continue;
            const mpz_class prime(static_cast<unsigned long>(p));
            const auto exponent = mpz_remove(value.get_mpz_t(), value.get_mpz_t(), prime.get_mpz_t());
            mpz_divexact_ui(shared.get_mpz_t(), shared.get_mpz_t(), p);
            mpz_class power;
            mpz_ui_pow_ui(power.get_mpz_t(), p, exponent);
            factor.odd *= power;
            factor.powers.emplace_back(p, exponent);
        }
        if (shared != 1) throw std::runtime_error("Small-factor extraction failed");
        return factor;
    }

    std::vector<std::uint32_t> candidates;

private:
    mpz_class odd_primorial;
};

class Builder {
public:
    explicit Builder(Width leaf_limit) : leaf_limit(leaf_limit) {}

    Node build(mpz_class value, Width width) const {
        Node node;
        node.width = width;
        if (value == 0) {
            node.full_bits = node.best_bits = 2;
            node.full_mode = node.best_mode = zero;
            return node;
        }
        node.factor = small.extract(value);
        for (const auto& [p, exponent] : node.factor.powers) append_prime(node.primes, p, exponent);

        const auto remainder_width = width - node.factor.removed_bits();
        node.leaf_width = remainder_width;
        node.full_bits = node.best_bits = 2 + width;
        const auto prefix_bits = 2 + node.factor.code_bits();
        if (!node.factor.trivial()) {
            node.full_mode = factored;
            node.full_bits = prefix_bits + remainder_width;
            consider(node, factored, node.full_bits);
        }
        if (remainder_width > leaf_limit && remainder_width >= 2) {
            const auto low_width = remainder_width / 2;
            auto low = lower_bits(value, low_width);
            value >>= low_width;
            node.left = std::make_unique<Node>(build(std::move(value), remainder_width - low_width));
            node.right = std::make_unique<Node>(build(std::move(low), low_width));
            node.full_mode = split_node;
            node.full_bits = prefix_bits + node.left->full_bits + node.right->full_bits;
            consider(node, split_node, prefix_bits + node.left->best_bits + node.right->best_bits);
        }
        return node;
    }

private:
    static void consider(Node& node, Mode mode, Width bits) {
        if (bits < node.best_bits) {
            node.best_bits = bits;
            node.best_mode = mode;
        }
    }

    static void append_prime(std::string& log, unsigned long p, Width exponent) {
        if (!log.empty()) log += " * ";
        log += std::to_string(p) + "^" + std::to_string(exponent);
    }

    Width leaf_limit;
    SmallPrimes small;
};

static void write_node(BitWriter& writer, const Node& node, mpz_class value, bool best) {
    const auto mode = best ? node.best_mode : node.full_mode;
    writer.put(mode, 2);
    if (mode == zero) return;
    if (mode == literal) {
        writer.number(value, node.width);
        return;
    }
    node.factor.write(writer);
    divide_by(value, node.factor);
    if (mode == factored) {
        writer.number(value, node.leaf_width);
        return;
    }
    auto low = lower_bits(value, node.right->width);
    value >>= node.right->width;
    write_node(writer, *node.left, std::move(value), best);
    write_node(writer, *node.right, std::move(low), best);
}

static mpz_class read_node(BitReader& reader, Width width) {
    const auto mode = reader.get(2);
    if (mode == zero) return 0;
    if (mode == literal) return reader.number(width);
    const auto shift = reader.gamma() - 1;
    const auto odd_width = reader.gamma();
    if (shift >= width || odd_width > width - shift) throw std::runtime_error("Invalid factor width");

    mpz_class odd = 1;
    if (odd_width > 1) {
        odd = reader.number(odd_width - 2);
        odd <<= 1;
        mpz_setbit(odd.get_mpz_t(), odd_width - 1);
        mpz_setbit(odd.get_mpz_t(), 0);
    }
    const auto remainder_width = width - (shift + odd_width - 1);
    mpz_class value;
    if (mode == factored) {
        if (!shift && odd_width == 1) throw std::runtime_error("Empty factor");
        value = reader.number(remainder_width);
    } else {
        if (remainder_width < 2) throw std::runtime_error("Invalid split");
        const auto low_width = remainder_width / 2;
        value = read_node(reader, remainder_width - low_width);
        value <<= low_width;
        value += read_node(reader, low_width);
    }
    value *= odd;
    value <<= shift;
    if (bit_length(value) > width) throw std::runtime_error("Invalid reconstructed node");
    return value;
}

static std::string_view name(Mode mode) {
    switch (mode) {
        case literal: return "letterale";
        case zero: return "zero";
        case factored: return "fattore";
        case split_node: return "due_figli";
    }
    throw std::runtime_error("Invalid mode");
}

static void report_nodes(std::ostream& out, const Node& node, const std::string& id, unsigned level) {
    out << id << '\t' << level << '\t' << node.width << '\t' << node.leaf_width << '\t'
        << (node.primes.empty() ? "-" : node.primes) << '\t' << name(node.full_mode) << '\t'
        << name(node.best_mode) << '\t' << node.full_bits << '\t' << node.best_bits << '\n';
    if (node.left) {
        report_nodes(out, *node.left, id + "0", level + 1);
        report_nodes(out, *node.right, id + "1", level + 1);
    }
}

static void encode(const char* input_path, const char* archive_path, const char* report_path, Width leaf_bytes, bool best) {
    const auto size = std::filesystem::file_size(input_path);
    if (!size || size > std::numeric_limits<Width>::max() / 8) throw std::runtime_error("Invalid file size");
    mpz_class value;
    {
        std::ifstream input(input_path, std::ios::binary);
        std::vector<unsigned char> bytes(size);
        read_bytes(input, reinterpret_cast<char*>(bytes.data()), bytes.size());
        value = import(bytes.data(), size);
    }
    const Node root = Builder(leaf_bytes * 8).build(value, 8 * size);

    std::ofstream report(report_path);
    report << "node\tlevel\twidth_bits\tcofactor_bits\tprime_factors\tsaved_node\tcheapest_choice\ttree_bits\tbest_bits\n";
    report_nodes(report, root, "Q", 0);
    report.close();
    if (!report) throw std::runtime_error("Could not write the tree report");

    std::ofstream archive(archive_path, std::ios::binary);
    write_bytes(archive, magic.data(), magic.size());
    BitWriter writer(archive);
    writer.gamma(size);
    write_node(writer, root, std::move(value), best);
    if (writer.written != gamma_width(size) + (best ? root.best_bits : root.full_bits)) {
        throw std::runtime_error("Stored size differs from the calculation");
    }
    writer.finish();
    archive.close();
    if (!archive) throw std::runtime_error("Could not complete the archive");

    std::cout << "input_bytes " << size << '\n'
              << "prime_limit " << prime_limit << '\n'
              << "leaf_max_bytes " << leaf_bytes << '\n'
              << "tree_bytes " << magic.size() + bytes_for(gamma_width(size) + root.full_bits) << '\n'
              << "pruned_bytes " << magic.size() + bytes_for(gamma_width(size) + root.best_bits) << '\n'
              << "pruned_root " << name(root.best_mode) << '\n';
}

// The compact formats put factor descriptors after the leaf stream. Child
// widths and internal/leaf transitions follow from the quotient width and header.
static void write_u64(std::ostream& out, Width value) {
    char field[8];
    for (unsigned i = 0; i < 8; ++i) field[i] = static_cast<char>(value >> (8 * i));
    write_bytes(out, field, sizeof(field));
}

static Width read_u64(std::istream& in) {
    char field[8];
    read_bytes(in, field, sizeof(field));
    Width value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= Width(static_cast<unsigned char>(field[i])) << (8 * i);
    return value;
}

static void write_varint(std::ostream& out, Width value) {
    while (value >= 128) {
        const char byte = static_cast<char>((value & 127) | 128);
        write_bytes(out, &byte, 1);
        value >>= 7;
    }
    const char byte = static_cast<char>(value);
    write_bytes(out, &byte, 1);
}

static Width read_varint(std::istream& in) {
    Width value = 0;
    for (unsigned shift = 0; shift < 64; shift += 7) {
        const auto byte = in.get();
        if (byte < 0 || (shift == 63 && byte > 1)) throw std::runtime_error("Invalid variable-length integer");
        value |= Width(byte & 127) << shift;
        if (byte < 128) return value;
    }
    throw std::runtime_error("Invalid variable-length integer");
}

static void encode_event(RangeEncoder& coder, bool event, std::uint32_t total) {
    coder.encode(event ? 0 : 1, event ? 1 : total - 1, total);
}

static bool decode_event(RangeDecoder& coder, std::uint32_t total) {
    const bool event = coder.get_freq(total) == 0;
    coder.decode(event ? 0 : 1, event ? 1 : total - 1);
    return event;
}

static void encode_exponent(RangeEncoder& coder, Width exponent, unsigned prime, unsigned first_total) {
    constexpr unsigned unary_limit = 8;
    for (unsigned i = 0; i < unary_limit; ++i) {
        const auto total = i == 0 ? first_total : prime;
        if (total > 1) encode_event(coder, exponent > i, total);
        else if (exponent == i) throw std::runtime_error("Missing implied divisor");
        if (exponent == i) return;
    }
    const auto tail = exponent - unary_limit + 1;
    const auto width = bit_length(tail);
    for (Width i = 1; i < width; ++i) coder.bits(0, 1);
    for (Width i = width; i; --i) coder.bits((tail >> (i - 1)) & 1, 1);
}

static Width decode_exponent(RangeDecoder& coder, unsigned prime, unsigned first_total, Width limit) {
    constexpr unsigned unary_limit = 8;
    for (Width i = 0; i < unary_limit; ++i) {
        const auto total = i == 0 ? first_total : prime;
        if (total > 1 && !decode_event(coder, total)) return i;
    }
    unsigned zeros = 0;
    while (!coder.bits(1)) {
        if (++zeros == 64 || coder.overrun()) throw std::runtime_error("Invalid exponent tail");
    }
    Width tail = 1;
    for (unsigned i = 0; i < zeros; ++i) tail = 2 * tail + coder.bits(1);
    if (limit < unary_limit || tail > limit - unary_limit + 1) throw std::runtime_error("Exponent exceeds node width");
    return tail + unary_limit - 1;
}

constexpr std::array<unsigned, 6> wheel_primes{2, 3, 5, 7, 11, 13};
constexpr unsigned wheel_modulus = 30'030;
using Residues = std::array<unsigned, wheel_primes.size()>;
constexpr Residues coprime_residues{1, 1, 1, 1, 1, 1};

static unsigned power_two_mod(Width exponent, unsigned modulus) {
    unsigned factor = 2;
    unsigned result = 1;
    while (exponent) {
        if (exponent & 1) result = result * factor % modulus;
        factor = factor * factor % modulus;
        exponent >>= 1;
    }
    return result;
}

static Residues quotient_residues(const Residues& inherited, const Factor& factor) {
    Residues blocked = coprime_residues;
    if (inherited == Residues{}) return blocked;
    const auto odd = mpz_fdiv_ui(factor.odd.get_mpz_t(), wheel_modulus);
    const auto factor_mod = odd * power_two_mod(factor.twos, wheel_modulus) % wheel_modulus;
    for (std::size_t i = 0; i < blocked.size(); ++i) {
        const auto p = wheel_primes[i];
        for (unsigned r = 1; r < p; ++r) {
            if (inherited[i] & (1u << (r * factor_mod % p))) blocked[i] |= 1u << r;
        }
    }
    return blocked;
}

static Residues last_child_residues(const Residues& blocked, const mpz_class& prefix, Width width) {
    const auto residue = mpz_fdiv_ui(prefix.get_mpz_t(), wheel_modulus);
    const auto shifted = residue * power_two_mod(width, wheel_modulus) % wheel_modulus;
    Residues result{};
    for (std::size_t i = 0; i < result.size(); ++i) {
        const auto p = wheel_primes[i];
        for (unsigned r = 0; r < p; ++r) {
            if (blocked[i] & (1u << ((r + shifted) % p))) result[i] |= 1u << r;
        }
    }
    return result;
}

class Wheel {
public:
    explicit Wheel(const Residues& blocked = coprime_residues) {
        for (unsigned r = 0; r < modulus; ++r) {
            if (!allowed(r, blocked)) continue;
            index[r] = residues.size();
            residues.push_back(r);
        }
        if (residues.empty()) throw std::runtime_error("No allowed wheel residues");
    }

    mpz_class rank_count(Width width, const Factor& factor) const {
        mpz_class end = 0;
        mpz_setbit(end.get_mpz_t(), width);
        end -= 1;
        end >>= factor.twos;
        if (factor.odd != 1) end /= factor.odd;
        mpz_class groups;
        const auto last = mpz_fdiv_q_ui(groups.get_mpz_t(), end.get_mpz_t(), modulus);
        const auto tail = std::upper_bound(residues.begin(), residues.end(), last) - residues.begin();
        return groups * static_cast<unsigned long>(residues.size()) + static_cast<unsigned long>(tail);
    }

    mpz_class rank(const mpz_class& value) const {
        mpz_class groups;
        const auto r = mpz_fdiv_q_ui(groups.get_mpz_t(), value.get_mpz_t(), modulus);
        if (index[r] >= residues.size() || residues[index[r]] != r) {
            throw std::runtime_error("Leaf violates its residue constraints");
        }
        return groups * static_cast<unsigned long>(residues.size()) + index[r];
    }

    mpz_class unrank(const mpz_class& encoded) const {
        mpz_class groups;
        const auto r = mpz_fdiv_q_ui(groups.get_mpz_t(), encoded.get_mpz_t(), residues.size());
        return groups * modulus + residues[r];
    }

private:
    static bool allowed(unsigned residue, const Residues& blocked) {
        for (std::size_t i = 0; i < blocked.size(); ++i) {
            if (blocked[i] & (1u << (residue % wheel_primes[i]))) return false;
        }
        return true;
    }

    static constexpr unsigned modulus = wheel_modulus;
    std::uint16_t index[modulus]{};
    std::vector<unsigned> residues;
};

struct Layer {
    Width nodes = 0, splits = 0, leaves = 0, factored_nodes = 0;
};

class CompactTree {
public:
    CompactTree(Width limit, unsigned fanout, bool advanced = false, int offset = 0,
                std::vector<unsigned> arities = {}, unsigned seed = 0)
        : leaf_limit(limit), fanout(fanout), advanced(advanced), offset(offset), schedule(std::move(arities)),
          seed(seed), small(schedule.empty() ? prime_limit : wheel_primes.back()) {}

    void encode(RangeEncoder& metadata, BitWriter& leaves, mpz_class value, Width width,
                unsigned level = 0, std::vector<unsigned char>* earlier = nullptr, bool last = false,
                const Residues& inherited = {}) {
        if (level == layers.size()) layers.emplace_back();
        ++layers[level].nodes;
        const bool is_zero = value == 0;
        if (!last) encode_event(metadata, is_zero, zero_total(width));
        else if (is_zero) throw std::runtime_error("The last child of an odd quotient is nonzero");
        if (is_zero) {
            ++layers[level].leaves;
            return; // Zero counts as divisible by all primes for sibling conditioning.
        }

        const auto factor = small.extract(value);
        if (!factor.trivial()) ++layers[level].factored_nodes;
        std::size_t at = 0;
        for (std::size_t i = 0; i < small.candidates.size(); ++i) {
            const auto p = small.candidates[i];
            const auto exponent = at < factor.powers.size() && factor.powers[at].first == p
                ? factor.powers[at++].second : 0;
            const unsigned total = first_total(p, width, earlier, i, last, inherited);
            if (total) encode_exponent(metadata, exponent, p, total);
            else if (exponent) throw std::runtime_error("Factor contradicts sibling context");
            if (earlier && !last && !exponent) ++(*earlier)[i];
        }
        const auto rest = width - factor.removed_bits();
        const auto children = arity(rest, level);
        const auto blocked = advanced ? quotient_residues(inherited, factor) : coprime_residues;
        if (children == 1) {
            ++layers[level].leaves;
            raw_leaf_bits += rest;
            if (blocked == coprime_residues) {
                write_leaf(leaves, wheel, value, width, factor);
            } else {
                const Wheel contextual_wheel(blocked);
                write_leaf(leaves, contextual_wheel, value, width, factor);
            }
            return;
        }
        ++layers[level].splits;
        std::vector<unsigned char> sibling_counts(small.candidates.size());
        auto shift = rest;
        for (unsigned i = 0; i < children; ++i) {
            const auto child_width = part_width(rest, children, i, level);
            shift -= child_width;
            auto child = bit_slice(value, shift, child_width);
            if (advanced && i + 1 == children) {
                const auto conditions = last_child_residues(blocked, mpz_class(value >> child_width), child_width);
                encode(metadata, leaves, std::move(child), child_width, level + 1, &sibling_counts, true, conditions);
                continue;
            }
            encode(metadata, leaves, std::move(child), child_width, level + 1, &sibling_counts, i + 1 == children);
        }
    }

    mpz_class decode(RangeDecoder& metadata, BitReader& leaves, Width width,
                     unsigned level = 0,
                     std::vector<unsigned char>* earlier = nullptr, bool last = false,
                     const Residues& inherited = {}) const {
        if (!last && decode_event(metadata, zero_total(width))) return 0;
        Factor factor;
        for (std::size_t i = 0; i < small.candidates.size(); ++i) {
            const auto p = small.candidates[i];
            const auto total = first_total(p, width, earlier, i, last, inherited);
            const auto exponent = total ? decode_exponent(metadata, p, total, width) : 0;
            if (earlier && !last && !exponent) ++(*earlier)[i];
            if (!exponent) continue;
            if (exponent >= width) throw std::runtime_error("Invalid factor exponent");
            if (p == 2) factor.twos = exponent;
            else {
                mpz_class power;
                mpz_ui_pow_ui(power.get_mpz_t(), p, exponent);
                factor.odd *= power;
            }
            if (factor.removed_bits() >= width) throw std::runtime_error("Factors exceed the node width");
        }
        if (metadata.overrun()) throw std::runtime_error("Truncated factor descriptors");
        const auto rest = width - factor.removed_bits();
        const auto children = arity(rest, level);
        const auto blocked = advanced ? quotient_residues(inherited, factor) : coprime_residues;
        mpz_class value;
        if (children == 1) {
            if (blocked == coprime_residues) {
                value = read_leaf(leaves, wheel, width, factor);
            } else {
                const Wheel contextual_wheel(blocked);
                value = read_leaf(leaves, contextual_wheel, width, factor);
            }
        } else {
            std::vector<unsigned char> sibling_counts(small.candidates.size());
            for (unsigned i = 0; i < children; ++i) {
                const auto child_width = part_width(rest, children, i, level);
                const auto conditions = advanced && i + 1 == children
                    ? last_child_residues(blocked, value, child_width) : Residues{};
                value <<= child_width;
                value += decode(metadata, leaves, child_width, level + 1, &sibling_counts,
                                i + 1 == children, conditions);
            }
        }
        value *= factor.odd;
        value <<= factor.twos;
        if (bit_length(value) > width) throw std::runtime_error("Invalid reconstructed node width");
        return value;
    }

    std::vector<Layer> layers;
    Width raw_leaf_bits = 0;

private:
    // Truncated binary uses the otherwise unused codewords to store small ranks
    // in one fewer bit.
    static mpz_class short_ranks(const mpz_class& count, Width bits) {
        mpz_class cutoff;
        mpz_setbit(cutoff.get_mpz_t(), bits);
        return cutoff - count;
    }

    void write_leaf(BitWriter& leaves, const Wheel& allowed, const mpz_class& value,
                    Width width, const Factor& factor) const {
        const auto count = allowed.rank_count(width, factor);
        const auto bits = bit_length(mpz_class(count - 1));
        if (schedule.empty() || !bits) {
            leaves.number(leaves.counting() ? mpz_class{} : allowed.rank(value), bits);
            return;
        }
        const auto cutoff = short_ranks(count, bits);
        if (leaves.counting()) {
            // Rank is monotone on the allowed values. In counting mode only
            // the value at the boundary between the two code lengths matters.
            const bool short_code = cutoff != 0 && value < allowed.unrank(cutoff);
            leaves.number(mpz_class{}, bits - short_code);
            return;
        }
        const auto rank = allowed.rank(value);
        if (rank < cutoff) leaves.number(rank, bits - 1);
        else leaves.number(mpz_class(rank + cutoff), bits);
    }

    mpz_class read_leaf(BitReader& leaves, const Wheel& allowed, Width width, const Factor& factor) const {
        const auto count = allowed.rank_count(width, factor);
        if (count <= 0) throw std::runtime_error("No value fits the leaf width");
        const auto bits = bit_length(mpz_class(count - 1));
        if (schedule.empty() || !bits) return allowed.unrank(leaves.number(bits));
        const auto cutoff = short_ranks(count, bits);
        auto rank = leaves.number(bits - 1);
        if (rank >= cutoff) {
            rank <<= 1;
            rank += leaves.get(1);
            rank -= cutoff;
        }
        return allowed.unrank(rank);
    }

    // For the final sibling, the parent quotient already rules out a factor of 2.
    // If all earlier siblings were divisible by p, this one must also avoid p.
    unsigned first_total(unsigned p, Width width, const std::vector<unsigned char>* earlier,
                         std::size_t i, bool last, const Residues& inherited) const {
        if (bit_length(Width(p)) > width) return 0;
        if (!last) return p;
        if (advanced && i < inherited.size()) {
            auto forbidden = inherited[i];
            if (forbidden & 1) return 0;
            unsigned allowed = p;
            while (forbidden) {
                --allowed;
                forbidden &= forbidden - 1;
            }
            return allowed;
        }
        if (p == 2 || (*earlier)[i] == 0) return 0;
        return (*earlier)[i] == 1 ? p - 1 : p;
    }

    static unsigned zero_total(Width width) { return 1U << std::min<Width>(width, 16); }

    unsigned arity(Width width, unsigned level) const {
        const auto needed = (width - 1) / leaf_limit + 1;
        if (!schedule.empty()) {
            const auto index = std::min<std::size_t>(level, schedule.size() - 1);
            return std::min<Width>(needed, schedule[index]);
        }
        unsigned arity = 1;
        while (arity < fanout && arity < needed) arity *= 2;
        return arity;
    }

    int boundary_shift(Width width, unsigned children, unsigned boundary, unsigned level) const {
        if (boundary == 0 || boundary == children) return 0;
        const auto cap = static_cast<unsigned>(std::min<Width>((width / children - 1) / 2, 32));
        // Fixed unsigned arithmetic makes the cut schedule identical on both sides.
        std::uint32_t hash = std::uint32_t(width) ^ std::uint32_t(width >> 32);
        hash ^= seed * 0x9e3779b9U + level * 0x85ebca6bU + boundary * 0xc2b2ae35U;
        hash = (hash ^ (hash >> 16)) * 0x7feb352dU;
        hash = (hash ^ (hash >> 15)) * 0x846ca68bU;
        hash ^= hash >> 16;
        return static_cast<int>(hash % (2 * cap + 1)) - static_cast<int>(cap);
    }

    Width part_width(Width width, unsigned children, unsigned index, unsigned level) const {
        const auto baseline = width / children + (index < width % children);
        if (seed) {
            const auto adjustment = boundary_shift(width, children, index + 1, level)
                - boundary_shift(width, children, index, level);
            return adjustment >= 0 ? baseline + adjustment : baseline - (-adjustment);
        }
        if ((children & 1) && index + 1 == children) return baseline;
        const auto cap = std::min<Width>(width / children - 1, 32);
        const auto shift = std::clamp(offset, -static_cast<int>(cap), static_cast<int>(cap));
        const auto adjustment = index % 2 == 0 ? shift : -shift;
        return adjustment >= 0 ? baseline + adjustment : baseline - (-adjustment);
    }

    const Width leaf_limit;
    const unsigned fanout;
    const bool advanced;
    const int offset;
    const std::vector<unsigned> schedule;
    const unsigned seed;
    const SmallPrimes small;
    const Wheel wheel;
};

static bool valid_fanout(Width number) {
    return number >= 2 && number <= max_tree_arity && (number & (number - 1)) == 0;
}

static mpz_class load_compact_input(const char* input_path, Width& size) {
    size = std::filesystem::file_size(input_path);
    if (!size || size > std::numeric_limits<Width>::max() / 8) throw std::runtime_error("Invalid file size");
    std::ifstream input(input_path, std::ios::binary);
    std::vector<unsigned char> bytes(size);
    read_bytes(input, reinterpret_cast<char*>(bytes.data()), bytes.size());
    return import(bytes.data(), size);
}

static std::streampos write_compact_header(std::ostream& archive, Width size, Width leaf_bytes,
                                          unsigned fanout, bool advanced, int skew,
                                          const std::vector<unsigned>& schedule, unsigned seed) {
    const auto format = seed ? seeded_magic : !schedule.empty() ? mixed_magic : advanced ? residue_magic : compact_magic;
    write_bytes(archive, format.data(), format.size());
    if (schedule.empty()) {
        write_u64(archive, size);
        write_u64(archive, leaf_bytes);
        write_u64(archive, fanout | (advanced ? (unsigned(skew + 32) << 8) : 0));
    } else {
        write_varint(archive, size);
        write_varint(archive, leaf_bytes);
        write_varint(archive, seed ? seed : skew + 32);
        write_varint(archive, schedule.size());
        for (const auto arity : schedule) write_varint(archive, arity - 2);
    }
    const auto offset_field = archive.tellp();
    write_u64(archive, 0);
    return offset_field;
}

static void encode_compact(const char* input_path, const char* archive_path, const char* report_path,
                           Width leaf_bytes, unsigned fanout, bool advanced = false, int skew = 0,
                           const std::vector<unsigned>& schedule = {}, unsigned seed = 0) {
    Width size;
    auto value = load_compact_input(input_path, size);
    std::ofstream archive(archive_path, std::ios::binary);
    const auto offset_field = write_compact_header(archive, size, leaf_bytes, fanout, advanced, skew, schedule, seed);
    const auto header_size = archive.tellp();

    CompactTree tree(leaf_bytes * 8, fanout, advanced, skew, schedule, seed);
    RangeEncoder metadata;
    BitWriter leaves(archive);
    tree.encode(metadata, leaves, std::move(value), size * 8);
    leaves.finish();
    const auto offset = archive.tellp();
    const auto descriptors = metadata.finish();
    write_bytes(archive, reinterpret_cast<const char*>(descriptors.data()), descriptors.size());
    archive.seekp(offset_field);
    write_u64(archive, offset);
    archive.close();
    if (!archive) throw std::runtime_error("Could not complete the archive");

    std::ofstream report(report_path);
    report << "level\tnodes\tsplit_nodes\tleaves\tnodes_with_factors\n";
    for (std::size_t i = 0; i < tree.layers.size(); ++i) {
        const auto& layer = tree.layers[i];
        report << i << '\t' << layer.nodes << '\t' << layer.splits << '\t' << layer.leaves << '\t'
               << layer.factored_nodes << '\n';
    }
    report.close();
    if (!report) throw std::runtime_error("Could not write the layer summary");
    const auto payload = bytes_for(leaves.written);
    const auto total = Width(header_size) + payload + descriptors.size();
    if (total != std::filesystem::file_size(archive_path)) throw std::runtime_error("Archive size mismatch");
    std::cout << "input_bytes " << size << '\n';
    if (schedule.empty()) {
        std::cout << "fanout " << fanout << '\n';
    } else {
        std::cout << "fanout_schedule " << schedule.front();
        for (std::size_t i = 1; i < schedule.size(); ++i) std::cout << ',' << schedule[i];
        std::cout << '\n';
    }
    if (seed) std::cout << "seed " << seed << '\n';
    else std::cout << "offset_bits " << skew << '\n';
    std::cout << "header_bytes " << header_size << '\n'
              << "descriptor_bytes " << descriptors.size() << '\n'
              << "leaf_raw_bits " << tree.raw_leaf_bits << '\n'
              << "leaf_encoded_bits " << leaves.written << '\n'
              << "total_bytes " << total << '\n';
}

static mpz_class decode_compact(std::istream& archive, Width file_size, Width& size, std::string_view format) {
    const bool advanced = format != compact_magic;
    const bool seeded = format == seeded_magic;
    const bool mixed = format == mixed_magic || seeded;
    size = mixed ? read_varint(archive) : read_u64(archive);
    const auto leaf_bytes = mixed ? read_varint(archive) : read_u64(archive);
    Width fanout = 2;
    Width offset_tag = 32;
    unsigned seed = 0;
    std::vector<unsigned> schedule;
    if (mixed) {
        const auto selector = read_varint(archive);
        if (seeded) {
            if (!selector || selector >= 128) throw std::runtime_error("Invalid cut seed");
            seed = static_cast<unsigned>(selector);
        } else {
            offset_tag = selector;
        }
        const auto count = read_varint(archive);
        if (!count || count > max_schedule_length) throw std::runtime_error("Invalid branching schedule length");
        for (Width i = 0; i < count; ++i) {
            const auto arity = read_varint(archive);
            if (arity > max_tree_arity - 2) throw std::runtime_error("Invalid branching schedule arity");
            schedule.push_back(arity + 2);
        }
    } else {
        const auto parameters = read_u64(archive);
        fanout = advanced ? parameters & 255 : parameters;
        if (advanced) offset_tag = parameters >> 8;
    }
    const auto offset = read_u64(archive);
    const auto body = archive.tellg();
    if (!size || size > std::numeric_limits<Width>::max() / 8 ||
        !leaf_bytes || leaf_bytes > std::numeric_limits<Width>::max() / 8 ||
        !valid_fanout(fanout) || offset_tag > 64 || offset < Width(body) || offset > file_size || file_size - offset < 5) {
        throw std::runtime_error("Invalid compact header");
    }
    const auto skew = static_cast<int>(offset_tag) - 32;

    archive.seekg(offset);
    std::vector<std::uint8_t> descriptors(file_size - offset);
    read_bytes(archive, reinterpret_cast<char*>(descriptors.data()), descriptors.size());
    archive.seekg(body);
    RangeDecoder metadata(descriptors.data(), descriptors.data() + descriptors.size());
    BitReader leaves(archive);
    auto value = CompactTree(leaf_bytes * 8, fanout, advanced, skew, std::move(schedule), seed).decode(metadata, leaves, size * 8);
    leaves.align();
    if (metadata.overrun() || Width(archive.tellg()) != offset) throw std::runtime_error("Incorrect stream lengths");
    return value;
}

static void decode(const char* archive_path, const char* output_path) {
    std::ifstream archive(archive_path, std::ios::binary);
    char header[magic.size()];
    read_bytes(archive, header, sizeof(header));
    Width size;
    mpz_class value;
    const std::string_view format(header, sizeof(header));
    if (format == compact_magic || format == residue_magic || format == mixed_magic || format == seeded_magic) {
        value = decode_compact(archive, std::filesystem::file_size(archive_path), size, format);
    } else if (format == magic) {
        BitReader reader(archive);
        size = reader.gamma();
        if (size > std::numeric_limits<Width>::max() / 8) throw std::runtime_error("Invalid archive size");
        value = read_node(reader, size * 8);
        reader.finish();
    } else {
        throw std::runtime_error("Invalid archive magic");
    }
    const auto bytes = export_fixed(value, size * 8);
    std::ofstream output(output_path, std::ios::binary);
    write_bytes(output, reinterpret_cast<const char*>(bytes.data()), bytes.size());
    output.close();
    if (!output) throw std::runtime_error("Could not complete the join");
}

static std::vector<unsigned> branching_schedule(std::string_view argument) {
    std::vector<unsigned> schedule;
    for (;;) {
        const auto comma = argument.find(',');
        const std::string field(argument.substr(0, comma));
        if (field.empty() || field.find_first_not_of("0123456789") != std::string::npos) {
            throw std::runtime_error("Expected a comma-separated branching schedule");
        }
        const auto arity = std::stoull(field);
        if (arity < 2 || arity > max_tree_arity || schedule.size() == max_schedule_length) {
            throw std::runtime_error("Branching schedule must contain 1 to 32 arities from 2 to 128");
        }
        schedule.push_back(arity);
        if (comma == std::string_view::npos) return schedule;
        argument.remove_prefix(comma + 1);
    }
}

static int parse_offset(const char* argument) {
    const std::string text(argument);
    std::size_t parsed = 0;
    const auto offset = std::stoi(text, &parsed);
    if (parsed != text.size() || offset < -32 || offset > 32) {
        throw std::runtime_error("Offset must be between -32 and 32 bits");
    }
    return offset;
}

static Width parse_leaf_bytes(const std::string& argument) {
    std::size_t parsed = 0;
    const auto width = std::stoull(argument, &parsed);
    if (parsed != argument.size() || argument.front() == '-' || !width || width > std::numeric_limits<Width>::max() / 8) {
        throw std::runtime_error("Invalid maximum leaf size");
    }
    return width;
}

static unsigned parse_seed(const std::string& argument) {
    std::size_t parsed = 0;
    const auto seed = std::stoull(argument, &parsed);
    if (parsed != argument.size() || argument.front() == '-' || !seed || seed >= 128) {
        throw std::runtime_error("Cut seed must be between 1 and 127");
    }
    return static_cast<unsigned>(seed);
}

static void probe_mixed(const char* input_path, const char* plan_path) {
    std::ifstream plan(plan_path);
    if (!plan) throw std::runtime_error("Could not open the branching plan");
    Width size;
    const auto value = load_compact_input(input_path, size);
    std::cout << "leaf_max_bytes\tschedule\tselector\troot_children\tlevels\tnodes\tleaves\theader_bytes"
                 "\tdescriptor_bytes\tleaf_raw_bits\tleaf_encoded_bits\ttotal_bytes\tdelta_bytes\n";
    std::string line;
    while (std::getline(plan, line)) {
        std::istringstream row(line);
        std::string width_text, arities, selector, extra;
        if (!(row >> width_text)) continue;
        if (!(row >> arities >> selector) || row >> extra) {
            throw std::runtime_error("Each plan row requires leaf bytes, arities and an offset or sSEED");
        }
        const auto width = parse_leaf_bytes(width_text);
        const auto schedule = branching_schedule(arities);
        const bool seeded = selector.front() == 's';
        const auto seed = seeded ? parse_seed(selector.substr(1)) : 0;
        const auto skew = seeded ? 0 : parse_offset(selector.c_str());

        std::ostringstream header;
        write_compact_header(header, size, width, 2, true, skew, schedule, seed);
        const auto header_bytes = Width(header.tellp());
        CompactTree tree(width * 8, 2, true, skew, schedule, seed);
        RangeEncoder metadata;
        BitWriter leaves;
        tree.encode(metadata, leaves, value, size * 8);
        const auto descriptor_bytes = metadata.finish().size();
        const auto total = header_bytes + descriptor_bytes + bytes_for(leaves.written);
        Width nodes = 0, leaf_count = 0;
        for (const auto& layer : tree.layers) {
            nodes += layer.nodes;
            leaf_count += layer.leaves;
        }
        const auto root_children = tree.layers.size() > 1 ? tree.layers[1].nodes : 0;
        std::cout << width << '\t' << arities << '\t' << selector << '\t' << root_children << '\t'
                  << tree.layers.size() << '\t' << nodes << '\t' << leaf_count << '\t' << header_bytes << '\t'
                  << descriptor_bytes << '\t' << tree.raw_leaf_bits << '\t' << leaves.written << '\t' << total << '\t'
                  << (static_cast<std::int64_t>(total) - static_cast<std::int64_t>(size)) << std::endl;
    }
    if (plan.bad()) throw std::runtime_error("Could not read the branching plan");
}

int main(int argc, char** argv) {
    try {
        const std::string_view cmd = argc > 1 ? argv[1] : "";
        if ((argc == 6 && (cmd == "split" || cmd == "split-best")) || (argc == 7 && cmd == "split-compact")
                || (argc == 8 && (cmd == "split-residues" || cmd == "split-mixed" || cmd == "split-seeded"))) {
            const auto width = parse_leaf_bytes(argv[5]);
            if (cmd == "split-mixed") {
                encode_compact(argv[2], argv[3], argv[4], width, 2, true, parse_offset(argv[7]), branching_schedule(argv[6]));
            } else if (cmd == "split-seeded") {
                encode_compact(argv[2], argv[3], argv[4], width, 2, true, 0, branching_schedule(argv[6]), parse_seed(argv[7]));
            } else if (cmd == "split-compact" || cmd == "split-residues") {
                std::size_t parsed = 0;
                const std::string fanout_text(argv[6]);
                const auto fanout = std::stoull(fanout_text, &parsed);
                if (parsed != fanout_text.size() || !valid_fanout(fanout)) {
                    throw std::runtime_error("Fanout must be a power of two from 2 to 128");
                }
                if (cmd == "split-residues") {
                    encode_compact(argv[2], argv[3], argv[4], width, fanout, true, parse_offset(argv[7]));
                } else {
                    encode_compact(argv[2], argv[3], argv[4], width, fanout);
                }
            } else {
                encode(argv[2], argv[3], argv[4], width, cmd == "split-best");
            }
        } else if (argc == 4 && cmd == "join") {
            decode(argv[2], argv[3]);
        } else if (argc == 4 && cmd == "probe-mixed") {
            probe_mixed(argv[2], argv[3]);
        } else {
            std::cerr << "Usage: factor-tree split|split-best INPUT ARCHIVE REPORT MAX_LEAF_BYTES\n"
                         "       factor-tree split-compact INPUT ARCHIVE REPORT MAX_LEAF_BYTES MAX_FANOUT\n"
                         "       factor-tree split-residues INPUT ARCHIVE REPORT MAX_LEAF_BYTES MAX_FANOUT OFFSET_BITS\n"
                         "       factor-tree split-mixed INPUT ARCHIVE REPORT MAX_LEAF_BYTES ARITY[,ARITY...] OFFSET_BITS\n"
                         "       factor-tree split-seeded INPUT ARCHIVE REPORT MAX_LEAF_BYTES ARITY[,ARITY...] SEED\n"
                         "       factor-tree probe-mixed INPUT PLAN\n"
                         "       factor-tree join ARCHIVE OUTPUT\n";
            return 2;
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
