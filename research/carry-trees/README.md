# Integer carries across tree boundaries

## Question and prior work

Does multiplying or dividing a file before splitting expose regions that the same transformation on individual leaves misses?

### Source files and compatibility

The original mixed-arity trees divide an integer and split its quotient. The hybrid Q archive in `lab/hutter/divisors/q-ibrido/ibrido.py` selects disjoint spans in 12Q. CRT1 and SCL1 are new experiments based on those two constructions.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/carry-trees/codec.py encode runs/large/raw/mapped-text runs/mapped.crt --profile joint
python3 research/carry-trees/codec.py decode runs/mapped.crt runs/mapped.restored
cmp runs/large/raw/mapped-text runs/mapped.restored
python3 research/carry-trees/sparse_scale.py encode "$Q" runs/q.scl --profile informed
python3 research/carry-trees/sparse_scale.py decode runs/q.scl runs/q-scale.restored
cmp "$Q" runs/q-scale.restored
```

## Variants and format

CRT1 uses literal, Zstandard, split and map nodes on roots up to 4 MiB. An odd multiplier is bijective modulo 2ⁿ. The power of two in a factor rotates bits, preserving those that would otherwise overflow. The inverse solves the exact carry and reverses the rotation. A map above a split carries information across its boundary. Encoder shortlist decisions cost no decoder bits. SCL1 applies a single map across the entire file and uses weighted interval scheduling over verified compressed replacements. The probe-selected `joint` profile and the `informed` profile, which adds the original lab candidate 12, are reported separately.

## Inputs and measurement

Inputs include full Q, full Neif, real numerical bytes, noise, and 24 MiB of distinct Wikipedia fragments deliberately scrambled by independent page-local arithmetic maps.

## Results

On the scrambled text the combined tree gave 9,869,511 bytes, versus 14,295,184 for splitting alone. The independent numerical input gave 13,992,442 versus 14,355,119 for arithmetic alone. The 4 MiB tree stored all of Q literally. On full Q the sparse region-only archive was 96,993,475 bytes, the whole-file joint search gave 96,991,891, and explicitly including factor 12 gave 96,990,415. The original V15 package still has the larger saving. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#carry-trees) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Compare with [whiteboard trees](../whiteboard-trees/README.md), [whole-integer formulas](../integer-formulas/README.md) and [arithmetic reference patches](../arithmetic-references/README.md).
