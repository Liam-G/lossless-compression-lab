#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>

constexpr unsigned MaxWidth = 32;

struct Pattern {
    std::array<unsigned char, MaxWidth> digits{};
    unsigned width, wire_bytes;
};

std::uint32_t key(const unsigned char* bytes, unsigned width) {
    std::uint32_t result = 0;
    for (unsigned i = 0; i < width; ++i) result = result << 8 | bytes[i];
    return result;
}

void write32(std::uint32_t number) {
    for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>(number >> (8 * i)));
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::ifstream bank(argv[1], std::ios::binary);
    std::ifstream source(argv[2], std::ios::binary | std::ios::ate);
    if (!bank || !source) throw std::runtime_error("Cannot open the formula bank or source");
    const auto size = source.tellg();
    if (size < 0 || std::uint64_t(size) > UINT32_MAX) throw std::runtime_error("Invalid source size");
    std::vector<unsigned char> bytes(static_cast<std::size_t>(size));
    source.seekg(0);
    if (!source.read(reinterpret_cast<char*>(bytes.data()), size)) throw std::runtime_error("Incomplete source");

    std::vector<Pattern> patterns;
    std::array<std::unordered_map<std::uint32_t, std::vector<unsigned>>, 5> index;
    for (int width; (width = bank.get()) != EOF;) {
        const int wire = bank.get();
        std::array<char, 4> recipe{};
        if (width < 1 || width > int(MaxWidth) || wire < 1 || wire > int(recipe.size()))
            throw std::runtime_error("Invalid bank geometry");
        Pattern entry{{}, static_cast<unsigned>(width), static_cast<unsigned>(wire)};
        if (!bank.read(reinterpret_cast<char*>(entry.digits.data()), width) || !bank.read(recipe.data(), wire)
                || !entry.digits[0]) throw std::runtime_error("Incomplete or noncanonical bank entry");
        const auto prefix = std::min(entry.width, 4u);
        index[prefix][key(entry.digits.data(), prefix)].push_back(patterns.size());
        patterns.push_back(entry);
    }

    std::ios::sync_with_stdio(false);
    unsigned zeros = 0;
    for (std::size_t start = 0; start < bytes.size(); ++start) {
        if (!bytes[start]) {
            zeros = std::min(zeros + 1, MaxWidth - 1);
            continue;
        }
        auto try_width = [&](unsigned prefix) {
            if (prefix > bytes.size() - start) return;
            const auto list = index[prefix].find(key(bytes.data() + start, prefix));
            if (list == index[prefix].end()) return;
            for (auto id : list->second) {
                const auto& entry = patterns[id];
                if (entry.width > bytes.size() - start ||
                    std::memcmp(entry.digits.data(), bytes.data() + start, entry.width) != 0)
                    continue;
                for (unsigned pad = 0; pad <= std::min(zeros, MaxWidth - entry.width); ++pad) {
                    const unsigned width = pad + entry.width;
                    if (width <= 6 + entry.wire_bytes) continue;
                    write32(start - pad);
                    std::cout.put(static_cast<char>(width));
                    write32(id);
                }
            }
        };
        try_width(4);
        if (zeros >= 5) {
            try_width(1);
            try_width(2);
            try_width(3);
        }
        zeros = 0;
    }
    return !std::cout;
}
