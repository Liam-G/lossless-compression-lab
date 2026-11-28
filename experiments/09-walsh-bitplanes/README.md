# Experiment 09 · Walsh–Hadamard prediction and bit planes

> **Verdict: loses on real data.** Best real input: Scanned manual: Graphviz guides, 65.1× larger vs DjVu.
>
> Part of [chapter 2](../../report/2-dynamics.md) of the [report](../../report/README.md). Terms: [glossary](../../report/glossary.md).

## Question

Can a few large Walsh–Hadamard (binary Fourier) coefficients predict each bit plane, so that only the coefficients and the wrong bits need storing?

## How it works

```mermaid
flowchart LR
    I["Byte block"] --> T["Reorder planes and retain Walsh coefficients"]
    T --> W["Send coefficients and exact XOR mask"]
```

Each bit plane is transformed, its largest coefficients are kept, and the plane they predict is XORed with the real one to give a sparse correction.

<details><summary>Technical details</summary>

Do bit planes and sparse Walsh–Hadamard coefficients produce a better binary prediction once coefficient and residual bytes are counted?

The original hunt program identifies large Walsh coefficients and estimates the cost of correcting discordant bits. This experiment serializes the prediction and its inverse.

**Mechanism and test.** A few coefficients can describe extensive regular patterns. Precision is recovered through the mask, whose size can exceed the avoided literals. Compare plane-only and predictor-only profiles to isolate the source of a change.

Split into 32-byte blocks and optionally transpose to bit-plane order. Map bits to signed amplitudes, zero-pad to a power of two, and apply the fast Walsh–Hadamard transform. Try 0, 1, 2, 4 or 8 retained coefficients by actual record size. Transmit each coefficient index and ZigZag amplitude. Threshold the inverse transform and DEFLATE the exact XOR mask. All four profiles use the same residual backend and framing. The decoder reverses the plane layout after applying residuals.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

</details>

## Results on 20 MiB inputs

Every archive below decoded byte-exact. *Our archive* is this project's own format. *Our transform → standard tool* reshapes the bytes reversibly and hands the result to gzip, zstd or xz; it is listed only where it beats that same tool on the raw bytes. *Best standard tool* is the smallest of gzip, bzip2, xz, Zstandard, Brotli and PPMd (plus domain codecs for images, scans and video) on the raw bytes. *Difference* compares the better of our two columns with it; negative = ours is smaller.

| Input | Kind | Raw bytes | Our archive | Our transform → standard tool | Best standard tool | Difference |
|---|---|---:|---:|---:|---:|---:|
| Scanned manual: Graphviz guides | real | 24,642,792 | 12,437,412 (`pilot09-direct`) | — | 191,132 (DjVu) | 65.1× larger |
| Scanned manual: Graphviz library | real | 24,283,584 | 13,922,627 (`pilot09-combined`) | — | 175,164 (DjVu) | 79.5× larger |

<details><summary>All profiles, timings and entropy measurements</summary>

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. *Bytes saved* is raw size minus archive (and any reference the decoder needs). Timings are one run on a shared desktop.

These tables list every measured profile. The comparison with the best standard tool on each input (gzip, bzip2, xz, Zstandard, Brotli, PPMd and the domain codecs) is the Results table above.

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### manual-library · 24,283,584 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot09-combined` | 13,922,627 | +10,360,957 | 1254.920 | 268.980 | 24,712 / 23,596 |

Same-input baseline archives (bytes) · DjVu 202,780 · DjVu (separated foreground) 202,666 · DjVu (wide strips) 175,164 · CCITT Group 4 1,678,602 · JBIG 1,049,864 · 1-bit PNG 1,996,848 · XZ 9 extreme 1,304,420 · Zstandard 19 1,457,017 · Zstandard 3 1,903,366

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#manual-library)

### manual-graphs · 24,642,792 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `pilot09-combined` | 12,936,974 | +11,705,818 | 424.479 | 123.117 | 24,808 / 23,620 |
| `pilot09-direct` | 12,437,412 | +12,205,380 | 43.868 | 33.618 | 24,680 / 23,352 |

Same-input baseline archives (bytes) · DjVu 214,067 · DjVu (separated foreground) 213,732 · DjVu (wide strips) 191,132 · CCITT Group 4 1,270,850 · JBIG 707,797 · 1-bit PNG 1,418,635 · XZ 9 extreme 930,864 · Zstandard 19 1,034,431 · Zstandard 3 1,325,134

[Input hash and all measured codecs](../../research/large-scale/results/by-dataset.md#manual-graphs)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-09-walsh-bitplanes --project 09-walsh-bitplanes --all-profiles
```

[Dataset preparation](../../research/large-scale/README.md#inputs) · [Archive hashes and settings](../../research/large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

</details>

## Small-scale results

Use a periodic binary signal with 0, 16 or 128 flipped positions, plus fax masks and quantized medical-image bytes. A separate positive control contains exact Walsh basis signals. Trial details count how often each coefficient count is selected.

Each block starts a fresh DEFLATE stream. Its framing overhead is especially visible on the short real samples.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

On the noiseless periodic control, plane separation reduced 284 bytes to 220. Adding spectral prediction produced the same size, while whole-file Zstd used 24 bytes. On the additional Walsh-basis positive control, the combined predictor used 276 bytes, three fewer than the better single component.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| periodic-noise0 | 512 | planes | 220 | 24 |
| uniform | 512 | direct | 716 | 525 |
| periodic-noise16 | 512 | planes | 272 | 97 |
| periodic-noise128 | 512 | planes | 481 | 238 |
| planted-Walsh-basis | 512 | combined | 276 | 173 |
| fax.bin | 512 | direct | 220 | 22 |
| fax-mid.bin | 512 | direct | 310 | 80 |
| medical.bin | 512 | planes | 333 | 137 |

All 32 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

## Run it

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 09 test
python3 ../../lab.py 09 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 09 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 09 benchmark ../../runs/recheck-09
```

## Provenance

<details><summary>Where this code came from</summary>

The spectral family in the C++ search supplies the signed Walsh predictor. The new wire format retains each coefficient and its exact correction. Paths below are relative to the original workspace.

- `lab/arena/hunt.cpp`

</details>
