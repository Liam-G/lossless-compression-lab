// Lab: build a grammar with grammar_lab.cpp (env GP_POWER, GP_SPACE), GLZ-encode, verify, write a statico archive.
// usage: gbuild IN OUT [prod-cost]
#include <cstdio>
#include <cstdlib>
#include "../statico/src/decode.hpp"
#include "../statico/src/grammar.hpp"
#include "../statico/src/glz.hpp"
#include "../statico/src/io.hpp"
int main(int argc, char** argv) {
    std::vector<uint8_t> in; if (argc < 3 || !read_all(argv[1], in)) return 1;
    GrammarParams gp; gp.production_cost = argc > 3 ? std::atof(argv[3]) : 6.0; gp.verbose = 1;
    Grammar g = build_grammar(in.data(), in.size(), gp);
    if (expand(g) != in) { std::fprintf(stderr, "EXPAND MISMATCH\n"); return 3; }
    std::vector<uint8_t> out = write_header(Header{GRAMMAR, in.size(), sha256(in.data(), in.size())});
    auto pl = glz_encode(g, in.size()); out.insert(out.end(), pl.begin(), pl.end());
    std::vector<uint8_t> back; std::string err;
    if (decode_archive(out, back, err) || back != in) { std::fprintf(stderr, "ROUND TRIP FAILED %s\n", err.c_str()); return 3; }
    size_t bs = 0; for (auto& r : g.rules) bs += r.size();
    std::printf("main=%zu rules=%zu body=%zu archive=%zu\n", g.main.size(), g.rules.size(), bs, out.size());
    return write_all(argv[2], out) ? 0 : 1;
}
