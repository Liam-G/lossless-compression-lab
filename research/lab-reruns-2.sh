#!/usr/bin/env bash
# Second batch of recovered lab experiments (shape search on planted programs, known width then known compressor,
# exact stride scans). Usage (from the repository root): CORPUS=../corpus bash research/lab-reruns-2.sh runs/lab
set -euo pipefail
OUT=${1:-runs/lab}; CORPUS=${CORPUS:-../corpus}; R=$(cd "$(dirname "$0")" && pwd); B=$R/build
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
say() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$OUT/progress.log"; }
step() { [ -f "$OUT/$1/DONE" ] && { say "skip $1 (done)"; return 1; }; mkdir -p "$OUT/$1"; say "start $1"; return 0; }
done_() { date +%s > "$OUT/$1/DONE"; say "done $1"; }

if step shape-planted; then
  D=$OUT/shape-planted
  python3 "$R/stride-scan/planted.py" "$D/planted" > "$D/planted.log"
  CAP=1048576 python3 "$R/stride-scan/shapesearch.py" "$D/shapes-planted.json" "$D"/planted/* > "$D/shapes-planted.log"
  for f in "$D"/planted/*; do printf '%s xz %s\n' "$(basename "$f")" "$(xz -9e -T1 -c "$f" | wc -c)"; done > "$D/xz.txt"
  rm -rf "$D/planted"; done_ shape-planted
fi

if step shape-then-known; then
  D=$OUT/shape-then-known
  (cd "$D" && CORPUS=$CORPUS python3 "$R/stride-scan/shape_before_known.py" > shape_before_known.log && rm -f t t.7z)
  done_ shape-then-known
fi

if step stride-scan; then
  D=$OUT/stride-scan
  for f in canterbury/ptt5 canterbury/kennedy.xls silesia/mr silesia/x-ray silesia/nci silesia/dickens; do
    n=$(basename "$f"); "$B/stride-scan" "$CORPUS/$f" "$D/$n.tsv" 1-4096 > "$D/$n.log" 2>&1
  done
  done_ stride-scan
fi
say "ALL DONE 2"
