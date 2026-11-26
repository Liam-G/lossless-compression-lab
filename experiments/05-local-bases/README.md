# Experiment 05 · Local bases and exceptional digits

## Question and prior work

Does the lowest-entropy numeral base also minimize the archive after dominant digits, exceptions and selectors are paid for?

The source prototype searches bases 2–257 and compares empirical entropy with the exact encodings of digit exceptions in fixed-width integer-tree leaves.

### Source files and compatibility

The original leaf scorer supplies the dominant-digit and entropy rules. This implementation prices an explicit list of exception position/value pairs. Paths below are relative to the original workspace.

- `lab/hutter/ragc/entropy_base_tree/trial.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 05 test
python3 ../../lab.py 05 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 05 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 05 benchmark ../../runs/recheck-05
```

## Variants and format

Each 16-byte word has 13 candidate bases from 2 through 257. Represent it by a digit count, a dominant digit and a list of exceptional positions and values in least-significant-digit order. All fields use unsigned varints. Global profiles transmit one common base and per-word literal flags. Local profiles use one selector per word, including the raw escape. Entropy scoring uses per-digit empirical entropy. Byte scoring includes literal fallback. The decoder restores each word to its original byte width.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

The structured input contains repeated digits in changing local bases with a one-place perturbation. A cofactor window and quantized medical-image data exercise the same word format.

The base set is a frozen subset of the original search range. Details in the trial CSV count changed base choices, including blocks that subsequently take the raw escape, and the complete selector stream.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

Local selection by encoded size saved five bytes over the better individual change on the planted mixed-base input.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| mixed-local-bases | 512 | local-bytes | 236 | 288 |
| uniform | 512 | local-entropy | 556 | 525 |
| integer.bin | 512 | local-entropy | 556 | 525 |
| medical.bin | 512 | local-bytes | 343 | 137 |

All 16 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

### Base selection on the mixed-base control

| Profile | Archive bytes | Transmitted selector bytes | Blocks where the two scoring rules differ |
|---|---:|---:|---:|
| global-entropy | 546 | 33 | 32 |
| local-entropy | 241 | 32 | 2 |
| global-bytes | 457 | 33 | 32 |
| local-bytes | 236 | 32 | 2 |


## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#05-local-bases) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 01 represents the no-exception case. Experiment 14 provides competing position codes.
