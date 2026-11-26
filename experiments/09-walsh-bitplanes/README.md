# Experiment 09 · Walsh–Hadamard prediction and bit planes

## Question and prior work

Do bit planes and sparse Walsh–Hadamard coefficients produce a better binary prediction once coefficient and residual bytes are counted?

The original hunt program identifies large Walsh coefficients and estimates the cost of correcting discordant bits. This experiment serializes the prediction and its inverse.

### Source files and compatibility

The spectral family in the C++ search supplies the signed Walsh predictor. The new wire format retains each coefficient and its exact correction. Paths below are relative to the original workspace.

- `lab/arena/hunt.cpp`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 09 test
python3 ../../lab.py 09 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 09 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 09 benchmark ../../runs/recheck-09
```

## Variants and format

Split into 32-byte blocks and optionally transpose to bit-plane order. Map bits to signed amplitudes, zero-pad to a power of two, and apply the fast Walsh–Hadamard transform. Try 0, 1, 2, 4 or 8 retained coefficients by actual record size. Transmit each coefficient index and ZigZag amplitude. Threshold the inverse transform and DEFLATE the exact XOR mask. All four profiles use the same residual backend and framing. The decoder reverses the plane layout after applying residuals.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Use a periodic binary signal with 0, 16 or 128 flipped positions, plus fax masks and quantized medical-image bytes. A separate positive control contains exact Walsh basis signals. Trial details count how often each coefficient count is selected.

Each block starts a fresh DEFLATE stream. Its framing overhead is especially visible on the short real samples.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

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

## Connections

Experiment 08 offers a low-rank predictor. Experiment 14 compares the residuals obtained from both predictors.
