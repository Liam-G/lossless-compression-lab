# Conditional patches after arithmetic alignment

## Question and prior work

Can a cheap arithmetic transformation turn a reference into a useful predictor, and what does the result cost when the receiver must also obtain the reference?

### Source files and compatibility

Reports 021, 057 and 058 distinguish a shared model, a reference patch and computational reproduction. ARF1 is a new, general archive with a content-addressed reference. It also tests the older lab observation that the matching FX2 numerator is exactly 3,072 times Q.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
BASE=../lab/hutter/divisors/fx2-cmix-transformer-archive9.bin
python3 research/arithmetic-references/codec.py encode "$Q" runs/q.arf --reference "$BASE" --profile exact
python3 research/arithmetic-references/codec.py decode runs/q.arf runs/q-relative.restored --reference "$BASE"
cmp "$Q" runs/q-relative.restored
```

## Variants and format

The encoder compares direct Zstandard 9, Zstandard patch-from, and an XOR delta after multiplying or dividing the entire reference integer. Dispersed exact-byte probes shortlist scales. The exact profile can omit the residual when the prediction is identical. The header carries the target width, mode, scale and required reference SHA-256. Direct mode can decode without a base.

## Inputs and measurement

The complete award release and the exact original FX2 numerator are separate references for Q. Two independent transfers use the decompressed package tar streams of adjacent NumPy and Mesa releases. The measurements identify both hashes and show base delivery separately.

## Results

The matching 96,994,188-byte numerator and a 46-byte formula recover all of Q; delivering both costs 96,994,234 bytes. With the other FX2 award release the exact profile selected direct coding at 96,996,466. The NumPy update used 1,347,467 bytes relative to its older package, versus 10,201,056 direct. Mesa also benefited from a conventional patch. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#arithmetic-references) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 12 uses local copies. [Scale-and-region coding](../carry-trees/README.md) seeks arithmetic structure without an external reference.
