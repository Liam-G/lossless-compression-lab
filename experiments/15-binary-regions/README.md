# Experiment 15 · Regenerating binary regions

## Question and prior work

How much of a binary can a versioned generator catalog recreate after every interval and recipe is counted?

The earlier archive9 study regenerated 187 bytes in 18 intervals and saved 107 archive bytes with an external decoder. Part of its constants catalog had been selected after inspecting archive9.

### Source files and compatibility

The catalog ports the square-root and FNV constants. The ELF prototype motivates reconstruction by parameters. The new header profile also handles regular multi-segment executable headers without modeling program headers. Paths below are relative to the original workspace.

- `lab/hutter/catalogo-formule/RISULTATI.md`
- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/elf64.py`
- `lab/hutter/catalogo-formule/formule.py`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 15 test
python3 ../../lab.py 15 encode ../../fixtures/scanner.elf sample.lcx
python3 ../../lab.py 15 decode sample.lcx sample.restored
cmp ../../fixtures/scanner.elf sample.restored
python3 ../../lab.py 15 benchmark ../../runs/recheck-15
```

## Variants and format

Cross ELF header generation with local formula scanning. A little-endian ELF64 header is reconstructed from a fixed identification prefix and varint fields. Use the original integer square-root/FNV constant catalog, repeated-byte runs and backward copies for the remaining regions. Weighted interval scheduling maximizes saved bytes with absolute positions, widths, tags, recipe lengths and parameters included. Uncovered bytes stay literal. The decoder regenerates each interval in output order.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

The planted file contains a generated ELF header, indexed constants, runs and random gaps. Two complete held-out lab executables are the rusage wrapper with a GCC build comment and the repdigit scanner containing a Clang build comment. Treat both as byte strings. Family statistics give regenerated and record bytes. Subtract the latter for net savings.

The ELF rule applies only to the frozen identification prefix. The comparison targets two program builds. The collection CSV measures an executable Python package containing both archives and a single decoder and verifies both extracted files.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

Across the two real executables, the combined profile used 18,900 archive bytes. The runnable package with one shared decoder used 26,330 bytes and decoded both files.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| generated-header-and-regions | 640 | combined | 461 | 488 |
| uniform | 640 | literal | 652 | 653 |
| rusage.elf | 16,584 | combined | 5,984 | 3,294 |
| scanner.elf | 23,128 | combined | 12,916 | 7,647 |

All 16 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json). [Collection delivery costs](results/reference/collection.csv).


## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#15-binary-regions) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 01 supplies arithmetic regions, experiment 12 supplies reference copies and experiment 16 compares competing intervals.
