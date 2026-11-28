# Original compression experiments

[Research findings, controlled comparisons and entropy plots](large-scale/findings.md)

The original lab explored arithmetic descriptions of large integers, reversible matrix dynamics, file-specific context models, and the cost of delivering the decoder. The projects below restore those implementations and test new combinations on real files and controlled inputs. The [idea atlas](evidence/idea-atlas.md) links the original formulas and project conversations to the implementations and open proposals. The [report index](evidence/report-index.tsv) identifies each retained historical measurement by source and digest.

## Large-file research

The [large benchmark](large-scale/README.md) covers real text, numerical samples, software revisions, documents, images, video, archived formula instructions, full executables, and generated controls. Each result row has at least 20 MiB of verified raw bytes. The [complete trial table](large-scale/results/by-dataset.md) includes losses and literal fallbacks.

| Project | Question |
|---|---|
| [Whiteboard census and witnesses](whiteboard-census/README.md) | Are the original formula records predictable from their six arithmetic parameters? |
| [Python-isolated arithmetic packages](portable-arithmetic/README.md) | Can a complete package with its decoder beat canonical Q? |
| [Jointly learned cellular rules](learned-cellular-rules/README.md) | Can correlated binary innovations identify an otherwise hidden transition table? |
| [Wikipedia structures](wiki-structures/README.md) | How do page ordering, arithmetic templates and primed CM3 members interact? |
| [Shared factor forest](shared-factor-forest/README.md) | Can repdigit formulas become profitable below a factor and be shared between leaves? |
| [Carry trees and sparse scaling](carry-trees/README.md) | Should a reversible multiply or divide come before or after a split? |
| [Prime index trees](prime-index-trees/README.md) | Do locally profitable prime ordinals improve the whole archive? |
| [Whole-integer formulas](integer-formulas/README.md) | How much must the receiver know to evaluate a square, consecutive product or modular-square formula? |
| [Generator sums](generator-sums/README.md) | What survives the cost of a three-seed search and its signed residual? |
| [Shared checkerboard clocks](checkerboard-orbits/README.md) | Can sharing the time reduce the cost of choosing among 1,001 predecessors? |
| [Byte-valued Kronecker factors](modular-kronecker/README.md) | Does a reversible orbit hide the product of two small matrices modulo 256? |
| [Four-dimensional factors](four-dimensional-factors/README.md) | Can an inverse cellular rule expose noisy low rank and equivalent bases? |
| [Integer lattice prediction](lattice-prediction/README.md) | Can inferred widths and strides make separated bit planes cheaper? |
| [Distance geometry](distance-geometry/README.md) | Can distances to a few landmarks predict an entire triangular matrix? |
| [Reversible image wavelets](reversible-wavelets/README.md) | How do color decorrelation and multi-scale prediction interact? |
| [Motion residuals](motion-residuals/README.md) | Do temporal changes, motion vectors or spatial predictors explain real grayscale frames? |
| [Bitmap glyph residuals](glyph-residuals/README.md) | Can a dictionary of connected components and an exact page correction beat an ordinary bitmap coder? |
| [Text fields and BWT](text-views/README.md) | Does spelling and field normalization before sorting transfer to a separate text window? |
| [Arithmetic reference patches](arithmetic-references/README.md) | What changes when the reference comes from the same release, another release, or must be delivered? |

## Where to start

| Project | What the implementation lets you test | Measured result |
|---|---|---|
| [Raster shape contexts](shape-context/README.md) | Recover a row width and range-code bits from their neighbors | Full Canterbury fax, 28,037 bytes vs 32,344 with Group 4 TIFF and 39,860 with XZ extreme. The spatial model lost to XZ on all 134 separate console fonts. |
| [Factor splitting](factor-trees/README.md) | Extract small primes, split the remaining bits into up to 128 children and reconstruct the parent | On 96,994,187 bytes of Q, binary splits cost 31 extra bytes and seeded splits cost 27. |
| [Whiteboard quotient trees](whiteboard-trees/README.md) | Find a scaled ratio of two repdigits at a tree node, or split the cofactor again | The original codec rebuilds a 1.5 MiB planted file from 33 bytes. A new hybrid finds 507 hidden quotient leaves on a different control. |
| [Adaptive repdigit intervals](repdigit-intervals/README.md) | Move the boundaries and charge for each position, width and formula | Q contains a few profitable literal-to-formula replacements. The 255-byte search saves 86 bytes overall. |
| [Recursive quartic trees](quartic-trees/README.md) | Calculate both operands of each fourth-power quotient and recurse into them | A real 1 MiB Q prefix expands to 2,483,741 bytes with its width-preserving wrapper. |
| [Hierarchical GF(2)](hierarchical-gf2/README.md) | Place an automaton before or after a recursive binary matrix factorization | An evolved rank-four fixture falls from 8,205 to 4,492 bytes only when the full model can reverse evolution before factoring. |
| [3D automata and matrix panels](tensor-orbits/README.md) | Step backward through a volume and encode the resulting low-rank panels | Combined archive saves 116,311 bytes over the better single method on the planted volume and 47 bytes on the real MR prefix. |
| [Statico M1](statico/README.md) | Build a grammar, transmit reusable productions and range-code the symbols | Fresh full-file archives of 2,723,344 bytes on Silesia osdb and 2,780,136 on dickens. |
| [CM3 context mixing](context-mixer/README.md) | Mix byte, word, match and recurrent predictions in the arithmetic coder | Local full-enwik8 record of 17,811,463 bytes. The repository also measures three configurations on a 128 KiB prefix. |

The [field notes](evidence/README.md) trace adjacent work on prime-index trees, whole-file matrices, residuals, grammar, reference archives and text prediction. The [source register](evidence/report-index.tsv) identifies 149 original reports by path and SHA-256. The projects above carry runnable source. Other report entries point back into the original workspace.

## Build and reproduce

Use Linux, Python 3.11+, NumPy, GNU Make, a C/C++20 toolchain, GMP C++ development headers, and the Zstandard CLI. The shell commands throughout this directory start at the repository root. The smaller experiments in the top-level index have their own requirements.

```sh
make -C research -j2
python3 research/test.py
make -C research/statico -j2 test
mkdir -p runs
python3 research/hierarchical-gf2/benchmark.py runs/full-gf2
```

For the full measurements, set these paths once in your shell. The defaults below refer to the original workspace layout. Each benchmark page names its input files. The repository contains the small GFH1 fixtures, the archived 33-byte whiteboard record, the 28,037-byte fax archive and the Statico test sample. Supply the larger corpus and Q to repeat the corresponding runs.

```sh
export CORPUS=../corpus
export Q=../lab/hutter/divisors/work/cofattore-Q.base256
```

Q is the canonical big-endian base-256 cofactor used by the factor experiments. Its SHA-256 is `5f7921346a0b045f6196be84b1c794344455a47eaf84bf9ef81b8707559ca547`. The original enwik8 text, Q, and the Neif archive are three different inputs. A result on one says little about the others.

Archive sizes include the fields each format needs to recover the input with the specified decoder and profile. The decoder executable is shared. The reported sizes exclude delivering it. The corpus comparisons use Zstandard level 3 on stdin and Python's XZ container with LZMA preset 9 extreme where those baselines appear. Timings are single wall-clock observations. Statico's historical XZ references and CM3's original full-file measurement are identified separately on their project pages.
