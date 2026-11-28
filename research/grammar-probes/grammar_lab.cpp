// Grammar construction by repeated suffix-array rounds.
//
// Working sequence W = main SEP body_0 SEP body_1 ... so rule bodies keep being compressed.
// Each round: suffix array + LCP over W, enumerate left-maximal repeats (LCP intervals), estimate the
// profit of turning each into a rule with an order-0 cost model, try the best batch, claim
// non-overlapping occurrences, rewrite. Stop when a round accepts nothing.
#include "../statico/src/grammar.hpp"
#include <cstdlib>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include "../statico/third_party/libsais/libsais.h"

std::vector<uint8_t> expand(const Grammar& g) {
    std::vector<uint8_t> out;
    std::vector<std::pair<const std::vector<uint32_t>*, size_t>> st;
    st.push_back({&g.main, 0});
    while (!st.empty()) {
        auto& [seq, i] = st.back();
        if (i == seq->size()) { st.pop_back(); continue; }
        uint32_t s = (*seq)[i++];
        if (s < 256) out.push_back((uint8_t)s);
        else st.push_back({&g.rules.at(s - 256), 0});
    }
    return out;
}

namespace {
const uint32_t SEP = 0xFFFFFFFFu;

struct Fenwick {
    std::vector<int32_t> t;
    explicit Fenwick(size_t n) : t(n + 1, 0) {}
    void add(size_t i) { for (i++; i < t.size(); i += i & (0 - i)) t[i]++; }
    int64_t prefix(size_t i) const { int64_t s = 0; for (; i > 0; i -= i & (0 - i)) s += t[i]; return s; }   // sum [0,i)
    int64_t range(size_t a, size_t b) const { return b > a ? prefix(b) - prefix(a) : 0; }                      // [a,b)
};

struct Cand { float profit; int32_t lb, rb, len; };

// Resolve unit rules, inline rules used exactly once, drop unreachable rules, renumber.
Grammar compact(Grammar g) {
    const size_t R = g.rules.size();
    std::vector<uint32_t> rep(256 + R);
    for (uint32_t s = 0; s < 256 + R; s++) {
        uint32_t t = s; size_t guard = 0;
        while (t >= 256 && g.rules[t - 256].size() == 1) { t = g.rules[t - 256][0]; if (++guard > R) throw std::runtime_error("internal: unit-rule cycle"); }
        rep[s] = t;
    }
    for (auto& x : g.main) x = rep[x];
    for (auto& b : g.rules) for (auto& x : b) x = rep[x];
    // uses over the part reachable from main
    std::vector<uint64_t> uses(R, 0);
    std::vector<uint8_t> seen(R, 0);
    std::vector<uint32_t> todo;
    auto visit_seq = [&](const std::vector<uint32_t>& q) {
        for (uint32_t x : q) if (x >= 256) { uses[x - 256]++; if (!seen[x - 256]) { seen[x - 256] = 1; todo.push_back(x - 256); } }
    };
    visit_seq(g.main);
    while (!todo.empty()) { uint32_t r = todo.back(); todo.pop_back(); visit_seq(g.rules[r]); }
    std::vector<uint32_t> newid(R, UINT32_MAX);
    uint32_t k = 0;
    for (size_t r = 0; r < R; r++) if (uses[r] >= 2 && g.rules[r].size() >= 2) newid[r] = k++;
    // flatten: copy a sequence, splicing in bodies of inlined rules (iteratively)
    auto flatten = [&](const std::vector<uint32_t>& q) {
        std::vector<uint32_t> out;
        std::vector<std::pair<const std::vector<uint32_t>*, size_t>> st = {{&q, 0}};
        while (!st.empty()) {
            auto& [sq, i] = st.back();
            if (i == sq->size()) { st.pop_back(); continue; }
            uint32_t x = (*sq)[i++];
            if (x < 256) out.push_back(x);
            else if (newid[x - 256] != UINT32_MAX) out.push_back(256 + newid[x - 256]);
            else st.push_back({&g.rules[x - 256], 0});
        }
        return out;
    };
    Grammar o;
    o.main = flatten(g.main);
    o.rules.resize(k);
    for (size_t r = 0; r < R; r++) if (newid[r] != UINT32_MAX) o.rules[newid[r]] = flatten(g.rules[r]);
    return o;
}

double g_power = std::getenv("GP_POWER") ? std::atof(std::getenv("GP_POWER")) : 0.0;
int g_space = std::getenv("GP_SPACE") ? std::atoi(std::getenv("GP_SPACE")) : 0;
int g_words = std::getenv("GP_WORDS") ? std::atoi(std::getenv("GP_WORDS")) : 0;
double secs() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
}  // namespace

Grammar build_grammar(const uint8_t* data, size_t n, const GrammarParams& prm) {
    Grammar g;
    if (n >= (size_t)INT32_MAX / 2) throw std::runtime_error("input too large for v1 (int32 suffix arrays)");
    std::vector<uint32_t> W(data, data + n);
    std::vector<int32_t> seg_start = {0};   // start of main, then of each body in W

    for (int round = 1;; round++) {
        double t0 = secs();
        const int32_t N = (int32_t)W.size();
        if (N < 4) break;
        const uint32_t nsym = 256 + (uint32_t)g.rules.size();

        // dense remap; SEP -> 0, symbol s -> 1 + s
        std::vector<int32_t> T(N);
        std::vector<int64_t> cnt(nsym, 0);
        for (int32_t i = 0; i < N; i++) {
            if (W[i] == SEP) T[i] = 0; else { T[i] = 1 + (int32_t)W[i]; cnt[W[i]]++; }
        }
        int64_t Nreal = 0; for (auto c : cnt) Nreal += c;

        std::vector<int32_t> SA(N);
        if (libsais_int(T.data(), SA.data(), N, (int32_t)nsym + 1, 0) != 0) throw std::runtime_error("libsais_int failed");
        std::vector<int32_t> LCP(N);
        {
            std::vector<int32_t> PLCP(N);
            if (libsais_plcp_int(T.data(), SA.data(), PLCP.data(), N) != 0) throw std::runtime_error("plcp failed");
            if (libsais_lcp(PLCP.data(), SA.data(), LCP.data(), N) != 0) throw std::runtime_error("lcp failed");
        }
        // prefix order-0 costs along W
        std::vector<double> cost(nsym);
        for (uint32_t s = 0; s < nsym; s++) cost[s] = cnt[s] ? std::log2((double)Nreal / cnt[s]) : 0;
        std::vector<double> P(N + 1, 0.0);
        for (int32_t i = 0; i < N; i++) P[i + 1] = P[i] + (W[i] == SEP ? 0.0 : cost[W[i]]);
        // BWT change prefix: Dp[i] = number of j in [1,i] with bwt[j] != bwt[j-1]  (left-maximality test)
        std::vector<int32_t> Dp(N, 0);
        auto bwt = [&](int32_t i) -> int64_t { return SA[i] ? (int64_t)T[SA[i] - 1] : -1; };
        for (int32_t i = 1; i < N; i++) Dp[i] = Dp[i - 1] + (bwt(i) != bwt(i - 1) || bwt(i) == 0);  // SEP never extends
        T.clear(); T.shrink_to_fit();

        auto seg_end = [&](int32_t p) -> int32_t {   // first SEP position after p (or N)
            auto it = std::upper_bound(seg_start.begin(), seg_start.end(), p);
            return it == seg_start.end() ? N : *it - 1;
        };

        // enumerate LCP intervals
        std::vector<Cand> cands;
        std::vector<std::pair<int32_t, int32_t>> st = {{0, 0}};   // (lcp, lb)
        auto process = [&](int32_t l, int32_t lb, int32_t rb) {
            if (l < 2) return;
            if (Dp[rb] - Dp[lb] == 0) return;              // not left-maximal: dominated by the left extension
            int32_t p = SA[lb];
            l = std::min(l, seg_end(p) - p);               // never cross a separator
            if (l < 2) return;
            if (g_words && round == 1) {      // LAB: first round = whole space-prefixed lowercase words only (GLZA -w)
                auto wc = [](uint32_t x) { return (x >= 'a' && x <= 'z') || (x >= '0' && x <= '9') || (x >= 0x80 && x < 256); };
                if (W[p] != ' ' || !wc(W[p + 1])) return;
                int32_t k = 1; while (k < l && wc(W[p + k])) k++;
                if (k != l) return;           // string must be exactly " word" (its end is checked per occurrence)
            }
            double occ = rb - lb + 1;
            double C = P[p + l] - P[p];
            double newc = std::log2((double)(Nreal + 1) / occ);
            double profit = occ * (C - newc) - C - prm.production_cost;
            if (profit > 0) {
                // LAB: GLZA-style ordering. score = profit * (saving per use / string cost)^power, and a penalty for
                // strings that end in a single space (prefer " word" over "word ").
                double ratio = std::max(1e-12, (C - newc) / C);
                double score = std::log(profit) + g_power * std::log(ratio);      // log space: no underflow
                if (g_space && l >= 2 && W[p + l - 1] == 32 && W[p + l - 2] != 32) score += std::log(0.03);
                cands.push_back({(float)score, lb, rb, l});
            }
        };
        for (int32_t i = 1; i <= N; i++) {
            int32_t li = i < N ? LCP[i] : 0;
            int32_t lb = i - 1;
            while (li < st.back().first) {
                auto [l, b] = st.back(); st.pop_back();
                process(l, b, i - 1);
                lb = b;
            }
            if (li > st.back().first) st.push_back({li, lb});
        }
        LCP.clear(); LCP.shrink_to_fit(); Dp.clear(); Dp.shrink_to_fit();
        if (cands.empty()) break;

        double bf = std::getenv("GP_BATCH") ? std::atof(std::getenv("GP_BATCH")) : prm.batch_frac;
        size_t B = std::max(prm.min_batch, (size_t)(bf * cands.size()));
        if (g_words && round == 1) B = cands.size();
        B = std::min(B, cands.size());
        std::partial_sort(cands.begin(), cands.begin() + B, cands.end(), [](const Cand& a, const Cand& b) { return a.profit > b.profit; });

        // select: claim non-overlapping, unclaimed occurrences
        std::vector<int32_t> mark(N, 0);   // 0 free, -1 interior of a claimed span, r+1 at the start of a span of rule r
        Fenwick starts(N);
        std::vector<int32_t> pos, take;
        size_t accepted = 0;
        for (size_t c = 0; c < B; c++) {
            const Cand& cd = cands[c];
            int32_t l = cd.len;
            pos.assign(SA.begin() + cd.lb, SA.begin() + cd.rb + 1);
            std::sort(pos.begin(), pos.end());
            take.clear();
            int64_t last_end = -1;
            for (int32_t p : pos) {
                if (p < last_end || p + l > seg_end(p)) continue;
                if (mark[p] != 0 || mark[p + l - 1] != 0 || starts.range(p + 1, p + l) != 0) continue;
                if (g_words && round == 1 && p + l < N) {
                    uint32_t x = W[p + l];
                    if ((x >= 'a' && x <= 'z') || (x >= '0' && x <= '9') || (x >= 0x80 && x < 256)) continue;
                }
                take.push_back(p); last_end = p + l;
            }
            double k = take.size();
            if (k < 2) continue;
            double C = P[take[0] + l] - P[take[0]];
            double profit = k * (C - std::log2((double)(Nreal + 1) / k)) - C - prm.production_cost;
            if (profit <= 0) continue;
            uint32_t r = (uint32_t)g.rules.size();
            g.rules.emplace_back(W.begin() + take[0], W.begin() + take[0] + l);
            for (int32_t p : take) {
                mark[p] = (int32_t)r + 1; starts.add(p);
                std::fill(mark.begin() + p + 1, mark.begin() + p + l, -1);
            }
            accepted++;
        }
        if (prm.verbose)
            std::fprintf(stderr, "round %d: N=%d syms=%u cands=%zu tried=%zu accepted=%zu (%.1fs)\n",
                         round, N, nsym, cands.size(), B, accepted, secs() - t0);
        if (!accepted) break;

        // rewrite W: claimed spans become their rule symbol; new bodies are appended as new segments
        size_t first_new = g.rules.size() - accepted;
        std::vector<uint32_t> W2; W2.reserve(N);
        std::vector<int32_t> seg2 = {0};
        for (int32_t i = 0; i < N;) {
            if (mark[i] > 0) { uint32_t r = (uint32_t)mark[i] - 1; W2.push_back(256 + r); i += (int32_t)g.rules[r].size(); }
            else { if (W[i] == SEP) seg2.push_back((int32_t)W2.size() + 1); W2.push_back(W[i]); i++; }
        }
        for (size_t r = first_new; r < g.rules.size(); r++) {
            W2.push_back(SEP); seg2.push_back((int32_t)W2.size());
            W2.insert(W2.end(), g.rules[r].begin(), g.rules[r].end());
        }
        W.swap(W2); seg_start.swap(seg2);
        // converged: left-over candidates only look profitable because their estimate counts overlapping occurrences
        if ((int64_t)N - (int64_t)W.size() < (int64_t)N / 100000) break;
    }

    // split W back into main + bodies (segment j>0 is the body of rule j-1)
    std::vector<std::vector<uint32_t>> segs(1);
    for (uint32_t s : W) { if (s == SEP) segs.emplace_back(); else segs.back().push_back(s); }
    if (segs.size() != g.rules.size() + 1) throw std::runtime_error("internal: segment count mismatch");
    g.main = std::move(segs[0]);
    for (size_t r = 0; r < g.rules.size(); r++) g.rules[r] = std::move(segs[r + 1]);
    return compact(std::move(g));
}
