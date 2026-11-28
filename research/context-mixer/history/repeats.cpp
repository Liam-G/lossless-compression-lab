// How much of a file sits inside long blocks repeated from EARLIER in the file?
// Greedy parse: at each position find the longest earlier match (8-byte anchors, up to 32 candidates per anchor),
// take it if >= MINB bytes, else move on one byte. Also compares "most recent candidate" vs "best of 32 candidates".
// usage: repeats FILE
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>
#include "../../statico/src/io.hpp"
int main(int argc, char** argv) {
    std::vector<uint8_t> x; if (argc < 2 || !read_all(argv[1], x)) return 1; size_t n = x.size();
    const int HB = 24; std::vector<uint32_t> head(1u << HB, UINT32_MAX), prev(n, UINT32_MAX);
    auto key = [&](size_t i) { uint64_t v = 0; for (int k = 0; k < 8; k++) v = v << 8 | x[i + k]; v *= 0x9E3779B97F4A7C15ull; return (uint32_t)(v >> (64 - HB)); };
    const size_t th[4] = {32, 100, 1000, 10000}; size_t cover[4] = {0, 0, 0, 0}, cover1[4] = {0, 0, 0, 0}; size_t longest = 0, at = 0, from = 0;
    size_t i = 0, ins = 0;
    auto insert_upto = [&](size_t lim) { for (; ins < lim && ins + 8 <= n; ins++) { uint32_t k = key(ins); prev[ins] = head[k]; head[k] = (uint32_t)ins; } };
    while (i + 8 <= n) {
        insert_upto(i);
        uint32_t k = key(i); size_t best = 0, bestp = 0, first = 0; int c = 0;
        for (uint32_t p = head[k]; p != UINT32_MAX && c < 32; p = prev[p], c++) {
            size_t L = 0; while (i + L < n && x[p + L] == x[i + L]) L++;
            if (c == 0) first = L; if (L > best) { best = L; bestp = p; }
        }
        for (int t = 0; t < 4; t++) { if (best >= th[t]) cover[t] += best; if (first >= th[t]) cover1[t] += first; }
        if (best > longest) { longest = best; at = i; from = bestp; }
        i += best >= 32 ? best : 1;
    }
    std::printf("%s: %zu bytes\n", argv[1], n);
    for (int t = 0; t < 4; t++) std::printf("  bytes inside repeats of >= %5zu bytes: best of 32 candidates %5.1f%% | most recent only %5.1f%%\n", th[t], 100.0 * cover[t] / n, 100.0 * cover1[t] / n);
    std::printf("  longest repeated block: %zu bytes at %zu (copy of %zu)\n", longest, at, from);
    return 0;
}
