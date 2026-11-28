# Recursive fourth-power quotients

[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)

## Question and prior work

How long is a whole-file formula when its operands also have to be specified? The original GMP engine in `lab/hutter/divisors/q-torri-quoziente/ricorsiva/quartiche.cpp` constructs nodes of the form `F(k,a,d) = floor((a⁴ + d⁴) / 2ᵏ)`. The decoder knows how to derive the shift and child widths. The encoder uses integer fourth roots and remainders to construct both children and continues recursively. Small subtrees use a shared 65,536-entry dictionary whose terminal operands are the integers 0 through 15.

## Run the experiment

```sh
mkdir -p runs
head -c 4096 "$Q" > runs/q-prefix.bin
python3 research/quartic-trees/codec.py encode runs/q-prefix.bin runs/q.quartic
python3 research/quartic-trees/codec.py decode runs/q.quartic runs/q-prefix.restored
cmp runs/q-prefix.bin runs/q-prefix.restored
python3 research/benchmark_native.py "$Q" runs/native-quartics
```

## Variants and format

The historical engine accepted the integer width separately. The QW01 wrapper stores the original byte count and significant bit width in a 20-byte header, preserving empty input and leading zero bytes. The original engine supplies the remaining bytes. Each recursive reference or explicitly encoded pair of child descriptions contributes to the formula length.

### Method diagram

```mermaid
flowchart LR
    I["Whole-file integer"] --> T["Decompose recursively into fourth-power operands"]
    T --> W["Write subtree references or explicit operands"]
```

**Mechanism and test.** An exact formula can lengthen an archive when each operand requires another description. The fresh full-Q and Wikipedia runs measure how much the recursive operands cost at file scale.

## Inputs and measurement

The primary trial measures `quartic` on the complete `wiki-transfer` input (25,165,824 raw bytes). The runner invokes a separate decoder and compares the reconstructed file byte for byte. The earlier measurements below retain their original input sizes.

## Results

Fresh Q prefixes of 4 KiB, 64 KiB and 1 MiB produced 11,450, 181,137 and 2,483,741 archive bytes with the wrapper. All decoded exactly. The [historical full-Q measurement](original-full-q.json) recorded 247,891,597 formula bytes before wrapper framing, with 956,890,129 fourth-power nodes when fully expanded and maximum depth 39. It includes matching input and reconstructed SHA-256 digests. A fresh QW01 encode of all 96,994,187 Q bytes produced 247,891,575 archive bytes and passed independent decoding. The receipts preserve each measurement under its own format and build. Both full runs spent more bytes describing the two operands than the original integer occupied. [Prefix replay](../evidence/native-replay/trials.csv)

## Large-file benchmark

On `wiki-transfer` (25,165,824 raw bytes), `quartic` produced 69,926,330 archive bytes. Zstandard level 3 used 8,968,456 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#wiki-transfer) · [All project measurements](../large-scale/results/by-experiment.md#quartic-trees)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

On the primary input `wiki-transfer`, `quartic` delivers 69,926,330 bytes, 60,957,874 bytes larger than standalone Zstandard 3 (8,968,456 bytes).

Holding `quartic` fixed across the 2 measured input/reference settings with a standalone Zstandard 3 control gives **0 smaller, 0 equal and 2 larger** delivered archives. Each setting counts once.

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `quartic` | 69,926,330 | -44,760,506 | 349.841 | 133.186 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-transfer)

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `quartic` | 247,891,575 | -150,897,388 | 1986.913 | 1309.108 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-quartic-trees --project quartic-trees --all-profiles
```

[Dataset preparation](../large-scale/README.md#inputs) · [Archive hashes and settings](../large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

## Connections

[Whole-file square, product and modular-square formulas](../integer-formulas/README.md) · [Integer carries across tree boundaries](../carry-trees/README.md)
