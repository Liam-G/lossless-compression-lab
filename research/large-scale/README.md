# Large-file compression benchmarks

Every published row contains **at least 20 MiB (20,971,520 raw bytes)**. The runner encodes the whole named input, launches a separate decoder and compares every reconstructed byte with the source using `cmp`. It records the complete archive size and SHA-256 only after that comparison succeeds. The [full results by dataset](results/by-dataset.md) give archive sizes, reference charges, rates and timings. The [index by experiment](results/by-experiment.md) groups the same observations by implementation. The [JSONL receipts](results/archives.jsonl) also identify the archive, source, configuration, and recorded selections.

## What worked, and on which data

| Question | Complete raw input | Measured result |
|---|---:|---|
| Can the original whiteboard equations compress their **recorded witnesses**? | 22,630,320 bytes from the original N=26 run | Column coding gave 2,306,827 bytes, arithmetic regeneration alone 1,600,689, and the combination **1,082,142**. [Census and records](../whiteboard-census/README.md) |
| Can the 2019 formula be useful **inside a factor tree**? | 25,165,824 generated product bytes | Factor-only and formula-only each gave 14,336,766 bytes. Nested inline formulas gave 13,286,101. Sharing recipes gave **13,097,327**, below XZ extreme at 13,309,788. The shared recipes gave no additional saving on the real numerical stream. [Experiment](../shared-factor-forest/README.md) |
| Does a **3D automaton expose matrix rank**? | 25,165,824 generated volume bytes | Rank alone gave 24,837,235, orbit alone 20,763,341, and their combination **9,632,435**. On 25,696,748 real numerical bytes, combining the two saved 153 bytes over rank alone. [Experiment](../tensor-orbits/README.md) |
| What if the matrix is noisy and has **four axes**? | 25,165,824 generated space-time bytes | Orbit alone gave 19,601,212 bytes. Reversing the orbit and storing two binary factors plus the exact error gave **9,414,787**. The factor stage added no gain on Samba or the real numerical stream. [Experiment](../four-dimensional-factors/README.md) |
| Can a reversible **byte-valued orbit hide a Kronecker product**? | 25,165,824 generated panel bytes | Orbit alone gave 24,560,134 bytes. Two 4 × 4 factors plus corrections after orbit reversal gave **4,471,016**. All four fixed-pivot profiles tied on the real numerical corpus. [Experiment](../modular-kronecker/README.md) |
| Can the cellular rule and its residual matrix be **learned together**? | 29,491,200 generated video bytes | Fitting them sequentially gave 25,054,265 bytes. Joint fitting gave **11,051,733**. A second random seed reproduced the gain. Shifting error planes independently reduced it to one byte. On three real clips the two configurations tied. [Experiment](../learned-cellular-rules/README.md) |
| Can the encoder amortize **1,000-step searches**? | 25,165,824 generated orbit bytes | Storing a time per matrix gave 13,612,025 bytes. Sharing a time across a page gave **12,415,836**. Natural numerical bytes and uniform noise kept the direct representation. [Experiment](../checkerboard-orbits/README.md) |
| Does a grid reveal structure in **ordinary numerical data**? | 25,696,748 real Silesia bytes | Prediction plus separated integer planes and XZ gave **10,421,725** bytes. XZ extreme on the original stream gave 11,662,476. The matched blocked XZ control gave 11,846,741. [Experiment](../lattice-prediction/README.md) |
| Can a decoder infer **distance geometry**? | 21,155,400 derived geographic bytes | Four landmark columns and exact residuals gave **3,850,014** bytes on quantized chord distances, against 16,711,344 for XZ extreme. Mapping great-circle angles to chord bins before prediction gave **4,242,861** on the angular table. A matched random triangle selected literal storage. [Experiment](../distance-geometry/README.md) |
| Does a generic formula shorten **canonical Q**? | 96,994,187 original cofactor bytes | Sparse-prefix plus modular-square coding saved **136 bytes**. A sparse region search including the historically identified global multiplier 12 saved **3,772 bytes**. The new informed package saved **1,684 bytes including its decoder**. The earlier file-specific V15 package saved 73,220 bytes including its decoders. [Package comparison](../portable-arithmetic/README.md) [Integer formulas](../integer-formulas/README.md) · [Scale and split](../carry-trees/README.md) · [Portable replay](../evidence/portable-q-v15.json) |
| Does the old **fax** result transfer to other documents? | 24,642,792 and 24,283,584 raw rendered bytes | Learned glyph placements with exact residuals gave **189,603** and **160,297** bytes. Wide-strip DjVu gave 191,132 and 175,164. On NASM the same DjVu configuration won by 5,613 bytes. On Valgrind the glyph archive used 394,104 bytes versus 828,622. [Glyph experiment](../glyph-residuals/README.md) [Document rows](results/by-dataset.md#manual-graphs) |
| Does a **reference** remove the whole payload? | 96,994,187 cofactor bytes | The exact matching numerator permits a 46-byte authenticated arithmetic descriptor. Delivering its 96,994,188-byte reference as well costs **96,994,234**. Another FX2 release failed to give that relation. [Experiment](../arithmetic-references/README.md) |

For each comparison, the size includes selectors, headers, lengths, literal escapes, seeds, parameters, dictionaries and residuals stored by that codec. The standard rows assume the specified decoder and libraries are installed. The reference total charges uncompressed delivery of any additional data required at the receiver. Encoding may inspect an optional reference and still choose a stream that decodes without it. CM3 needs the profile in the receipt and compatible floating-point behavior at both ends.

## Inputs

| Source | How the raw bytes were defined |
|---|---|
| Silesia and Wikipedia | Four complete Silesia members, plus mr + x-ray + sao concatenated in that order. Two disjoint 24 MiB enwik8 slices start at 0 and 67,108,864. Full enwik8 and enwik9 use their original 100,000,000 and 1,000,000,000 bytes. [Member paths, offsets and hashes](datasets.json) |
| Whiteboard census | Complete archived N=24 cost tables and N=26 arithmetic witness records, a shuffled control, and a newly enumerated N=28 target restricted to non-unit denominators. [Source members](whiteboard.json) |
| Historical compression artifacts | Canonical FX2-Q, its decimal digits plus newline, the Neif ELF, and the two distinct FX2 numerator/archive references live in the original workspace. The expanded affine-pair stream and formula listing are the first complete 24 MiB of their specified representations. The original compact tape consumed just 6,291,456 bytes for the same affine instructions. [Project data](project-data.json) |
| Generated controls | Fresh random words or matrices are written throughout. There is no repeated tiny fixture used to meet the size floor. Run the original generators with the supplied seeds for the [factor and volume controls](controls.json), mapped text, shared clock, noisy four-axis field, and three-generator sums. [Additional seeds, raw hashes and source programs](synthetic.json) |
| Document rasters | Graphviz dotguide + neatoguide (51 distinct pages) and libguide (46 pages), plus the first 64 pages of the independent NASM and Valgrind manuals, rendered as 1,728-bit-wide monochrome rows. Page pixels are concatenated in order, with black represented by 1. The source PDF hashes and page heights are recorded. [Document manifests](documents.json) |
| Images and video | Three local wallpaper images were decoded to canonical 8-bit P6 RGB. Three independent clips yielded 128 grayscale frames each at 640×360. Reference algorithms restore these canonical rasters. Audio, the original image metadata and compressed video bitstreams are outside the raw target. [Images](images.json) · [Video](videos.json) |
| Triangular distance tables | Real enwik9 coordinates supply chord and angular distances for 4,600 distinct sites. A planar walk and equal-size uniform triangle provide two controls. Every table uses 21,155,400 bytes of little-endian uint16 distances. [Distances](distances.json) |
| Software package updates | Entire decompressed tar streams from two successive NumPy versions and two Mesa versions. Their packaged and raw reference hashes distinguish the revisions. [Package manifest](packages.json) |

Independent files and derived views can share input material. The per-dataset table gives each denominator individually. For example, the two enwik8 slices are disjoint from each other and both occur inside full enwik8. The two geographic tables describe the same points under different metrics.

## Reproduce a result

Run from the repository root on Linux using Python 3.11+, NumPy, python-zstandard, a C/C++20 compiler, GNU Make, GMP development headers, and the Zstandard and XZ CLIs. For the optional whole-integer formulas use gmpy2, and set `GMP_PYTHON` when it lives in another interpreter. Image, video and document rows additionally use Pillow, Poppler, FFmpeg, JBIG-KIT, DjVuLibre, Netpbm or JPEG XL according to method; glyph extraction uses SciPy. After installing the dependencies, the repository operates on local data.

```sh
make -C research -j2
make -C research/statico -j2
python3 research/large-scale/test.py
python3 research/large-scale/datasets.py ../corpus runs/large/raw
python3 research/large-scale/replay.py numerical runs/replay-numerical lattice-joint-xz
```

To reproduce a planted cellular-rule benchmark from a clean checkout using the included generator, run the following once in a fresh raw-data directory. The command compares the archive hash with the published result and measures a Zstandard control on the same field.

```sh
make -C research -j2
mkdir -p runs/ca-input
python3 research/learned-cellular-rules/control.py runs/ca-input/learned-field
python3 suite.py benchmark runs/ca-replay --project learned-cellular-rules --raw runs/ca-input
```

The top-level benchmark commands select a measured experiment and run its same-input Zstandard control. The default full suite covers all project folders. Use `--list` to inspect the selection, `--group experiments` for the sixteen theses, or `--project` for one folder. The original fixture-size comparisons are accessible under `suite.py diagnostics`. The optional input audit hashes the external workspace and all prepared files.

```sh
python3 suite.py benchmark --list
python3 lab.py 07 benchmark runs/replay-07
python3 suite.py benchmark runs/own-glyph --project glyph-residuals --input runs/large/raw/manual-library --codec glyph-position
python3 research/large-scale/audit.py --raw runs/large/raw --workspace ..
```

To run a measurement on a different file, provide a fresh receipt path and one or more profiles. Each trial uses a temporary directory for the archive and reconstruction. `runs/` is ignored by Git.

```sh
python3 research/large-scale/bench.py runs/large/raw/numerical runs/my-grid.jsonl lattice-direct lattice-layout lattice-predict lattice-joint zstd3 xz9e
python3 research/large-scale/report.py runs/large/measurements runs/my-tables
```

To regenerate the remaining groups, run the applicable commands below against a fresh output directory, or against the same directory after making the basic corpus files. The scripts create new output files. The replay tool verifies each raw hash before encoding and checks the resulting archive hash.

```sh
python3 research/large-scale/controls.py runs/large/raw
python3 research/modular-kronecker/control.py runs/large/raw/modular-panels
python3 research/modular-kronecker/control.py runs/large/raw/modular-transfer --seed 832181
python3 research/modular-kronecker/control.py runs/large/raw/modular-free --seed 688271 --free-pivot
python3 research/large-scale/project_data.py .. runs/large/raw
python3 research/checkerboard-orbits/control.py runs/large/raw/shared-orbit-1000
python3 research/carry-trees/control.py runs/large/raw/wiki-dev runs/large/raw/mapped-text
python3 research/four-dimensional-factors/control.py runs/large/raw/noisy-spacetime
python3 research/generator-sums/control.py runs/large/raw/three-seeds
python3 research/distance-geometry/data.py ../corpus/enwik9/enwik9 runs/large/raw
python3 research/large-scale/document_data.py /usr/share/doc/graphviz runs/large/raw
python3 research/large-scale/document_data.py /usr/share/doc/graphviz runs/large/raw --transfer /usr/share/doc/nasm/nasmdoc.pdf
python3 research/large-scale/document_data.py /usr/share/doc/graphviz runs/large/raw --transfer /usr/share/doc/valgrind/valgrind_manual.pdf --name manual-valgrind
python3 research/learned-cellular-rules/control.py runs/large/raw/learned-field
python3 research/learned-cellular-rules/control.py runs/large/raw/field-transfer --seed 144211
python3 research/learned-cellular-rules/control.py runs/large/raw/field-independent --kind independent
python3 research/learned-cellular-rules/control.py runs/large/raw/field-uniform --kind uniform
python3 research/whiteboard-census/data.py .. runs/large/raw
python3 research/whiteboard-census/control.py runs/large/raw/whiteboard-witnesses runs/large/raw/shuffled-witnesses
python3 research/large-scale/image_data.py /usr/share/hypr runs/large/raw
python3 research/large-scale/video_data.py /usr/share/sddm/themes runs/large/raw
python3 research/large-scale/package_data.py /var/cache/pacman/pkg runs/large/raw
```

The replay tool also accepts `--raw DIR`, `--workspace DIR` and `--reference-name NAME`. Omitting the profile list replays all published profiles on that dataset. Generated arithmetic and automaton controls can be reproduced without the source corpus. Distribution-provided artwork, packages, corpus members and large historical binaries must match the hashes in the manifests.

## Measurement details

- A pilot run is one LCP1 archive containing ordered 32 KiB records processed by the original experiment codec. The collection pays for its own header, each 4-byte record length and each complete inner archive. The model restarts at each record. The large native codecs use their own block sizes or process a whole file.
- Zstandard CLI baselines use one thread and a regular input file at level 3 or 19. XZ extreme uses preset 9e and a single thread. Transform comparisons keep their internal coder and framing fixed for the ablation. Whole-file baselines can exploit longer histories.
- Times include process startup and temporary-file I/O; the final byte comparison and hashing are outside the two timings. They are single observations. Other trials ran concurrently, so sizes and reproducibility are more reliable comparisons here than speed rankings. Later receipts include peak resident KiB from Linux child-process accounting. Earlier rows omit the field.
- Natural corpora, generated controls, derived mathematical data and externally conditioned patches answer different questions. See the [idea atlas](../evidence/idea-atlas.md) and [149 historical reports](../evidence/report-index.tsv) for earlier results and incomplete proposals.

The reference machine used an Intel Core Ultra 7 165U, x86-64 Linux, GCC 16.2.1, Python 3.14.10, NumPy 2.4.2, SciPy 1.17.1, Pillow 12.1.1 and python-zstandard 0.25.0. External programs included Zstandard 1.5.7, XZ 5.8.4, FFmpeg 9.1, Poppler 26.11.0, DjVuLibre 3.5.30 and JPEG XL 0.13.0. Byte-identical archive replay can depend on these versions. C3P1 also records the hash of the CM3 executable.

Portable application rows include their shipped decoders in the archive size. The 15-byte WCT1 cost-table calculation and the 48-byte WRT1 witness calculation assume matching enumerators are installed. The 6,068-byte source package pays for the witness extractor and the enumerator and needs a compatible toolchain and GMP. Experiment 02 retains the original per-word CPU-time search limit, so a different processor can choose a different correct factor record.
