# Experiment 02 · Near-factorization and digit concatenation

[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)

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

### Method diagram

```mermaid
flowchart LR
    I["16-byte integer"] --> T["Try corrected products and split operands"]
    T --> W["Store operands and correction or literal"]
```

**Mechanism and test.** A small factor is useful only if both operands and the signed correction are cheap to describe. Perturbed products test that condition directly. Searching more divisors can find shorter records at additional encode cost.

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

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

On the primary input `wiki-transfer`, `pilot02-first-exact` delivers 26,751,758 bytes, 17,783,302 bytes larger than standalone Zstandard 3 (8,968,456 bytes).

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `pilot02-first-exact` | 26,751,758 | -1,585,934 | 705.904 | 4.083 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#wiki-transfer)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-02-near-factorization --project 02-near-factorization --all-profiles
```

[Dataset preparation](../../research/large-scale/README.md#inputs) · [Archive hashes and settings](../../research/large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

## Connections

Experiment 01 supplies repdigit factor leaves. Experiment 10 can represent a sequence of product corrections as affine instructions.
