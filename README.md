# Lossless Compression Lab

Sixteen experiments ask the same question. How much space do two methods save together once the archive pays for everything the decoder needs?

Start with [repdigit ratios and adaptive segmentation](experiments/01-repdigit-segmentation/README.md). It includes the codec, tests, benchmark driver and a measured run. Each subsequent experiment will use the [experiment template](templates/experiment/README.md).

## Experiment index

| ID | Experiment | Comparison |
|---|---|---|
| [01](experiments/01-repdigit-segmentation/README.md) | Repdigit ratios and adaptive segmentation | Fixed or adaptive boundaries × direct or extended recipe catalog |
| 02 | Near-factorization and digit concatenation | Exact or corrected products × indivisible or split factors |
| 03 | Powers, generator sums and exact residuals | Generator family × additive or XOR correction under a search budget |
| 04 | Irrational sums, backtracking and checkpoints | Signed coefficients, number of terms and restart costs |
| 05 | Local bases and exceptional digits | Global or per-block base × entropy or serialized-byte selection |
| 06 | Reversible automata and step counts | Checkerboard or Margolus orbits with fixed, restricted or omitted step indices |
| 07 | Automata and recursive GF(2) factorization | Automaton placement × factorization depth |
| 08 | Equivalent matrix factors and error masks | Original or transformed factor bases at fixed rank and error mask |
| 09 | Walsh–Hadamard prediction and bit planes | Plane splitting × spectral prediction with exact XOR correction |
| 10 | Affine instruction chains | Three parameter encodings and two reconstruction algorithms |
| 11 | Grammars and shared subexpressions | Flat instructions, sequence grammar or expression DAG |
| 12 | Relative compression | Fixed-offset XOR, variable-offset copies or local alignment |
| 13 | Burrows–Wheeler transform and prediction | Byte reordering × prediction with a common residual coder |
| 14 | Sparse residual coding | Enumerative ranks, Rice gaps, bit contexts or per-block selection |
| 15 | Regenerating binary regions | ELF header generation × local formula scanning |
| 16 | Joint selection of compression methods | Single method, fixed-block switching or variable intervals |

The source also proposes three joint studies. Experiments 01, 02 and 11 exchange formula trees to measure the cost of sharing factors. Experiments 06, 07, 08 and 14 exchange matrices and error masks to isolate predictor and residual costs. Experiments 12, 15 and 16 compare copies and locally generated regions with and without a shared reference.
