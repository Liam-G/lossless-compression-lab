#!/usr/bin/env bash
# Re-run every experiment recovered from the lab notebooks, from public inputs, one after another.
# Usage (from the repository root):  CORPUS=../corpus bash research/lab-reruns.sh runs/lab
# Each step writes its log under OUT/<step>/ and a marker OUT/<step>/DONE, so the script can be resumed.
set -euo pipefail
OUT=${1:-runs/lab}; CORPUS=${CORPUS:-../corpus}; R=$(cd "$(dirname "$0")" && pwd); B=$R/build
E8=$CORPUS/enwik8/enwik8
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
say() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$OUT/progress.log"; }
step() { [ -f "$OUT/$1/DONE" ] && { say "skip $1 (done)"; return 1; }; mkdir -p "$OUT/$1"; say "start $1"; return 0; }
done_() { date +%s > "$OUT/$1/DONE"; say "done $1"; }

# ---- shared inputs -------------------------------------------------------------------------------
mkdir -p "$OUT/inputs"; I=$OUT/inputs
[ -f "$I/e10m" ] || head -c 10000000 "$E8" > "$I/e10m"
[ -f "$I/e1m" ] || head -c 1048576 "$E8" > "$I/e1m"
[ -f "$I/e1k" ] || head -c 1024 "$E8" > "$I/e1k"
[ -f "$I/target300.txt" ] || head -c 4423 "$E8" | tail -c 300 > "$I/target300.txt"   # bytes 4123..4422: Anarchism article
[ -f "$I/e1m.xz" ] || xz -9e -T1 -c "$I/e1m" > "$I/e1m.xz"
[ -f "$I/e1m.ppmd" ] || { 7z a -bd -bso0 -t7z -m0=PPMd:mem=768m:o=10 "$I/e1m.7z" "$I/e1m" >/dev/null; mv "$I/e1m.7z" "$I/e1m.ppmd"; }
sha256sum "$I"/* > "$OUT/inputs.sha256"

# ---- 1. coincidence hunt -------------------------------------------------------------------------
if step coincidence-hunt; then
  D=$OUT/coincidence-hunt
  python3 "$R/coincidence-hunt/digits.py" "$D/digits" > "$D/digits.log"
  "$B/hunt" "$I/target300.txt" "$D/digits" > "$D/anarchism.log"
  "$B/hunt" "$R/coincidence-hunt/controls/ctl_formula.txt" "$D/digits" formulas > "$D/control-formula.log"
  "$B/hunt" "$R/coincidence-hunt/controls/ctl_primes.txt" "$D/digits" intseq > "$D/control-primes.log"
  "$B/hunt" "$R/coincidence-hunt/controls/ctl_sqrt.bin" "$D/digits" roots > "$D/control-sqrt.log"
  "$B/hunt" "$R/coincidence-hunt/controls/ctl_xorshift.bin" "$D/digits" prng > "$D/control-xorshift.log"
  done_ coincidence-hunt
fi

# ---- 2. rules versus noise (the counting argument) -----------------------------------------------
if step rules-vs-noise; then
  D=$OUT/rules-vs-noise
  python3 "$R/rules-vs-noise/irrational_digits.py" "$I/e1m" "$I/e1m.xz" > "$D/irrational.log"
  python3 "$R/rules-vs-noise/noise_rules.py" "$I/e1m.xz" "$I/e1m.ppmd" > "$D/noise_rules.log"
  done_ rules-vs-noise
fi

# ---- 3. block programs ---------------------------------------------------------------------------
if step block-programs; then
  D=$OUT/block-programs
  "$B/blockgen" "$I/e1k" 1024 64 "$OUT/coincidence-hunt/digits" math "$D/e1k_math.prog" > "$D/blockgen-math.log"
  "$B/blockgen" "$I/e1k" 1024 64 "$OUT/coincidence-hunt/digits" all "$D/e1k_all.prog" > "$D/blockgen-all.log"
  for c in gzip xz brotli; do case $c in gzip) gzip -9 -c "$I/e1k";; xz) xz -9e -c "$I/e1k";; brotli) brotli -q 11 -c "$I/e1k";; esac | wc -c | sed "s/^/$c /"; done > "$D/baselines.txt"
  "$B/gen" "$I/e10m" "$OUT/coincidence-hunt/digits" 4096 12 --plant > "$D/gen-planted.log"
  done_ block-programs
fi

# ---- 4. BWT lab ----------------------------------------------------------------------------------
if step bwt-lab; then
  "$B/bwtlab" "$I/e10m" > "$OUT/bwt-lab/bwtlab-10m.log"; done_ bwt-lab
fi

# ---- 5. context-mixing history on the same 10 MB -------------------------------------------------
if step cm-history; then
  D=$OUT/cm-history; H=$R/context-mixer/history
  "$B/cmlab" "$I/e10m" > "$D/cmlab-v1.log"
  for v in 2 3 4 5 6 7 8 9 10; do
    env $(cat "$H/cm2lab_v$v.config") "$B/cm2lab" "$I/e10m" > "$D/cm2lab-v$v.log"
  done
  for v in 5 7 8; do
    env $(grep -o 'CM3_[A-Z0-9]*=[^ ]*' "$H/cm3_v$v.config" | grep -v CM3_SIZES | grep -v CM3_BITS) CM3_BITS=20 "$B/cm3" "$I/e10m" > "$D/cm3-v$v.log"
  done
  env $(grep -o 'CM3_[A-Z0-9]*=[^ ]*' "$R/context-mixer/cm3_v9.config" | grep -v CM3_SIZES | grep -v CM3_BITS) CM3_BITS=20 "$B/cm3" "$I/e10m" > "$D/cm3-v9.log"
  "$B/repeats" "$E8" > "$D/repeats-enwik8.log"
  done_ cm-history
fi

# ---- 6. grammar probes (Statico) -----------------------------------------------------------------
if step grammar-probes; then
  D=$OUT/grammar-probes
  "$R/statico/statico" c "$I/e10m" "$D/e10m.m1.stc" > "$D/statico-m1-10m.log" 2>&1
  GP_POWER=8 GP_SPACE=1 "$B/grammar-lab" "$I/e10m" "$D/e10m.glza.stc" > "$D/grammar-lab-10m.log" 2>&1
  "$R/statico/unstatico" "$D/e10m.glza.stc" "$D/e10m.back" && cmp "$I/e10m" "$D/e10m.back" && rm "$D/e10m.back"
  "$B/m3probe" "$D/e10m.m1.stc" > "$D/m3probe-10m.log" 2>&1
  "$B/m3probe" "$D/e10m.m1.stc" 12345 > "$D/m3probe-10m-shuffled.log" 2>&1
  ls -l "$D"/*.stc > "$D/sizes.txt"
  done_ grammar-probes
fi

# ---- 7. reshape tournament (381 reversible chains x zstd/bzip2/xz on 10 MB) ---------------------
if step reshape-tournament; then
  D=$OUT/reshape-tournament
  python3 "$R/reshape-tournament/arena.py" cheap "$I/e10m" "$D/work" "$D/cheap.jsonl" > "$D/cheap.log"
  rm -rf "$D/work"; done_ reshape-tournament
fi

# ---- 8. article order on enwik8 ------------------------------------------------------------------
if step article-order; then
  D=$OUT/article-order; mkdir -p "$D/work"
  (cd "$D" && python3 "$R/article-order/reorder.py" "$E8" > reorder.log && python3 "$R/article-order/order_compress.py" > compress.log)
  rm -f "$D"/work/*.bin; done_ article-order
fi

# ---- 9. stride scan and shape search (first MiB of each corpus file) -----------------------------
if step shape-search; then
  D=$OUT/shape-search
  CAP=1048576 python3 "$R/stride-scan/shapesearch.py" "$D/shapes.json" \
    "$CORPUS"/canterbury/{alice29.txt,kennedy.xls,ptt5,sum} "$CORPUS"/silesia/{dickens,mr,x-ray,sao,osdb,nci,ooffice} "$I/e1m" > "$D/shapes.log"
  done_ shape-search
fi

# ---- 10. transform controls on random and already-compressed data ---------------------------------
if step transform-controls; then
  D=$OUT/transform-controls
  python3 "$R/transform-controls/part1_search.py" --dickens "$CORPUS/silesia/dickens" --work "$D/work" --outdir "$D" > "$D/part1.log" 2>&1
  python3 "$R/transform-controls/part2_perm.py" --file "$CORPUS/silesia/dickens" --work "$D/work" --out "$D/part2.json" > "$D/part2.log" 2>&1
  rm -rf "$D/work"; done_ transform-controls
fi
say "ALL DONE"
