# Automata, factors and residual coding

[Method diagram](#method-diagram) · [Charts and benchmark tables](#large-file-benchmark)

## Question and prior work

Does undoing an automaton step reduce residual cost when the factor model stays fixed?

## Run the experiment

Run from the repository root on Linux with Python and the Zstd CLI.

```sh
python3 studies/run.py automaton-factor-residual runs/automaton-factor-residual
```

## Variants and format

Fit two GF(2) basis vectors per eight-row matrix using experiment 08. The orbit profiles consider up to three reverse Checkerboard steps from experiment 06. Rank from experiment 07 breaks ties after residual weight. Send the selected step, basis, coordinates and a nested experiment 14 residual archive. First compare direct and orbit prediction with enumerative coding. Then hold orbit selection fixed while switching among enumeration, Rice gaps, contexts and per-block selection.

### Method diagram

```mermaid
flowchart LR
    I["Binary matrix"] --> T["Search predecessors and fit a two-vector basis"]
    T --> W["Send step, factors and coded residual"]
```

**Mechanism and test.** A lower error weight can improve subset coding while leaving long or irregular gaps. Switching the residual coder with the orbit held fixed tests whether the gain comes from the fit or from the mask representation.

## Inputs and measurement

The planted control evolves noisy rank-two matrices. The real controls are a fax window and medical-image bytes. Transform selection minimizes residual weight with a fixed tie rule. Every residual profile sees the same chosen factors for an orbit input.

## Results

The following table records the original small diagnostic. The primary benchmark follows it.

With enumeration fixed, the orbit reduced the evolved control from 475 bytes to 339. Holding that prediction fixed, Rice used 350 bytes and the context code used 355.

| Input | Profile | Raw bytes | Archive | Archive plus required base | Zstd |
|---|---|---:|---:|---:|---:|
| evolved-noisy-rank-two | direct-enumerative | 384 | 475 | 475 | 397 |
| evolved-noisy-rank-two | orbit-enumerative | 384 | 339 | 339 | 397 |
| evolved-noisy-rank-two | orbit-rice | 384 | 350 | 350 | 397 |
| evolved-noisy-rank-two | orbit-context | 384 | 355 | 355 | 397 |
| evolved-noisy-rank-two | orbit-adaptive | 384 | 351 | 351 | 397 |
| uniform | direct-enumerative | 384 | 509 | 509 | 397 |
| uniform | orbit-enumerative | 384 | 537 | 537 | 397 |
| uniform | orbit-rice | 384 | 554 | 554 | 397 |
| uniform | orbit-context | 384 | 577 | 577 | 397 |
| uniform | orbit-adaptive | 384 | 549 | 549 | 397 |
| fax-mid.bin | direct-enumerative | 512 | 313 | 313 | 80 |
| fax-mid.bin | orbit-enumerative | 512 | 377 | 377 | 80 |
| fax-mid.bin | orbit-rice | 512 | 393 | 393 | 80 |
| fax-mid.bin | orbit-context | 512 | 425 | 425 | 80 |
| fax-mid.bin | orbit-adaptive | 512 | 393 | 393 | 80 |
| medical.bin | direct-enumerative | 512 | 353 | 353 | 137 |
| medical.bin | orbit-enumerative | 512 | 417 | 417 | 137 |
| medical.bin | orbit-rice | 512 | 433 | 433 | 137 |
| medical.bin | orbit-context | 512 | 460 | 460 | 137 |
| medical.bin | orbit-adaptive | 512 | 433 | 433 | 137 |

All 20 study archives reconstructed their original bytes. The [trial table](results/reference/trials.csv) includes input hashes, side-stream byte counts and single-run timings. [Study implementation](benchmark.py).

## Large-file benchmark

On `manual-graphs` (24,642,792 raw bytes), `study18-orbit-enumerative` produced 17,725,221 archive bytes. Zstandard level 3 used 1,325,134 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#manual-graphs) · [All project measurements](../../research/large-scale/results/by-experiment.md#automaton-factor-residual)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

On the primary input `manual-graphs`, `study18-orbit-enumerative` delivers 17,725,221 bytes, 16,400,087 bytes larger than standalone Zstandard 3 (1,325,134 bytes).

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### manual-graphs · 24,642,792 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `study18-direct-enumerative` | 14,653,191 | +9,989,601 | 65.912 | 95.317 | 25,252 / 23,828 |
| `study18-orbit-enumerative` | 17,725,221 | +6,917,571 | 288.920 | 58.864 | 25,120 / 23,664 |

Same-input baseline archives (bytes) · DjVu 214,067 · DjVu (separated foreground) 213,732 · DjVu (wide strips) 191,132 · CCITT Group 4 1,270,850 · JBIG 707,797 · 1-bit PNG 1,418,635 · XZ 9 extreme 930,864 · Zstandard 19 1,034,431 · Zstandard 3 1,325,134

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#manual-graphs)

### noisy-spacetime · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `study18-direct-enumerative` | 31,450,511 | -6,284,687 | 761.297 | 563.380 | 25,096 / 23,492 |

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#noisy-spacetime)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-automaton-factor-residual --project automaton-factor-residual --all-profiles
```

[Dataset preparation](../../research/large-scale/README.md#inputs) · [Archive hashes and settings](../../research/large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

## Connections

[Jointly learning a cellular rule and the matrix of its prediction errors](../../research/learned-cellular-rules/README.md) · [Reversible 3D automata before GF(2) panel coding](../../research/tensor-orbits/README.md)
