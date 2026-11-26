# Experiment 10 · Affine instruction chains

## Question and prior work

Which format best describes an affine instruction stream, and how does evaluation order affect reconstruction time?

The reference C encoder stores common a=240 instructions in one byte, falls back to ZigZag varints, and evaluates chains sequentially or by balanced composition using GMP.

### Source files and compatibility

The C reference supplies the 240 shortcut, escape tags, signed integers and ordered affine composition. Only the fixed instruction body follows that convention. Paths below are relative to the original workspace.

- `lab/hutter/divisors/q-correzioni-fattori/formula_codec.c`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 10 test
python3 ../../lab.py 10 encode ../../fixtures/affine-0.bin sample.lcx
python3 ../../lab.py 10 decode sample.lcx sample.restored
cmp ../../fixtures/affine-0.bin sample.restored
python3 ../../lab.py 10 benchmark ../../runs/recheck-10
```

## Variants and format

Input is a sequence of big-endian signed 16-bit (a,c) pairs with a verbatim partial tail. The fixed profile ports the 240 shortcut and both escape cases. Dictionary transmits the ordered multiplier table. Conditional additionally transmits the modal c per multiplier and codes deviations from it. Both dictionary profiles encode the multiplier index and signed residual with varints. Decode the same instructions into their original bytes, and evaluate x ← a·x+c from x=0 using both sequential and balanced algorithms. Compare the exact resulting integers.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Use a frequent multiplier control and a multiplier-dependent offset control. The two real samples normalize consecutive original formula.bin instructions into the 16-bit interchange format.

The original permits arbitrary-size operands. This study fixes input operand width while the accumulator and composed results use arbitrary-precision integers. The trial details report separate evaluation times in nanoseconds. Overall decode time includes both evaluations.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

The fixed 240 shortcut won the frequent-multiplier case, while the conditional model won the multiplier-dependent offset control. Both evaluation orders produced the same integer for every trial.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| frequent-multiplier | 640 | fixed | 172 | 358 |
| uniform | 640 | fixed | 1,047 | 653 |
| conditional-offset | 640 | conditional | 347 | 267 |
| affine-0.bin | 512 | fixed | 140 | 309 |
| affine-1.bin | 512 | fixed | 140 | 300 |

All 15 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

### Affine evaluation on the multiplier-dependent offset control

| Format | Archive bytes | Sequential (µs) | Balanced (µs) |
|---|---:|---:|---:|
| fixed | 652 | 13.1 | 34.2 |
| dictionary | 533 | 22.4 | 45.9 |
| conditional | 347 | 13.9 | 38.3 |


## Large-file benchmark

On `affine-pairs` (25,165,824 raw bytes), `pilot10-fixed` produced 6,304,526 archive bytes. Zstandard level 3 used 9,297,292 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#affine-pairs) · [All project measurements](../../research/large-scale/results/by-experiment.md#10-affine-chains)

## Connections

Experiment 02 yields multiplier–correction pairs and experiment 11 can share their expression structure.
