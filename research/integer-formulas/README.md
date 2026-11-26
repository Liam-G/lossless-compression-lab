# Whole-file square, product and modular-square formulas

## Question and prior work

What is left to send after fitting a whole integer with squares, products of consecutive integers, or a modular square preceded by a sparse polynomial?

### Source files and compatibility

The three archive formats come from `lab/hutter/divisors/q-formula-intera/{formula,quadrato_modulare,composta}.py`. The English source preserves their wire formats. The composite runner computes its own temporary modular root. Decoding QFC1 requires only the descriptor and gmpy2.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
# Use a Python environment containing gmpy2 for this project.
"${GMP_PYTHON:-python3}" research/integer-formulas/run.py composite "$Q" runs/q.qfc
"${GMP_PYTHON:-python3}" research/integer-formulas/run.py decode runs/q.qfc runs/q-formula.restored
cmp "$Q" runs/q-formula.restored
```

## Variants and format

QFE1 recursively describes the signed error after a floor square, a nearest square or the nearest of the allowed squares and consecutive products. QMS1 chooses a compact root modulo 2ᵇ for eligible odd integers congruent to 1 modulo 8. QFC1 transmits the width, prefix length, divisor, positions and values of sparse prefix coefficients, and the modular root of the suffix. The QMS1/QFC1 encoders require at least three significant bits and the stated congruence.

## Inputs and measurement

The entire 96,994,187-byte FX2 cofactor was encoded by each profile. Each independent decode was compared with canonical Q; the final archive includes all coefficients, signs and widths. Shared arithmetic software and the encoder’s temporary root are excluded.

## Results

Floor, nearest and mixed QFE1 descriptors gave 96,994,288, 96,994,277 and 96,994,272 bytes. QMS1 gave 96,994,197. The sparse prefix and modular suffix gave 96,994,051, saving 136 bytes. The original search identified 232 prefix bytes, 42 nonzero coefficients and divisor 12. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `cofattore-Q.base256` (96,994,187 raw bytes), `integer-composite` produced 96,994,051 archive bytes. Zstandard level 3 used 96,996,424 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#cofattore-qbase256) · [All project measurements](../large-scale/results/by-experiment.md#integer-formulas)

## Connections

The [quartic tree](../quartic-trees/README.md) recursively describes operands. The [sparse multiplier](../carry-trees/README.md) tests whether the same arithmetic structure helps an entropy coder.

QMS1 and QFC1 require an input congruent to 1 modulo 8 with at least three significant bits. The `modular-adjusted` and `composite-adjusted` profiles extend the experiment to arbitrary byte strings. QMA1 stores the original three low bits, lifts very small inputs into the valid range, and embeds an ordinary modular or composite descriptor. Its decoder also restores the exact byte width and the empty string.
