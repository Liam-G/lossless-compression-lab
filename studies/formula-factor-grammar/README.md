# Formula leaves, factors and grammar references

## Question and prior work

How much does a shared-factor dictionary add when the factor itself already has a short repdigit recipe?

## Run the experiment

Run from the repository root on Linux with Python and the Zstd CLI.

```sh
python3 studies/run.py formula-factor-grammar runs/formula-factor-grammar
```

## Variants and format

All four profiles use the same small-divisor search and product tree. Each 16-byte input word is represented by the first fitting divisor and its cofactor. Experiment 02 supplies literal operand coding. Experiment 01 supplies the bounded direct/ratio catalog and arithmetic inverse. The sharing profiles intern cofactor values at first occurrence using experiment 11’s reference token encoding. Each leaf has an operator tag. Only shared profiles build the dictionary, which the decoder reconstructs in order.

## Inputs and measurement

The planted file contains 80 products built from four repeating quotient leaves. A cofactor window and an equal-sized random control provide comparison inputs. The study shares factor leaves. A deeper product-tree search would test additional kinds of reuse.

## Results

The following table records the original small diagnostic. The primary benchmark follows it.

Sharing alone used 303 bytes on the planted input. Enabling arithmetic leaves as well reduced it to 264 bytes. Arithmetic without shared references used 492 bytes.

| Input | Profile | Raw bytes | Archive | Archive plus required base | Zstd |
|---|---|---:|---:|---:|---:|
| shared-quotient-factors | literal-leaves | 1280 | 1273 | 1273 | 153 |
| shared-quotient-factors | arithmetic-leaves | 1280 | 492 | 492 | 153 |
| shared-quotient-factors | shared-leaves | 1280 | 303 | 303 | 153 |
| shared-quotient-factors | combined | 1280 | 264 | 264 | 153 |
| uniform | literal-leaves | 1280 | 1726 | 1726 | 1293 |
| uniform | arithmetic-leaves | 1280 | 1726 | 1726 | 1293 |
| uniform | shared-leaves | 1280 | 1726 | 1726 | 1293 |
| uniform | combined | 1280 | 1726 | 1726 | 1293 |
| real-cofactor-words | literal-leaves | 512 | 697 | 697 | 525 |
| real-cofactor-words | arithmetic-leaves | 512 | 697 | 697 | 525 |
| real-cofactor-words | shared-leaves | 512 | 697 | 697 | 525 |
| real-cofactor-words | combined | 512 | 697 | 697 | 525 |

All 12 study archives reconstructed their original bytes. The [trial table](results/reference/trials.csv) includes input hashes, side-stream byte counts and single-run timings. [Study implementation](benchmark.py).

## Large-file benchmark

On `hidden-products` (25,165,824 raw bytes), `study17-combined` produced 20,296,188 archive bytes. Zstandard level 3 used 14,343,987 bytes on the same input. [Input and timing](../../research/large-scale/results/by-dataset.md#hidden-products) · [All project measurements](../../research/large-scale/results/by-experiment.md#formula-factor-grammar)

## Connections

[Shared formulas inside a factor tree](../../research/shared-factor-forest/README.md) · [Whiteboard quotients inside factor trees](../../research/whiteboard-trees/README.md)
