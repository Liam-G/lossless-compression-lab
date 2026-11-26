# Recursive fourth-power quotients

## Question and prior work

How long is a whole-file formula when its operands also have to be specified? The original GMP engine in `lab/hutter/divisors/q-torri-quoziente/ricorsiva/quartiche.cpp` constructs nodes of the form `F(k,a,d) = floor((a⁴ + d⁴) / 2ᵏ)`. The decoder knows how to derive the shift and child widths. The encoder uses integer fourth roots and remainders to construct both children and continues recursively. Small subtrees use a shared 65,536-entry dictionary whose terminal operands are the integers 0 through 15.

## Run the experiment

```sh
mkdir -p runs
head -c 4096 "$Q" > runs/q-prefix.bin
python3 research/quartic-trees/codec.py encode runs/q-prefix.bin runs/q.quartic
python3 research/quartic-trees/codec.py decode runs/q.quartic runs/q-prefix.restored
cmp runs/q-prefix.bin runs/q-prefix.restored
python3 research/benchmark_native.py "$Q" runs/native-quartics
```

## Variants and format

The historical engine accepted the integer width separately. The QW01 wrapper stores the original byte count and significant bit width in a 20-byte header, preserving empty input and leading zero bytes. The original engine supplies the remaining bytes. Each recursive reference or explicitly encoded pair of child descriptions contributes to the formula length.

## Inputs, results and interpretation

Fresh Q prefixes of 4 KiB, 64 KiB and 1 MiB produced 11,450, 181,137 and 2,483,741 archive bytes with the wrapper. All decoded exactly. The [historical full-Q measurement](original-full-q.json) recorded 247,891,597 formula bytes before wrapper framing, with 956,890,129 fourth-power nodes when fully expanded and maximum depth 39. It includes matching input and reconstructed SHA-256 digests. A fresh QW01 encode of all 96,994,187 Q bytes produced 247,891,575 archive bytes and passed independent decoding. The receipts preserve each measurement under its own format and build. Both full runs spent more bytes describing the two operands than the original integer occupied. [Prefix replay](../evidence/native-replay/trials.csv)

## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#quartic-trees) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.
