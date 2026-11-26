// Match p * recipe at every byte boundary. The 64-bit suffix filters candidates;
// every accepted match is checked with exact bytewise multiplication.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

using byte = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
constexpr std::array<unsigned, 17> factors{1,2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53};
constexpr unsigned limit = 255;
struct Leaf { std::vector<byte> value; unsigned cost, mode; };
struct Entry { u64 tail; u32 id; };

u64 mix(u64 v) {
    v ^= v >> 30; v *= 0xbf58476d1ce4e5b9ULL;
    v ^= v >> 27; v *= 0x94d049bb133111ebULL;
    return v ^ (v >> 31);
}

void emit32(u32 n) {
    for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>(n >> (8*i)));
}

int main(int argc, char** argv) {
    if (argc < 3) return 2;
    std::ifstream bank(argv[1], std::ios::binary);
    if (!bank) throw std::runtime_error("missing bank");
    std::vector<Leaf> leaves;
    std::vector<Entry> index;
    constexpr unsigned mask = (1u << 24) - 1;
    std::vector<bool> filter1(mask + 1), filter2(mask + 1);
    for (int width; (width = bank.get()) != EOF;) {
        int cost = bank.get();
        if (width < 1 || cost < 1 || cost > 4) throw std::runtime_error("bank layout");
        Leaf leaf{std::vector<byte>(width), unsigned(cost), 0};
        std::array<byte, 4> wire{};
        if (!bank.read(reinterpret_cast<char*>(leaf.value.data()), width) ||
            !bank.read(reinterpret_cast<char*>(wire.data()), cost)) throw std::runtime_error("short read");
        leaf.mode = wire.front() >> 6;
        u64 tail = 0;
        for (byte b : leaf.value) tail = (tail << 8) | b;
        for (unsigned j = 0; j < factors.size(); ++j) {
            u64 t = tail * factors[j], hash = mix(t);
            index.push_back({t, static_cast<u32>(leaves.size() * factors.size() + j)});
            filter1[hash & mask] = true;
            filter2[(hash >> 32) & mask] = true;
        }
        leaves.push_back(std::move(leaf));
    }
    std::sort(index.begin(), index.end(), [](auto a, auto b) { return a.tail < b.tail; });
    for (int file = 2; file < argc; ++file) {
        std::ifstream source(argv[file], std::ios::binary | std::ios::ate);
        auto size = source.tellg();
        if (size < 0 || u64(size) > UINT32_MAX) throw std::runtime_error("invalid source size");
        std::vector<byte> bytes(static_cast<size_t>(size));
        source.seekg(0);
        if (!source.read(reinterpret_cast<char*>(bytes.data()), size)) throw std::runtime_error("short input");
        // For each end, width and operator family keep its cheapest exact spelling.
        std::map<std::pair<unsigned,unsigned>, std::pair<unsigned,u32>> hits;
        u64 tail = 0;
        for (std::size_t end = 1; end <= bytes.size(); ++end) {
            tail = (tail << 8) | bytes[end-1];
            u64 hash = mix(tail);
            if (end < 8 || !filter1[hash & mask] || !filter2[(hash >> 32) & mask]) continue;
            auto first = std::lower_bound(index.begin(), index.end(), tail,
                [](const Entry& e, u64 t) { return e.tail < t; });
            for (auto it = first; it != index.end() && it->tail == tail; ++it) {
                auto j = it->id % factors.size();
                const auto& leaf = leaves[it->id / factors.size()];
                unsigned w = leaf.value.size(), carry = 0;
                if (w > end) continue;
                bool equal = true;
                for (unsigned k = 0; k < w; ++k) {
                    unsigned v = leaf.value[w-1-k] * factors[j] + carry;
                    if (byte(v) != bytes[end-1-k]) { equal = false; break; }
                    carry = v >> 8;
                }
                if (!equal) continue;
                if (carry) {
                    if (w == end || carry != bytes[end-1-w]) continue;
                    ++w;
                }
                unsigned cost = leaf.cost + unsigned(j != 0);
                unsigned family = leaf.mode + 2 * unsigned(j != 0);
                for (; w <= limit; ++w) {
                    if (w > 6 + cost) {
                        auto key = std::make_pair(w, family);
                        auto rec = std::make_pair(cost, it->id);
                        auto pos = hits.find(key);
                        if (pos == hits.end() || pos->second > rec) hits[key] = rec;
                    }
                    if (w == end || bytes[end-1-w] != 0) break;
                }
            }
            for (auto& [key, record] : hits) {
                std::cout.put(static_cast<char>(file - 2));
                emit32(static_cast<u32>(end - key.first));
                std::cout.put(static_cast<char>(key.first));
                emit32(record.second);
            }
            hits.clear();
        }
    }
    return !std::cout;
}
