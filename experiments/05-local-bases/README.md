# Experiment 05 · Local bases and exceptional digits

[View this project's benchmark tables](#large-file-benchmark)

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

On `manual-graphs` (24,642,792 raw bytes), `pilot05-local-bytes` produced 8,312,441 archive bytes. Zstandard level 3 used 1,325,134 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#manual-graphs) · [All project measurements](../../research/large-scale/results/by-experiment.md#05-local-bases)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### manual-graphs · 24,642,792 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot05-local-bytes` | 8,312,441 | +16,330,351 | 302.298 | 29.921 | 27,736 / 23,628 |

Same-input baseline archives (bytes) · DjVu 214,067 · DjVu (separated foreground) 213,732 · DjVu (wide strips) 191,132 · CCITT Group 4 1,270,850 · JBIG 707,797 · 1-bit PNG 1,418,635 · XZ 9 extreme 930,864 · Zstandard 19 1,034,431 · Zstandard 3 1,325,134

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#manual-graphs)

### whiteboard-costs · 33,554,432 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot05-local-bytes` | 17,808,940 | +15,745,492 | 819.370 | 67.864 | 29,728 / 23,616 |

Same-input baseline archives (bytes) · XZ 9 extreme 2,203,672 · Zstandard 19 2,286,184 · Zstandard 3 3,513,689

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#whiteboard-costs)

### wiki-dev · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot05-local-bytes` | 26,744,147 | -1,578,323 | 1503.476 | 4.334 | 24,932 / 23,676 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,602,488 · Zstandard 19 6,873,848 · Zstandard 3 8,951,574

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#wiki-dev)

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `pilot05-local-bytes` | 26,747,076 | -1,581,252 | 2761.713 | 2.306 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#wiki-transfer)

<!-- END generated project measurements -->

## Connections

Experiment 01 represents the no-exception case. Experiment 14 provides competing position codes.
