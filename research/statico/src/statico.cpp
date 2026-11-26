// Compressor CLI:
//   statico c [--mode=order0|grammar] [--prod-cost=X] [--grammar-limit=BYTES] [-v] IN OUT
//   statico d IN OUT
// Every archive is decoded in memory and compared before it is written.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include "decode.hpp"
#include "io.hpp"
#include "grammar.hpp"
#include "glz.hpp"

static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

int main(int argc, char** argv) {
    if (argc < 2) goto usage;
    {
        std::string cmd = argv[1];
        std::string mode = "grammar"; double prod_cost = 6.0; int verbose = 0;
        uint64_t grammar_limit = 256ull << 20;   // v1 scope: larger inputs would exceed the 10 GB budget
        std::vector<const char*> files;
        for (int i = 2; i < argc; i++) {
            if (!std::strncmp(argv[i], "--mode=", 7)) mode = argv[i] + 7;
            else if (!std::strncmp(argv[i], "--prod-cost=", 12)) prod_cost = std::atof(argv[i] + 12);
            else if (!std::strncmp(argv[i], "--grammar-limit=", 16)) grammar_limit = std::strtoull(argv[i] + 16, nullptr, 10);
            else if (!std::strcmp(argv[i], "-v")) verbose = 1;
            else files.push_back(argv[i]);
        }
        if (files.size() != 2) goto usage;
        std::vector<uint8_t> in, out; std::string err;
        if (!read_all(files[0], in)) { std::fprintf(stderr, "cannot read %s\n", files[0]); return 1; }
        if (cmd == "d") {
            int rc = decode_archive(in, out, err);
            if (rc) { std::fprintf(stderr, "statico: %s\n", err.c_str()); return rc; }
        } else if (cmd == "c") {
            double t0 = now();
            Header h{ORDER0, in.size(), sha256(in.data(), in.size())};
            std::vector<uint8_t> payload;
            if (mode == "grammar" && in.size() > grammar_limit) {
                std::fprintf(stderr, "statico: input is larger than the grammar limit (%llu bytes); using order-0 mode\n", (unsigned long long)grammar_limit);
                mode = "order0";
            }
            if (mode == "order0") payload = order0_encode(in.data(), in.size());
            else if (mode == "grammar") {
                GrammarParams gp; gp.production_cost = prod_cost; gp.verbose = verbose;
                Grammar g = build_grammar(in.data(), in.size(), gp);
                double tg = now();
                payload = glz_encode(g, in.size());
                h.mode = GRAMMAR;
                if (verbose) {
                    size_t bs = 0; for (auto& r : g.rules) bs += r.size();
                    std::fprintf(stderr, "grammar: main=%zu rules=%zu body symbols=%zu, build %.1fs, glz %.1fs\n",
                                 g.main.size(), g.rules.size(), bs, tg - t0, now() - tg);
                }
            }
            else { std::fprintf(stderr, "unknown mode %s\n", mode.c_str()); return 1; }
            out = write_header(h);
            out.insert(out.end(), payload.begin(), payload.end());
            std::vector<uint8_t> stored = write_header(Header{STORED, in.size(), {}});
            if (out.size() >= stored.size() + in.size()) { out = stored; out.insert(out.end(), in.begin(), in.end()); }
            double t1 = now();
            std::vector<uint8_t> back;
            if (decode_archive(out, back, err) || back != in) { std::fprintf(stderr, "statico: INTERNAL ERROR, self-check failed: %s\n", err.c_str()); return 3; }
            if (verbose) std::fprintf(stderr, "%zu -> %zu bytes, encode %.2fs, verify %.2fs\n", in.size(), out.size(), t1 - t0, now() - t1);
        } else goto usage;
        if (!write_all(files[1], out)) { std::fprintf(stderr, "cannot write %s\n", files[1]); return 1; }
        return 0;
    }
usage:
    std::fprintf(stderr, "usage: statico c [--mode=order0|grammar] [--prod-cost=X] [--grammar-limit=BYTES] [-v] IN OUT\n       statico d IN OUT\n");
    return 1;
}
