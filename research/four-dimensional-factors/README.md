# Four-dimensional automata with noisy binary matrix factors

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Can inverse evolution recover approximate low rank after motion in four axes? Can equally valid bases yield different coded lengths?

### Source files and compatibility

This extends the U/V/E constructions from local reports 028–031, the predecessor search in report 013, and numbered experiments 06–08. F4D1 is a new format with a small native panel factorizer and a separate forward inverse.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/four-dimensional-factors/control.py runs/spacetime.bin
python3 research/four-dimensional-factors/codec.py encode runs/spacetime.bin runs/spacetime.f4d --profile joint
python3 research/four-dimensional-factors/codec.py decode runs/spacetime.f4d runs/spacetime.restored
cmp runs/spacetime.bin runs/spacetime.restored
```

## Variants and format

Each 64 KiB volume has open time, z, y and packed x axes. Each axis has two parity updates. Linear neighbor-XOR and nonlinear two-neighbor rules have an exact inverse obtained by reversing the schedule. Independently, each 16×8 panel stores two basis rows, two coordinate bit masks and its exact XOR residual. Six binary changes of basis preserve the product. The joint mode ranks predecessor samples and fully prices two candidate factorizations plus the step-zero factorization. Stored bases and coordinates are sufficient to decode.

## Inputs and measurement

The 24 MiB plant has slowly changing bases, independently sampled coordinates and a deliberate one-bit error in every other panel. Each volume then evolves a chosen number of steps. The real numerical and Samba inputs and uniform bytes use exactly the same search.

## Results

On the plant, direct and equivalent-factor profiles gave 25,120,549 bytes. The orbit alone gave 19,601,212. Combining inverse evolution with factor/residual coding gave 9,414,787. On real numerical data the joint profile tied the orbit-only result of 16,013,206. Samba and uniform data also showed no incremental factor gain. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `noisy-spacetime` (25,165,824 raw bytes), `four-joint` produced 9,414,787 archive bytes. [Input and timing](../large-scale/results/by-dataset.md#noisy-spacetime) · [All project measurements](../large-scale/results/by-experiment.md#four-dimensional-factors)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

H0 measures byte frequencies. H1 conditions on the previous byte. Both use bits per byte of their own stream. Post H0 per raw byte accounts for changes in stream length. In the paired compressor tables, a positive percentage means preprocessing made the compressed file smaller.

### noisy-spacetime · 25,165,824 raw bytes

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `four-joint` | 34,605,324 | 7.9645 → 3.2005 | 7.9554 → 2.0327 | 4.4010 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `four-joint` | 25,042,968 → 9,362,367 (+62.61%) | 25,166,413 → 9,397,974 (+62.66%) | 25,063,412 → 8,109,204 (+67.65%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `four-direct` | 25,120,549 | +45,275 | 1.351 | 0.902 |
| `four-equivalent` | 25,120,549 | +45,275 | 7.538 | 1.313 |
| `four-joint` | 9,414,787 | +15,751,037 | 71.639 | 12.335 |
| `four-orbit` | 19,601,212 | +5,564,612 | 46.702 | 7.518 |
| `four-rank` | 25,120,549 | +45,275 | 5.129 | 0.756 |

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#noisy-spacetime)

### numerical · 25,696,748 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `four-direct` | 16,014,181 | +9,682,567 | 1.946 | 1.080 |
| `four-equivalent` | 16,014,181 | +9,682,567 | 10.374 | 1.016 |
| `four-joint` | 16,013,206 | +9,683,542 | 98.398 | 1.591 |
| `four-orbit` | 16,013,206 | +9,683,542 | 49.426 | 1.247 |
| `four-rank` | 16,014,181 | +9,682,567 | 5.019 | 1.167 |

Same-input baseline archives (bytes) · XZ 9 extreme 11,662,476 · Zstandard 19 13,213,336 · Zstandard 3 15,163,683

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numerical)

### samba · 21,606,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `four-direct` | 5,843,228 | +15,763,172 | 1.975 | 1.221 |
| `four-equivalent` | 5,843,228 | +15,763,172 | 12.148 | 0.739 |
| `four-joint` | 5,843,228 | +15,763,172 | 52.373 | 0.861 |
| `four-orbit` | 5,843,228 | +15,763,172 | 39.657 | 1.470 |
| `four-rank` | 5,843,228 | +15,763,172 | 5.621 | 1.424 |

Same-input baseline archives (bytes) · XZ 9 extreme 3,739,524 · Zstandard 19 3,894,675 · Zstandard 3 4,957,768

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#samba)

### uniform · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `four-direct` | 25,168,140 | -2,316 | 0.882 | 0.824 |
| `four-equivalent` | 25,168,140 | -2,316 | 7.082 | 1.470 |
| `four-joint` | 25,168,140 | -2,316 | 59.974 | 0.834 |
| `four-orbit` | 25,168,140 | -2,316 | 48.124 | 0.760 |
| `four-rank` | 25,168,140 | -2,316 | 4.588 | 1.319 |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

<!-- END generated project measurements -->

## Connections

The [three-dimensional exact rank study](../tensor-orbits/README.md) uses different panels. The [motion residual study](../motion-residuals/README.md) works on natural sequences of luminance frames.
