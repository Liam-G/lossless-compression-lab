# Repeated glyphs and an exact bitmap residual

## Question and prior work

Can the lab's idea of storing a reusable shape plus a correction work on an entire technical manual? The raster-context prototype in `lab/shape` predicted each pixel. This extension finds connected components, reuses their bitmaps at different positions and tests whether the remaining pixels still benefit from a fax coder. Lossless DjVu provides a mature symbol-coding comparison.

## Run the experiment

```sh
python3 research/glyph-residuals/codec.py encode runs/large/raw/manual-library runs/manual.glr --profile position
python3 research/glyph-residuals/codec.py decode runs/manual.glr runs/manual.raw
cmp runs/large/raw/manual-library runs/manual.raw
```

## Variants and format

GLR1 counts 8-connected components in 512-row strips. It takes at most 4,096 repeated bitmaps. A position can use an exact shape or a nearby shape with the same dimensions. The encoder XORs every placement out of the source and codes the residual using Zstandard or JBIG. Applying the same placements to the residual restores every pixel, including boundaries, drawings and any correction to an approximate match.

The original position stream sorts placements by their top or bottom, then codes glyph IDs, row steps and signed horizontal gaps. The `position` profile also estimates a baseline offset for each shape, groups events by inferred text line, and tests causal predictors for the next symbol and character spacing. It charges the dictionary, baseline offsets, choices, positions, and residual. Dimensions and all stream lengths are in the archive. The bitmap uses MSB-first, black-one rows and accepts widths divisible by eight.

## Inputs and measurement

Two complete Graphviz manual sets supplied the first comparison. Two different books supplied the first 64 NASM and Valgrind pages. The Valgrind pages were reserved when the new position model was introduced. All four rasters exceed 20 MiB. DjVuLibre's lossless `cjb2` was measured with 8,192- and 32,760-row strips, bundled with `djvm`. A third reference uses foreground RLE and bundled `csepdjvu`. Each DjVu decoder recreated the same pixels for `cmp`.

## Results

| Raster | Raw bytes | Glyphs + JBIG | Learned positions | DjVu, 32,760 rows |
|---|---:|---:|---:|---:|
| Graphviz graph/layout guides | 24,642,792 | 211,517 | 189,603 | 191,132 |
| Graphviz library manual | 24,283,584 | 196,530 | 160,297 | 175,164 |
| NASM | 31,809,024 | 225,552 | 195,223 | 189,610 |
| Valgrind | 30,924,288 | 435,746 | 394,104 | 828,622 |

Learning positions saved bytes on all four inputs. The wider-strip DjVu archive remained 5,613 bytes smaller on NASM. These are digitally typeset PDFs rendered to monochrome. Performance on scanned or degraded paper is a separate question. [Individual archives, timing and hashes](../large-scale/results/by-dataset.md#manual-graphs)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#glyph-residuals) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

[Raster shape contexts](../shape-context/README.md) · [Shared recipe dictionaries](../shared-factor-forest/README.md) · [Document inputs](../large-scale/documents.json)
