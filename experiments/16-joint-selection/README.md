# Experiment 16 · Joint selection of compression methods

## Question and prior work

Does selecting a method at different offsets beat a single method once headers and model resets are fully priced?

The prior mixed archive combines generated blocks with compressed literals. The original formula scanner uses dynamic programming over competing intervals.

### Source files and compatibility

The mixed-archive source supplies the generated-record and literal-stream comparison. This implementation prices local DEFLATE streams and the three proposed candidate families. Paths below are relative to the original workspace.

- `lab/arena/pattern_archive.py`
- `lab/hutter/catalogo-formule/RISULTATI.md`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 16 test
python3 ../../lab.py 16 encode ../../fixtures/medical.bin sample.lcx
python3 ../../lab.py 16 decode sample.lcx sample.restored
cmp ../../fixtures/medical.bin sample.restored
python3 ../../lab.py 16 benchmark ../../runs/recheck-16
```

## Variants and format

Each candidate emits a method tag, regenerated width, body length and body. Compare a complete-file choice, choices on fixed 32-byte blocks and variable intervals starting at every byte. At each permitted width try DEFLATE, a direct repdigit from a frozen catalog, or an exact rank-one GF(2) row model with a basis byte and row mask. Variable search uses widths 1, 4, 8, 12, 16, 24, 32, 48 and 64, clipped at EOF, plus a complete-file edge. The regions extension additionally tests ELF headers and frozen constants. Dynamic programming charges a fresh DEFLATE stream at every literal interruption and checks the serialized record bytes against its predicted cost.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

The mixed control alternates 11 random bytes, a 24-byte arithmetic region, 16 bytes of rank-one rows and an eight-byte constant. Only the generator knows these boundaries. A second positive control changes the repdigit exponent, basis and constant across regions. Test uniform noise and prefixes of two real executables and a medical-image file.

The shortest path is optimal within the stated interval and method catalog. The arithmetic search and rank-one model are bounded subsets of the families in experiments 01 and 07. Full-file DEFLATE can benefit from a larger history than local literal streams.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

On the repeated-motif input the complete-file candidate used 191 bytes and variable selection tied it. On the separate 1,824-byte varying-recipe control, single used 1,369 bytes, variable intervals used 1,158, and adding local regions reduced the archive to 1,020. Zstd used 1,384 bytes on that control.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| mixed-11-24-16-8 | 354 | single | 191 | 185 |
| uniform | 354 | single | 382 | 367 |
| mixed-varying-recipes | 1,824 | intervals-regions | 1,020 | 1,384 |
| rusage.elf | 512 | single | 175 | 173 |
| scanner.elf | 512 | single | 179 | 179 |
| medical.bin | 512 | single | 141 | 137 |

All 24 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json).


## Large-file benchmark

The [primary measurements for this experiment](../../research/large-scale/results/by-experiment.md#16-joint-selection) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 01 motivates arithmetic records, experiment 07 motivates matrix records, and the final profile uses shared region generators from experiment 15.
