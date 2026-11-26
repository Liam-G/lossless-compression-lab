// Archive decoding shared by `statico d` and `unstatico`.
#pragma once
#include <new>
#include <string>
#include <vector>
#include "format.hpp"
#include "order0.hpp"
#include "glz.hpp"
#include "sha256.hpp"

// Returns 0 on success, 2 on a corrupt or truncated archive (err says why).
inline int decode_archive(const std::vector<uint8_t>& in, std::vector<uint8_t>& out, std::string& err) {
    const uint8_t* p = in.data(); const uint8_t* end = p + in.size();
    Header h{};
    if (!read_header(p, end, h)) { err = "not a statico archive (bad header)"; return 2; }
    if (h.size > (1ull << 40)) { err = "implausible original size"; return 2; }
    try { out.assign(h.size, 0); } catch (const std::bad_alloc&) { err = "cannot allocate the claimed original size (corrupt header?)"; return 2; }
    bool ok = false;
    switch (h.mode) {
    case STORED:
        if ((uint64_t)(end - p) != h.size) { err = "stored payload has wrong length"; return 2; }
        std::copy(p, end, out.begin()); return 0;
    case ORDER0: ok = order0_decode(p, end, out.data(), out.size()); break;
    case GRAMMAR: ok = glz_decode(p, end, out.data(), out.size()); break;
    }
    if (!ok) { err = "payload truncated or corrupt"; return 2; }
    if (sha256(out.data(), out.size()) != h.hash) { err = "checksum mismatch"; return 2; }
    return 0;
}
