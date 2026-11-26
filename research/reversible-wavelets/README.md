# Integer lifting and color differences

## Question and prior work

Does a reversible 2D wavelet become more useful when it sees color-difference planes instead of red, green and blue?

### Source files and compatibility

This combines the signal and Walsh topics of the dossier with the integer row/plane hypothesis from `lab/shape/nested.py`. The implementation uses the reversible integer 5/3 lifting transform and a green-centered reversible color transform. RWL1 is a new archive.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/reversible-wavelets/codec.py encode runs/large/raw/wall2.ppm runs/image.rwl --profile joint
python3 research/reversible-wavelets/codec.py decode runs/image.rwl runs/image.restored.ppm
cmp runs/large/raw/wall2.ppm runs/image.restored.ppm
```

## Variants and format

Each tile can use direct, color-only, lifting-only or combined coding. The encoder tries one, two or three pyramid levels. Each subband retains signed coefficients using ZigZag mapping and low/high byte planes. Odd row and column counts reuse the nearest endpoint; the inverse reverses the predict/update steps. All variants use the same Zstandard backend.

## Inputs and measurement

The three original wallpaper PNGs were decoded to canonical 8-bit P6 RGB before benchmarking. Every method restores that complete canonical byte stream, including its header. Timings and sizes cover encoding the raster, rather than reproducing the source PNG container. Dedicated baselines include PNG, lossless WebP and lossless JPEG XL.

## Results

On wall2, 96,560,657 raw bytes, direct coding gave 37,922,336, color 37,365,473, lifting 32,521,660 and their combination 32,392,630. Lossless JPEG XL gave 21,138,142. On wall1 every wavelet profile chose the same 644,213-byte result. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#reversible-wavelets) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 09 uses Walsh terms and XOR. The [lattice](../lattice-prediction/README.md) discovers integer widths, while [motion residuals](../motion-residuals/README.md) add a previous frame.
