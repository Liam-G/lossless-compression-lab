# Experiment 06 · Reversible automata and step counts

## Question and prior work

Can a simpler predecessor grid repay the cost of telling the decoder how many automaton steps to run?

The original 8×8 experiment reduced a 20,000-byte evolved-grid control from 17,050 to 12,189 bytes. Its executable test selected step zero on all 17 selected grids.

### Source files and compatibility

The native orbit encoder supplies Checkerboard parity and the asymmetric tie rules for legal step bounds. The Margolus profile uses its own fixed involution. Paths below are relative to the original workspace.

- `lab/hutter/automa-8x8-passo-byte/orbite/RISULTATI.md`
- `lab/hutter/automa-8x8-passo-byte/orbite/orbite.cpp`
- `lab/hutter/automa-8x8-passo-byte/scacchiera.cpp`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 06 test
python3 ../../lab.py 06 encode ../../fixtures/fax-mid.bin sample.lcx
python3 ../../lab.py 06 decode sample.lcx sample.restored
cmp ../../fixtures/fax-mid.bin sample.restored
python3 ../../lab.py 06 benchmark ../../runs/recheck-06
```

## Variants and format

Read each eight bytes as a 64-cell torus. Checkerboard uses the original alternating parity update. Margolus alternates two partitions with an explicit reversible four-cell substitution. Search backwards 3 or 15 steps, retaining the earliest minimum-minority state. Encode the seed by weight and combinadic rank. A fixed index uses the full step range. Restricted indices derive legal bounds by walking the orbit from the seed. Step bits are packed across blocks. Literal tags, seed widths, step padding and the verbatim tail are charged. The zero profile only considers the input state.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Three-particle seeds evolve under each of the two rules. The suite also tests fax bitmap and medical-image samples. Each trial reports seed bytes (including literal full grids), step bits and padded step bytes.

The restricted index uses a fixed bit width within the legal interval. The one-byte population or literal selector for each block is in the metadata stream.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

On the Checkerboard control the zero-step profile needed 148 bytes. With a 15-step search, a fixed index used 97 and the restricted index used 95.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| checker-sparse-orbits | 192 | checker-15-restricted | 95 | 167 |
| uniform | 192 | zero | 228 | 205 |
| margolus-sparse-orbits | 192 | margolus-15-fixed | 97 | 205 |
| fax.bin | 192 | zero | 37 | 22 |
| fax-mid.bin | 192 | zero | 71 | 61 |
| medical.bin | 192 | zero | 145 | 106 |

All 54 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).


## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#06-reversible-automata) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 07 uses the Checkerboard rule in a factorization tree. Experiment 14 can replace the combinadic seed code.
