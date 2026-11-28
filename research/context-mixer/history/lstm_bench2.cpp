#include <chrono>
#include <cstdio>
#include "../lstm.hpp"
using C = std::chrono::steady_clock;
int main() { int N = 128; LSTM L(N, 16, 0.002f); double tf = 0, tu = 0, tb = 0;
    for (int i = 0; i < 20000; i++) { int y = (i * 7 + i / 13) & 127;
        auto a = C::now(); L.forward(y); auto b = C::now(); tf += std::chrono::duration<double>(b - a).count(); }
    // output-gradient part of update only (no bptt): emulate
    for (int i = 0; i < 20000; i++) { auto a = C::now(); L.wn = 0; float* DH = &L.DHo[0]; std::memset(DH, 0, sizeof(float) * N); const float* HS = &L.Hs[0];
        int cnt = 0; for (int q = 0; q < 256; q++) { float d = L.probs[q] - (q == 5); if (std::fabs(d) < 1e-5f) continue; cnt++; float* w = &L.Wy[(size_t)q * N]; float* g = &L.gWy[(size_t)q * N];
            L.gby[q] += d; for (int k = 0; k < N; k++) { g[k] += d * HS[k]; DH[k] += d * w[k]; } }
        auto b = C::now(); tu += std::chrono::duration<double>(b - a).count(); if (i == 0) std::printf("output rows touched: %d of 256\n", cnt); }
    for (int i = 0; i < 2000; i++) { auto a = C::now(); L.bptt(); auto b = C::now(); tb += std::chrono::duration<double>(b - a).count(); }
    std::printf("forward %.1f us | output grad %.1f us | bptt+adam per window %.1f us (= %.1f us per byte at T=16)\n", tf / 20000 * 1e6, tu / 20000 * 1e6, tb / 2000 * 1e6, tb / 2000 * 1e6 / 16); }
