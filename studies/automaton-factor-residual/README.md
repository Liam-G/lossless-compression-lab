# Automata, factors and residual coding

## Question

Does undoing an automaton step reduce residual cost when the factor model stays fixed?

## Run the study

Run from the repository root on Linux with Python and the Zstd CLI.

```sh
python3 studies/run.py automaton-factor-residual runs/automaton-factor-residual
```

## Variants and inputs

Fit two GF(2) basis vectors per eight-row matrix using experiment 08. The orbit profiles consider up to three reverse Checkerboard steps from experiment 06. Rank from experiment 07 breaks ties after residual weight. Send the selected step, basis, coordinates and a nested experiment 14 residual archive. First compare direct and orbit prediction with enumerative coding. Then hold orbit selection fixed while switching among enumeration, Rice gaps, contexts and per-block selection.

The planted control evolves noisy rank-two matrices. The real controls are a fax window and medical-image bytes. Transform selection minimizes residual weight with a fixed tie rule. Every residual profile sees the same chosen factors for an orbit input.

## Results

With enumeration fixed, the orbit reduced the evolved control from 475 bytes to 339. Holding that prediction fixed, Rice used 350 bytes and the context code used 355.

| Input | Profile | Raw bytes | Archive | Archive plus required base | Zstd |
|---|---|---:|---:|---:|---:|
| evolved-noisy-rank-two | direct-enumerative | 384 | 475 | 475 | 397 |
| evolved-noisy-rank-two | orbit-enumerative | 384 | 339 | 339 | 397 |
| evolved-noisy-rank-two | orbit-rice | 384 | 350 | 350 | 397 |
| evolved-noisy-rank-two | orbit-context | 384 | 355 | 355 | 397 |
| evolved-noisy-rank-two | orbit-adaptive | 384 | 351 | 351 | 397 |
| uniform | direct-enumerative | 384 | 509 | 509 | 397 |
| uniform | orbit-enumerative | 384 | 537 | 537 | 397 |
| uniform | orbit-rice | 384 | 554 | 554 | 397 |
| uniform | orbit-context | 384 | 577 | 577 | 397 |
| uniform | orbit-adaptive | 384 | 549 | 549 | 397 |
| fax-mid.bin | direct-enumerative | 512 | 313 | 313 | 80 |
| fax-mid.bin | orbit-enumerative | 512 | 377 | 377 | 80 |
| fax-mid.bin | orbit-rice | 512 | 393 | 393 | 80 |
| fax-mid.bin | orbit-context | 512 | 425 | 425 | 80 |
| fax-mid.bin | orbit-adaptive | 512 | 393 | 393 | 80 |
| medical.bin | direct-enumerative | 512 | 353 | 353 | 137 |
| medical.bin | orbit-enumerative | 512 | 417 | 417 | 137 |
| medical.bin | orbit-rice | 512 | 433 | 433 | 137 |
| medical.bin | orbit-context | 512 | 460 | 460 | 137 |
| medical.bin | orbit-adaptive | 512 | 433 | 433 | 137 |

All 20 study archives reconstructed their original bytes. The [trial table](results/reference/trials.csv) includes input hashes, side-stream byte counts and single-run timings. [Study implementation](benchmark.py).

## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#automaton-factor-residual) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.
