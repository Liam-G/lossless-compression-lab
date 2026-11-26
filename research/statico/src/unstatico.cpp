// Decompressor: unstatico IN OUT
#include <cstdio>
#include "decode.hpp"
#include "io.hpp"

int main(int argc, char** argv) {
    if (argc != 3) { std::fprintf(stderr, "usage: unstatico IN OUT\n"); return 1; }
    std::vector<uint8_t> in, out; std::string err;
    if (!read_all(argv[1], in)) { std::fprintf(stderr, "cannot read %s\n", argv[1]); return 1; }
    int rc = decode_archive(in, out, err);
    if (rc) { std::fprintf(stderr, "unstatico: %s\n", err.c_str()); return rc; }
    if (!write_all(argv[2], out)) { std::fprintf(stderr, "cannot write %s\n", argv[2]); return 1; }
    return 0;
}
