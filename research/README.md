# Research projects

Every method in this repository, grouped by the [report](../report/README.md) chapter that discusses it. Each folder holds the code, a one-page description (verdict, question, method, results, how to run) and its measurements. Numbered experiments live in [`experiments/`](../experiments) and combined studies in [`studies/`](../studies).

## 1 · Formulas, numbers and coincidences

| Project | Verdict | Evidence |
|---|---|---|
| [Adaptive repdigit intervals](repdigit-intervals/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0006% vs zstd -19. |
| [Block programs: describe each block with the cheapest generator](block-programs/README.md) | loses to every ordinary compressor | The first kilobyte of enwik8 costs 946 bytes with mathematical generators only and 526 bytes once "copy earlier data" and "predict from context" generators are allowed, against 300 bytes for brotli, 350 for gzip and 420 for xz. On 10 MB, no real block was described better by any generator than by its own letter counts (0 of 7); 4 of 5 planted blocks were found. |
| [Coincidence hunt](coincidence-hunt/README.md) | no coincidence exists to be found | About ten billion candidate rules were tried on 300 characters of Wikipedia. The best (2,134 bits) needs 21% more bits than gzip and 54% more than brotli; in every family the longest exact match is no longer than the bits needed to name the rule. All four planted controls are found exactly. |
| [Experiment 01 · Repdigit ratios and adaptive segmentation](../experiments/01-repdigit-segmentation/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 3.8× larger vs xz -9e. |
| [Experiment 02 · Near-factorization and digit concatenation](../experiments/02-near-factorization/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 4.0× larger vs xz -9e. |
| [Experiment 03 · Powers, generator sums and exact residuals](../experiments/03-generator-residuals/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 4.0× larger vs xz -9e. |
| [Experiment 04 · Irrational sums, backtracking and checkpoints](../experiments/04-irrational-checkpoints/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 4.1× larger vs xz -9e. |
| [Experiment 05 · Local bases and exceptional digits](../experiments/05-local-bases/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 4.0× larger vs xz -9e. |
| [Experiment 10 · Affine instruction chains](../experiments/10-affine-chains/README.md) | no meaningful gain on real data | Best real input: Our archived formula instructions, −0.4% vs bzip2 -9. |
| [Experiment 11 · Grammars and shared subexpressions](../experiments/11-shared-subexpressions/README.md) | loses on real data | Best real input: Our formula listing as text, +15.3% vs PPMd. |
| [Formula leaves, factors and grammar references](../studies/formula-factor-grammar/README.md) | planted data only | Planted control: Products hiding a repdigit factor, +53.5% vs brotli -11. |
| [Integer carries across tree boundaries](carry-trees/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0044% vs zstd -19. |
| [Mixed-arity factor trees](factor-trees/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0004% vs zstd -19. |
| [Prime ordinal and product coding](prime-index-trees/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, +0.0110% vs zstd -19. |
| [Recursive fourth-power quotients](quartic-trees/README.md) | loses on real data | Best real input: Q: the record archive as an integer, 2.6× larger vs zstd -19. |
| [Rules against noise, and digits of irrational numbers](rules-vs-noise/README.md) | the counting argument, measured | No family of rules reproduces compressed data, random bytes or text for longer than it costs to name the rule. Planted rule outputs are found completely. |
| [Shared formulas inside a factor tree](shared-factor-forest/README.md) | detector only | Best real input: Silesia numerical files (mr + x-ray + sao), +30.9% vs xz -9e. Planted control: Products hiding a repdigit factor, −1.6% vs brotli -11. |
| [The whiteboard census and its formula witnesses](whiteboard-census/README.md) | self-generated data only | The input is the output of our own program. |
| [Three seeded generators plus a signed residual](generator-sums/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0005% vs zstd -19. Planted control: Sums of three generators, 683× smaller vs zstd -19. |
| [Whiteboard quotients inside factor trees](whiteboard-trees/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0005% vs zstd -19. Planted control: Products hiding a repdigit factor, +25.3% vs brotli -11. |
| [Whole-file square, product and modular-square formulas](integer-formulas/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0006% vs zstd -19. |

## 2 · Automata and matrix factors

| Project | Verdict | Evidence |
|---|---|---|
| [A shared clock for 8 × 8 checkerboard automata](checkerboard-orbits/README.md) | detector only | Best real input: Scanned manual: Valgrind, +23.8% vs DjVu. Planted control: Stamps evolved by an automaton, −92.2% vs PPMd. |
| [Automata, factors and residual coding](../studies/automaton-factor-residual/README.md) | loses on real data | Best real input: Scanned manual: Graphviz guides, 76.7× larger vs DjVu. |
| [Byte-valued cellular automata and Kronecker factors](modular-kronecker/README.md) | detector only | Best real input: Silesia numerical files (mr + x-ray + sao), +28.2% vs xz -9e. Planted control: Byte orbit hiding a Kronecker product, −82.8% vs brotli -11. |
| [Experiment 06 · Reversible automata and step counts](../experiments/06-reversible-automata/README.md) | planted data only |  |
| [Experiment 07 · Automata and recursive GF(2) factorization](../experiments/07-recursive-gf2/README.md) | loses on real data | Best real input: Scanned manual: Graphviz guides, 16.3× larger vs DjVu. |
| [Experiment 08 · Equivalent matrix factors and error masks](../experiments/08-equivalent-factors/README.md) | loses on real data | Best real input: Silesia numerical files (mr + x-ray + sao), 2.1× larger vs xz -9e. |
| [Experiment 09 · Walsh–Hadamard prediction and bit planes](../experiments/09-walsh-bitplanes/README.md) | loses on real data | Best real input: Scanned manual: Graphviz guides, 65.1× larger vs DjVu. |
| [Four-dimensional automata with noisy binary matrix factors](four-dimensional-factors/README.md) | loses on real data | Best real input: Silesia numerical files (mr + x-ray + sao), +37.3% vs xz -9e. |
| [Hierarchical GF(2) with checkerboard evolution](hierarchical-gf2/README.md) | loses on real data | Best real input: Scanned manual: Graphviz guides, 16.2× larger vs DjVu. |
| [Jointly learning a cellular rule and the matrix of its prediction errors](learned-cellular-rules/README.md) | detector only | Best real input: Video clip 3 (grayscale frames), +55.2% vs H.264 lossless. Planted control: Field from a hidden cellular rule, −64.2% vs gzip -9. |
| [Reversible 3D automata before GF(2) panel coding](tensor-orbits/README.md) | detector only | Best real input: Silesia numerical files (mr + x-ray + sao), +24.5% vs xz -9e. Planted control: 3-D field from a hidden automaton + low rank, −60.9% vs brotli -11. |

## 3 · Reshaping data for a standard compressor

| Project | Verdict | Evidence |
|---|---|---|
| [Article order: does sorting Wikipedia pages help?](article-order/README.md) | under 1% | Grouping the enwik8 pages by their first category makes xz 0.65% and PPMd 0.25% smaller; sorting by title helps even less; a random order makes everything 0.4–0.5% larger. The decoder can undo the order for free (it sorts pages back by their ID). |
| [Experiment 13 · Burrows–Wheeler transform and prediction](../experiments/13-bwt-prediction/README.md) | loses on real data | Best real input: Wikipedia text, 24 MiB, 4.0× larger vs xz -9e. |
| [Local integer grids and bit-plane residuals](lattice-prediction/README.md) | wins on real data | Best: NOAA weather records 1990, −73.0% vs zstd -3. Planted control: Distances along a random planar walk, −51.1% vs xz -9e. |
| [Reshape tournament: 381 reversible chains × 3 compressors](reshape-tournament/README.md) | small gains for weak compressors only | On the first 10 MB of enwik8 the best chain (word codes, then BWT) makes xz 5.7% and zstd 2.9% smaller. Nothing comes close to a strong model: plain PPMd is 15% smaller than the best xz chain. Expanding the data (base 2, 3, 4) or compressing twice never helps. |
| [Shape search: fold the bytes into a shape and look for a local rule](stride-scan/README.md) | finds every planted program; on real files only plain grids help | Planted programs (an LFSR, rule 30, rule 110, an x XOR y image) are found and described in 24–287 bytes. On real files the only shapes that win are ordinary rasters and columns: the fax page (−25% vs xz, estimate) and a spreadsheet (−23%). Triangles, spirals, Hilbert and Morton orders and formula-defined walks never win. Text has no shape (+17% to +35% vs xz). |
| [Text fields, BWT and move-to-front](text-views/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, +24.0% vs xz -9e. |
| [Transform controls: what reshaping can and cannot do](transform-controls/README.md) | controls | On random bytes and on already-compressed data no reshape helps; the price of a permutation always eats what sorting saves; re-reading bits in a different symbol size makes normal files larger. When data really is hidden inside a bigger alphabet (hex, base64, UTF-16), undoing it is found and saves 1–31%. |

## 4 · Specialised models

| Project | Verdict | Evidence |
|---|---|---|
| [Distance matrices reconstructed from landmarks](distance-geometry/README.md) | wins on data derived from real data | Best: Distances between 4,600 real places, −77.0% vs xz -9e. Planted control: Distances along a random planar walk, −84.1% vs xz -9e. |
| [Experiment 12 · Relative compression](../experiments/12-relative-patches/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 6.1× larger vs xz -9e. |
| [Experiment 14 · Sparse residual coding](../experiments/14-sparse-residuals/README.md) | loses on real data | Best real input: Silesia numerical files (mr + x-ray + sao), +75.8% vs xz -9e. |
| [Experiment 15 · Regenerating binary regions](../experiments/15-binary-regions/README.md) | loses on real data | Best real input: Silesia mozilla (Firefox binaries), 2.6× larger vs xz -9e. |
| [Experiment 16 · Joint selection of compression methods](../experiments/16-joint-selection/README.md) | loses on real data | Best real input: Wikipedia text, another 24 MiB, 5.0× larger vs xz -9e. |
| [Integer lifting and color differences](reversible-wavelets/README.md) | loses on real data | Best real input: Photo 3 (RGB), +53.2% vs JPEG XL. |
| [Motion and spatial residuals on grayscale frame sequences](motion-residuals/README.md) | loses on real data | Best real input: Video clip 3 (grayscale frames), +45.6% vs H.264 lossless. |
| [Raster shape search with an actual range-coded archive](shape-context/README.md) | loses on real data | Best real input: Silesia numerical files (mr + x-ray + sao), +38.6% vs xz -9e. |
| [Reference copies, local formulas and interval selection](../studies/reference-formula-intervals/README.md) | loses on real data | Best real input: NumPy release given the previous one, 8.7× larger vs xz -9e. |
| [Repeated glyphs and an exact bitmap residual](glyph-residuals/README.md) | wins on real data | Best: Scanned manual: Valgrind, −52.4% vs DjVu. |

## 5 · Text compressors

| Project | Verdict | Evidence |
|---|---|---|
| [BWT lab: sort first, then model](bwt-lab/README.md) | helps weak models, loses to context mixing | On the first 10 MB of enwik8 the best BWT pipeline costs 2,390,774 bytes, against 2,222,042 for our first context mixer on the raw text and about 2.0 MB for CM3. Telling the decoder which letters follow (via count headers) never pays. |
| [CM3 context mixing](context-mixer/README.md) | wins on real data | Best: Wikipedia text, 24 MiB, −24.3% vs xz -9e. |
| [Grammar probes: where does Statico lose to GLZA?](grammar-probes/README.md) | better rule choice helps; better symbol coding helps less than hoped | Choosing grammar rules the way GLZA does takes Statico on enwik8 from 26,346,968 to 23,774,125 bytes (−9.8%, now better than xz). Better coding of the rule numbers alone would give about −8% (24.3 MB); both together about 22.05 MB (estimate). GLZA itself reaches 20.07 MB, and our context mixer 17.81 MB. |
| [Statico M1 grammar compressor](statico/README.md) | loses on real data | Best real input: Wikipedia text, enwik8 (100 MB), +6.1% vs xz -9e. |
| [Wikipedia page order, algebraic templates and primed context mixing](wiki-structures/README.md) | wins on real data | Best: Wikipedia text, another 24 MiB, −20.0% vs xz -9e. |

## 6 · The record archive

| Project | Verdict | Evidence |
|---|---|---|
| [Arithmetic packages that include their decoder](portable-arithmetic/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0022% vs zstd -19. |
| [Conditional patches after arithmetic alignment](arithmetic-references/README.md) | no meaningful gain on real data | Best real input: Q: the record archive as an integer, −0.0004% vs zstd -19. |

## Build

```sh
make -C research -j4        # native code used by the benchmark
make -C research lab         # tools of the recovered lab experiments
python3 research/test.py     # tests
```

Measurements and how to repeat them: [benchmark runner](large-scale/README.md) · [methods](../report/methods.md).
