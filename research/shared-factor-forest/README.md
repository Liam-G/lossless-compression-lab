# Shared formulas inside a factor tree

## Question and prior work

Can an exact ratio from the 2019 whiteboard become useful after dividing a word and cutting its cofactor at a bit boundary? Can several words pay for the same formula once?

### Source files and compatibility

The recipe dictionary and inverse follow the [whiteboard implementation](../whiteboard-trees/README.md), originally from `lab/hutter/ragc/entropy_base_tree`. SFF1 is a new page format. It encodes the shared divisor and widths explicitly.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/shared-factor-forest/codec.py encode runs/large/raw/hidden-products runs/products.sff --profile shared
python3 research/shared-factor-forest/codec.py decode runs/products.sff runs/products.restored
cmp runs/large/raw/hidden-products runs/products.restored
```

## Variants and format

Each 256 KiB page can store direct bytes, Zstandard 3, a split after a common factor, an inline formula, or an indexed formula dictionary. Candidate widths are 16, 32 and 64 bytes. For an exact factor of x + δ, the decoder joins the two cofactor children, multiplies, then subtracts δ. The page pays for the exceptions, recipe book, references, little integer fields, literal lanes, and tail. Formula-aware search uses sampled recipe hits to shortlist divisors. The factor-only profile ranks divisors without that signal.

## Inputs and measurement

The planted 24 MiB stream contains independently generated words. One child of a 17-fold product is an exact repunit quotient and the other has fresh random bits. The numerical stream, real affine instructions and uniform control use the same encoder.

## Results

Direct, factor-only and formula-only all gave 14,336,766 bytes on the plant. Inline composition gave 13,286,101. Sharing gave 13,097,327, beating inline by 188,774 and whole-file XZ extreme by 212,461. On the numerical data the shared and inline results tied at 15,271,526. On uniform data every profile tied at 25,166,508. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `hidden-products` (25,165,824 raw bytes), `shared-shared` produced 13,097,327 archive bytes. Zstandard level 3 used 14,343,987 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#hidden-products) · [All project measurements](../large-scale/results/by-experiment.md#shared-factor-forest)

On the generated hidden products, the full representation before a standard compressor occupied 13,379,724 bytes from 25,165,824 raw bytes. Its byte entropy increased from 6.374 to 7.928 bits per byte. Accounting for its shorter length gives 4.215 post-transform H0 bits per original byte. Whole-stream Zstandard 3 shrank from 14,343,986 to 13,038,675 bytes. [Matched preprocessing measurements](../large-scale/results/preprocessing.md)

## Connections

Experiment 01 defines the leaves, experiment 02 the factor operations and experiment 11 the shared-expression question. The [carry tree](../carry-trees/README.md) measures an alternate way of deciding where to split.
