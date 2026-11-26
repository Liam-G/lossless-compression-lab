# Experiment 14 · Sparse residual coding

## Question and prior work

When does spatial error structure favor a combinatorial rank, gap code or adaptive context model?

The earlier internal-stream study measured 7,053 bytes for plane enumeration and 6,635 for its contextual KT2 model on 8,192 input bytes.

### Source files and compatibility

The adaptive arithmetic update and KT count increments follow the predictor source. The new context uses local reconstructed bits and position. Paths below are relative to the original workspace.

- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/margolus/misure.json`
- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/predittori.py`
- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/margolus/prova.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 14 test
python3 ../../lab.py 14 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 14 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 14 benchmark ../../runs/recheck-14
```

## Variants and format

Use 32-byte blocks. Enumerative stores the weight and colexicographic subset rank. Rice optimizes the parameter k and encodes increasing error-position gaps. Context uses a 32-bit arithmetic coder with KT counts keyed by bit position and the preceding two bits. Adaptive chooses the shortest serialized option per block, including its selector, parameters, payload size and padding. All modes restore the mask exactly.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Three 4,096-bit masks each contain exactly 128 errors distributed independently, in bursts or periodically by row. Real masks come from experiment 08 GF(2) errors, experiment 09 spectral residuals and experiment 12 aligned literal gaps. The driver calls their implementations on the frozen source fixtures.

The context implementation uses reconstructed prefix bits. It needs no free list-boundary side information. Each block starts with fresh counts. The trial details show which codes the adaptive profile selected.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

At equal density, the isolated mask favored enumeration at 147 bytes and the clustered mask favored context coding at 119 bytes.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| isolated | 512 | enumerative | 147 | 210 |
| uniform | 512 | enumerative | 567 | 525 |
| clustered | 512 | context | 119 | 76 |
| row-pattern | 512 | enumerative | 156 | 24 |
| fax.bin-GF2 | 512 | enumerative | 44 | 22 |
| fax.bin-Walsh | 512 | enumerative | 44 | 22 |
| fax-mid.bin-GF2 | 512 | enumerative | 44 | 22 |
| fax-mid.bin-Walsh | 512 | enumerative | 147 | 129 |
| medical.bin-GF2 | 512 | enumerative | 96 | 138 |
| medical.bin-Walsh | 512 | rice | 154 | 114 |
| aligned-logo-exceptions | 210 | adaptive | 50 | 29 |

All 44 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

### Cost by error distribution at the same density

| Distribution | Enumerative | Rice | Context | Adaptive including selector |
|---|---:|---:|---:|---:|
| isolated | 147 | 165 | 194 | 163 |
| clustered | 141 | 143 | 119 | 120 |
| row-pattern | 156 | 156 | 156 | 172 |


## Large-file benchmark

On `numerical` (25,696,748 raw bytes), `pilot14-adaptive` produced 20,503,460 archive bytes. Zstandard level 3 used 15,163,683 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#numerical) · [All project measurements](../../research/large-scale/results/by-experiment.md#14-sparse-residuals)

## Connections

Experiments 08, 09 and 12 directly generate the benchmark inputs.
