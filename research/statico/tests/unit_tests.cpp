// Assert-based unit tests. Each test is a function registered in main().
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>
#include "../src/rc.hpp"
#include "../src/sha256.hpp"
#include "../src/format.hpp"
#include "../src/order0.hpp"
#include "../src/grammar.hpp"
#include "../src/glz.hpp"
#include <fstream>
#include <iterator>

#define CHECK(c) do { if (!(c)) { std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); std::exit(1); } } while (0)

static std::string hex(const std::array<uint8_t, 32>& h) {
    static const char* d = "0123456789abcdef"; std::string s;
    for (uint8_t b : h) { s += d[b >> 4]; s += d[b & 15]; }
    return s;
}

static void test_sha256() {
    CHECK(hex(sha256((const uint8_t*)"", 0)) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    CHECK(hex(sha256((const uint8_t*)"abc", 3)) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    std::string m(1000000, 'a');  // FIPS 180-2 long vector
    CHECK(hex(sha256((const uint8_t*)m.data(), m.size())) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
}

static void test_rc_roundtrip() {
    std::mt19937_64 rng(1);
    const int N = 1000000, K = 300;
    std::vector<int> syms(N); std::vector<uint32_t> raw(N);
    for (int i = 0; i < N; i++) {
        double u = std::uniform_real_distribution<double>(0, 1)(rng);
        syms[i] = std::min(K - 1, (int)(K * u * u * u));   // skewed
        raw[i] = rng() & 0x1FFF;
    }
    RangeEncoder enc; AdaptiveModel m(K);
    for (int i = 0; i < N; i++) { m.encode(enc, syms[i]); enc.bits(raw[i], 13); }
    auto buf = enc.finish();
    RangeDecoder dec(buf.data(), buf.data() + buf.size()); AdaptiveModel m2(K);
    for (int i = 0; i < N; i++) { CHECK(m2.decode(dec) == syms[i]); CHECK(dec.bits(13) == raw[i]); }
    CHECK(!dec.overrun());
}

static void test_uniform_large() {
    std::mt19937_64 rng(2);
    for (uint64_t n : {1ull, 2ull, 65535ull, 65536ull, 65537ull, 1000000ull, (1ull << 40) + 3}) {
        std::vector<uint64_t> vals = {0, n - 1};
        for (int i = 0; i < 1000; i++) vals.push_back(rng() % n);
        RangeEncoder enc;
        for (auto v : vals) encode_uniform(enc, v, n);
        auto buf = enc.finish();
        RangeDecoder dec(buf.data(), buf.data() + buf.size());
        for (auto v : vals) CHECK(decode_uniform(dec, n) == v);
        CHECK(!dec.overrun());
    }
}

static void test_header() {
    for (Mode md : {STORED, ORDER0, GRAMMAR}) {
        Header h{md, 123456789012ull, {}};
        for (int i = 0; i < 32; i++) h.hash[i] = (uint8_t)(i * 7);
        auto b = write_header(h);
        const uint8_t* p = b.data(); Header g{};
        CHECK(read_header(p, b.data() + b.size(), g));
        CHECK(p == b.data() + b.size());
        CHECK(g.mode == md && g.size == h.size);
        if (md != STORED) CHECK(g.hash == h.hash);
    }
    const uint8_t bad[] = {'X', 'T', 'C', '1', 0, 0};
    const uint8_t* p = bad; Header g{};
    CHECK(!read_header(p, bad + sizeof bad, g));
}

static void test_stored_header_size() {
    CHECK(write_header(Header{STORED, 1ull << 40, {}}).size() <= 11);
}

static std::vector<uint8_t> read_file(const char* path) {
    std::ifstream f(path, std::ios::binary); CHECK(f.good());
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static std::vector<uint8_t> skewed_bytes(size_t n, uint64_t seed) {
    std::mt19937_64 rng(seed); std::vector<uint8_t> v(n);
    for (auto& b : v) { double u = std::uniform_real_distribution<double>(0, 1)(rng); b = (uint8_t)(255 * u * u); }
    return v;
}
static double order0_entropy_bytes(const std::vector<uint8_t>& v) {
    double c[256] = {0}; for (uint8_t b : v) c[b]++;
    double h = 0; for (double x : c) if (x) h -= x * std::log2(x / v.size());
    return h / 8;
}

static void test_order0_roundtrip() {
    for (auto& v : {skewed_bytes(1000000, 3), read_file("tests/data/sample.txt"), std::vector<uint8_t>{}, std::vector<uint8_t>{42}}) {
        auto z = order0_encode(v.data(), v.size());
        std::vector<uint8_t> out(v.size());
        CHECK(order0_decode(z.data(), z.data() + z.size(), out.data(), out.size()));
        CHECK(out == v);
    }
}

static void test_order0_near_entropy() {
    auto v = skewed_bytes(1000000, 4);
    auto z = order0_encode(v.data(), v.size());
    CHECK(z.size() <= 1.01 * order0_entropy_bytes(v) + 64);
}

static std::vector<std::vector<uint8_t>> grammar_inputs() {
    std::vector<std::vector<uint8_t>> v;
    v.push_back(read_file("tests/data/sample.txt"));
    std::mt19937_64 rng(5); std::vector<uint8_t> r(65536); for (auto& b : r) b = (uint8_t)rng(); v.push_back(r);
    std::string ab; for (int i = 0; i < 100000; i++) ab += "ab"; v.push_back(std::vector<uint8_t>(ab.begin(), ab.end()));
    v.push_back({7}); v.push_back({});
    return v;
}

static void test_grammar_expand_identity() {
    for (auto& x : grammar_inputs()) CHECK(expand(build_grammar(x.data(), x.size(), GrammarParams{})) == x);
}

static void test_grammar_reduces() {
    auto x = read_file("tests/data/sample.txt");
    auto g = build_grammar(x.data(), x.size(), GrammarParams{});
    CHECK(g.main.size() < x.size() / 3);
}

static void test_grammar_periodic() {
    std::vector<uint8_t> z(1000000, 0);   // order-0 cost of a constant run is already ~0: identity only
    CHECK(expand(build_grammar(z.data(), z.size(), GrammarParams{})) == z);
    std::mt19937_64 rng(6); uint8_t blk[16]; for (auto& b : blk) b = (uint8_t)rng();
    std::vector<uint8_t> x; for (int i = 0; i < 65536; i++) x.insert(x.end(), blk, blk + 16);
    auto g = build_grammar(x.data(), x.size(), GrammarParams{});
    size_t tot = g.main.size(); for (auto& r : g.rules) tot += r.size();
    CHECK(tot < 200);
    CHECK(expand(g) == x);
}

static void test_grammar_bodies_valid() {
    auto x = read_file("tests/data/sample.txt");
    auto g = build_grammar(x.data(), x.size(), GrammarParams{});
    for (size_t i = 0; i < g.rules.size(); i++) {
        CHECK(g.rules[i].size() >= 2);
        for (uint32_t s : g.rules[i]) CHECK(s < 256 + g.rules.size() && s != 256 + i);
    }
}

static bool glz_roundtrip(const Grammar& g, std::vector<uint8_t>* outp = nullptr) {
    auto ref = expand(g);
    auto z = glz_encode(g, ref.size());
    std::vector<uint8_t> out(ref.size());
    bool ok = glz_decode(z.data(), z.data() + z.size(), out.data(), out.size());
    if (outp) *outp = out;
    return ok && out == ref;
}

static void test_glz_roundtrip() {
    Grammar g;   // hand-built: R0="ab", R1=R0 R0 'c', main = R1 'x' R0 R1 R1
    g.rules = {{'a', 'b'}, {256, 256, 'c'}};
    g.main = {257, 'x', 256, 257, 257};
    CHECK(glz_roundtrip(g));
    CHECK(glz_roundtrip(Grammar{}));
    for (auto& x : grammar_inputs()) {
        auto gg = build_grammar(x.data(), x.size(), GrammarParams{});
        CHECK(glz_roundtrip(gg));
    }
}

static void test_glz_deep_nesting() {
    Grammar g;
    g.rules.push_back({'a', 'b'});
    for (uint32_t i = 1; i < 100000; i++) g.rules.push_back({256 + i - 1, (uint32_t)('a' + i % 26)});
    g.main = {256 + 99999, 256 + 99999};
    CHECK(glz_roundtrip(g));
}

static void test_glz_corrupt() {
    auto x = read_file("tests/data/sample.txt");
    auto g = build_grammar(x.data(), x.size(), GrammarParams{});
    auto z = glz_encode(g, x.size());
    std::vector<uint8_t> out(x.size());
    bool ok = glz_decode(z.data(), z.data() + z.size() / 2, out.data(), out.size());
    CHECK(!ok || out != x);
    std::mt19937_64 rng(9);
    for (int t = 0; t < 20; t++) {   // random byte flips: must not crash
        auto zz = z; zz[rng() % zz.size()] ^= (uint8_t)(1 + rng() % 255);
        (void)glz_decode(zz.data(), zz.data() + zz.size(), out.data(), out.size());
    }
}

int main() {
    test_sha256(); test_rc_roundtrip(); test_uniform_large(); test_header(); test_stored_header_size();
    test_order0_roundtrip(); test_order0_near_entropy();
    test_grammar_expand_identity(); test_grammar_reduces(); test_grammar_periodic(); test_grammar_bodies_valid();
    test_glz_roundtrip(); test_glz_deep_nesting(); test_glz_corrupt();
    // LATER_TESTS
    std::puts("all tests passed");
}
