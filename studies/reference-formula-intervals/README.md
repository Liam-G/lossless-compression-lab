# Reference copies, local formulas and interval selection

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

When a target contains both movable reference spans and generated spans, does their joint selection repay its metadata?

## Run the experiment

Run from the repository root on Linux with Python and the Zstd CLI.

```sh
python3 studies/run.py reference-formula-intervals runs/reference-formula-intervals
```

## Variants and format

Experiment 12 proposes variable-offset reference copies. Experiment 15 proposes local headers, constants, runs and backward copies. The interval selection from experiment 16 is extended with a state indicating whether the external reference digest has already been paid. Every record includes target offset, width, kind, recipe size and recipe. Untouched bytes remain literal. The decoder checks the reference SHA-256 whenever an external copy was selected.

## Inputs and measurement

Inputs include a planted copy/run mixture, a matched-size random control, two actual Statico source revisions and two packaged versions of the same PNG. The new-recipient figure includes the complete raw base only when a selected record requires it.

## Results

The following table records the original small diagnostic. The primary benchmark follows it.

The mixed archive needed 66 bytes on the planted update and 1,090 bytes when delivering the base as well. The formulas-only archive required 1,042 bytes and was independently decodable.

| Input | Profile | Raw bytes | Archive | Archive plus required base | Zstd |
|---|---|---:|---:|---:|---:|
| copied-and-generated | copies | 1222 | 259 | 1283 | 1046 |
| copied-and-generated | formulas | 1222 | 1042 | 1042 | 1046 |
| copied-and-generated | mixed | 1222 | 66 | 1090 | 1046 |
| uniform | copies | 1222 | 1235 | 1235 | 1235 |
| uniform | formulas | 1222 | 1235 | 1235 | 1235 |
| uniform | mixed | 1222 | 1235 | 1235 | 1235 |
| src | copies | 967 | 240 | 1016 | 526 |
| src | formulas | 967 | 829 | 829 | 526 |
| src | mixed | 967 | 233 | 1009 | 526 |
| logo | copies | 1678 | 1691 | 1691 | 1691 |
| logo | formulas | 1678 | 1691 | 1691 | 1691 |
| logo | mixed | 1678 | 1691 | 1691 | 1691 |

All 12 study archives reconstructed their original bytes. The [trial table](results/reference/trials.csv) includes input hashes, side-stream byte counts and single-run timings. [Study implementation](benchmark.py).

## Large-file benchmark

On `numpy-update` (53,800,960 raw bytes), `study19-mixed` produced 18,553,077 archive bytes. Delivering the required reference as well costs 72,272,117 bytes. Zstandard level 3 used 11,502,762 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#numpy-update) · [All project measurements](../../research/large-scale/results/by-experiment.md#reference-formula-intervals)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### numpy-update · 53,800,960 raw bytes

**Standalone archives**

| Profile | Archive bytes | Archive + required reference (bytes) | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|---:|
| `study19-mixed` (base `numpy-base`) | 18,553,077 | 72,272,117 | -18,471,157 | 679.012 | 15.730 | 45,340 / 23,684 |

Same-input baseline archives (bytes) · XZ 9 extreme 8,272,288 · Zstandard 19 9,104,011 · Zstandard 3 11,502,762

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#numpy-update)

<!-- END generated project measurements -->

## Connections

[Conditional patches after arithmetic alignment](../../research/arithmetic-references/README.md) · [Adaptive repdigit intervals](../../research/repdigit-intervals/README.md)
