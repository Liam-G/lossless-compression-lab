# Three seeded generators plus a signed residual

## Question and prior work

If the encoder searches 16,777,216 seed triples, how much of the target can those three transmitted seed bytes actually explain?

### Source files and compatibility

This is the original QGS1 encoder and decoder from `lab/hutter/divisors/q-somma-generatori`, with English diagnostics. It uses the precise SHAKE domains and signed residual representation of the original experiment.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/generator-sums/control.py runs/sums.bin
python3 research/generator-sums/encode.py runs/sums.bin runs/sums.qgs --block 4096
python3 research/generator-sums/decoder.py runs/sums.qgs runs/sums.restored
cmp runs/sums.bin runs/sums.restored
```

## Variants and format

The first term carries a seed byte as its high byte. Each of the other terms has a leading zero byte. Ordered sums of two terms support a nearest-neighbor search. A prefix bound safely eliminates candidates before the remaining full-width differences are evaluated. Each unit transmits three seeds, a signed-length descriptor and the exact absolute residual. Block size zero describes one whole-file integer.

## Inputs and measurement

The plant has 6,144 distinct seed triples across 24 MiB. Half the blocks also receive a small signed correction. Real Q, ordinary numerical bytes and equally long uniform bytes use the same search budget.

## Results

The planted block archive was 36,872 bytes. Zstd-19 and XZ extreme both grew the 25,165,824-byte source. On complete Q, one search gave 96,994,205 bytes and 4 KiB searches gave 97,021,897. On uniform data the 4 KiB mode also expanded. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#generator-sums) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 03 uses a small generator budget; experiment 04 prices checkpointed irrational sums. The [integer formulas](../integer-formulas/README.md) try wholly different generators on the same Q.
