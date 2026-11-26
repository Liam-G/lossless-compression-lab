# Lossless Compression Lab

This repository contains the original compression engines and a set of 16 smaller experiments that isolate their component ideas. The [research index](research/README.md) links nine project folders, benchmark commands, archive formats and measurements. The [field notes](research/evidence/README.md) connect them to 149 original reports.

Three experiments illustrate the range. A [raster shape coder](research/shape-context/README.md) compresses the 513,216-byte Canterbury fax to 28,037 bytes. A [whiteboard quotient tree](research/whiteboard-trees/README.md) reconstructs a 1.5 MiB planted file from two formulas and one split. A [3D cellular automaton with binary matrix factors](research/tensor-orbits/README.md) shows a large joint gain on a planted volume and a 47-byte gain over matrix coding alone on a real MR slice. The [mixed-arity factor-tree replay](research/factor-trees/README.md) and [adaptive formula scanner](research/repdigit-intervals/README.md) run on the full 96,994,187-byte cofactor Q.

The [experiment template](templates/experiment/README.md) defines the common questions about source, archive cost, reconstruction and controls. For a compact first example, see [repdigit ratios and adaptive segmentation](experiments/01-repdigit-segmentation/README.md).

## Run from a clean checkout

The 16 compact experiments use Python 3.10 or newer, the standard library, the Zstd CLI and the included inputs. For the native projects, follow the [research build and replay instructions](research/README.md#build-and-reproduce).

```sh
python3 suite.py test
python3 lab.py 07 benchmark runs/recursive-gf2
python3 suite.py benchmark runs/all-experiments
```

Each benchmark command creates a new output directory. For individual encode/decode examples, profiles and results, open the experiment below. The [measurement protocol](PROTOCOL.md) explains metadata, decoder delivery and the difference between an update patch and a full archive.

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
