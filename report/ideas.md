# Every idea we tried

One line per idea, grouped by chapter. **Verdict** compares with the best standard tool on the same bytes
(see [methods](methods.md)). **Where**: a folder in this repository (runnable) or "notes only" (the original
notebook and its abstract are in the [report register](../research/evidence/report-index.tsv); the code
depended on third-party archives or GPL sources that are not redistributed).

Symbols: ✅ beats the best standard tool on real data · ➖ ties or wins only on its own planted data ·
❌ loses on real data · 🔬 detector or measurement tool, not a compressor.

## 1 · Formulas, numbers and coincidences

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Whiteboard: *d* = repdigit / repdigit | [whiteboard-census](../research/whiteboard-census/README.md) | every *d* < 2²⁸ | 974 of 268 million numbers get shorter, none by 16 bits | ❌ |
| Census tables and witnesses rebuilt from the enumerator | [whiteboard-census](../research/whiteboard-census/README.md) | our own enumerator output | 15–48 B + program; shuffled records lose the gain | ➖ self-generated |
| Whiteboard formula as a leaf of a factor tree, shared recipes | [shared-factor-forest](../research/shared-factor-forest/README.md), [whiteboard-trees](../research/whiteboard-trees/README.md) | planted products; Q; numerical | planted −1.6% vs xz; no gain on real data | ➖ |
| Repdigit ratios with adaptive segments (exp. 01) | [experiments/01](../experiments/01-repdigit-segmentation/README.md) | plants; Wikipedia | 3.8× xz on Wikipedia | ❌ |
| Repdigit intervals with movable boundaries | [repdigit-intervals](../research/repdigit-intervals/README.md) | Q | −86 B of 97 MB | ❌ |
| Near-factorization and digit concatenation (exp. 02) | [experiments/02](../experiments/02-near-factorization/README.md) | plants; Wikipedia | loses to zstd even on its plant | ❌ |
| Powers and generator sums with residuals (exp. 03), three-generator sums | [experiments/03](../experiments/03-generator-residuals/README.md), [generator-sums](../research/generator-sums/README.md) | plants; Q; Wikipedia | planted 25 MB → 37 kB; Q +18 B | ➖ |
| Sums of irrational numbers with checkpoints (exp. 04) | [experiments/04](../experiments/04-irrational-checkpoints/README.md) | plants; Wikipedia | 4.1× xz on Wikipedia | ❌ |
| Local number bases (exp. 05); Q in all bases 2–257 | [experiments/05](../experiments/05-local-bases/README.md); notes only (report 080) | plants; Q | best base still larger than Q | ❌ |
| Exact formula for enwik7 / enwik9 as one integer | notes only (reports 002–003) | enwik7, enwik9 | correction is 79,999,935 of 80,000,000 bits | ❌ |
| Whole-integer formulas (squares, products, modular squares) | [integer-formulas](../research/integer-formulas/README.md) | Q | −136 B | ❌ |
| Factor trees: split cofactors, recurse | [factor-trees](../research/factor-trees/README.md), [carry-trees](../research/carry-trees/README.md) | Q | +27 to +31 B; with factor 12: −3,772 B | ❌ |
| Prime-index trees | [prime-index-trees](../research/prime-index-trees/README.md) | Q | literal root wins | ❌ |
| Recursive fourth-power quotients | [quartic-trees](../research/quartic-trees/README.md) | Q | 2.6× larger | ❌ |
| Division chains (219 million divisions) and their patterns | notes only (reports 023–026) | Neif | inversion exact; no pattern pays | ❌ |
| Learned finite-field recurrences, modular differences, periodic edits | notes only (reports 133, 135, 136) | Q windows | no fit; planted rules found | ❌ |
| Affine instruction chains (exp. 10) | [experiments/10](../experiments/10-affine-chains/README.md) | our archived instruction stream | 0.6% larger than bzip2 -9 | ➖ |
| Shared subexpressions, expression DAG (exp. 11) | [experiments/11](../experiments/11-shared-subexpressions/README.md) | our formula listing | 5.3× xz | ❌ |
| Coincidence hunt: any rule matching 300 characters | [coincidence-hunt](../research/coincidence-hunt/README.md) | enwik8 Anarchism article | best "win" is ASCII layout, worse than letter statistics | ❌ |
| Rules recreating noise (automata, XOR pairs, LFSRs) | [rules-vs-noise](../research/rules-vs-noise/README.md) | xz/PPMd output, random | bits found = bits to name the rule | 🔬 counting argument |
| Digits of √2, √3, √5, e, π and their sums | [rules-vs-noise](../research/rules-vs-noise/README.md) | text, xz output, random | 26 bits found vs 26 bits to name the position | 🔬 counting argument |
| Block-by-block generator programs | [block-programs](../research/block-programs/README.md) | first 1 KB of enwik8 | 946 B (math only), 526 B (with copies) vs brotli 300 B | ❌ |
| Transform search on random and already-compressed data | [transform-controls](../research/transform-controls/README.md) | 8 MiB random; xz output of dickens | nothing helps | 🔬 control |
| Price of a permutation (sorted bytes + the permutation) | [transform-controls](../research/transform-controls/README.md) | dickens | the permutation costs more than sorting saves | 🔬 control |
| Re-reading bits as k-bit symbols, hidden alphabets, base change | [transform-controls/alphabet](../research/transform-controls/alphabet) | Silesia, Canterbury | no gain beyond noise | ❌ |

## 2 · Automata and matrix factors

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Reversible automata with stored step counts (exp. 06) | [experiments/06](../experiments/06-reversible-automata/README.md) | plants | finds planted steps | ➖ |
| Automaton + recursive GF(2) factorization (exp. 07) | [hierarchical-gf2](../research/hierarchical-gf2/README.md) | plants; scanned manual | 16× DjVu on the manual | ❌ |
| Equivalent factor bases (exp. 08) | [experiments/08](../experiments/08-equivalent-factors/README.md) | plants; numerical | 2.1× xz | ❌ |
| Walsh–Hadamard bit planes (exp. 09) | [experiments/09](../experiments/09-walsh-bitplanes/README.md) | plants; manuals | 65× DjVu | ❌ |
| 3-D automata + matrix panels | [tensor-orbits](../research/tensor-orbits/README.md) | planted volume; numerical, samba, MR | planted −61%; real +24% to +83% | ➖ |
| 4-D automata + bit factors | [four-dimensional-factors](../research/four-dimensional-factors/README.md) | planted field; numerical, samba | real +37% to +56% | ➖ |
| Byte-valued orbits + Kronecker factors | [modular-kronecker](../research/modular-kronecker/README.md) | planted panels; numerical | planted −82%; real +28% | ➖ |
| Learning the cellular rule and residual basis jointly | [learned-cellular-rules](../research/learned-cellular-rules/README.md) | planted field; 3 video clips | planted −62%; video +55% to 2.1× H.264 | ➖ |
| One shared automaton clock per page | [checkerboard-orbits](../research/checkerboard-orbits/README.md) | planted; numerical | real +31% | ➖ |
| Checkerboard automaton on 11 million 8-byte matrices of Neif | notes only (reports 004–005) | Neif | lower bit entropy, archive 4% larger | ❌ |
| GF(2) grids, cellular automata with XOR corrections on Neif | notes only (reports 028–031) | Neif | no gain | ❌ |

## 3 · Reshaping data for a standard compressor

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Route each field of a record to its own stream | [lattice-prediction](../research/lattice-prediction/ragged-rows.md) | NOAA weather, Covertype | forest cover −30% vs the best standard tool; NOAA weather −42% to −47% vs xz | ✅ |
| Integer lattice prediction, separated bit planes | [lattice-prediction](../research/lattice-prediction/README.md) | Silesia numerical | −10.6% vs xz -9e | ✅ |
| Scanline XOR + quadtree of empty regions | [checkerboard-orbits/bitmap-trees](../research/checkerboard-orbits/bitmap-trees.md) | 4 scanned manuals | −33% to −39% for zstd, but 4–6× DjVu | ❌ |
| Stride scan: find the row width of a file | [stride-scan](../research/stride-scan/README.md) | Silesia, Canterbury | finds widths in images and tables | 🔬 |
| Shape search: fold into shapes, walk in formula orders | [stride-scan](../research/stride-scan/README.md) | first MiB of 12 files | only raster and column-major orders win (fax, spreadsheet) | ➖ |
| Reversible text views: BWT, MTF, spelling, field normalisation | [text-views](../research/text-views/README.md) | Wikipedia | helps gzip and zstd, hurts xz | ❌ |
| Tournament: 381 reversible reshape chains × 3 compressors | [reshape-tournament](../research/reshape-tournament/README.md) | 10 MB of enwik8 | best: words + BWT, xz −5.7% | ➖ |
| Capital-letter flags, word codes, header columns | [text-views](../research/text-views/README.md) (textfront) | enwik8 | xz −5.9%, bzip2 −8.6%, CM none | ➖ helps weak back ends |
| Article reordering | [article-order](../research/article-order/README.md) | enwik8 | category order −0.25% to −0.67% | ➖ |
| xz option search (lc/lp/pb, x86 filter) | notes only | Silesia | small per-file gains | ➖ |
| Grammar from arithmetic (split, multiply, remainder, references) | notes only (report 119) | random, xz output, planted products | random +15 B; planted −58% | ➖ |
| Line grammar with backward references and edits | notes only (report 126) | FX2 text tape | — | ❌ |
| Byte-pair tokens ranked by frequency | notes only (report 144) | enwik9 | — | ❌ |

## 4 · Specialised models

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Glyph dictionary + exact page residual | [glyph-residuals](../research/glyph-residuals/README.md) | 4 scanned manuals | beats DjVu on 3 of 4 | ✅ |
| Raster shape context (fax) | [shape-context](../research/shape-context/README.md) | Canterbury ptt5 | 28,037 B: beats Group 4 (32,344) and xz, loses to JBIG (25,917) and DjVu (22,490) | ❌ vs the right tool |
| Distances from landmark columns | [distance-geometry](../research/distance-geometry/README.md) | distances between 4,600 real places | −77% vs xz | ✅ derived data |
| Reversible colour transform + wavelets | [reversible-wavelets](../research/reversible-wavelets/README.md) | 3 photos | +53% to +62% vs JPEG XL | ❌ |
| Motion vectors + spatial prediction | [motion-residuals](../research/motion-residuals/README.md) | 3 video clips | +46% to 2.1× H.264 lossless | ❌ |
| Patches against the previous software release | [arithmetic-references](../research/arithmetic-references/README.md) | NumPy, Mesa updates | +16% to +23% vs xz | ❌ |
| Regenerate ELF headers, local formulas (exp. 15) | [experiments/15](../experiments/15-binary-regions/README.md) | Firefox binaries | 2.6× xz | ❌ |
| Per-interval method selection (exp. 16) | [experiments/16](../experiments/16-joint-selection/README.md) | scanned manual | 1.7× xz | ❌ |
| Relative patches (exp. 12) | [experiments/12](../experiments/12-relative-patches/README.md) | Wikipedia vs Wikipedia | 2.3× xz | ❌ |
| BWT + prediction (exp. 13), sparse residual coding (exp. 14) | [experiments/13](../experiments/13-bwt-prediction/README.md), [14](../experiments/14-sparse-residuals/README.md) | Wikipedia; numerical | 4× and 1.8× xz | ❌ |

## 5 · Text compressors on enwik8

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Statico M1 grammar | [statico](../research/statico/README.md) | enwik8, Silesia | 26.35 MB vs xz 24.70 | ❌ |
| GLZA-style rule scoring | [grammar-probes](../research/grammar-probes/README.md) | enwik8 | 23.77 MB | ✅ vs xz, ❌ vs PPMd |
| Better symbol coding for the grammar | [grammar-probes](../research/grammar-probes/README.md) | enwik8 | about −8% | ➖ |
| BWT + context mixing | [bwt-lab](../research/bwt-lab/README.md) | 10 MB of enwik8 | 2.39 MB vs ~2.0 MB for raw-text CM | ❌ |
| Context mixing CM → CM2 → CM3 | [context-mixer](../research/context-mixer/README.md) | enwik8 | **17,811,463 B** | ✅ beats paq8l, PPMd, xz |
| LSTM as an extra predictor (with learning-rate decay) | [context-mixer](../research/context-mixer/README.md) | enwik8 | −1.3% at 100 MB | ✅ |
| Best of 32 earlier matches ("longest block") | [context-mixer](../research/context-mixer/README.md) | enwik8 | −0.91% | ✅ |
| Learned second mixing layer, second match model, word stems | [context-mixer](../research/context-mixer/README.md) | enwik8 | −0.57% | ✅ |
| Generators (π digits, patterns) as mixer inputs | notes only | 3 MB of enwik8 | +150 B and +15 B (worse) | ❌ |
| Wikipedia structure: page order, templates, primed CM3 members | [wiki-structures](../research/wiki-structures/README.md) | 2 × 24 MiB of Wikipedia | 5.31 MB vs xz 6.64 | ✅ vs xz |

## 6 · The record archive

| Idea | Where | Tested on | Result | Verdict |
|---|---|---|---|---|
| Portable Q packages V8 → V15 (ELF, weights rebuilt inside 12Q) | [portable-arithmetic](../research/portable-arithmetic/README.md) | Q | −73,220 B (0.075%) incl. decoder | ✅ tiny |
| Conditional coding against the exact record archive | [arithmetic-references](../research/arithmetic-references/README.md) | Q | 46 B + the 97 MB reference | ➖ |
| Article-order descriptors (AOR4–7, AOG1, AOH1) | notes only (reports 040–047) | FX2 page order | order in 39 kB | ➖ |
| Dictionary reconstruction (DCR3–7) | notes only (reports 048–052) | FX2 lexicon | 19,353 B given the Neif dictionary | ➖ |
| Executable prefix models (PNR4–7, ELF, libm) | notes only (reports 053–056, 060, 064) | FX2 prefix, math library | a few kB | ➖ |
| Re-encoding model weights (INT4 tensors, QWX7/8) | notes only (reports 015–020, 101) | FX2/Neif weights | Q: part of −73 kB; Neif: all larger | ➖ |
| Reproduce Q by re-running FX2 on enwik9 | notes only (report 058) | enwik9 | 92.78 MB package, full run unverified | 🔬 |
| Rank, URL, link-target and title predictors in Neif | notes only (reports 091–118) | Neif windows | 150–560 B per experiment | ➖ |
| Link titles from decoded page-title affixes | notes only (report 131) | FX2 link tail | −111,826 B of 2.47 MB (PPMd archive) | ✅ component |
| Articles reordered by topic | notes only (report 105) | Neif text band | +525,442 B | ❌ |
| Engineering the FX2 transformer (memory, parallel rows, determinism) | notes only (reports 059–079) | FX2 | runtime studies, no size change | 🔬 |
