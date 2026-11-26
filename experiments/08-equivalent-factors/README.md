# Experiment 08 · Equivalent matrix factors and error masks

## Question and prior work

Can changing a GF(2) factor basis reduce the archive while preserving both the prediction and its exact error mask?

The matrix laboratory serializes U, V and E such that M = UV XOR E. The source thesis proposes the additional equivalent-basis comparison.

### Source files and compatibility

The original matrix encoding uses separate U, V and E streams. This experiment adds a two-dimensional change-of-basis search and checks the factor identity directly. Paths below are relative to the original workspace.

- `lab/hutter/divisors/q-correzioni-fattori/encoder-cofattori/cmix-neif-2.0/griglie-intere/encoding-matrici/RISULTATI.md`
- `lab/hutter/divisors/q-correzioni-fattori/encoder-cofattori/cmix-neif-2.0/griglie-intere/encoding-matrici/matrici.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 08 test
python3 ../../lab.py 08 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 08 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 08 benchmark ../../runs/recheck-08
```

## Variants and format

Treat 16 rows of eight bits as a matrix. Greedily choose two basis vectors from observed rows to reduce residual Hamming weight. For each row choose the nearest of four products. Test the initial basis, swaps, elementary XOR, and a search over the six invertible two-coordinate basis transforms. Apply the corresponding inverse operation to the coordinates. Serialize both coordinate columns and both basis rows as varints, and DEFLATE the unchanged E stream. Metadata gives the U and V lengths. Actual U, V and E bytes are recorded separately.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Construct rank-two matrices with two independent rows, then add four errors in isolated cells, a burst or a single row. Evaluate the same predictors on fax and medical-image bytes.

The factor budget is two columns. Degenerate inputs can use fewer independent vectors. Initial factors are fitted from observed rows, so the resulting E need not equal the planted noise.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

The full equivalent-basis search reduced the isolated-error archive from 281 to 276 bytes with the same residual.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| isolated | 384 | search | 276 | 386 |
| uniform | 384 | search | 559 | 397 |
| burst | 384 | search | 272 | 363 |
| one-row | 384 | search | 286 | 347 |
| fax.bin | 512 | initial | 157 | 22 |
| fax-mid.bin | 512 | initial | 195 | 80 |
| medical.bin | 512 | xor | 283 | 137 |

All 28 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).

### Factor and error bytes on the isolated-error control

| Basis search | Coordinate columns U | Basis rows V | Mask E |
|---|---:|---:|---:|
| initial | 124 | 73 | 70 |
| swap | 124 | 73 | 70 |
| xor | 123 | 72 | 70 |
| search | 121 | 71 | 70 |


## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#08-equivalent-factors) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 07 compresses factors recursively. Experiment 14 benchmarks the actual residual masks produced here.
