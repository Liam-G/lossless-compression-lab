# Adaptive repdigit intervals

## Question and prior work

Do whiteboard formulas occur at profitable positions inside the real cofactor Q? This experiment tries each useful byte offset and selects a set of disjoint replacements by dynamic programming. The original RPS1 codec and native scanner are from `lab/hutter/ragc/repdigit_split`, the arithmetic records from `lab/hutter/ragc/rfce_check/repdigits.py`, and the QFT1 multiplier extension from `lab/hutter/ragc/entropy_base_tree/{quotient_trial.py,product_scan.cpp}`.

## Run the experiment

```sh
mkdir -p runs
python3 research/repdigit-intervals/benchmark.py runs/intervals --q "$Q"
python3 research/repdigit-intervals/quotient_trial.py bench "$Q" research/build/product-scan runs/products
python3 research/repdigit-intervals/quotient_trial.py decode runs/products/Q.qft runs/products/restored
cmp "$Q" runs/products/restored
```

The drivers generate seeded planted and random controls and preserve the winning real archive in the output directory. RPS1 also accepts a single file via `codec.py encode INPUT OUTPUT --scanner research/build/interval-scan` and `codec.py decode ARCHIVE RESTORED`.

## Variants and format

RPS1 caps each interval at 32 bytes and enumerates arithmetic descriptions up to 28 bits. It compares fixed 32-byte boundaries, movable intervals with direct repdigits, exact cross-base quotients and zero runs. A 12-byte header carries source size and record count. Every substitution pays for a 4-byte offset, a byte width, a recipe length and its packed recipe. Literal gaps fill the rest. QFT1 extends the maximum interval to 255 bytes and permits a small prime as a multiplier.

## Inputs, results and interpretation

On full Q, fixed RPS1 blocks occupied 96,994,199 bytes. Moving the boundaries and enabling all families produced 96,994,108 bytes, saving 79 bytes over the input. The selected intervals were six direct repdigits and three zero runs. On the 184,958-byte plant, adding quotients reduced 148,418 bytes to 116,299. The random control paid only the header. [RPS1 replay](results/intervals.jsonl)

QFT1 reached 96,994,101 bytes on Q, saving 86 bytes over the input. The full-width solution used six direct repdigits and two zero runs. Enabling prime-scaled quotients added no savings to that solution. The same implementation selected them on its planted input. All distinct archive selections in the evaluation were reconstructed and compared in a separate process. [QFT1 replay and selected recipe families](results/products.json)
