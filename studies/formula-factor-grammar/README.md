# Formula leaves, factors and grammar references

## Question

How much does a shared-factor dictionary add when the factor itself already has a short repdigit recipe?

## Run the study

Run from the repository root on Linux with Python and the Zstd CLI.

```sh
python3 studies/run.py formula-factor-grammar runs/formula-factor-grammar
```

## Variants and inputs

All four profiles use the same small-divisor search and product tree. Each 16-byte input word is represented by the first fitting divisor and its cofactor. Experiment 02 supplies literal operand coding. Experiment 01 supplies the bounded direct/ratio catalog and arithmetic inverse. The sharing profiles intern cofactor values at first occurrence using experiment 11’s reference token encoding. Each leaf has an operator tag. Only shared profiles build the dictionary, which the decoder reconstructs in order.

The planted file contains 80 products built from four repeating quotient leaves. A cofactor window and an equal-sized random control provide comparison inputs. The study shares factor leaves. A deeper product-tree search would test additional kinds of reuse.

## Results

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
