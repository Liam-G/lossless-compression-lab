# Raster shape search with an actual range-coded archive

## Question and prior work

The old search in `lab/shapes2/shapesearch.py` found a 1,729-bit row and a useful neighborhood on the Canterbury fax. Its 29,745-byte result was an estimated description and sequential code length. SCX1 uses this observation, encodes the bits with the original Statico range coder, and decodes them from the archive alone.

## Run the experiment

The [28,037-byte archive](results/ptt5.scx) is included. With the native engine built, the following command restores the complete fax without a corpus checkout.

```sh
mkdir -p runs
research/build/shape decode research/shape-context/results/ptt5.scx runs/canterbury-fax.bin
```

```sh
mkdir -p runs
research/build/shape encode "$CORPUS/canterbury/ptt5" runs/fax.scx
research/build/shape decode runs/fax.scx runs/fax.restored
cmp "$CORPUS/canterbury/ptt5" runs/fax.restored
python3 research/shape-context/benchmark.py "$CORPUS" runs/raster
python3 research/shape-context/fax_baselines.py "$CORPUS/canterbury/ptt5" runs/fax-containers.csv
python3 research/shape-context/benchmark.py /usr/share/kbd/consolefonts runs/font-check --fonts
```

## Variants and format

The history baseline sees the previous two bits. The original stencil uses the previous bit, two neighbors above and to the right, and the bit directly above two rows back. The larger stencil uses two preceding bits, five neighbors in the previous row, and one two rows back. Both sides traverse the input MSB-first, initialize each context with one count for each outcome, and update and periodically halve the counts identically.

The encoder tries widths 1,728 and 1,729 and up to three additional widths selected by sample conditional entropy from widths up to 2,048. It writes the smallest actual payload among these models, the history baseline and literal bytes. Its 15-byte header records magic, length, row width and model. A selected width is a predictor parameter and can span a record or part of a row.

## Inputs, results and interpretation

| Input | History only | Shape search | Zstandard 3 | XZ extreme |
|---|---:|---:|---:|---:|
| Canterbury ptt5, 513,216 bytes | 61,788 | **28,037** | 54,421 | 39,860 |
| Rule 30 at width 257, 65,792 bytes | 16,942 | **156** | 12,565 | 12,020 |
| Canterbury kennedy.xls, 1,029,744 bytes | 625,246 | 95,150 | 111,828 | **51,868** |
| enwik8, first MiB | 1,025,100 | 873,471 | 364,070 | **302,792** |

On the fax the eight-tap model chose width 1,729. Its complete archive is 11,823 bytes smaller than XZ on this file. The fax informed the design. On the Rule 30 control the width selector recovered 257. The random control selected literal bytes. [Archive rows and hashes](results/trials.csv)

For a fax-specific comparison, Pillow encoded the same bits as a 1,728 × 2,376 monochrome image. A CCITT Group 4 TIFF with a single white-is-zero strip used 32,344 bytes, a default Group 4 TIFF used 33,316, and a 1-bit PNG used 53,277. All decoded to the original packed bytes. SCX1 saved 4,307 bytes over the smaller TIFF. Its selected 1,729-bit predictor stride differs from the actual image width by one bit. Pillow with libtiff support is optional and used only by this baseline script. [Image-container results](results/fax-containers.csv)

After fixing the codec, a separate check took every matching gzip-compressed PSF font in the local Linux console-font directory, decompressed each in full and eliminated byte-identical duplicates by SHA-256. The 134 distinct files include headers, glyphs and Unicode tables. Each file was encoded and decoded separately. Combined input was 748,915 bytes. Summed archive sizes were 362,124 with SCX1, 324,801 with Zstandard and 267,744 with XZ. SCX1 beat Zstandard on five fonts and XZ on zero. The fax result does not generalize across this collection. [Font-by-font results](results/fonts/trials.csv)

## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#shape-context) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.
