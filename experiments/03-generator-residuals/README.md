# Experiment 03 · Powers, generator sums and exact residuals

[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)

## Question and prior work

Which predictor family and correction operator produce the smallest exact archive for a fixed seed budget?

The QGS1 prototype encoded its own 4,096-byte generated control in 21 bytes using three 8-bit seeds. A separate integer-formula search tested powers, products and low-bit filters.

### Source files and compatibility

The QGS1 inverse supplies the domain-separated SHAKE idea. The integer search motivates powers, products and modular rejection. Paths below are relative to the original workspace.

- `lab/hutter/divisors/q-somma-generatori/misure.json`
- `lab/hutter/divisors/q-formula-intera/misure.json`
- `lab/hutter/divisors/q-somma-generatori/decoder.py`
- `lab/hutter/divisors/q-formula-intera/semi_brevi.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 03 test
python3 ../../lab.py 03 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 03 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 03 benchmark ../../runs/recheck-03
```

## Variants and format

Use 16-byte big-endian blocks. Generate a seventh power or the sum or product of two domain-separated SHAKE256 outputs derived from one seed. Reduce the prediction modulo the block width. Each tag carries the seed or the literal escape. Additive corrections use ZigZag LEB128. XOR corrections store a population count and the bit positions. A low-byte population bound prunes XOR candidates that already cost too much. Test seed budgets of 8, 32 and 64. The inverse requires only the profile, seed and residual.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

### Method diagram

```mermaid
flowchart LR
    I["16-byte word"] --> T["Generate candidate values from seeds"]
    T --> W["Store seed and additive or XOR correction"]
```

**Mechanism and test.** The kind of error matters. A small integer offset is cheap as a signed difference, while a handful of bit flips can be cheaper as positions. The planted controls vary these independently.

## Inputs and measurement

For each family, generate 24 words and perturb them with a small additive offset or two flipped bits. The real inputs are a cofactor window and medical-image bytes.

Each bounded family has one seed. The SHAKE construction differs from the original three-independent-seed QGS1 format. Timings include generating the catalog entries used by the profile.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

For powers with small offsets, increasing the additive search budget from 8 to 32 to 64 seeds reduced the archive from 144 to 101 to 60 bytes.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| power-small-offset | 384 | power-add-64 | 60 | 169 |
| uniform | 384 | power-add-8 | 420 | 397 |
| power-bit-flips | 384 | power-xor-64 | 108 | 181 |
| sum-small-offset | 384 | sum-add-64 | 60 | 361 |
| sum-bit-flips | 384 | sum-xor-64 | 108 | 361 |
| product-small-offset | 384 | product-add-64 | 60 | 362 |
| product-bit-flips | 384 | product-xor-64 | 108 | 362 |
| integer.bin | 512 | power-add-8 | 556 | 525 |
| medical.bin | 512 | power-xor-64 | 313 | 137 |

All 162 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

### Search budget on additive power controls

| Seeds tested per word | Archive bytes | Encode time (ms) | Generated words |
|---:|---:|---:|---:|
| 8 | 144 | 0.208 | 24 |
| 32 | 101 | 0.671 | 24 |
| 64 | 60 | 1.398 | 24 |

Point labels give the number of seeds tested per word.

![Measured archive sizes and encoding times at three seed budgets](results/reference/seed-search.png)


## Large-file benchmark

On `wiki-transfer` (25,165,824 raw bytes), `pilot03-sum-add-8` produced 26,751,758 archive bytes. Zstandard level 3 used 8,968,456 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#wiki-transfer) · [All project measurements](../../research/large-scale/results/by-experiment.md#03-generator-residuals)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

On the primary input `wiki-transfer`, `pilot03-sum-add-8` delivers 26,751,758 bytes, 17,783,302 bytes larger than standalone Zstandard 3 (8,968,456 bytes).

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot03-power-add-8` | 26,751,758 | -1,585,934 | 119.629 | 5.821 | 25,204 / 23,608 |
| `pilot03-sum-add-8` | 26,751,758 | -1,585,934 | 121.724 | 3.492 | — / — |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#wiki-transfer)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-03-generator-residuals --project 03-generator-residuals --all-profiles
```

[Dataset preparation](../../research/large-scale/README.md#inputs) · [Archive hashes and settings](../../research/large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

## Connections

Experiment 14 can encode the XOR mask and experiment 16 can charge a generator seed when selecting intervals.
