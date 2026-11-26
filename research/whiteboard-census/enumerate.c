// rep_fast.c -- exhaustive search for  d = R(c1,b1,r1) / R(c2,b2,r2),  R(c,b,r)
// = c*(b^r-1)/(b-1)
//
// Finds, for every d in [1, 2^N), the minimum "free" cost
//      F6(d) = min  bl(c1)+bl(b1)+bl(r1)+bl(c2)+bl(b2)+bl(r2)      (bl = binary
//      length)
// over ALL six-tuples with free cost <= K whose value is exactly d, and
//      F3(d) = min  bl(c)+bl(b)+bl(r)  over ALL triples with R(c,b,r) = d   (no
//      cost cap).
//
// Completeness argument (each step is exact or a rigorous bound):
//  (1) every triple costs >= 4 bits (bl(c)>=1, bl(b)>=2, bl(r)>=1), so in a
//  six-tuple of cost <= K
//      each triple costs <= S = K-4.  All triples of cost <= S are enumerated.
//  (2) r = 1: R(c,b,1) = c for every b > c, and (c, c+1, 1) is the cheapest
//  such triple, so only
//      b = c+1 is kept for r = 1 (the minimum cost of every d is unchanged).
//  (3) magnitude: c*b^(r-1) <= R(c,b,r) < 2*c*b^(r-1), so with x =
//  log2(c)+(r-1)*log2(b) we have
//      x <= log2 R < x+1.   1 <= R1/R2 < 2^N  implies  x1-N-1 < x2 < x1+1. Only
//      pairs inside this window (widened by a float slack) are tested; they are
//      tested EXACTLY (u64 or GMP).
//  (4) a triple of cost s is dropped only if x > max{x of triples with cost <=
//  K-s} + N + 3; such a
//      triple can be neither numerator nor denominator of a pair with total
//      cost <= K and quotient < 2^N.
//
// usage: rep_fast N K out_prefix        (K <= N-1 is what "any saving" needs; K
// = N-1 is the default use)
#include <gmp.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned __int128 u128;
static inline int bl(uint64_t x) { return x ? 64 - __builtin_clzll(x) : 0; }

typedef struct {
  double x;   // log2(c) + (r-1)*log2(b);  x <= log2(value) < x+1
  uint64_t v; // exact value when it fits in 64 bits (big == 0)
  uint32_t c, b, r;
  uint32_t big; // 0, or 1 + index into the mpz pool
} Trip;

#pragma pack(push, 1)
typedef struct {
  uint64_t d;
  uint32_t c1, b1, r1, c2, b2, r2, cost;
} Rec6;
typedef struct {
  uint64_t d;
  uint32_t c, b, r, cost;
} Rec3;
#pragma pack(pop)

static int N, K, S;
static uint64_t LIM; // 2^N
static uint8_t *F6, *F3;
static Rec6 *rec6;
static size_t nrec6, caprec6;
static Rec3 *rec3;
static size_t nrec3, caprec3;

static Trip *bucket[64];
static size_t nb[64], capb[64];
static mpz_t *pool;
static size_t npool, cappool;

static double slack(double x) { return 1e-3 + 1e-9 * fabs(x); }

static int exact_u64(uint32_t c, uint32_t b, uint32_t r, uint64_t *out) {
  // SMALL_BITS (test builds only): values >= 2^SMALL_BITS are forced onto the
  // GMP paths. The "denominator big, numerator small => V2 > V1" shortcut stays
  // valid for any SMALL_BITS.
#ifndef SMALL_BITS
#define SMALL_BITS 64
#endif
  u128 rep = 1;
  for (uint32_t k = 1; k < r; k++) {
    rep = rep * b + 1;
    if (rep >> SMALL_BITS)
      return 0;
  }
  u128 v = rep * c;
  if (v >> SMALL_BITS)
    return 0;
  *out = (uint64_t)v;
  return 1;
}

static int cmpx(const void *a, const void *b) {
  double xa = ((const Trip *)a)->x, xb = ((const Trip *)b)->x;
  return (xa > xb) - (xa < xb);
}

static uint64_t nhit;
static inline void hit(uint64_t d, int s, const Trip *a, const Trip *b) {
  nhit++;
  if (s < F6[d]) {
    F6[d] = (uint8_t)s;
    if (s < bl(d)) {
      if (nrec6 == caprec6) {
        caprec6 = caprec6 ? caprec6 * 2 : 1 << 16;
        rec6 = realloc(rec6, caprec6 * sizeof(Rec6));
        if (!rec6) {
          perror("realloc");
          exit(1);
        }
      }
      Rec6 *q = &rec6[nrec6++];
      q->d = d;
      q->c1 = a->c;
      q->b1 = a->b;
      q->r1 = a->r;
      q->c2 = b->c;
      q->b2 = b->b;
      q->r2 = b->r;
      q->cost = (uint32_t)s;
    }
  }
}

static void wr(const char *prefix, const char *suf, const void *p, size_t n) {
  char fn[4096];
  snprintf(fn, sizeof fn, "%s%s", prefix, suf);
  FILE *f = fopen(fn, "wb");
  if (!f) {
    perror(fn);
    exit(1);
  }
  if (n && fwrite(p, 1, n, f) != n) {
    perror("fwrite");
    exit(1);
  }
  fclose(f);
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s N K out_prefix\n", argv[0]);
    return 2;
  }
  N = atoi(argv[1]);
  K = atoi(argv[2]);
  const char *prefix = argv[3];
  if (N < 4 || N > 30 || K < 8 || K > 40) {
    fprintf(stderr, "bad N/K\n");
    return 2;
  }
  S = K - 4;
  LIM = 1ull << N;

  // ---------- pass 1: count triples per cost, max magnitude per cost
  // ----------
  uint64_t cnt[64] = {0}, cntraw[64] = {0};
  double maxx[64];
  for (int i = 0; i < 64; i++)
    maxx[i] = -1.0;
  for (int lb = 2; lb <= S - 2; lb++) {
    for (uint32_t b = 1u << (lb - 1); b < (1u << lb); b++) {
      double l2b = log2((double)b);
      for (uint32_t c = 1; c < b; c++) {
        int lc = bl(c);
        if (lc + lb + 1 > S)
          break;
        double l2c = log2((double)c);
        int maxlr = S - lc - lb;
        // r = 1 (only b = c+1 is kept, see (2))
        cntraw[lc + lb + 1]++; // raw count: r = 1 with every b > c
        if (b == c + 1) {
          int cost = lc + lb + 1;
          cnt[cost]++;
          if (l2c > maxx[cost])
            maxx[cost] = l2c;
        }
        for (int lr = 2; lr <= maxlr; lr++) {
          int cost = lc + lb + lr;
          uint32_t rlo = 1u << (lr - 1), rhi = (1u << lr) - 1;
          cnt[cost] += (uint64_t)(rhi - rlo + 1);
          cntraw[cost] += (uint64_t)(rhi - rlo + 1);
          double x = l2c + (double)(rhi - 1) * l2b;
          if (x > maxx[cost])
            maxx[cost] = x;
        }
      }
    }
  }
  double maxle[64];
  {
    double m = -1.0;
    for (int s = 0; s < 64; s++) {
      if (maxx[s] > m)
        m = maxx[s];
      maxle[s] = m;
    }
  }

  // ---------- pass 2: store triples that can take part in some pair ----------
  uint64_t kept[64] = {0};
  for (int lb = 2; lb <= S - 2; lb++) {
    for (uint32_t b = 1u << (lb - 1); b < (1u << lb); b++) {
      double l2b = log2((double)b);
      for (uint32_t c = 1; c < b; c++) {
        int lc = bl(c);
        if (lc + lb + 1 > S)
          break;
        double l2c = log2((double)c);
        int maxlr = S - lc - lb;
        uint32_t rmax = (1u << maxlr) - 1;
        for (uint32_t r = 1; r <= rmax; r++) {
          if (r == 1 && b != c + 1)
            continue;
          int cost = lc + lb + bl(r);
          double x = l2c + (double)(r - 1) * l2b;
          double lim = maxle[K - cost] + N + 3.0;
          if (x > lim + slack(x))
            break; // x grows with r (cost is non-decreasing in r, so lim is
                   // non-increasing)
          if (nb[cost] == capb[cost]) {
            capb[cost] = capb[cost] ? capb[cost] * 2 : 1024;
            bucket[cost] = realloc(bucket[cost], capb[cost] * sizeof(Trip));
            if (!bucket[cost]) {
              perror("realloc");
              exit(1);
            }
          }
          Trip *t = &bucket[cost][nb[cost]++];
          t->x = x;
          t->c = c;
          t->b = b;
          t->r = r;
          t->big = 0;
          t->v = 0;
          kept[cost]++;
        }
      }
    }
  }
  // exact values
  uint64_t nbig = 0;
  double maxkeptx = 0;
  uint64_t bigbits = 0;
  for (int s = 4; s <= S; s++)
    for (size_t i = 0; i < nb[s]; i++) {
      Trip *t = &bucket[s][i];
      if (t->x > maxkeptx)
        maxkeptx = t->x;
      if (!exact_u64(t->c, t->b, t->r, &t->v)) {
        if (npool == cappool) {
          cappool = cappool ? cappool * 2 : 1024;
          pool = realloc(pool, cappool * sizeof(mpz_t));
          if (!pool) {
            perror("realloc");
            exit(1);
          }
        }
        mpz_init(pool[npool]);
        mpz_ui_pow_ui(pool[npool], t->b, t->r);
        mpz_sub_ui(pool[npool], pool[npool], 1);
        mpz_divexact_ui(pool[npool], pool[npool], t->b - 1);
        mpz_mul_ui(pool[npool], pool[npool], t->c);
        bigbits += mpz_sizeinbase(pool[npool], 2);
        t->big = (uint32_t)(++npool);
        nbig++;
      }
    }
  for (int s = 4; s <= S; s++)
    qsort(bucket[s], nb[s], sizeof(Trip), cmpx);

  F6 = malloc(LIM);
  F3 = malloc(LIM);
  if (!F6 || !F3) {
    perror("malloc");
    return 1;
  }
  memset(F6, 255, LIM);

  // ---------- join ----------
  uint64_t c_u64 = 0, c_bs = 0, c_bb = 0, c_skip = 0;
  mpz_t q;
  mpz_init(q);
  for (int s1 = 4; s1 <= S; s1++)
    for (int s2 = 4; s1 + s2 <= K; s2++) {
      const Trip *A = bucket[s1], *B = bucket[s2];
      size_t nA = nb[s1], nB = nb[s2];
      size_t lo = 0, hi = 0;
      int s = s1 + s2;
      for (size_t i = 0; i < nA; i++) {
        const Trip *a = &A[i];
        double xl = a->x - N - 1.0 - 2 * slack(a->x),
               xh = a->x + 1.0 + 2 * slack(a->x);
        while (lo < nB && B[lo].x < xl)
          lo++;
        if (hi < lo)
          hi = lo;
        while (hi < nB && B[hi].x <= xh)
          hi++;
        if (!a->big) {
          uint64_t v1 = a->v;
          for (size_t j = lo; j < hi; j++) {
            const Trip *b = &B[j];
            if (b->big) {
              c_skip++;
              continue;
            } // V2 >= 2^64 > V1
            c_u64++;
            uint64_t v2 = b->v;
            if (v2 <= v1 && v1 % v2 == 0) {
              uint64_t d = v1 / v2;
              if (d < LIM)
                hit(d, s, a, b);
            }
          }
        } else {
          mpz_t *V1 = &pool[a->big - 1];
          for (size_t j = lo; j < hi; j++) {
            const Trip *b = &B[j];
            if (!b->big) {
              c_bs++;
              if (mpz_divisible_ui_p(*V1, b->v)) {
                mpz_divexact_ui(q, *V1, b->v);
                if (mpz_sgn(q) > 0 && mpz_cmp_ui(q, LIM) < 0)
                  hit(mpz_get_ui(q), s, a, b);
              }
            } else {
              c_bb++;
              mpz_t *V2 = &pool[b->big - 1];
              if (mpz_cmp(*V2, *V1) <= 0 && mpz_divisible_p(*V1, *V2)) {
                mpz_divexact(q, *V1, *V2);
                if (mpz_sgn(q) > 0 && mpz_cmp_ui(q, LIM) < 0)
                  hit(mpz_get_ui(q), s, a, b);
              }
            }
          }
        }
      }
    }

  // ---------- F3: exact minimum triple cost of every d < 2^N (no cost cap)
  // ----------
  F3[0] = 255;
  for (uint64_t d = 1; d < LIM; d++)
    F3[d] = (uint8_t)(bl(d) + bl(d + 1) + 1); // r = 1, b = d+1
  uint64_t n3 = 0;
#define UPD3(v, cost_, c_, b_, r_)                                             \
  do {                                                                         \
    n3++;                                                                      \
    if ((cost_) < F3[v]) {                                                     \
      F3[v] = (uint8_t)(cost_);                                                \
      if ((cost_) + 1 < bl(v)) {                                               \
        if (nrec3 == caprec3) {                                                \
          caprec3 = caprec3 ? caprec3 * 2 : 1 << 16;                           \
          rec3 = realloc(rec3, caprec3 * sizeof(Rec3));                        \
          if (!rec3) {                                                         \
            perror("realloc");                                                 \
            exit(1);                                                           \
          }                                                                    \
        }                                                                      \
        Rec3 *p_ = &rec3[nrec3++];                                             \
        p_->d = (v);                                                           \
        p_->c = (uint32_t)(c_);                                                \
        p_->b = (uint32_t)(b_);                                                \
        p_->r = (uint32_t)(r_);                                                \
        p_->cost = (uint32_t)(cost_);                                          \
      }                                                                        \
    }                                                                          \
  } while (0)
  for (uint64_t b = 2; b + 1 < LIM; b++) { // r = 2: value c*(b+1)
    int lb = bl(b);
    uint64_t cmax = (LIM - 1) / (b + 1);
    if (cmax > b - 1)
      cmax = b - 1;
    for (uint64_t c = 1; c <= cmax; c++) {
      uint64_t v = c * (b + 1);
      int cost = bl(c) + lb + 2;
      UPD3(v, cost, c, b, 2);
    }
  }
  for (uint32_t r = 3; r <= (uint32_t)N; r++) {
    int lr = bl(r);
    for (uint64_t b = 2;; b++) {
      u128 rep = 1;
      int ovf = 0;
      for (uint32_t k = 1; k < r; k++) {
        rep = rep * b + 1;
        if (rep >= LIM) {
          ovf = 1;
          break;
        }
      }
      if (ovf)
        break;
      int lb = bl(b);
      uint64_t rp = (uint64_t)rep;
      uint64_t cmax = (LIM - 1) / rp;
      if (cmax > b - 1)
        cmax = b - 1;
      for (uint64_t c = 1; c <= cmax; c++) {
        uint64_t v = c * rp;
        int cost = bl(c) + lb + lr;
        UPD3(v, cost, c, b, r);
      }
    }
  }

  wr(prefix, ".f6.u8", F6, LIM);
  wr(prefix, ".f3.u8", F3, LIM);
  wr(prefix, ".rec6.bin", rec6, nrec6 * sizeof(Rec6));
  wr(prefix, ".rec3.bin", rec3, nrec3 * sizeof(Rec3));

  uint64_t nfound = 0;
  for (uint64_t d = 1; d < LIM; d++)
    if (F6[d] != 255)
      nfound++;
  printf("{\"N\": %d, \"K\": %d, \"S\": %d,\n", N, K, S);
  printf(" \"triples_enumerated_by_cost\": {");
  {
    int f = 1;
    uint64_t tot = 0;
    for (int s = 4; s <= S; s++) {
      printf("%s\"%d\": %llu", f ? "" : ", ", s, (unsigned long long)cnt[s]);
      f = 0;
      tot += cnt[s];
    }
    printf("}, \"triples_enumerated_total\": %llu,\n", (unsigned long long)tot);
  }
  printf(" \"triples_raw_by_cost_no_r1_dedupe\": {");
  {
    int f = 1;
    for (int s = 4; s <= S; s++) {
      printf("%s\"%d\": %llu", f ? "" : ", ", s, (unsigned long long)cntraw[s]);
      f = 0;
    }
    printf("},\n");
  }
  printf(" \"small_bits\": %d,\n", (int)SMALL_BITS);
  printf(" \"triples_kept_by_cost\": {");
  {
    int f = 1;
    uint64_t tot = 0;
    for (int s = 4; s <= S; s++) {
      printf("%s\"%d\": %llu", f ? "" : ", ", s, (unsigned long long)kept[s]);
      f = 0;
      tot += kept[s];
    }
    printf("}, \"triples_kept_total\": %llu,\n", (unsigned long long)tot);
  }
  printf(" \"max_log2_by_cost_le\": {");
  {
    int f = 1;
    for (int s = 4; s <= S; s++) {
      printf("%s\"%d\": %.3f", f ? "" : ", ", s, maxle[s]);
      f = 0;
    }
    printf("},\n");
  }
  printf(" \"kept_big_values\": %llu, \"kept_big_total_bits\": %llu, "
         "\"max_log2_kept\": %.3f,\n",
         (unsigned long long)nbig, (unsigned long long)bigbits, maxkeptx);
  printf(" \"pairs_tested_u64\": %llu, \"pairs_tested_big_over_u64\": %llu, "
         "\"pairs_tested_big_over_big\": %llu, \"pairs_skipped_den_gt_num\": "
         "%llu,\n",
         (unsigned long long)c_u64, (unsigned long long)c_bs,
         (unsigned long long)c_bb, (unsigned long long)c_skip);
  printf(" \"integer_quotients_in_range\": %llu, "
         "\"distinct_d_with_tuple_cost_le_K\": %llu,\n",
         (unsigned long long)nhit, (unsigned long long)nfound);
  printf(" \"rec6_written\": %llu, \"rec3_written\": %llu, "
         "\"f3_candidates_r_ge_2\": %llu}\n",
         (unsigned long long)nrec6, (unsigned long long)nrec3,
         (unsigned long long)n3);
  return 0;
}
