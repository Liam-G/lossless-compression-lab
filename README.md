# Lossless Compression Lab

This English research repository contains 16 thesis experiments, three cross-experiment studies and 28 research projects recovered or extended from the original compression lab. The [large-file benchmark](research/large-scale/README.md) requires at least **20 MiB of raw input per trial** and checks exact reconstruction. The [idea atlas](research/evidence/idea-atlas.md) connects the local project conversations, the 51-topic dossier, and the original whiteboard formula to measured experiments and open proposals.

## Does preprocessing help a standard compressor?

The comparison uses two paths on identical input: **raw → standard compressor** and **reversible preprocessing → the same compressor**. We measure byte entropy before and after preprocessing, count every byte needed to undo it, and verify that both paths reconstruct the input.

![Byte entropy before and after preprocessing, alongside measured Zstandard savings. NOAA field routing leaves byte entropy near 3.95 bits and saves 40.85%. On Wikipedia the BWT leaves byte-frequency entropy nearly unchanged and saves 1.87%. On real numerical data lattice prediction lowers byte entropy from 6.35 to 4.93 bits per byte and saves 23.27%.](research/large-scale/results/preprocessing.png)

On two **24 MiB** samples of NOAA weather reports, simply gathering the bytes of each field together saved **40.85%** and **41.11%** with Zstandard. Byte-frequency entropy barely moved. Encoding a shared prefix against the previous value of the same field raised the savings to **43.34%** and **47.18%**. On UCI Covertype, grouping by field and byte position saved **37.62%**. [Weather and forest-cover experiments, controls and reproduction](research/lattice-prediction/ragged-rows.md)

The BWT on Wikipedia illustrates why we also measure context. Its byte histogram barely changed, but the next-byte entropy given the preceding byte fell from **3.881 to 2.801 bits**. That helped gzip and Zstandard. XZ compressed the original ordering better. [Paired entropy, stream lengths and sizes for all three compressors](research/large-scale/results/preprocessing.md)

## Standalone archive comparison

Each bar compares a verified experimental archive with XZ extreme on the same raw input. Positive values mean a smaller archive. The cellular orbit with Kronecker factors saved 82.2% on generated matrix products and used 28.2% more space on the real Silesia numerical stream.

![Archive size reductions versus XZ extreme. On archived and real data, whiteboard witness coding saved 59.6%, glyph coding saved 78.0%, lattice prediction saved 10.6%, and cellular Kronecker coding used 28.2% more space. On generated data, cellular Kronecker coding saved 82.2%, joint cellular rule learning saved 62.4%, and shared factor trees saved 1.6%.](research/large-scale/results/readme-summary.png)

[Exact sizes and timings for all benchmark results](research/large-scale/results/by-dataset.md)

## Project highlights

| Start with | What you can reproduce |
|---|---|
| [The original whiteboard census and witnesses](research/whiteboard-census/README.md) | Rebuild the 32 MiB cost table and use the recorded equations to compress a separate 22,630,320-byte witness file to 1,082,142 bytes. |
| [The whiteboard formula inside a factor tree](research/shared-factor-forest/README.md) | Divide, split a cofactor, encode one child as a quotient of repdigits, and share its recipe. |
| [Four-dimensional cellular automata and matrix factors](research/four-dimensional-factors/README.md) | Search backward, change the factor basis and store the exact XOR correction. |
| [Learn the cellular rule and its residual matrix together](research/learned-cellular-rules/README.md) | A 29,491,200-byte planted field drops from 25,054,265 to 11,051,733 bytes when the rule learns from correlations across error planes. |
| [Byte-valued cellular automata and Kronecker factors](research/modular-kronecker/README.md) | On 24 MiB of evolved, noisy matrix products, reversing the orbit and fitting two 4 × 4 factors reduced the archive from 24,560,134 to 4,471,016 bytes. |
| [Glyphs, baselines and exact residuals](research/glyph-residuals/README.md) | On 64 Valgrind manual pages, shared bitmaps and character positions use 394,104 bytes. Wide-strip lossless DjVu uses 828,622. |
| [Triangular distance matrices](research/distance-geometry/README.md) | Restore a 21,155,400-byte geographic distance table from four landmark columns and a residual in 3,850,014 bytes. |
| [Whole-file formulas and sparse arithmetic regions](research/carry-trees/README.md) | Compare multiplication before and after a split on the complete 96,994,187-byte cofactor Q. |
| [All implementations](research/README.md) · [Measurements by experiment](research/large-scale/results/by-experiment.md) | Browse runnable projects, exact sizes, conditional-reference charges and per-file timings. |
| [Historical reports](research/evidence/report-index.tsv) · [Protocol inventory](research/evidence/protocol-index.tsv) | Search 149 English report abstracts and the 583 original source/measurement directories. |

## Run from a clean checkout

The 16 compact diagnostic suites use Python 3.10 or newer, the standard library, the Zstd CLI and the included fixtures. Primary benchmark commands use at least 20 MiB per input. Set up the [large-file inputs and dependencies](research/large-scale/README.md#reproduce-a-result) for the projects you select. For the native projects, follow the [research build and replay instructions](research/README.md#build-and-reproduce).

```sh
python3 suite.py test
python3 suite.py benchmark --list
python3 lab.py 07 benchmark runs/recursive-gf2
python3 suite.py benchmark runs/all-experiments --group experiments
```

Each benchmark command creates a new output directory. The suite accepts an individual project, one group, or all projects by default. For the original small comparison tables, use `python3 suite.py diagnostics runs/diagnostics`. For individual encode/decode examples, profiles and results, open the experiment below. The [measurement protocol](PROTOCOL.md) explains metadata, decoder delivery and the difference between an update patch and a full archive.

## Experiment index

| ID | Experiment | Comparison |
|---|---|---|
| [01](experiments/01-repdigit-segmentation/README.md) | Repdigit ratios and adaptive segmentation | Fixed or adaptive boundaries × direct or extended recipe catalog |
| [02](experiments/02-near-factorization/README.md) | Near-factorization and digit concatenation | Exact or corrected products × indivisible or split factors |
| [03](experiments/03-generator-residuals/README.md) | Powers, generator sums and exact residuals | Generator family × additive or XOR correction under a search budget |
| [04](experiments/04-irrational-checkpoints/README.md) | Irrational sums, backtracking and checkpoints | Signed coefficients, number of terms and restart costs |
| [05](experiments/05-local-bases/README.md) | Local bases and exceptional digits | Global or per-block base × entropy or serialized-byte selection |
| [06](experiments/06-reversible-automata/README.md) | Reversible automata and step counts | Checkerboard or Margolus orbits with fixed, restricted or omitted step indices |
| [07](experiments/07-recursive-gf2/README.md) | Automata and recursive GF(2) factorization | Automaton placement × factorization depth |
| [08](experiments/08-equivalent-factors/README.md) | Equivalent matrix factors and error masks | Original or transformed factor bases at fixed rank and error mask |
| [09](experiments/09-walsh-bitplanes/README.md) | Walsh–Hadamard prediction and bit planes | Plane splitting × spectral prediction with exact XOR correction |
| [10](experiments/10-affine-chains/README.md) | Affine instruction chains | Three parameter encodings and two reconstruction algorithms |
| [11](experiments/11-shared-subexpressions/README.md) | Grammars and shared subexpressions | Flat instructions, sequence grammar or expression DAG |
| [12](experiments/12-relative-patches/README.md) | Relative compression | Fixed-offset XOR, variable-offset copies or local alignment |
| [13](experiments/13-bwt-prediction/README.md) | Burrows–Wheeler transform and prediction | Byte reordering × prediction with a common residual coder |
| [14](experiments/14-sparse-residuals/README.md) | Sparse residual coding | Enumerative ranks, Rice gaps, bit contexts or per-block selection |
| [15](experiments/15-binary-regions/README.md) | Regenerating binary regions | ELF header generation × local formula scanning |
| [16](experiments/16-joint-selection/README.md) | Joint selection of compression methods | Single method, fixed-block switching or variable intervals |

## Joint studies

- [Formula leaves, factors and grammar references](studies/formula-factor-grammar/README.md) combines experiments 01, 02 and 11.
- [Automata, factors and residual coding](studies/automaton-factor-residual/README.md) combines experiments 06, 07, 08 and 14.
- [Reference copies, local formulas and interval selection](studies/reference-formula-intervals/README.md) combines experiments 12, 15 and 16.
