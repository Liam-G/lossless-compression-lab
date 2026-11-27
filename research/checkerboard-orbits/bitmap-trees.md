# When does a cellular automaton help a bitmap tree?

A reversible preprocessor for packed monochrome images can discard empty quadrants, store the remaining 8 × 8 tiles, and let a standard compressor handle the result. On four technical manuals, XORing each scanline with the preceding one before building the tree saved **32.66–38.90% with Zstandard**. Reversing the lab’s checkerboard automaton was most effective on a different kind of input, where there really was an evolved field of repeating tiles underneath the pixels. [All paired results](../large-scale/results/preprocessing.md)

## Where the experiment came from

The original `lab/shapes2/shape_before_known.py` tried reading the Canterbury fax by columns and subtracting the row above before ordinary compression. The historical `scacchiera.cpp` evolved 8 × 8 toroidal words by updating alternating cell colors. Thesis 7 proposed comparing images with matrices evolved by the matching rule and a different rule. This experiment combines those questions on document-wide strips, using empty space and repeated leaf patterns as the structure to recover. The spatial tree follows the principle of a k²-tree, where a zero occupancy bit skips an entire square. We stop at 8 × 8 leaves and serialize the result for off-the-shelf compressors. [Original experiment atlas](../evidence/idea-atlas.md) · [Original checkerboard implementation](orbit.cpp) · [Brisaboa, Ladra and Navarro, *k²-trees for Compact Web Graph Representation*](https://users.dcc.uchile.cl/~gnavarro/ps/spire09.1.pdf)

## What each transform does

A strip holds at most 256 rows of 1,728 bits. The graph and library inputs use all rendered pages of their respective Graphviz manuals. The NASM and Valgrind inputs use the first 64 pages each. All four are complete, packed monochrome raster files of at least 20 MiB. Known width is part of the fixed codec format. Strips restart at fixed byte offsets, independently of page boundaries. [Document manifest and renderer inputs](../large-scale/documents.json)

| Stage | Profiles and decoder information |
|---|---|
| Predictor | `direct` keeps the packed pixels. `xor` records each scanline XOR the preceding scanline. `orbit` reverses one two-phase checkerboard step over the full strip. Its flip bit is (left AND right) XOR (above OR below). Each phase reads only the opposite color. Edges see zero. `rotated` exchanges the horizontal and vertical operators. |
| Empty quadrants | `flat` writes packed rows. `tree` writes one occupancy bit per 32 × 32 square, then four child bits per occupied square at each of two levels. The decoder scatters the occupied 8 × 8 leaves into their raster positions. Each leaf is eight bytes. |
| Leaf representation | `book` lists every distinct occupied tile in the strip and emits one- or two-byte indices. `hot` keeps at most 255 repeated tiles, sends a single-byte tag per occupied tile, and writes literal escapes in their own stream. `planes` transposes the eight row bytes of all occupied leaves. `hotplanes` applies that transposition separately to dictionary entries and escapes. |
| Selection and framing | `select` chooses the shortest Zstandard-3 candidate per strip among the original nine combinations of direct, XOR or orbit with flat, tree or book. The other fixed variants were measured separately. CBP1 carries the original length and a mode and payload length per strip. The final strip is zero-padded to a 32-row boundary and trimmed during decoding. |

We ran 76 paired trials on eight inputs ranging from 24,283,584 to 31,809,024 raw bytes. We measure the entire CBP1 stream before compression, including occupancy maps, indices, literals and dictionaries. Direct gzip 6, Zstandard 3 and XZ 6 use exactly the same settings as their corresponding prepared runs. Each comparison verifies the inverse and both backend paths. The native CBZ1 archive has its own separately measured whole-stream Zstandard wrapper. [Implementation](bitmap.py) · [Commands, sizes and hashes](../large-scale/results/preprocessing.jsonl)

## The real documents

Positive percentages mean the archive became smaller relative to the same compressor on the original bytes. H0 and H1 are measured in bits per byte of the stream being described. The normalized column multiplies prepared H0 by prepared length divided by original length.

| Input, scanline XOR + tree | Original → prepared bytes | H0 before → after | H1 before → after | Prepared H0 per original byte | gzip 6 saved | Zstd 3 saved | XZ 6 saved |
|---|---:|---:|---:|---:|---:|---:|---:|
| Graphviz graph/layout guides | 24,642,792 → 2,904,414 | 0.765 → 3.702 | 0.529 → 2.981 | 0.436 | 32.20% | 33.34% | 38.97% |
| Graphviz library manual | 24,283,584 → 4,312,007 | 1.090 → 3.649 | 0.769 → 2.934 | 0.648 | 32.41% | 38.90% | 47.87% |
| NASM | 31,809,024 → 5,128,749 | 0.993 → 3.344 | 0.645 → 2.703 | 0.539 | 32.35% | 34.81% | 47.30% |
| Valgrind | 30,924,288 → 8,128,963 | 1.304 → 3.436 | 0.809 → 2.719 | 0.903 | 25.88% | 32.66% | 46.27% |

On the library manual, only 17.1% of tiles after scanline XOR contained any set bits. The tree described the empty space compactly, so 4,312,007 prepared bytes replaced 24,283,584 original bytes. Zstandard compressed the original to 1,903,362 bytes and the prepared stream to **1,162,886**. H0 rose on the shorter stream while its normalized cost fell to **0.648 bits per original byte**. Dedicated document codecs can do considerably better on these pages. The lab's glyph-and-position model used 160,297 bytes on this same raster. [Occupancy counts](../large-scale/results/bitmap-occupancy.jsonl) · [Glyph and DjVu comparisons](../glyph-residuals/README.md)

The more elaborate leaf encodings lost ground on real pages. On the Graphviz guides, a full dictionary after scanline XOR made the Zstandard archive **4.41% larger** than direct compression. Restricting the dictionary to frequent tiles saved **23.76%**, and writing occupied tiles literally saved **33.34%**. Merely transposing the eight bytes within the leaf stream kept the prepared size exactly **2,904,414 bytes**, yet Zstandard savings fell to **9.31%**. On Valgrind that transposition even lowered H1 from **2.719 to 2.305** while Zstandard savings fell from **32.66% to 2.92%**. [Exact per-profile comparisons](../large-scale/results/preprocessing.md)

Shuffling the Graphviz guides by whole scanlines preserves every original line and the entire byte histogram. Occupied tiles in the raw grid rose from **11.4% to 37.7%**. Scanline XOR plus the tree, which saved **33.34%** with Zstandard on the original, made the shuffled archive **88.84% larger**. The selector chose the direct flat representation on every shuffled strip. On a separate 24 MiB uniform byte stream, all tiles contained set bits and the full dictionary grew the Zstandard archive by 23.59%. [Input hashes and generator settings](../large-scale/synthetic.json) · [Block choices](../large-scale/results/archives.jsonl)

## A matched and mismatched automaton

The generator places 32 randomly drawn stamps independently at active tile positions, with one position in eight active on average. Coordinates and IDs are regenerated throughout all 512 strips. Two 27 MiB inputs use those **same latent pixels**. One evolves the original checkerboard rule, the other its rotated rule. Each fixed decoder knows its rule through the stored mode. Both matching inverses recovered the identical latent raster, SHA-256 `e7af021f4086b461d9c2a728bd580072823872864878a803a9cbf63fecdf9eff`. [Control generator](bitmap_controls.py)

| Input | Direct Zstd 3 | Tree + full leaf dictionary | Original inverse + tree + dictionary | Rotated inverse + tree + dictionary |
|---|---:|---:|---:|---:|
| evolved-stamps | 9,210,659 | 2,654,150 (71.18% saved) | 622,700 (93.24% saved) | 5,366,106 (41.74% saved) |
| rotated-stamps | 7,867,492 | 2,244,509 (71.47% saved) | 5,441,366 (30.84% saved) | 622,584 (92.09% saved) |

Reversing the matching rule on the original-rule field restored the 32-symbol stamp vocabulary and reduced occupied tiles from 32.4% to 12.5%. Applying the same inverse to real Graphviz guide pages increased occupancy from 11.4% to 13.3%. A local rule can uncover a cheap representation when the data follows that rule. The two controlled fields share their underlying stamps and count as a paired intervention. [Per-input occupancy and dictionary counts](../large-scale/results/bitmap-occupancy.jsonl)

## Reproduce it

Run from the repository root with Python, NumPy, python-zstandard and the gzip, zstd and xz executables. The generator uses NumPy PCG64 with seed 771037. Use a fresh destination for each command. For the manuals, follow the existing document raster preparation instructions. [Corpus preparation](../large-scale/README.md#inputs)

```sh
mkdir -p runs/bitmap-replay
python3 research/checkerboard-orbits/bitmap_controls.py runs/bitmap-replay/evolved-stamps
python3 research/checkerboard-orbits/bitmap_controls.py runs/bitmap-replay/rotated-stamps --rotated
python3 research/checkerboard-orbits/bitmap_controls.py runs/bitmap-replay/graphs-shuffled-lines --shuffle-rows runs/large/raw/manual-graphs
python3 research/large-scale/entropy_bench.py checker-bitmap-orbit-book runs/bitmap-replay/evolved-stamps runs/bitmap-replay/stamps.json
python3 research/large-scale/entropy_bench.py checker-bitmap-xor-tree runs/large/raw/manual-library runs/bitmap-replay/library.json
python3 research/checkerboard-orbits/bitmap.py inspect runs/large/raw/manual-library runs/bitmap-replay/library-occupancy.json
```
