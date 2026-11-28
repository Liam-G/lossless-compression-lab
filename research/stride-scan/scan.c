// scan.c - exact byte-stride scan.
// For each candidate row width w, build the 256x256 joint histogram of
// (above = x[i-w], cur = x[i]) and report
//   H_up(w)    = H(cur | above) = H(joint) - H(above marginal over the same pairs)
//   H_delta(w) = order-0 entropy of (cur - above) mod 256
// Pairs never straddle a window boundary. With several windows the pooled
// figure comes from the summed histograms; per-window figures are also printed.
//
// usage: scan FILE OUT.tsv WSPEC [off:len ...]
//   WSPEC = "1-4096" (inclusive range) or "@listfile" (one w per line)
//   windows default to the whole file.
// Output: '#' header lines, then one row per w:
//   w  n_pairs  H_up  H_delta  [H_up_win0 H_delta_win0 ...]
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>

#define MAXWIN 64
static uint32_t h4[4][65536];
static uint64_t joint[65536], pooled[65536];

static double ent_from(const uint64_t *c, int k, uint64_t *ntot) {
    uint64_t n = 0; double s = 0.0;
    for (int i = 0; i < k; i++) { uint64_t v = c[i]; if (v) { n += v; s += (double)v * log2((double)v); } }
    if (ntot) *ntot = n;
    if (!n) return 0.0;
    return log2((double)n) - s / (double)n;
}

// from a joint histogram [above<<8|cur] compute H_up and H_delta
static void derive(const uint64_t *j, double *hup, double *hdelta, uint64_t *npairs) {
    uint64_t ctx[256], del[256]; memset(ctx, 0, sizeof ctx); memset(del, 0, sizeof del);
    for (int a = 0; a < 256; a++) {
        const uint64_t *row = j + (a << 8);
        uint64_t s = 0;
        for (int b = 0; b < 256; b++) { uint64_t v = row[b]; if (v) { s += v; del[(b - a) & 255] += v; } }
        ctx[a] = s;
    }
    uint64_t n; double hj = ent_from(j, 65536, &n);
    double hc = ent_from(ctx, 256, NULL);
    *hup = hj - hc; *hdelta = ent_from(del, 256, NULL); *npairs = n;
}

static void count_pairs(const uint8_t *p, size_t len, size_t w) {
    memset(h4, 0, sizeof h4);
    if (len <= w) { for (int i = 0; i < 65536; i++) joint[i] = 0; return; }
    const uint8_t *a = p, *b = p + w; size_t n = len - w, i = 0;
    for (; i + 4 <= n; i += 4) {
        h4[0][((uint32_t)a[i] << 8) | b[i]]++;
        h4[1][((uint32_t)a[i + 1] << 8) | b[i + 1]]++;
        h4[2][((uint32_t)a[i + 2] << 8) | b[i + 2]]++;
        h4[3][((uint32_t)a[i + 3] << 8) | b[i + 3]]++;
    }
    for (; i < n; i++) h4[0][((uint32_t)a[i] << 8) | b[i]]++;
    for (int k = 0; k < 65536; k++) joint[k] = (uint64_t)h4[0][k] + h4[1][k] + h4[2][k] + h4[3][k];
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: %s FILE OUT.tsv WSPEC [off:len ...]\n", argv[0]); return 2; }
    int fd = open(argv[1], O_RDONLY); if (fd < 0) { perror("open"); return 1; }
    struct stat st; fstat(fd, &st); size_t fsize = (size_t)st.st_size;
    const uint8_t *x = mmap(NULL, fsize, PROT_READ, MAP_PRIVATE, fd, 0);
    if (x == MAP_FAILED) { perror("mmap"); return 1; }
    size_t nw = 0, *ws = NULL;
    if (argv[3][0] == '@') {
        FILE *lf = fopen(argv[3] + 1, "r"); if (!lf) { perror("wlist"); return 1; }
        size_t cap = 1024; ws = malloc(cap * sizeof *ws); unsigned long long v;
        while (fscanf(lf, "%llu", &v) == 1) { if (nw == cap) { cap *= 2; ws = realloc(ws, cap * sizeof *ws); } ws[nw++] = (size_t)v; }
        fclose(lf);
    } else {
        unsigned long long lo, hi; if (sscanf(argv[3], "%llu-%llu", &lo, &hi) != 2 || lo < 1 || hi < lo) { fprintf(stderr, "bad WSPEC\n"); return 2; }
        nw = hi - lo + 1; ws = malloc(nw * sizeof *ws); for (size_t i = 0; i < nw; i++) ws[i] = lo + i;
    }
    size_t woff[MAXWIN], wlen[MAXWIN]; int nwin = 0;
    for (int i = 4; i < argc && nwin < MAXWIN; i++) {
        unsigned long long o, l; if (sscanf(argv[i], "%llu:%llu", &o, &l) != 2 || o + l > fsize) { fprintf(stderr, "bad window %s\n", argv[i]); return 2; }
        woff[nwin] = o; wlen[nwin] = l; nwin++;
    }
    if (!nwin) { woff[0] = 0; wlen[0] = fsize; nwin = 1; }
    FILE *out = fopen(argv[2], "w"); if (!out) { perror("out"); return 1; }
    // order-0 over all analysed bytes, pooled and per window
    uint64_t c0[256], c0w[256]; memset(c0, 0, sizeof c0); size_t nbytes = 0;
    fprintf(out, "# file\t%s\n# file_size\t%zu\n# n_windows\t%d\n", argv[1], fsize, nwin);
    for (int k = 0; k < nwin; k++) {
        memset(c0w, 0, sizeof c0w);
        for (size_t i = 0; i < wlen[k]; i++) c0w[x[woff[k] + i]]++;
        for (int v = 0; v < 256; v++) c0[v] += c0w[v];
        nbytes += wlen[k];
        fprintf(out, "# window\t%d\t%zu\t%zu\tH0=%.17g\n", k, woff[k], wlen[k], ent_from(c0w, 256, NULL));
    }
    fprintf(out, "# n_bytes\t%zu\n# H0\t%.17g\n", nbytes, ent_from(c0, 256, NULL));
    fprintf(out, "# columns\tw\tn_pairs\tH_up\tH_delta%s\n", nwin > 1 ? "\t(H_up_k H_delta_k per window)" : "");
    for (size_t wi = 0; wi < nw; wi++) {
        size_t w = ws[wi];
        double hu[MAXWIN], hd[MAXWIN]; uint64_t np;
        memset(pooled, 0, sizeof pooled);
        for (int k = 0; k < nwin; k++) {
            count_pairs(x + woff[k], wlen[k], w);
            if (nwin > 1) derive(joint, &hu[k], &hd[k], &np);
            for (int i = 0; i < 65536; i++) pooled[i] += joint[i];
        }
        double HU, HD; derive(pooled, &HU, &HD, &np);
        fprintf(out, "%zu\t%llu\t%.17g\t%.17g", w, (unsigned long long)np, HU, HD);
        if (nwin > 1) for (int k = 0; k < nwin; k++) fprintf(out, "\t%.17g\t%.17g", hu[k], hd[k]);
        fputc('\n', out);
    }
    fclose(out);
    return 0;
}
