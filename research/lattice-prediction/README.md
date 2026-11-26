# Local integer grids and bit-plane residuals

## Question and prior work

Can a file disclose its sample width and lag without an image or scientific-format parser? Do those predictors help once a general entropy coder sees the separated bit planes?

### Source files and compatibility

The historical `lab/shape/nested.py` measured conditional entropy from rows, byte lanes and planes of the original data. This new encoder turns the same idea into an actual inverse and compares the cost of its complete records.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/lattice-prediction/codec.py encode runs/large/raw/numerical runs/grid.ltp --profile joint-xz
python3 research/lattice-prediction/codec.py decode runs/grid.ltp runs/grid.restored
cmp runs/large/raw/numerical runs/grid.restored
```

## Variants and format

Each 1 MiB block tries 1-, 2- and 4-byte unsigned little-endian samples. Dispersed points shortlist lags; modular first differences, XOR, second differences, or a mixed two-axis derivative predict the current value. ZigZag maps signed differences back to fixed-width integers. Whole bytes, byte lanes and bit planes share the same backend. LTP1 uses Zstandard. LTX1 reprices the three best fast candidates and the unmodified block with XZ preset 6. The original length, per-block width, lag, predictor, layout, payload and tail are all recoverable.

## Inputs and measurement

The numerical file concatenates complete Silesia mr, x-ray and sao in that order. Other files include textual Silesia members, binary software, disjoint Wikipedia text, matched noise and derived distance matrices. The 1 MiB block boundaries cross the two numerical member boundaries.

## Results

On 25,696,748 numerical bytes, layout alone gave 13,018,122, prediction alone 13,025,639 and their joint Zstd-3 representation 11,654,765. Repricing with Zstd-19 gave 11,006,699. The matched blocked XZ control was 11,846,741 and the joint XZ archive 10,421,725. Whole-file XZ extreme gave 11,662,476. The gain disappeared on the held-out Wikipedia text. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `numerical` (25,696,748 raw bytes), `lattice-joint-xz` produced 10,421,725 archive bytes. Zstandard level 3 used 15,163,683 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#numerical) · [All project measurements](../large-scale/results/by-experiment.md#lattice-prediction)

## Connections

Compare with [integer wavelets](../reversible-wavelets/README.md), [shape contexts](../shape-context/README.md) and the [distance geometry](../distance-geometry/README.md) model for triangular layouts.
