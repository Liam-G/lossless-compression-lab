// Byte-level LSTM predictor (lab, own code). Reads the previous byte, predicts a distribution over the next byte.
// Trained online with truncated back-propagation through time (window T) and Adam; deterministic (fixed init seed),
// so the decoder, running the same code on the same bytes, gets identical predictions.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
#ifdef CM3_LSTM_CUDA
#include "lstm_cuda.hpp"
#endif

struct LSTM {
    int N, T; float lr; long adam_t = 0; float decay = 0;   // decay > 0: lr / sqrt(1 + updates/decay)
    int training_stride = 1, skip_matches = 0;
    int training_phase = 0, matched_bytes = 0;
    std::vector<float> Wx, Wh, b, Wy, by;            // 4N x 256, 4N x N, 4N, 256 x N, 256
    bool two = false; std::vector<float> Wx2, gWx2, mWx2, vWx2; std::vector<int> xs2; int xprev = 0;
    std::vector<float> gWx, gWh, gb, gWy, gby;       // gradients
    std::vector<float> mWx, vWx, mWh, vWh, mb, vb, mWy, vWy, mby, vby;
    std::vector<float> h, c, probs;                  // current state and prediction
    // window storage
    std::vector<int> xs; std::vector<float> Ig, Fg, Og, Gg, Cs, Cp, Hs, Hp, DHo, Dout; int wn = 0;
#ifdef CM3_LSTM_CUDA
    CudaLstmGradients cuda_gradients;
#endif
    explicit LSTM(int n = 128, int t = 16, float lr_ = 0.01f, bool two_ = false) : N(n), T(t), lr(lr_), two(two_)
#ifdef CM3_LSTM_CUDA
        , cuda_gradients(n, t)
#endif
    {
        uint64_t s = 0x12345678ABCDEFull; auto rnd = [&]() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return ((s >> 11) * (1.0 / 9007199254740992.0)) * 2 - 1; };
        float sc = 1.0f / std::sqrt((float)N);
        Wx.resize((size_t)4 * N * 256); Wh.resize((size_t)4 * N * N); b.assign(4 * N, 0); Wy.resize((size_t)256 * N); by.assign(256, 0);
        for (auto& w : Wx) w = (float)rnd() * 0.1f; for (auto& w : Wh) w = (float)rnd() * sc; for (auto& w : Wy) w = (float)rnd() * sc;
        for (int k = 0; k < N; k++) b[N + k] = 1.0f;   // forget-gate bias
        auto z = [](std::vector<float>& v, size_t n) { v.assign(n, 0); };
        z(gWx, Wx.size()); z(gWh, Wh.size()); z(gb, b.size()); z(gWy, Wy.size()); z(gby, 256);
        z(mWx, Wx.size()); z(vWx, Wx.size()); z(mWh, Wh.size()); z(vWh, Wh.size()); z(mb, b.size()); z(vb, b.size());
        z(mWy, Wy.size()); z(vWy, Wy.size()); z(mby, 256); z(vby, 256);
        h.assign(N, 0); c.assign(N, 0); probs.assign(256, 1.0f / 256);
        if (two) { Wx2.resize((size_t)4 * N * 256); for (auto& w : Wx2) w = (float)rnd() * 0.1f; gWx2.assign(Wx2.size(), 0); mWx2.assign(Wx2.size(), 0); vWx2.assign(Wx2.size(), 0); } xs2.assign(T, 0);
        xs.assign(T, 0); for (auto* v : {&Ig, &Fg, &Og, &Gg, &Cs, &Cp, &Hs, &Hp, &DHo}) v->assign((size_t)T * N, 0); Dout.assign((size_t)T * 256, 0);
        forward(0);
    }
    static float sg(float x) { return 1.0f / (1.0f + std::exp(-x)); }
    // advance one step with input byte x; stores activations at window slot wn
    void forward(int x) {
        std::vector<float> zz(4 * N);
        const float* __restrict__ wx = &Wx[(size_t)x * 4 * N]; const float* __restrict__ hh = h.data();
        for (int r = 0; r < 4 * N; r++) { const float* __restrict__ w = &Wh[(size_t)r * N]; float a = 0; for (int k = 0; k < N; k++) a += w[k] * hh[k]; zz[r] = a + b[r] + wx[r]; }
        xs2[wn] = xprev; if (two) { const float* __restrict__ w2 = &Wx2[(size_t)xprev * 4 * N]; for (int r = 0; r < 4 * N; r++) zz[r] += w2[r]; } xprev = x;
        for (int r = 0; r < 3 * N; r++) zz[r] = 1.0f / (1.0f + std::exp(-zz[r]));
        for (int r = 3 * N; r < 4 * N; r++) zz[r] = std::tanh(zz[r]);
        float* I = &Ig[(size_t)wn * N]; float* F = &Fg[(size_t)wn * N]; float* O = &Og[(size_t)wn * N]; float* G = &Gg[(size_t)wn * N];
        float* CS = &Cs[(size_t)wn * N]; float* CP = &Cp[(size_t)wn * N]; float* HS = &Hs[(size_t)wn * N]; float* HP = &Hp[(size_t)wn * N];
        xs[wn] = x;
        for (int k = 0; k < N; k++) { I[k] = zz[k]; F[k] = zz[N + k]; O[k] = zz[2 * N + k]; G[k] = zz[3 * N + k];
            CP[k] = c[k]; HP[k] = h[k]; c[k] = F[k] * c[k] + I[k] * G[k]; CS[k] = c[k]; h[k] = O[k] * std::tanh(c[k]); HS[k] = h[k]; }
        float mx = -1e30f;
        for (int y = 0; y < 256; y++) { const float* __restrict__ w = &Wy[(size_t)y * N]; float a = 0; for (int k = 0; k < N; k++) a += w[k] * hh[k]; probs[y] = a + by[y]; }
        for (int y = 0; y < 256; y++) mx = std::max(mx, probs[y]);
        for (int y = 0; y < 256; y++) probs[y] = std::exp(probs[y] - mx);
        float sum = 0; for (int y = 0; y < 256; y++) sum += probs[y];
        for (int y = 0; y < 256; y++) probs[y] = std::max(probs[y] / sum, 1e-6f);
    }
    // the byte that actually came: learn from the prediction error, then step forward with it as input
    void update(int y, bool predicted_by_match = false) {
        // output layer gradient for this step; store dh for BPTT
        if (training_phase == 0) {
            float* D = &Dout[(size_t)wn * 256];
            for (int q = 0; q < 256; q++) D[q] = probs[q] - (q == y ? 1.0f : 0.0f);
            matched_bytes += predicted_by_match;
        }
        wn++;
        if (wn == T) {
            if (training_phase == 0 && (skip_matches == 0 || matched_bytes < skip_matches)) bptt();
            if (++training_phase == training_stride) training_phase = 0;
            wn = 0;
            matched_bytes = 0;
        }
        forward(y);
    }
    void bptt() {
        // batched output layer: DH_t = Wy^T D_t (read Wy once), gWy += sum_t D_t (x) H_t, gby += sum_t D_t
#ifdef CM3_LSTM_CUDA
        cuda_gradients.backprop_output(Dout, Wy, Hs, DHo);
        for (int t = 0; t < T; t++) {
            for (int q = 0; q < 256; q++) gby[q] += Dout[(size_t)t * 256 + q];
        }
#else
        std::fill(DHo.begin(), DHo.end(), 0.0f);
        for (int q = 0; q < 256; q++) { const float* __restrict__ w = &Wy[(size_t)q * N]; float* __restrict__ g = &gWy[(size_t)q * N];
            for (int t = 0; t < T; t++) { float d = Dout[(size_t)t * 256 + q]; gby[q] += d; float* __restrict__ dh = &DHo[(size_t)t * N]; const float* __restrict__ hs = &Hs[(size_t)t * N];
                for (int k = 0; k < N; k++) dh[k] += d * w[k]; for (int k = 0; k < N; k++) g[k] += d * hs[k]; } }
#endif
        std::vector<float> dhn(N, 0), dcn(N, 0), dz(4 * N); std::vector<float> DZ((size_t)T * 4 * N);
        for (int t = T - 1; t >= 0; t--) {
            const float* I = &Ig[(size_t)t * N]; const float* F = &Fg[(size_t)t * N]; const float* O = &Og[(size_t)t * N]; const float* G = &Gg[(size_t)t * N];
            const float* CS = &Cs[(size_t)t * N]; const float* CP = &Cp[(size_t)t * N]; const float* HP = &Hp[(size_t)t * N]; const float* DH = &DHo[(size_t)t * N];
            for (int k = 0; k < N; k++) {
                float dh = DH[k] + dhn[k], tc = std::tanh(CS[k]);
                float dout = dh * tc, dc = dh * O[k] * (1 - tc * tc) + dcn[k];
                float di = dc * G[k], dg = dc * I[k], df = dc * CP[k]; dcn[k] = dc * F[k];
                dz[k] = di * I[k] * (1 - I[k]); dz[N + k] = df * F[k] * (1 - F[k]); dz[2 * N + k] = dout * O[k] * (1 - O[k]); dz[3 * N + k] = dg * (1 - G[k] * G[k]);
            }
            std::fill(dhn.begin(), dhn.end(), 0.0f);
            float* __restrict__ gx = &gWx[(size_t)xs[t] * 4 * N]; for (int r = 0; r < 4 * N; r++) { gb[r] += dz[r]; gx[r] += dz[r]; }
            if (two) { float* __restrict__ g2 = &gWx2[(size_t)xs2[t] * 4 * N]; for (int r = 0; r < 4 * N; r++) g2[r] += dz[r]; }
            float* __restrict__ dn = dhn.data(); std::memcpy(&DZ[(size_t)t * 4 * N], dz.data(), sizeof(float) * 4 * N);
            for (int r = 0; r < 4 * N; r++) { float d = dz[r]; const float* __restrict__ w = &Wh[(size_t)r * N]; for (int k = 0; k < N; k++) dn[k] += d * w[k]; }
        }
#ifdef CM3_LSTM_CUDA
        cuda_gradients.backprop_recurrent(DZ, Hp, gWh, gWy);
#else
        for (int r = 0; r < 4 * N; r++) { float* __restrict__ g = &gWh[(size_t)r * N];
            for (int t = 0; t < T; t++) { float d = DZ[(size_t)t * 4 * N + r]; const float* __restrict__ hp = &Hp[(size_t)t * N]; for (int k = 0; k < N; k++) g[k] += d * hp[k]; } }
#endif
        adam_t++;
        const float b1 = 0.9f, b2 = 0.999f, eps = 1e-6f; float lrt = decay > 0 ? lr / std::sqrt(1.0f + (float)adam_t / decay) : lr;
        float c1 = 1 - std::pow(b1, (float)adam_t), c2 = 1 - std::pow(b2, (float)adam_t), a1 = lrt / c1, ic2 = 1.0f / c2;
        auto apply = [&](float* __restrict__ W, float* __restrict__ G, float* __restrict__ M, float* __restrict__ V, size_t n) {
            for (size_t q = 0; q < n; q++) { float g = std::max(-5.0f, std::min(5.0f, G[q]));
                M[q] = b1 * M[q] + (1 - b1) * g; V[q] = b2 * V[q] + (1 - b2) * g * g; W[q] -= a1 * M[q] / (std::sqrt(V[q] * ic2) + eps); G[q] = 0; } };
        apply(Wh.data(), gWh.data(), mWh.data(), vWh.data(), Wh.size()); apply(b.data(), gb.data(), mb.data(), vb.data(), b.size());
        apply(Wy.data(), gWy.data(), mWy.data(), vWy.data(), Wy.size()); apply(by.data(), gby.data(), mby.data(), vby.data(), by.size());
        // lazy Adam for the input weights: only the byte columns used in this window
        bool seen[256] = {}; for (int t = 0; t < T; t++) { int xc = xs[t]; if (seen[xc]) continue; seen[xc] = true; size_t o = (size_t)xc * 4 * N;
            apply(&Wx[o], &gWx[o], &mWx[o], &vWx[o], 4 * N); }
        if (two) { bool seen2[256] = {}; for (int t = 0; t < T; t++) { int xc = xs2[t]; if (seen2[xc]) continue; seen2[xc] = true; size_t o = (size_t)xc * 4 * N;
            apply(&Wx2[o], &gWx2[o], &mWx2[o], &vWx2[o], 4 * N); } }
    }
    // probability that the next bit is 1 given the bits of this byte seen so far (node = 1 followed by those bits)
    float pbit(int node, int bitpos) const {   // bitpos 7..0
        int depth = 7 - bitpos; int lo = (node - (1 << depth)) << (8 - depth), span = 1 << (8 - depth);
        float p0 = 0, p1 = 0; for (int y = lo; y < lo + span / 2; y++) p0 += probs[y]; for (int y = lo + span / 2; y < lo + span; y++) p1 += probs[y];
        return p1 / (p0 + p1);
    }
};
