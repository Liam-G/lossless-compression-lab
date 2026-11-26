# Experiment 13 · Burrows–Wheeler transform and prediction

## Question and prior work

Does the Burrows–Wheeler transform help a generator, the residual coder, or both?

The source compares seeded xorshift, linear congruential and cellular generators on direct and transformed archive windows, retaining the BWT primary row for inversion.

### Source files and compatibility

The encoded rotation order and primary row are taken from the local BWT prototype. The implementation includes two of its generator families and a stable LF inverse. Paths below are relative to the original workspace.

- `lab/arena/coincidence_bwt.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 13 test
python3 ../../lab.py 13 encode ../../fixtures/bytecode-bwt.bin sample.lcx
python3 ../../lab.py 13 decode sample.lcx sample.restored
cmp ../../fixtures/bytecode-bwt.bin sample.restored
python3 ../../lab.py 13 benchmark ../../runs/recheck-13
```

## Variants and format

Cross BWT off/on with seed prediction off/on at block widths 16 and 64. Use the original sorted-rotation BWT construction and a stable LF-mapping inverse. Predict bytes in the chosen representation with eight LCG and eight xorshift seeds plus a zero predictor. Transmit a primary row and seed index when enabled. Compress every XOR residual with the same DEFLATE configuration and record its length.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Test planted LCG outputs, ordered records and a shuffled permutation of the same records, plus actual bytecode streams from two lab programs.

Seed search minimizes each block’s compressed residual length. Primary-row and selector widths are constant within a profile and are present in the final comparison. Every block pays for a fresh stream.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

On the planted LCG stream, the 16-byte direct predictor used 428 bytes and the transformed predictor used 876. The per-profile byte counts expose the cost of fitting the same generator family after reordering.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| lcg-seeds | 512 | predict-16 | 428 | 150 |
| uniform | 512 | direct-64 | 620 | 525 |
| ordered-records | 512 | direct-64 | 252 | 140 |
| shuffled-records | 512 | direct-64 | 287 | 186 |
| bytecode-bwt.bin | 512 | direct-64 | 337 | 212 |
| bytecode-base.bin | 512 | direct-64 | 376 | 243 |

All 48 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

## Connections

Experiment 03 provides candidate generator families and experiment 14 provides alternative residual codes.
