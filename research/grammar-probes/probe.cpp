// M3 probe (throwaway lab code): decode a statico GRAMMAR archive, record every GLZ event with what the
// decoder knows at that moment, then replay candidate symbol coders as ONLINE adaptive cost estimates.
// usage: probe ARCHIVE [shuffle-seed]
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>
#include "../statico/src/format.hpp"
#include "../statico/src/glz.hpp"
#include "../statico/src/io.hpp"

enum : uint8_t { REF = 0, NEWB = 1, NEWR = 2, CLOSE = 3 };
struct Ev {
    uint32_t id;        // decoder id (definition order); for NEWR patched at CLOSE
    uint32_t prev_id;   // last completed symbol before this event (UINT32_MAX at start)
    uint32_t aux;       // REF: index k in class list; NEWR: body length; NEWB: byte
    uint32_t csize;     // REF: class list size at this moment
    uint64_t len;       // expansion length (REF/CLOSE)
    uint8_t type, cls, prevb, fb, lb;
};

static std::vector<Ev> E;
static std::vector<uint32_t> sym_cls;     // by decoder id
static std::vector<uint8_t> sym_fb, sym_lb;
static std::vector<uint64_t> sym_len;

static bool record(const uint8_t* p, const uint8_t* end, std::vector<uint8_t>& outv) {
    using namespace glz;
    uint8_t* out = outv.data(); size_t n_out = outv.size();
    RangeDecoder rc(p, end); Models m;
    uint64_t main_len = get_bits(rc, 48);
    std::vector<uint64_t> off, len;
    std::vector<std::vector<uint32_t>> cl(NCLASS);
    struct Frame { uint64_t remaining; int64_t start; int cls; size_t ev; };
    std::vector<Frame> st = {{main_len, -1, 0, 0}};
    size_t pos = 0; uint32_t last = UINT32_MAX;
    while (!st.empty()) {
        Frame& f = st.back();
        if (f.remaining == 0) {
            if (f.start >= 0) {
                off.push_back((uint64_t)f.start); len.push_back(pos - (uint64_t)f.start);
                uint32_t id = (uint32_t)(off.size() - 1);
                cl[f.cls].push_back(id);
                E[f.ev].id = id;
                Ev c{}; c.type = CLOSE; c.id = id; c.cls = (uint8_t)f.cls; c.len = pos - f.start;
                c.fb = out[f.start]; c.lb = out[pos - 1]; c.prev_id = last; E.push_back(c);
                sym_cls.push_back(f.cls); sym_fb.push_back(c.fb); sym_lb.push_back(c.lb); sym_len.push_back(c.len);
                last = id;
            }
            st.pop_back(); continue;
        }
        f.remaining--;
        Ev e{}; e.prevb = pos ? out[pos - 1] : 0; e.prev_id = last;
        int ev = m.event.decode(rc);
        if (ev != EV_NEW) {
            auto& list = cl[ev];
            uint64_t k = decode_uniform(rc, list.size());
            uint32_t id = list[k];
            std::memcpy(out + pos, out + off[id], len[id]);
            e.type = REF; e.id = id; e.cls = (uint8_t)ev; e.aux = (uint32_t)k; e.csize = (uint32_t)list.size();
            e.len = len[id]; e.fb = out[pos]; e.lb = out[pos + len[id] - 1];
            pos += len[id]; last = id; E.push_back(e);
        } else {
            int c = m.cls.decode(rc);
            int is_rule = m.kind.decode(rc);
            e.cls = (uint8_t)c;
            if (!is_rule) {
                uint8_t b = (uint8_t)rc.bits(8); out[pos] = b;
                off.push_back(pos); len.push_back(1); uint32_t id = (uint32_t)(off.size() - 1); cl[c].push_back(id);
                e.type = NEWB; e.id = id; e.aux = b; e.len = 1; e.fb = e.lb = b;
                sym_cls.push_back(c); sym_fb.push_back(b); sym_lb.push_back(b); sym_len.push_back(1);
                pos++; last = id; E.push_back(e);
            } else {
                int b = m.lenb.decode(rc);
                uint64_t L1 = (1ull << (b - 1)) | get_bits(rc, b - 1);
                e.type = NEWR; e.aux = (uint32_t)(L1 + 1); E.push_back(e);
                st.push_back({L1 + 1, (int64_t)pos, c, E.size() - 1});
            }
        }
    }
    return pos == n_out && !rc.overrun();
}

// ---------- cost helpers ----------
static double lg(double x) { return std::log2(x); }
struct Ctx {   // many AdaptiveModels indexed by context
    std::vector<AdaptiveModel> v;
    Ctx(size_t nctx, int nsym, int inc = 24, uint32_t lim = 1u << 16) : v(nctx, AdaptiveModel(nsym, inc, lim)) {}
    double code(size_t c, int s) { double b = v[c].cost_bits(s); v[c].update(s); return b; }
};
static double len_bits(AdaptiveModel& lenb, uint32_t L) {   // body length L>=2 as in glz
    uint64_t L1 = L - 1; int b = glz::bitlen(L1);
    double c = lenb.cost_bits(b) + (b - 1); lenb.update(b); return c;
}
struct Totals { double ev = 0, idx = 0, newo = 0, extra = 0; double all() const { return ev + idx + newo + extra; } };
static void report(const char* name, const Totals& t, double base) {
    std::printf("%-58s %12.0f bytes  (%+6.2f%%)  [event %.0f  index %.0f  new %.0f  extra %.0f]\n", name, t.all() / 8,
                base > 0 ? 100.0 * (t.all() / 8 - base) / base : 0.0, t.ev / 8, t.idx / 8, t.newo / 8, t.extra / 8);
    std::fflush(stdout);
}

// Generic class+index coder with a context function for the event; NEW overhead as in glz.
template <class F>
static Totals run_ctx(size_t nctx, F ctx_of) {
    Totals t; Ctx evm(nctx, glz::NCLASS + 1); AdaptiveModel cls(glz::NCLASS), kind(2), lenb(40);
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) continue;
        size_t c = ctx_of(i);
        if (e.type == REF) { t.ev += evm.code(c, e.cls); t.idx += lg(e.csize); }
        else {
            t.ev += evm.code(c, glz::EV_NEW);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
        }
    }
    return t;
}

static int ctype(uint8_t b) {   // coarse character type of a byte
    if (b >= 'a' && b <= 'z') return 0;
    if (b >= 'A' && b <= 'Z') return 1;
    if (b >= '0' && b <= '9') return 2;
    if (b == ' ') return 3;
    if (b == '\n') return 4;
    if (b == '[' || b == ']') return 5;
    if (b == '<' || b == '>') return 6;
    if (b == '&' || b == ';') return 7;
    if (b == '.' || b == ',' || b == '\'' || b == '"') return 8;
    if (b == '|' || b == '=' || b == '{' || b == '}') return 9;
    if (b >= 0x80) return 10;
    return 11;
}

// First-byte bucketed coder: event (class|NEW) given ctx; for REF: first byte given (prevb), then uniform within
// (class, first byte) bucket. Bucket sizes grow at definition completion.
template <class F>
static Totals run_fb(size_t nctx, F ctx_of, bool fb_given_class) {
    Totals t; Ctx evm(nctx, glz::NCLASS + 1); AdaptiveModel cls(glz::NCLASS), kind(2), lenb(40);
    Ctx fbm(fb_given_class ? 256 * glz::NCLASS : 256, 256, 24, 1u << 16);
    std::vector<uint32_t> bucket(glz::NCLASS * 256, 0);
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) { bucket[e.cls * 256 + e.fb]++; continue; }
        size_t c = ctx_of(i);
        if (e.type == REF) {
            t.ev += evm.code(c, e.cls);
            size_t fc = fb_given_class ? (size_t)e.cls * 256 + e.prevb : e.prevb;
            t.extra += fbm.code(fc, e.fb);
            t.idx += lg(bucket[e.cls * 256 + e.fb]);
        } else {
            t.ev += evm.code(c, glz::EV_NEW);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
            if (e.type == NEWB) bucket[e.cls * 256 + e.fb]++;
        }
    }
    return t;
}

// Exact counts: at definition send the exact total use count within its class range (c raw bits);
// symbols live in buckets by REMAINING uses (floor log2), so exhausted symbols leave and frequent ones move down.
static Totals run_remaining(bool ctx_prevtype) {
    Totals t; Ctx evm(ctx_prevtype ? 12 : 1, glz::NCLASS + 1); AdaptiveModel cls(glz::NCLASS), kind(2), lenb(40);
    std::vector<uint64_t> uses(sym_cls.size(), 0);
    for (auto& e : E) if (e.type == REF || e.type == NEWB || e.type == CLOSE) uses[e.id]++;   // refs + definition
    std::vector<uint64_t> rem(sym_cls.size(), 0);
    std::vector<uint64_t> bsize(64, 0);
    auto rb = [&](uint64_t r) { return glz::bitlen(r) - 1; };   // r >= 1
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        auto define = [&](uint32_t id) {
            t.extra += sym_cls[id];               // exact count inside [2^c, 2^(c+1))
            rem[id] = uses[id] - 1;                // the definition is one use
            if (rem[id]) bsize[rb(rem[id])]++;
        };
        if (e.type == CLOSE) { define(e.id); continue; }
        size_t c = ctx_prevtype ? ctype(e.prevb) : 0;
        if (e.type == REF) {
            uint32_t id = e.id; int b = rb(rem[id]);
            t.ev += evm.code(c, b); t.idx += lg(bsize[b]);
            bsize[b]--; rem[id]--;
            if (rem[id]) bsize[rb(rem[id])]++;
        } else {
            t.ev += evm.code(c, glz::EV_NEW);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
            if (e.type == NEWB) define(e.id);
        }
    }
    return t;
}

// Recency: a move-to-front list of the last K distinct symbols; a hit is coded as event MTF + rank (log bucket + raw bits).
static Totals run_mtf(int K, int max_cls) {
    Totals t; AdaptiveModel evm(glz::NCLASS + 2), cls(glz::NCLASS), kind(2), lenb(40), rk(16);
    const int EV_MTF = glz::NCLASS + 1;
    std::vector<uint32_t> q;   // front = most recent
    auto touch = [&](uint32_t id) {
        if (sym_cls[id] > (uint32_t)max_cls) return;
        auto it = std::find(q.begin(), q.end(), id);
        if (it != q.end()) q.erase(it);
        q.insert(q.begin(), id); if ((int)q.size() > K) q.pop_back();
    };
    long hits = 0, refs = 0;
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) { touch(e.id); continue; }
        if (e.type == REF) {
            refs++;
            auto it = std::find(q.begin(), q.end(), e.id);
            if (it != q.end()) {
                hits++; int r = (int)(it - q.begin()); int b = glz::bitlen(r);   // 0 -> 0, 1 -> 1, 2..3 -> 2
                t.ev += evm.cost_bits(EV_MTF); evm.update(EV_MTF);
                t.idx += rk.cost_bits(b) + (b > 1 ? b - 1 : 0); rk.update(b);
            } else { t.ev += evm.cost_bits(e.cls); evm.update(e.cls); t.idx += lg(e.csize); }
            touch(e.id);
        } else {
            t.ev += evm.cost_bits(glz::EV_NEW); evm.update(glz::EV_NEW);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
            if (e.type == NEWB) touch(e.id);
        }
    }
    std::printf("   mtf K=%d max_cls=%d: %ld of %ld refs hit (%.1f%%)\n", K, max_cls, hits, refs, 100.0 * hits / refs);
    return t;
}

// Order-1 on symbol ids (PPM-C style, escape to the plain class+index coder). Ceiling estimate, beyond the design.
static Totals run_o1(const std::vector<uint32_t>& prev) {
    Totals t; AdaptiveModel evm(glz::NCLASS + 1), cls(glz::NCLASS), kind(2), lenb(40);
    struct Tab { uint32_t tot = 0; std::vector<std::pair<uint32_t, uint32_t>> v; };
    std::unordered_map<uint32_t, Tab> ctx; ctx.reserve(1 << 22);
    long hit = 0, refs = 0;
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) continue;
        uint32_t pc = prev[i];
        Tab* tab = pc == UINT32_MAX ? nullptr : &ctx[pc];
        bool coded = false;
        uint32_t want = e.type == REF ? e.id : UINT32_MAX - 1;   // NEW is a "symbol" too
        if (tab && tab->tot) {
            double den = tab->tot + tab->v.size();
            auto it = std::find_if(tab->v.begin(), tab->v.end(), [&](auto& p) { return p.first == want; });
            if (it != tab->v.end()) { t.extra += lg(den / it->second); it->second++; coded = true; if (e.type == REF) hit++; }
            else { t.extra += lg(den / tab->v.size()); tab->v.push_back({want, 1}); }
            tab->tot++;
        } else if (tab) { tab->v.push_back({want, 1}); tab->tot = 1; }
        if (e.type == REF) refs++;
        if (!coded) {
            if (e.type == REF) { t.ev += evm.cost_bits(e.cls); evm.update(e.cls); t.idx += lg(e.csize); }
            else { t.ev += evm.cost_bits(glz::EV_NEW); evm.update(glz::EV_NEW); }
        }
        if (e.type != REF) {
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
        }
    }
    std::printf("   order-1 ids: %ld of %ld refs predicted inside the context (%.1f%%)\n", hit, refs, 100.0 * hit / refs);
    return t;
}

// Adaptive per-symbol counts: at definition cnt = prior(class) * a; each use adds inc. P(x) = cnt/total over
// all defined symbols. Optional recency queue in front (event MTF). Decoder-reproducible (Fenwick tree).
static Totals run_adapt(double a, double inc, int K) {
    Totals t; AdaptiveModel evm(3), cls(glz::NCLASS), kind(2), lenb(40), rk(16);   // 0 sym, 1 NEW, 2 MTF
    std::vector<double> cnt(sym_cls.size(), 0); double total = 0;
    std::vector<uint32_t> q;
    auto touch = [&](uint32_t id) {
        if (!K) return;
        auto it = std::find(q.begin(), q.end(), id);
        if (it != q.end()) q.erase(it);
        q.insert(q.begin(), id); if ((int)q.size() > K) q.pop_back();
    };
    auto define = [&](uint32_t id) { cnt[id] = a * 1.5 * (double)(1ull << sym_cls[id]); total += cnt[id]; touch(id); };
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) { define(e.id); continue; }
        if (e.type == REF) {
            auto it = K ? std::find(q.begin(), q.end(), e.id) : q.end();
            if (it != q.end()) {
                int r = (int)(it - q.begin()), b = glz::bitlen(r);
                t.ev += evm.cost_bits(2); evm.update(2);
                t.idx += rk.cost_bits(b) + (b > 1 ? b - 1 : 0); rk.update(b);
            } else {
                t.ev += evm.cost_bits(0); evm.update(0);
                t.idx += lg(total / cnt[e.id]);
            }
            cnt[e.id] += inc; total += inc; touch(e.id);
        } else {
            t.ev += evm.cost_bits(1); evm.update(1);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
            if (e.type == NEWB) define(e.id);
        }
    }
    return t;
}

// Combined compliant coder: event {NEW, MTF, class c} | prev byte type; MTF rank; else first byte | (class, prev byte)
// and uniform index in the (class, first byte) bucket.
static Totals run_combo(int K) {
    Totals t; Ctx evm(12, glz::NCLASS + 2); AdaptiveModel cls(glz::NCLASS), kind(2), lenb(40), rk(16);
    Ctx fbm(256 * glz::NCLASS, 256);
    const int EV_MTF = glz::NCLASS + 1;
    std::vector<uint32_t> bucket(glz::NCLASS * 256, 0), q;
    auto touch = [&](uint32_t id) {
        auto it = std::find(q.begin(), q.end(), id);
        if (it != q.end()) q.erase(it);
        q.insert(q.begin(), id); if ((int)q.size() > K) q.pop_back();
    };
    for (size_t i = 0; i < E.size(); i++) {
        const Ev& e = E[i];
        if (e.type == CLOSE) { bucket[e.cls * 256 + e.fb]++; touch(e.id); continue; }
        size_t c = ctype(e.prevb);
        if (e.type == REF) {
            auto it = std::find(q.begin(), q.end(), e.id);
            if (it != q.end()) {
                int r = (int)(it - q.begin()), b = glz::bitlen(r);
                t.ev += evm.code(c, EV_MTF); t.idx += rk.cost_bits(b) + (b > 1 ? b - 1 : 0); rk.update(b);
            } else {
                t.ev += evm.code(c, e.cls);
                t.extra += fbm.code((size_t)e.cls * 256 + e.prevb, e.fb);
                t.idx += lg(bucket[e.cls * 256 + e.fb]);
            }
            touch(e.id);
        } else {
            t.ev += evm.code(c, glz::EV_NEW);
            t.newo += cls.cost_bits(e.cls); cls.update(e.cls);
            t.newo += kind.cost_bits(e.type == NEWR); kind.update(e.type == NEWR);
            t.newo += e.type == NEWB ? 8 : len_bits(lenb, e.aux);
            if (e.type == NEWB) { bucket[e.cls * 256 + e.fb]++; touch(e.id); }
        }
    }
    return t;
}

int main(int argc, char** argv) {
    std::vector<uint8_t> in;
    if (argc < 2 || !read_all(argv[1], in)) { std::fprintf(stderr, "usage: probe ARCHIVE\n"); return 1; }
    const uint8_t* p = in.data(); const uint8_t* end = p + in.size(); Header h{};
    if (!read_header(p, end, h) || h.mode != GRAMMAR) { std::fprintf(stderr, "not a grammar archive\n"); return 1; }
    std::vector<uint8_t> out(h.size);
    E.reserve(14000000);
    if (!record(p, end, out)) { std::fprintf(stderr, "decode failed\n"); return 1; }
    double actual = (double)in.size();
    size_t nref = 0, nnb = 0, nnr = 0;
    for (auto& e : E) { nref += e.type == REF; nnb += e.type == NEWB; nnr += e.type == NEWR; }
    std::printf("archive %.0f bytes, header %td bytes; events: %zu refs, %zu new bytes, %zu new rules; symbols %zu\n",
                actual, p - in.data(), nref, nnb, nnr, sym_cls.size());

    // 1. calibration: the current coder replayed
    Totals cur = run_ctx(1, [](size_t) { return (size_t)0; });
    double hdr = (double)(p - in.data()) + 6 + 5;
    std::printf("CALIBRATION: replay %.0f + header/flush %.0f = %.0f vs actual %.0f (%+.3f%%)\n", cur.all() / 8, hdr,
                cur.all() / 8 + hdr, actual, 100.0 * (cur.all() / 8 + hdr - actual) / actual);
    double base = cur.all() / 8;
    report("current coder (replay)", cur, base);

    if (argc > 2 && std::string(argv[2]) == "more") {
        for (double inc : {1.0, 4.0, 16.0, 64.0}) {
            char nm[96]; std::snprintf(nm, sizeof nm, "adaptive per-symbol counts, inc %.0f", inc);
            report(nm, run_adapt(1.0, inc, 0), base);
        }
        report("adaptive counts inc 16 + recency K=1024", run_adapt(1.0, 16.0, 1024), base);
        report("COMBO: recency 1024 + first byte | (class, prev byte) + event | type", run_combo(1024), base);
        report("COMBO with recency 4096", run_combo(4096), base);
        return 0;
    }
    // 2. breakdown by class
    {
        std::vector<double> evb(33, 0), idxb(33, 0); std::vector<long> cnt(33, 0); AdaptiveModel evm(33);
        for (auto& e : E) {
            if (e.type == CLOSE) continue;
            int s = e.type == REF ? e.cls : 32;
            double c = evm.cost_bits(s); evm.update(s);
            evb[s] += c; cnt[s]++; if (e.type == REF) idxb[s] += lg(e.csize);
        }
        std::printf("class  uses-range        refs     event-bytes   index-bytes   bits/ref\n");
        for (int s = 0; s < 33; s++) if (cnt[s])
            std::printf("%5s  %-14s %10ld %13.0f %13.0f %9.2f\n", s == 32 ? "NEW" : std::to_string(s).c_str(),
                        s == 32 ? "-" : (std::to_string(1ull << s) + ".." + std::to_string((2ull << s) - 1)).c_str(),
                        cnt[s], evb[s] / 8, idxb[s] / 8, (evb[s] + idxb[s]) / cnt[s]);
    }
    // 3. static order-0 ideal over the same stream (knows every count for free)
    {
        std::vector<uint64_t> uses(sym_cls.size(), 0); uint64_t N = 0, nnew = 0;
        for (auto& e : E) { if (e.type == CLOSE) continue; N++; if (e.type == REF) uses[e.id]++; else nnew++; }
        double b = 0; for (auto& e : E) if (e.type == REF) b -= lg((double)uses[e.id] / N);
        b -= nnew * lg((double)nnew / N);
        std::printf("STATIC ORDER-0 IDEAL (counts free, no defs): refs+new-flags %.0f bytes vs current event+index %.0f bytes\n",
                    b / 8, (cur.ev + cur.idx) / 8);
    }
    // 4. online candidates
    std::vector<uint8_t> pb(E.size()); for (size_t i = 0; i < E.size(); i++) pb[i] = E[i].prevb;
    std::vector<uint8_t> pbs = pb; std::mt19937_64 rng(12345); std::shuffle(pbs.begin(), pbs.end(), rng);
    report("event | prev byte (256 ctx)", run_ctx(256, [&](size_t i) { return (size_t)pb[i]; }), base);
    report("  CONTROL: prev byte shuffled", run_ctx(256, [&](size_t i) { return (size_t)pbs[i]; }), base);
    report("event | prev byte type (12 ctx)", run_ctx(12, [&](size_t i) { return (size_t)ctype(pb[i]); }), base);
    report("first byte | prev byte, then index in (class,first byte)", run_fb(256, [&](size_t i) { return (size_t)pb[i]; }, false), base);
    report("  same, first byte | (class, prev byte)", run_fb(256, [&](size_t i) { return (size_t)pb[i]; }, true), base);
    report("  CONTROL: prev byte shuffled", run_fb(256, [&](size_t i) { return (size_t)pbs[i]; }, false), base);
    report("exact counts, buckets by remaining uses", run_remaining(false), base);
    report("  same + event | prev byte type", run_remaining(true), base);
    report("recency queue K=256 (classes 0-3)", run_mtf(256, 3), base);
    report("recency queue K=1024 (all classes)", run_mtf(1024, 31), base);
    std::vector<uint32_t> prev(E.size()); for (size_t i = 0; i < E.size(); i++) prev[i] = E[i].prev_id;
    report("order-1 on symbol ids (PPM-C, ceiling; beyond design)", run_o1(prev), base);
    std::vector<uint32_t> prevs = prev; std::shuffle(prevs.begin(), prevs.end(), rng);
    report("  CONTROL: prev ids shuffled", run_o1(prevs), base);
    return 0;
}
