# Mixed-arity factor trees

## Question and prior work

Can extracting the small prime factors of every node pay for the tree when its children split at different bit positions? The native GMP implementation comes from `lab/hutter/divisors/q-fattori-ricorsivi/albero.cpp`. It uses Statico's range coder for factor descriptors. The [original sweep](original-arity-sweep.tsv) prices 129 schedules. Its final column identifies configurations originally written and checked with `cmp`.

## Run the experiment

Build the [research engines](../README.md#build-and-reproduce) and set `Q` as described there. QRT accepts nonempty files. These commands use the entire cofactor.

```sh
mkdir -p runs
research/build/factor-tree split-seeded "$Q" runs/q.qrt runs/levels.tsv 1048576 128 2
research/build/factor-tree join runs/q.qrt runs/q.restored
cmp "$Q" runs/q.restored
python3 research/benchmark_native.py "$Q" runs/native-trees
```

## Variants and format

At each node, divide out small prime powers. Split the remaining cofactor in binary, retaining each child's width so leading zeros can be restored. The decoder concatenates the child bit strings and multiplies the extracted factors back in. QRT4 carries the per-level arity schedule and a common cut offset. QRT5 carries a seed from which both sides derive individual boundary shifts. The seed, arities, arithmetic-coded factor descriptions, leaves and terminal padding all count.

## Inputs, results and interpretation

| Configuration, 1 MiB leaf limit | Archive bytes | Excess over Q |
|---|---:|---:|
| Centered binary | 96,994,218 | 31 |
| Arity 9 then 11, offset −9 bits | 96,994,215 | 28 |
| Arity cap 128, seed 2 | 96,994,214 | 27 |

The last configuration made 93 actual children at the root. Its 96,994,126 leaf bytes saved 61 bytes. The header and factor descriptors occupied 22 and 66 bytes, respectively. All three full reconstructions passed a byte comparison. Allowing more children improved the balance by four bytes over the binary tree. The [replay](../evidence/native-replay/trials.csv) includes timings and the input hash. For a child whose cofactor contains a formula, see the [nested experiment](../whiteboard-trees/README.md).

## Decimal splitting with a primorial GCD

QBF1 is the decimal implementation recovered from `lab/hutter/divisors/q-blocchi-fattori`. It divides the text into decimal groups, takes a GCD with the product of primes up to 100,000, removes each matching prime power and records the remaining cofactor. Groups longer than ten digits with no match split in half. Each terminal carries its digit count, so the decoder can restore leading zeroes. The final newline also has a representation.

```sh
research/build/decimal-blocks split ../lab/hutter/divisors/cofattore-Q.txt runs/q.qbf runs/decimal-blocks.tsv 100000000
research/build/decimal-blocks join runs/q.qbf runs/q-restored.txt
cmp ../lab/hutter/divisors/cofattore-Q.txt runs/q-restored.txt
```

The full input contained 233,585,278 decimal-text bytes. The benchmark archive used 96,994,346 bytes. Converting the same number directly to canonical binary needs 96,994,187 bytes, 159 fewer. The measurement name records its maximum decimal group width. [Decimal-source measurements](../large-scale/results/by-dataset.md#cofattore-qtxt)

## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#factor-trees) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.
