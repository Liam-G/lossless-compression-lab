# Experiment 02 · Near-factorization and digit concatenation

## Question and prior work

When does a nearby product pay for both factors and the signed correction? Can decimal concatenation make an otherwise expensive factor cheap?

The zero-gap study recovered a hidden factor of a constructed 260-bit product from known decimal geometry. A separate prime-index codec reduced a 130,001-byte planted file to 121,341 bytes.

### Source files and compatibility

The zero-gap and prime-tree programs establish the arithmetic and literal-cost baselines. The bounded divisor and concatenation search is a new comparison. Paths below are relative to the original workspace.

- `lab/hutter/ragc/rfce_check/RESULTS.md`
- `lab/hutter/ragc/prime_index_tree_followup/RESULTS.md`
- `lab/hutter/ragc/rfce_check/zero_gap.py`
- `lab/hutter/ragc/prime_index_tree_followup/prime_tree.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 02 test
python3 ../../lab.py 02 encode ../../fixtures/integer.bin sample.lcx
python3 ../../lab.py 02 decode sample.lcx sample.restored
cmp ../../fixtures/integer.bin sample.restored
python3 ../../lab.py 02 benchmark ../../runs/recheck-02
```

## Variants and format

Read 16-byte big-endian words. For each signed correction in {0, ±1, ±2}, try divisors 2–129 and candidates near the integer square root. A product record stores its ZigZag correction and both operands. Each operand carries a decimal suffix width. Width zero stores one integer, while a positive width stores high and low parts, including any internal zero padding. A tag per word selects raw bytes or a product. The first strategy accepts the first improving divisor group. The best strategy retains the cheapest candidate found. Each uses the same 5 ms CPU ceiling per word.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

The generator draws hidden small factors and decimal factors with long internal zero runs. Only serialized products reach the encoder. Exact and perturbed products share the factors. Real inputs include a cofactor window and two executable prefixes.

CPU ceilings can change which candidate is reached on a different machine. The first strategy can finish early. This measures search under an equal upper bound, and actual elapsed search time is recorded.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

On the perturbed products the best combined search used 236 bytes, saving 156 bytes over its better individual extension.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| hidden-products | 512 | best-split | 236 | 203 |
| uniform | 512 | first-exact | 556 | 525 |
| perturbed-products | 512 | best-combined | 236 | 203 |
| integer.bin | 512 | first-exact | 556 | 525 |
| rusage.elf | 512 | first-exact | 556 | 173 |
| scanner.elf | 512 | first-exact | 556 | 179 |

All 48 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).


## Large-file benchmark

On `wiki-transfer` (25,165,824 raw bytes), `pilot02-first-exact` produced 26,751,758 archive bytes. Zstandard level 3 used 8,968,456 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#wiki-transfer) · [All project measurements](../../research/large-scale/results/by-experiment.md#02-near-factorization)

## Connections

Experiment 01 supplies repdigit factor leaves. Experiment 10 can represent a sequence of product corrections as affine instructions.
