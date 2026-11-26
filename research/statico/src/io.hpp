// Whole-file read/write helpers for the CLIs.
#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

inline bool read_all(const char* path, std::vector<uint8_t>& v) {
    FILE* f = std::fopen(path, "rb"); if (!f) return false;
    v.clear(); uint8_t buf[1 << 16]; size_t k;
    while ((k = std::fread(buf, 1, sizeof buf, f)) > 0) v.insert(v.end(), buf, buf + k);
    bool ok = !std::ferror(f); std::fclose(f); return ok;
}
inline bool write_all(const char* path, const std::vector<uint8_t>& v) {
    FILE* f = std::fopen(path, "wb"); if (!f) return false;
    bool ok = std::fwrite(v.data(), 1, v.size(), f) == v.size();
    return (std::fclose(f) == 0) && ok;
}
